"""
面试题：Agent 的记忆机制如何实现？
==================================

来源：Agent面试真题01（题7）、AI高频面试题、面了阿里大模型Agent

面试回答要点：
  - 感觉记忆（原始输入）：原始输入缓存，短期保留
  - 短期记忆（对话历史）：当前会话上下文，LLM 窗口内
  - 长期记忆（外部存储）：向量数据库/知识库，持久化
  - MemGPT 层级架构：Tier1(HBM) → Tier2(DRAM) → Tier3(SSD)
  - 关键问题：上下文窗口限制、记忆衰减、检索策略

技术栈：LangChain Memory + LangGraph 持久化 + ChromaDB
"""

import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnablePassthrough
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains import ConversationChain
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

load_dotenv()


# ─── 方式一：ConversationBufferMemory 短期记忆 ──────────

def demo_short_term_memory():
    """
    短期记忆：基于 Buffer 的对话历史存储
    对应面试题："Agent 中的记忆机制如何实现 - 短期记忆"
    """
    print("=" * 60)
    print("短期记忆：ConversationBufferMemory")
    print("=" * 60)

    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )

    memory = ConversationBufferMemory(return_messages=True)
    conversation = ConversationChain(llm=llm, memory=memory, verbose=False)

    messages = [
        "我叫张三，是一名算法工程师",
        "我最近在学习 AI Agent 开发",
        "你还记得我叫什么名字吗？做什么工作的？",
    ]

    for msg in messages:
        print(f"\n用户: {msg}")
        response = conversation.predict(input=msg)
        print(f"助手: {response}")

    print(f"\n📦 当前记忆内容:")
    print(memory.buffer)


# ─── 方式二：SummaryMemory 摘要记忆 ──────────────────────

def demo_summary_memory():
    """
    摘要记忆：将长对话压缩成摘要
    对应面试题："如何处理 Agent 的长期对话？"
    """
    print("\n" + "=" * 60)
    print("摘要记忆：ConversationSummaryMemory")
    print("=" * 60)

    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )

    memory = ConversationSummaryMemory(llm=llm, return_messages=True)
    conversation = ConversationChain(llm=llm, memory=memory, verbose=False)

    messages = [
        "帮我分析一下 Python 和 Java 的优缺点",
        "那 Python 在 AI 领域有什么优势？",
        "总结一下我们刚才的讨论，我记性不好",
    ]

    for msg in messages:
        print(f"\n用户: {msg}")
        response = conversation.predict(input=msg)
        print(f"助手: {response[:150]}...")

    print(f"\n📦 记忆摘要:")
    print(memory.buffer)


# ─── 方式三：LangGraph 持久化记忆 ────────────────────────

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated, Sequence
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Agent 状态：包含消息列表"""
    messages: Annotated[Sequence[HumanMessage | AIMessage], add_messages]
    user_profile: Dict[str, Any]


def create_memory_agent():
    """使用 LangGraph 实现持久化记忆"""
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )

    def chat_node(state: AgentState) -> Dict:
        """对话节点"""
        messages = state["messages"]
        # 添加系统提示
        system_msg = SystemMessage(content=f"""你是一个有记忆的助手。
