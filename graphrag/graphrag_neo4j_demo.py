"""
GraphRAG with Neo4j Implementation

This module implements a GraphRAG (Graph Retrieval Augmented Generation) system
using Neo4j as the graph database backend.

Workflow:
1. Load documents
2. Convert documents to text nodes
3. Extract entities and relationships from text using LLM
4. Store the extracted knowledge graph in Neo4j
5. Query the knowledge graph using natural language

Based on LlamaIndex's GraphRAG approach:
https://docs.llamaindex.ai/en/stable/examples/cookbooks/GraphRAG_v1/
https://docs.llamaindex.ai/en/stable/examples/cookbooks/GraphRAG_v2/
"""

import os
import pandas as pd
from dotenv import load_dotenv
from llama_index.core import PropertyGraphIndex
from llama_index.core import Document
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
import openai
from neo4j import GraphDatabase

# 自定义 LLM 实现
class CustomLLM:
    """Custom LLM implementation for DeepSeek model"""
    
    def __init__(self, api_key, api_base, model):
        self.api_key = api_key
        # 确保 api_base 格式正确
        if not api_base.endswith("/v1"):
            if api_base.endswith("/"):
                api_base = api_base + "v1"
            else:
                api_base = api_base + "/v1"
        self.api_base = api_base
        self.model = model
        # Initialize OpenAI client
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
        print(f"Initialized CustomLLM with base_url: {self.api_base}")

    def complete(self, prompt, **kwargs):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            class Response:
                def __init__(self, text):
                    self.text = text
            return Response(response.choices[0].message.content)
        except Exception as e:
            print(f"API 调用错误: {e}")
            # 返回一个空响应而不是抛出异常，以便演示能继续
            class Response:
                def __init__(self, text):
                    self.text = f"{{\"entities\": [], \"relationships\": []}}"
            return Response()

# Neo4j 版本的 GraphRAG 抽取器
class GraphRAGExtractor:
    """
    GraphRAG 抽取器：使用 LLM 从文本中抽取三元组（实体-关系-实体），适配 Neo4j。
    """
    def __init__(self, llm):
        self.llm = llm
    
    async def acall(self, *args, **kwargs):
        """
        异步调用，对于我们的简单实现，直接调用同步方法。
        对于实际生产环境，应该实现真正的异步处理。
        """
        return self.extract(*args, **kwargs)
    
    def extract(self, nodes, show_progress=False, **kwargs):
        """
        从节点列表中抽取实体和关系。
        返回 EntityNode 和 Relation 的列表。
        
        参数:
            nodes: 要处理的节点列表
            show_progress: 是否显示进度，兼容PropertyGraphIndex的调用
            **kwargs: 其他可能的参数
        """
        all_entities = []
        all_relationships = []
        
        # 输出调试信息
        print(f"Extract method called with {len(nodes)} nodes")
        print(f"Node types: {[type(node).__name__ for node in nodes]}")
        
        # 检查nodes是否是列表
        if not isinstance(nodes, list):
            print(f"WARNING: nodes is not a list but a {type(nodes)}")
            # 尝试转换为列表
            nodes = list(nodes)
        
        for i, node in enumerate(nodes):
            print(f"Processing node {i} of type {type(node).__name__}")
            # 确保我们可以访问节点的node_id和text
            try:
                node_id = getattr(node, "node_id", None) or str(i)
                node_text = getattr(node, "text", None)
                if node_text is None and hasattr(node, "get_content"):
                    node_text = node.get_content()
                
                if node_text is None:
                    print(f"WARNING: Node {i} has no text attribute")
                    # 尝试其他可能的属性
                    for attr in ["content", "get_text", "__str__"]:
                        if hasattr(node, attr):
                            if callable(getattr(node, attr)):
                                node_text = getattr(node, attr)()
                            else:
                                node_text = getattr(node, attr)
                            print(f"Found text in {attr}: {node_text[:50]}...")
                            break
                    
                    if node_text is None:
                        print(f"SKIPPING node {i} as no text could be found")
                        continue
                
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
                
                TEXT: {node_text}
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
                    
                    from llama_index.core.graph_stores.types import EntityNode, Relation
                    
                    # 构建实体节点
                    entities = [
                        EntityNode(
                            label=entity.get("entity_type", "Entity"),
                            properties={
                                "id": entity.get("entity_id", ""),
                                "entity_description": entity.get("entity_description", ""),
                                "triplet_source_id": node_id
                            },
                            name=entity.get("entity_id", "")
                        )
                        for entity in data.get("entities", [])
                    ]
                    
                    # 构建关系
                    relationships = [
                        Relation(
                            label=relation.get("relation", "Related"),
                            source_id=relation.get("source", ""),
                            target_id=relation.get("target", ""),
                            properties={
                                "relationship_description": relation.get("relationship_description", ""),
                                "triplet_source_id": node_id
                            }
                        )
                        for relation in data.get("relationships", [])
                    ]
                    
                    all_entities.extend(entities)
                    all_relationships.extend(relationships)
                    
                except Exception as e:
                    print(f"Error parsing response for node {i}: {e}")
                    print(f"Response text: {response.text[:100]}...")
            
            except Exception as e:
                print(f"Error processing node {i}: {e}")
        
        print(f"Extraction completed: {len(all_entities)} entities, {len(all_relationships)} relationships")
        return all_entities, all_relationships


