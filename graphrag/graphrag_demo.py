import os
import pandas as pd
from dotenv import load_dotenv
from llama_index.core import Document, PropertyGraphIndex
from llama_index.core.llms import LLM
from llama_index.core.llms import LLMMetadata
import openai

# 自定义 GraphRAG 组件
class GraphRAGExtractor:
    """
    GraphRAG 抽取器：使用 LLM 从文本中抽取三元组（实体-关系-实体）。
    """
    def __init__(self, llm):
        self.llm = llm
        
    def extract_triplets(self, text):
        """
        从文本中抽取主语-关系-宾语三元组。
        返回实体列表和关系列表。
        """
        prompt = f"""
        Extract key entities and their relationships from the following text.
        Format your response as a JSON with 'entities' and 'relationships' keys.
        
        For each entity, include:
        - 'entity_id': A unique identifier for the entity
        - 'entity_type': The type of entity (e.g., Person, Organization, Product)
        - 'entity_description': A brief description of the entity
        
        For each relationship, include:
        - 'source': The source entity ID
        - 'target': The target entity ID
        - 'relation': The type of relation
        - 'relationship_description': A description of the relationship
        
        YOUR RESPONSE MUST BE VALID JSON. Make sure to return only a JSON object with no additional text or explanation.
        
        TEXT: {text}
        """
        
        response = self.llm.complete(prompt)
        
        # 实际应用中应解析 LLM 返回的 JSON 并结构化数据
        try:
            import json
            import re
            
            # Try to extract JSON from the response if there's other text
            response_text = response.text.strip()
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text
                
            # Parse the JSON
            data = json.loads(json_str)
            
            # 解析实体
            entities = [
                {
                    "id": entity.get("entity_id", ""),
                    "type": entity.get("entity_type", "Entity"),
                    "description": entity.get("entity_description", "")
                }
                for entity in data.get("entities", [])
            ]
            
            # 解析关系
            relationships = [
                {
                    "source": relation.get("source", ""),
                    "target": relation.get("target", ""),
                    "relation": relation.get("relation", "Related"),
                    "description": relation.get("relationship_description", "")
                }
                for relation in data.get("relationships", [])
            ]
            
            return entities, relationships
        except Exception as e:
            print(f"Error parsing response: {e}")
            print(f"Response text: {response.text[:100]}...")
            return [], []


class GraphRAGStore:
    """
    简单的内存知识图谱存储。
    实际生产中可替换为 Neo4j 或其他图数据库。
    """
    def __init__(self):
        # 用字典存储实体，key 为实体 id
        self.entities = {}  # entity_id -> entity_data
        # 用列表存储所有关系
        self.relationships = []  # list of relationship dicts
        
    def add_entity(self, entity_id, entity_type, description):
        """
        向图谱中添加实体。
        """
        if entity_id not in self.entities:
            self.entities[entity_id] = {
                "id": entity_id,
                "type": entity_type,
                "description": description
            }
        
    def add_relationship(self, source_id, target_id, relation_type, description):
        """
        向图谱中添加关系。
        """
        self.relationships.append({
            "source": source_id,
            "target": target_id,
            "relation": relation_type,
            "description": description
        })
        
    def get_entities(self):
        """
        获取所有实体。
        """
        return list(self.entities.values())
    
    def get_relationships(self):
        """
        获取所有关系。
        """
        return self.relationships
    
    def build_communities(self):
        """
        社区发现（本 demo 仅打印提示，未做实际聚类）。
        """
        print("Building communities (demo version - no actual clustering)")