用户信息: {json.dumps(state.get('user_profile', {}), ensure_ascii=False)}
请利用记忆中的用户信息提供个性化回复。""")
        all_messages = [system_msg] + list(messages)

        response = llm.invoke(all_messages)
        return {"messages": [response]}

    def extract_profile(state: AgentState) -> Dict:
        """提取用户画像"""
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                text = msg.content
                if "我叫" in text:
                    # 简单提取名字
                    name_start = text.find("我叫") + 2
                    name_end = text.find("，") if "，" in text[name_start:] else len(text)
                    name = text[name_start:name_start + name_end].strip()
                    return {"user_profile": {**state.get("user_profile", {}), "name": name}}
                if "工作" in text and ("是" in text or "做" in text):
                    return {"user_profile": {**state.get("user_profile", {}), "job": "算法工程师"}}
        return {}

    builder = StateGraph(AgentState)
    builder.add_node("chat", chat_node)
    builder.add_node("profile", extract_profile)
    builder.add_edge(START, "chat")
    builder.add_edge("chat", "profile")
    builder.add_edge("profile", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


def demo_langgraph_memory():
    """演示 LangGraph 持久化记忆"""
    print("\n" + "=" * 60)
    print("LangGraph 持久化记忆（跨会话记忆）")
    print("=" * 60)

    if not os.getenv("LLM_API_KEY") or os.getenv("LLM_API_KEY") == "your-llm-api-key":
        print("\n⏭️  跳过（需配置 LLM_API_KEY）")
        return

    agent = create_memory_agent()
    config = {"configurable": {"thread_id": "memory-demo-1"}}

    # 第一轮对话
    print("\n--- 第一轮对话 ---")
    result = agent.invoke({
        "messages": [HumanMessage(content="你好！我叫张三，是一名算法工程师")],
        "user_profile": {},
    }, config)
    print(f"助手: {result['messages'][-1].content}")

    # 第二轮对话（应该记住名字）
    print("\n--- 第二轮对话（检查记忆）---")
    result = agent.invoke({
        "messages": [HumanMessage(content="你还记得我是谁吗？我做什么工作？")],
    }, config)
    print(f"助手: {result['messages'][-1].content}")

    # 获取持久化状态
    state = agent.get_state(config)
    print(f"\n📦 持久化用户画像: {state.values.get('user_profile', {})}")


# ─── 方式四：长期记忆（ChromaDB）────────────────────────

class LongTermMemory:
    """
    长期记忆系统：使用 ChromaDB 存储和检索
    对应面试题："Agent 如何存储和检索长期记忆？"
    """

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY"),
            base_url=os.getenv("EMBEDDING_BASE_URL") or os.getenv("LLM_BASE_URL"),
        )
        self.vector_store = Chroma(
            collection_name="agent_long_term_memory",
            embedding_function=self.embeddings,
            persist_directory="./.agent_memory_db",
        )

    def remember(self, topic: str, content: str):
        """存储一条长期记忆"""
        doc = Document(
            page_content=f"[{topic}] {content}",
            metadata={"topic": topic, "timestamp": datetime.now().isoformat()},
        )
        self.vector_store.add_documents([doc])
        print(f"💾 已记住 '{topic}': {content[:50]}...")

    def recall(self, query: str, k: int = 3) -> List[str]:
        """检索相关记忆"""
        docs = self.vector_store.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]

    def forget(self, topic: str):
        """删除关于某个主题的记忆"""
        self.vector_store.delete(filter={"topic": topic})
        print(f"🗑️ 已忘记关于 '{topic}' 的所有记忆")


def demo_long_term_memory():
    """演示长期记忆系统"""
    print("\n" + "=" * 60)
    print("长期记忆：ChromaDB 向量存储")
    print("=" * 60)

    try:
        memory = LongTermMemory()

        # 存储记忆
        memory.remember("user_preference", "用户喜欢 Python 和 TypeScript，不喜欢 Java")
        memory.remember("project_info", "用户正在开发一个 AI Agent 面试题 Demo 集合")
        memory.remember("learning_goal", "用户想系统学习 LangGraph 和 Multi-Agent 系统")

        # 检索记忆
        print("\n检索'技术栈偏好':")
        results = memory.recall("用户喜欢什么编程语言")
        for r in results:
            print(f"  → {r}")

        print("\n检索'当前项目':")
        results = memory.recall("用户在做什么项目")
        for r in results:
            print(f"  → {r}")

    except Exception as e:
        print(f"⏭️  跳过（需要 Embedding API 和网络连接）: {e}")


if __name__ == "__main__":
    print("🔥 Agent 面试题实战 Demo #03: Agent 记忆机制\n")

    # 短期记忆
    if os.getenv("LLM_API_KEY") and os.getenv("LLM_API_KEY") != "your-llm-api-key":
        demo_short_term_memory()
        demo_summary_memory()
        demo_langgraph_memory()
    else:
        print("⏭️  LLM 记忆 Demo 跳过（需配置 LLM_API_KEY）")

    # 长期记忆
    demo_long_term_memory()

    print("\n" + "=" * 60)
    print("📝 面试回答要点总结")
    print("=" * 60)
    print("""
1. 记忆三层架构：
   - 感觉记忆（Sensory）：原始输入缓存
   - 短期记忆（Short-term）：对话历史窗口
   - 长期记忆（Long-term）：外部持久化存储

2. 短期记忆方案：
   - BufferMemory：全部对话历史
   - SummaryMemory：压缩摘要
   - SummaryBufferMemory：混合策略（摘要 + 最近窗口）

3. 长期记忆方案：
   - 向量数据库（ChromaDB / Pinecone / Milvus）
   - 知识图谱（Neo4j）
   - Key-Value 存储（Redis）

4. MemGPT 层级架构：
   - Tier 1: HBM（模型上下文窗口）
   - Tier 2: DRAM（外部向量存储）
   - Tier 3: SSD（归档存储）

5. 关键问题：
   - 上下文窗口限制：需要压缩策略
   - 记忆衰减：时间权重递减
   - 检索精度：embedding 质量决定
    """)