class GraphRAGStore:
    """
    Neo4j 图数据库存储的包装类，提供 GraphRAG 相关接口。
    """
    def __init__(self, username, password, url):
        # 初始化 Neo4j 图存储
        self.graph_store = Neo4jPropertyGraphStore(
            username=username,
            password=password,
            url=url
        )
    
    def get_triplets(self):
        """
        获取所有三元组（关系映射）。
        """
        return self.graph_store.get_rel_map().items()
    
    def build_communities(self):
        """
        社区发现（本 demo 仅打印提示，未做实际聚类）。
        """
        print("Building communities... (Demo version - no actual clustering)")
        # 实际应用中可用社区发现算法并在 Neo4j 中创建社区节点


class GraphRAGQueryEngine:
    """
    基于 Neo4j 图存储的 GraphRAG 查询引擎。
    使用 Cypher 直接查询 Neo4j。
    """
    def __init__(self, graph_store, llm, index=None, similarity_top_k=5):
        self.graph_store = graph_store
        self.llm = llm
        self.index = index
        self.similarity_top_k = similarity_top_k
        
        # Neo4j连接信息
        self.uri = os.getenv("NEO4J_URL")
        self.username = os.getenv("NEO4J_USERNAME")
        self.password = os.getenv("NEO4J_PASSWORD")
    
    def query(self, query_text):
        """
        使用 Cypher 查询图谱，拼接上下文，调用 LLM 进行问答。
        """
        # 获取图谱数据作为上下文
        context = self._get_context_from_neo4j()
        
        # 拼接最终 prompt，交给 LLM 回答
        prompt = f"""
        Use the following knowledge graph information to answer the user's question.
        If the information is not in the knowledge graph, say that you don't know.
        
        {context}
        
        User Question: {query_text}
        
        Answer:
        """
        
        response = self.llm.complete(prompt)
        
        class Response:
            def __init__(self, text):
                self.response = text
        
        return Response(response.text)
    
    def _get_context_from_neo4j(self):
        """
        从 Neo4j 获取图谱数据作为上下文。
        """
        try:
            # 打开一个Neo4j会话
            driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            
            context = "Knowledge Graph Information:\n\n"
            
            with driver.session() as session:
                # 获取所有实体
                entities_result = session.run("""
                MATCH (entity) 
                RETURN entity.name as name, labels(entity) as labels, entity.description as description
                LIMIT 20
                """)
                
                for record in entities_result:
                    entity_name = record["name"]
                    entity_label = record["labels"][0] if record["labels"] else "Entity"
                    entity_desc = record["description"] or ""
                    context += f"- {entity_name} ({entity_label}): {entity_desc}\n"
                
                # 获取所有关系
                relations_result = session.run("""
                MATCH (source)-[rel]->(target)
                RETURN source.name as source, target.name as target, type(rel) as type, rel.description as description
                LIMIT 20
                """)
                
                for record in relations_result:
                    source = record["source"]
                    target = record["target"]
                    rel_type = record["type"]
                    rel_desc = record["description"] or ""
                    context += f"- {source} --{rel_type}--> {target}: {rel_desc}\n"
            
            driver.close()
            return context
        
        except Exception as e:
            print(f"Error querying Neo4j: {e}")
            return "Unable to retrieve knowledge graph information due to an error."


