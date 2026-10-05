"""
面试题：RAG 在 Agent 中的应用？向量数据库为什么重要？
========================================================

来源：Agent面试真题01（题8）、微信/为什么向量数据库在Agent面试中如此重要、小红书/面试题精讲

面试回答要点：
  - RAG = Retrieval-Augmented Generation，检索增强生成
  - Agent + RAG：Agent 把 RAG 作为一个工具调用
  - 向量数据库是 RAG 的核心：语义检索、相似度匹配
  - 混合搜索：语义搜索 + 关键词搜索 + 重排序
  - 实战问题：chunk 大小、embedding 模型、检索策略

技术栈：LangChain RAG + ChromaDB + 多种检索策略
"""

import os
from typing import List, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

load_dotenv()


# ─── 知识库数据：Agent 面试知识点 ────────────────────────

AGENT_KNOWLEDGE = [
    "AI Agent 是一种能够自主感知环境、做出决策并采取行动的智能系统。它结合了大语言模型的推理能力与外部工具的执行能力。",
    "ReAct 范式是 Agent 最主流的设计模式，核心思想是让 LLM 交替进行推理（Reasoning）和行动（Acting），形成思考-行动-观察的循环。",
    "Function Calling 是 LLM 调用外部工具的机制。模型输出结构化的 tool call，包含工具名称和参数，由运行时调度执行。",
    "Tool Schema 定义了工具的名称、描述、输入参数和输出格式。精准的 Schema 设计是 Agent 正确选择工具的关键。",
    "Agent 的记忆分为三层：感觉记忆（原始输入缓存）、短期记忆（对话历史窗口）、长期记忆（外部向量存储）。",
    "MemGPT 提出了分层的记忆架构：Tier1 HBM 用于模型推理，Tier2 DRAM 存储活跃的外部知识，Tier3 SSD 用于归档。",
    "Multi-Agent 系统有几种常见协作模式：监督者模式（Supervisor）、竞拍模式（Auction）、流水线模式（Pipeline）、共享工作空间模式。",
    "LangGraph 是 LangChain 的图框架，支持有状态的多步骤工作流、条件分支、循环和人工介入。",
    "MCP（Model Context Protocol）是模型与外部工具交互的统一协议标准，类似于 AI 界的 USB 接口。",
    "Agent 评估体系包括：任务完成率、工具选择准确率、Token 效率、响应延迟、鲁棒性（异常处理能力）。",
    "Plan-and-Execute 模式将任务分解为规划（Plan）和执行（Execute）两个阶段，先制定计划再逐步执行。",
    "上下文工程（Context Engineering）是优化 Agent 输入上下文的技术，包括提示词设计、记忆管理、检索增强。",
    "工具调用失败处理策略包括：重试（Retry）、降级（Fallback）、超时控制、错误反馈循环。",
    "Chain 是预定义的处理序列，每一步固定；Agent 是动态决策系统，每一步由 LLM 选择下一步操作。",
    "LangChain 的核心抽象包括：Model I/O（模型输入输出）、Retrieval（检索）、Chain（链）、Agent（智能体）和 Callback（回调）。",
    "混合搜索（Hybrid Search）结合向量相似度搜索和关键词搜索，再用重排序模型（Reranker）精排结果。",
    "Chunk 策略是 RAG 的关键设计：chunk 太小丢失上下文，太大引入噪声。常用重叠分块策略。",
    "Embedding 模型选择影响检索质量。中文场景常用：text-embedding-3-small、bge-large-zh、m3e-large。",
    "RAG 在 Agent 中的应用方式：Agent 将 RAG 作为一个工具调用，当需要外部知识时触发检索。",
    "Agent 安全与对齐：输出过滤、权限控制、沙箱执行、人类监督（Human-in-the-Loop）。",
]

# ─── 构建 RAG 系统 ──────────────────────────────────────

