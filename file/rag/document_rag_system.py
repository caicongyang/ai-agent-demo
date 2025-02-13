import os
from typing import List, Dict, Any
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_community.document_loaders.word_document import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_models import ChatOpenAI as CommunityChatOpenAI

class DocumentRAGSystem:
    def __init__(
        self, 
        embedding_api_key: str = None, 
        embedding_base_url: str = None,
        llm_api_key: str = None,
        llm_base_url: str = None,
        embedding_model: str = "BAAI/bge-m3",
        chat_model: str = "deepseek-chat"
    ):
        """
        初始化文档RAG系统
        
        :param embedding_api_key: Embedding API密钥
        :param embedding_base_url: Embedding API基础URL
        :param llm_api_key: LLM API密钥
        :param llm_base_url: LLM API基础URL
        :param embedding_model: 嵌入模型
        :param chat_model: 聊天模型
        """
        # 设置 Embedding API 密钥
        if embedding_api_key:
            os.environ["EMBEDDING_API_KEY"] = embedding_api_key
        
        # 设置 LLM API 密钥
        if llm_api_key:
            os.environ["LLM_API_KEY"] = llm_api_key
        
        # 初始化嵌入模型
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=embedding_api_key,
            openai_api_base=embedding_base_url if embedding_base_url else None
        )
        
        # 初始化聊天模型
        self.llm = ChatOpenAI(
            model=chat_model,
            openai_api_key=llm_api_key,
            openai_api_base=llm_base_url if llm_base_url else None
        )
        
        # 向量存储
        self.vectorstore = None
        
        # 文档加载器映射
        self.loader_map = {
            '.txt': TextLoader,
            '.pdf': PyPDFLoader,
            '.docx': Docx2txtLoader
        }
    
    def load_documents(self, document_paths: List[str]) -> List[Any]:
        """
        加载文档
        
        :param document_paths: 文档路径列表
        :return: 文档列表
        """
        documents = []
        for path in document_paths:
            ext = os.path.splitext(path)[1].lower()
            loader_class = self.loader_map.get(ext)
            
            if loader_class:
                loader = loader_class(path)
                documents.extend(loader.load())
            else:
                print(f"不支持的文件类型: {path}")
        
        return documents
    
    def split_documents(
        self, 
        documents: List[Any], 
        chunk_size: int = 200,
        chunk_overlap: int = 20
    ) -> List[Any]:
        """
        分割文档
        
        :param documents: 文档列表
        :param chunk_size: 分块大小
        :param chunk_overlap: 分块重叠大小
        :return: 分割后的文档块
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap
        )
        return text_splitter.split_documents(documents)
    
    def create_vectorstore(
        self, 
        documents: List[Any], 
        persist_directory: str = './chroma_db',
        batch_size: int = 64
    ) -> Chroma:
        """
        创建向量存储
        
        :param documents: 文档块
        :param persist_directory: 持久化目录
        :param batch_size: 每批处理的文档数量
        :return: Chroma向量存储
        """
        # 分批处理文档
        if not documents:
            raise ValueError("没有文档需要处理")
        
        # 创建向量存储
        self.vectorstore = Chroma(
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )
        
        # 分批添加文档
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            if not self.vectorstore:
                self.vectorstore = Chroma.from_documents(
                    documents=batch,
                    embedding=self.embeddings,
                    persist_directory=persist_directory
                )
            else:
                self.vectorstore.add_documents(batch)
        
        return self.vectorstore
    
    def create_rag_chain(self, template: str = None):
        """
        创建RAG检索链
        
        :param template: 自定义提示模板
        :return: RAG检索链
        """
        if not self.vectorstore:
            raise ValueError("请先创建向量存储")
        
        # 默认提示模板
        default_template = """
        基于以下上下文回答问题:
        
        {context}
        
        问题: {question}
        """
        
        prompt = ChatPromptTemplate.from_template(
            template or default_template
        )
        
        # 创建检索器
        retriever = self.vectorstore.as_retriever()
        
        # 构建RAG链
        rag_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        return rag_chain
    
    def query_documents(self, query: str, rag_chain: Any) -> str:
        """
        查询文档
        
        :param query: 查询问题
        :param rag_chain: RAG检索链
        :return: 回答
        """
        return rag_chain.invoke(query)

def main():
    # 创建RAG系统实例
    rag_system = DocumentRAGSystem(
        embedding_api_key="sk-xhqwgtcihxrfkjjvcscvzfgulfhwfgsvdsszjtrjvyztrrct",
        embedding_base_url="https://api.siliconflow.cn/v1",
        llm_api_key="sk-00acc077d0d34f43a21910049163d796",
        llm_base_url="https://api.deepseek.com/v1",
        embedding_model="BAAI/bge-m3",
        chat_model="deepseek-chat"
    )
    
    # 文档路径
    document_paths = [
        './rag/documents/test.pdf'
    ]
    
    # 确保文档目录存在
    os.makedirs('./rag/documents', exist_ok=True)
    
    # 加载文档
    documents = rag_system.load_documents(document_paths)
    
    # 分割文档
    split_docs = rag_system.split_documents(documents)
    
    # 创建向量存储
    rag_system.create_vectorstore(split_docs)
    
    # 创建RAG检索链
    rag_chain = rag_system.create_rag_chain()
    
    # 测试查询
    test_queries = [
        "文档的主要内容是什么？",
        "能否总结关键信息？",
        "文档中最重要的观点是什么？"
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        answer = rag_system.query_documents(query, rag_chain)
        print("回答:", answer)

if __name__ == "__main__":
    main() 