class GraphRAGQueryEngine:
    """
    简单的查询引擎。
    实际生产中可扩展为更复杂的图查询。
    """
    def __init__(self, graph_store, llm):
        self.graph_store = graph_store
        self.llm = llm
        
    def query(self, query_text):
        """
        基于知识图谱和用户问题生成上下文，调用 LLM 进行问答。
        """
        entities = self.graph_store.get_entities()
        relationships = self.graph_store.get_relationships()
        
        # 构建知识图谱上下文
        context = "Knowledge Graph Information:\n\n"
        
        context += "Entities:\n"
        for entity in entities:
            context += f"- {entity['id']} ({entity['type']}): {entity['description']}\n"
        
        context += "\nRelationships:\n"
        for rel in relationships:
            context += f"- {rel['source']} {rel['relation']} {rel['target']}: {rel['description']}\n"
        
        # 拼接最终 prompt，交给 LLM 回答
        prompt = f"""
        Use the following knowledge graph information to answer the user's question.
        
        {context}
        
        User Question: {query_text}
        
        Answer:
        """
        
        response = self.llm.complete(prompt)
        
        class Response:
            def __init__(self, text):
                self.response = text
        
        return Response(response.text)


class CustomLLM:
    """Custom LLM implementation for DeepSeek model"""
    
    def __init__(self, api_key, api_base, model):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        # Initialize OpenAI client
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )

    def complete(self, prompt, **kwargs):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        class Response:
            def __init__(self, text):
                self.text = text
        return Response(response.choices[0].message.content)


# 主演示函数
# 运行流程：加载环境变量 -> 初始化 LLM -> 构建知识图谱 -> 查询
def run_demo():
    # 加载 .env 文件中的环境变量
    load_dotenv()
    
    # 检查 OpenAI API Key 是否存在
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment variables or .env file")
        print("Please set your OpenAI API key before running this demo.")
        return
    
    # 初始化 OpenAI LLM
    llm = CustomLLM(
        api_key=os.getenv("OPENAI_API_KEY"),
        api_base=os.getenv("OPENAI_API_BASE"),
        model="deepseek-chat"
    )
    
    # 示例文档（实际应用可从文件或数据库加载）
    documents = [
        Document(text="Apple Inc. is a technology company founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976. "
                "The company is known for its iPhone products and is headquartered in Cupertino, California."),
        Document(text="Microsoft Corporation was founded by Bill Gates and Paul Allen in 1975. "
                "The company develops Windows operating system and Office software suite."),
        Document(text="Amazon was founded by Jeff Bezos in 1994 as an online bookstore. "
                "It has since expanded to sell various products and services including cloud computing through AWS.")
    ]
    
    print("Step 1: Initializing GraphRAG components...")
    extractor = GraphRAGExtractor(llm)
    graph_store = GraphRAGStore()
    
    print("\nStep 2: Processing documents and extracting knowledge...")
    # 处理每个文档，抽取知识
    for doc in documents:
        print(f"Processing document: {doc.text[:50]}...")
        entities, relationships = extractor.extract_triplets(doc.text)
        
        # 添加实体到图谱
        for entity in entities:
            graph_store.add_entity(
                entity_id=entity["id"], 
                entity_type=entity["type"], 
                description=entity["description"]
            )
        
        # 添加关系到图谱
        for rel in relationships:
            graph_store.add_relationship(
                source_id=rel["source"], 
                target_id=rel["target"], 
                relation_type=rel["relation"], 
                description=rel["description"]
            )
    
    print("\nStep 3: Building communities (simplified for demo)...")
    graph_store.build_communities()
    
    print("\nStep 4: Creating query engine...")
    query_engine = GraphRAGQueryEngine(graph_store, llm)
    
    print("\nStep 5: Ready to answer queries!")
    print("Knowledge graph contains:")
    print(f"- {len(graph_store.get_entities())} entities")
    print(f"- {len(graph_store.get_relationships())} relationships")
    
    print("\nExample queries:")
    queries = [
        "What companies are mentioned in the documents?",
        "Who founded Apple?",
        "What is the relationship between Jeff Bezos and Amazon?"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        response = query_engine.query(query)
        print(f"Response: {response.response}")


if __name__ == "__main__":
    run_demo() 