class AgentRAGSystem:
    """
    Agent 知识库 RAG 系统
    对应面试题："RAG 在 Agent 中的应用"
    """

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=200,
            chunk_overlap=50,
            separators=["\n\n", "。", "；", "，", " "],
        )
        self._init_embeddings()
        self._init_vector_store()
        self._init_retrievers()
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,
        )

    def _init_embeddings(self):
        """初始化 embedding 模型"""
        api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY") or ""
        base_url = os.getenv("EMBEDDING_BASE_URL") or os.getenv("LLM_BASE_URL") or ""
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=api_key,
            base_url=base_url,
        )

    def _init_vector_store(self):
        """初始化向量数据库"""
        docs = [Document(page_content=t, metadata={"source": "agent_interview_knowledge"})
                for t in AGENT_KNOWLEDGE]
        split_docs = self.text_splitter.split_documents(docs)
        self.vector_store = Chroma.from_documents(
            documents=split_docs,
            embedding=self.embeddings,
            persist_directory="./.agent_rag_db",
            collection_name="agent_knowledge",
        )

    def _init_retrievers(self):
        """初始化多种检索器"""
        # 基础检索
        self.base_retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3},
        )
        # MMR 检索（多样性）
        self.mmr_retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 3, "fetch_k": 10, "lambda_mult": 0.7},
        )

    def basic_rag(self, query: str) -> str:
        """基础 RAG：检索 + 生成"""
        prompt = ChatPromptTemplate.from_template("""
你是一个 Agent 面试知识库助手。基于以下知识回答问题。
如果知识不足以回答，请诚实说明。

知识：
{context}

问题：{question}

请用中文回答：""")

        def format_docs(docs):
            return "\n\n".join([d.page_content for d in docs])

        chain = (
            {"context": self.base_retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        return chain.invoke(query)

    def mmr_rag(self, query: str) -> str:
        """MMR RAG：多样性检索"""
        prompt = ChatPromptTemplate.from_template("""
基于以下知识回答问题：

知识：
{context}

问题：{question}

回答：""")

        def format_docs(docs):
            return "\n\n".join([d.page_content for d in docs])

        chain = (
            {"context": self.mmr_retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        return chain.invoke(query)

    def hybrid_search(self, query: str, k: int = 3) -> List[str]:
        """混合搜索：关键词 + 语义"""
        # 关键词匹配
        keyword_results = []
        query_lower = query.lower()
        for doc in AGENT_KNOWLEDGE:
            if any(word.lower() in doc.lower() for word in query_lower.split()):
                keyword_results.append(doc)

        # 语义匹配
        semantic_results = self.vector_store.similarity_search(query, k=k)
        semantic_texts = [d.page_content for d in semantic_results]

        # 合并并去重
        combined = list(dict.fromkeys(keyword_results + semantic_texts))
        return combined[:k]

    def search_as_tool(self, query: str) -> str:
        """
        Agent 视角：将 RAG 作为一个工具
        对应面试题："Agent 如何结合 RAG"
        """
        results = self.hybrid_search(query)
        context = "\n\n".join(results)
        prompt = f"""你是一个知识库工具。根据检索结果回答问题。

检索结果：
{context}

问题：{query}

请基于以上信息给出回答。"""
        return self.llm.invoke([{"role": "user", "content": prompt}]).content

    def show_retrieval_details(self, query: str):
        """显示检索详情，用于面试讲解"""
        print(f"\n  查询: '{query}'")
        print(f"  检索策略: MMR (多样性)")
        docs = self.mmr_retriever.invoke(query)
        for i, doc in enumerate(docs):
            print(f"  [{i+1}] {doc.page_content}")
        return docs


# ─── 演示 ──────────────────────────────────────────────

def demo_rag_system():
    """演示完整的 RAG 系统"""
    print("=" * 60)
    print("面试题：RAG 在 Agent 中的应用")
    print("=" * 60)

    try:
        rag = AgentRAGSystem()
    except Exception as e:
        print(f"\n⏭️  需要 Embedding API 连接: {e}")
        print("   请在 .env 中配置 EMBEDDING_API_KEY / EMBEDDING_BASE_URL")
        return

    # 1. 展示检索细节
    print("\n📚 1. 混合搜索演示（关键词 + 语义）")
    queries = [
        "ReAct 范式是什么？",
        "Agent 的工具调用怎么实现",
        "Multi-Agent 有哪些协作模式",
    ]
    for q in queries:
        rag.show_retrieval_details(q)
        print()

    # 2. RAG 问答
    print("\n💬 2. RAG 问答")
    if os.getenv("LLM_API_KEY") and os.getenv("LLM_API_KEY") != "your-llm-api-key":
        for q in queries:
            print(f"\n问题: {q}")
            answer = rag.basic_rag(q)
            print(f"回答: {answer}")

    # 3. 展示 RAG as a Tool
    print("\n🔧 3. RAG 作为 Agent 工具")
    print("Agent 调用 RAG 工具的方式:")
    print('''
    class RAGTool(BaseTool):
        name = "knowledge_retrieval"
        description = "从 Agent 知识库检索相关信息"
        
        def _run(self, query: str) -> str:
            results = vector_store.similarity_search(query, k=3)
            return format_results(results)
    ''')

    # 4. 对比不同 Chunk 策略
    print("\n📐 4. Chunk 策略对比")
    text = AGENT_KNOWLEDGE[0]
    for chunk_size, overlap in [(100, 20), (200, 50), (500, 100)]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=overlap
        )
        chunks = splitter.split_text(text)
        print(f"   chunk_size={chunk_size}, overlap={overlap}: {len(chunks)} 个块")


if __name__ == "__main__":
    print("🔥 Agent 面试题实战 Demo #04: RAG in Agent\n")

    demo_rag_system()

    print("\n" + "=" * 60)
    print("📝 面试回答要点总结")
    print("=" * 60)
    print("""
1. RAG 原理：
   - Indexing：文档分块 → Embedding → 存入向量数据库
   - Retrieval：查询 → Embedding → 相似度搜索 → 返回 Top-K
   - Generation：检索结果 + 原始查询 → LLM → 生成回答

2. Agent 如何结合 RAG：
   - 方式一：RAG 作为 Agent 的一个工具（推荐）
   - 方式二：RAG 作为 Agent 的长期记忆存储
   - 方式三：RAG 结果作为 Agent 推理的上下文

3. 向量数据库为什么重要：
   - 语义检索（理解意图而非关键词）
   - 大规模知识管理（百万级文档毫秒级响应）
   - 多模态支持（文本、图片、代码均可向量化）
   - 增量更新（动态知识库）

4. 生产级 RAG 策略：
   - Chunk 策略：200-500 token，重叠 10-20%
   - 检索策略：混合搜索 + MMR + Reranker
   - Embedding 模型：按语言和领域选择合适的模型
    """)