# 主演示函数
def run_neo4j_demo():
    """
    运行Neo4j GraphRAG演示
    
    流程:
    1. 加载环境变量和初始化LLM
    2. 创建示例文档
    3. 从文档中提取文本节点
    4. 使用LLM从文本中提取实体和关系
    5. 将实体和关系存储到Neo4j中
    6. 使用自然语言查询知识图谱
    """
    # 加载 .env 文件中的环境变量
    load_dotenv()
    
    # 检查 LLM API Key 是否存在 (使用与其他模块一致的变量名)
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    if not api_key:
        print("ERROR: LLM_API_KEY not found in environment variables or .env file")
        print("Please set your LLM API key before running this demo.")
        return
    
    # 检查 Neo4j 相关配置 
    neo4j_user = os.getenv("NEO4J_USERNAME")  
    neo4j_password = os.getenv("NEO4J_PASSWORD")  
    neo4j_url = os.getenv("NEO4J_URL")
    
    print(f"Using API Key: {api_key[:5]}...")
    print(f"Using API Base: {api_base}")
    print(f"Using Neo4j config: {neo4j_user}@{neo4j_url}")
    
    # 初始化自定义 LLM
    llm = CustomLLM(
        api_key=api_key,
        api_base=api_base,
        model="deepseek-chat"
    )
    
    # 示例文档
    documents = [
        Document(text="Apple Inc. is a technology company founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976. "
                "The company is known for its iPhone products and is headquartered in Cupertino, California."),
        Document(text="Microsoft Corporation was founded by Bill Gates and Paul Allen in 1975. "
                "The company develops Windows operating system and Office software suite."),
        Document(text="Amazon was founded by Jeff Bezos in 1994 as an online bookstore. "
                "It has since expanded to sell various products and services including cloud computing through AWS.")
    ]
    
    try:
        print("Step 1: Initializing Neo4j GraphRAG components...")
        extractor = GraphRAGExtractor(llm)
        
        # 不需要再次验证URL，因为已在前面处理
        try:
            graph_store = GraphRAGStore(
                username=neo4j_user,
                password=neo4j_password,
                url=neo4j_url
            )
            print("Neo4j连接成功!")
        except Exception as neo4j_error:
            print(f"Neo4j连接错误: {neo4j_error}")
            print("继续尝试处理，但可能会在后续步骤失败...")
            raise  # 由于图存储是必须的，这里还是需要终止执行
        
        print("\nStep 2: Creating nodes from documents...")
        # 按照 GraphRAG v1 文档，先创建节点/chunks
        from llama_index.core.node_parser import SentenceSplitter
        
        # 创建文本分割器
        splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
        
        # 从文档创建节点
        nodes = []
        for doc in documents:
            # 确保文档有metadata
            if not hasattr(doc, "metadata") or doc.metadata is None:
                doc.metadata = {}
            
            # 分割文档成节点
            doc_nodes = splitter.get_nodes_from_documents([doc])
            nodes.extend(doc_nodes)
        
        print(f"Created {len(nodes)} nodes from {len(documents)} documents")
        
        print("\nStep 3: Extracting entities and relations directly...")
        try:
            # 直接使用抽取器提取三元组
            entities, relations = extractor.extract(nodes)
            print(f"Extracted {len(entities)} entities and {len(relations)} relationships")
            
            # 直接加载到Neo4j
            print("Loading entities and relations into Neo4j...")
            
            # 获取Neo4j图存储
            neo4j_store = graph_store.graph_store
            
            # 使用更简单的方法 - 使用Neo4j客户端直接执行Cypher
            
            # 获取Neo4j连接信息
            uri = neo4j_url
            username = neo4j_user
            password = neo4j_password
            
            # 打开一个Neo4j会话
            driver = GraphDatabase.driver(uri, auth=(username, password))
            print("Connected to Neo4j directly")
            
            with driver.session() as session:
                # 清除现有数据
                session.run("MATCH (n) DETACH DELETE n")
                print("Cleared existing data")
                
                # 创建实体
                for entity in entities:
                    cypher = """
                    CREATE (e:`{label}` {{name: $name, description: $desc, id: $id}})
                    """.format(label=entity.label)
                    
                    session.run(cypher, {
                        "name": entity.name,
                        "desc": entity.properties.get("entity_description", ""),
                        "id": entity.properties.get("id", entity.name)
                    })
                    print(f"Added entity {entity.name} ({entity.label})")
                
                # 创建关系
                for relation in relations:
                    cypher = """
                    MATCH (source) WHERE source.name = $source_name
                    MATCH (target) WHERE target.name = $target_name
                    CREATE (source)-[r:`{label}` {{description: $desc}}]->(target)
                    """.format(label=relation.label)
                    
                    session.run(cypher, {
                        "source_name": relation.source_id,
                        "target_name": relation.target_id,
                        "desc": relation.properties.get("relationship_description", "")
                    })
                    print(f"Added relation {relation.source_id}--{relation.label}-->{relation.target_id}")
            
            driver.close()
            print("Neo4j connection closed")
            
            # 创建一个简单的自定义索引，不需要使用PropertyGraphIndex
            class SimpleGraphIndex:
                def __init__(self, graph_store):
                    self.property_graph_store = graph_store
            
            # 使用自定义索引
            index = SimpleGraphIndex(neo4j_store)
            print("实体和关系加载成功!")
            
        except Exception as extract_error:
            print(f"Error extracting or loading entities: {extract_error}")
            raise
        
        print("\nStep 4: Building communities...")
        graph_store.build_communities()
        
        print("\nStep 5: Creating query engine...")
        query_engine = GraphRAGQueryEngine(
            graph_store=None,  # 我们不再需要传递graph_store，因为我们直接连接Neo4j
            llm=llm,
            index=None,        # 我们不再需要index
            similarity_top_k=5
        )
        
        print("\nStep 6: Ready to answer queries!")
        
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
            
    except Exception as e:
        print(f"Error: {e}")
        print("\nNOTE: This demo requires a running Neo4j instance. If you don't have Neo4j set up,")
        print("try running the simpler in-memory demo with: python graphrag/graphrag_demo.py")
        print("\nTo set up Neo4j:")
        print("1. Install Neo4j Desktop from https://neo4j.com/download/")
        print("2. Create a new database and start it")
        print("3. Add the following to your .env file:")
        print("   NEO4J_USERNAME=neo4j")
        print("   NEO4J_PASSWORD=your_password")
        print("   NEO4J_URL=localhost")


if __name__ == "__main__":
    run_neo4j_demo() 