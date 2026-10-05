"""
面试题：Chain 和 Agent 的区别？LangChain 核心抽象？
=====================================================

来源：Agent面试真题03（题1-2）、微信/LangChain 面试13题、小红书/面试八股文

面试回答要点：
  - Chain：预定义的处理序列，每一步固定，确定性强
  - Agent：动态决策系统，每一步由 LLM 选择下一步操作，灵活性强
  - 选型原则：确定性任务用 Chain，探索性任务用 Agent
  - LangChain 核心抽象：Model I/O, Retrieval, Chain, Agent, Callback
  - LCEL（LangChain Expression Language）：声明式组合 Chain

技术栈：LangChain Chain + LCEL + Agent + 对比分析
"""

import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.tools import tool

load_dotenv()


# ─── 方式一：Chain（确定性流水线）───────────────────────

class ChainDemo:
    """
    Chain 演示：预定义的处理步骤
    对应面试题："Chain 的核心抽象是什么？"
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,
        ) if os.getenv("LLM_API_KEY") and os.getenv("LLM_API_KEY") != "your-llm-api-key" else None

    def simple_chain(self, topic: str) -> str:
        """
        简单 Chain：输入 → 提示词 → LLM → 输出解析
        对应面试题："LangChain 最简单的链是什么？"
        """
        prompt = ChatPromptTemplate.from_template(
            "用一句话解释什么是{topic}，适合初学者理解。"
        )
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"topic": topic})

    def sequential_chain(self, topic: str) -> Dict:
        """
        顺序 Chain：多步串联
        第一步：生成解释，第二步：生成示例，第三步：总结
        """
        # 第一步：解释
        explain_prompt = ChatPromptTemplate.from_template(
            "解释什么是{topic}，50字以内。"
        )
        # 第二步：示例
        example_prompt = ChatPromptTemplate.from_template(
            "针对'{explanation}'，给出一个具体的应用示例。"
        )
        # 第三步：总结
        summary_prompt = ChatPromptTemplate.from_template(
            "基于以下内容，用一句话总结：\n解释：{explanation}\n示例：{example}"
        )

        chain = (
            {"explanation": explain_prompt | self.llm | StrOutputParser()}
            | RunnablePassthrough.assign(
                example=lambda x: (
                    example_prompt | self.llm | StrOutputParser()
                ).invoke({"explanation": x["explanation"]})
            )
            | RunnablePassthrough.assign(
                summary=lambda x: (
                    summary_prompt | self.llm | StrOutputParser()
                ).invoke(x)
            )
        )
        return chain.invoke({"topic": topic})

    def parallel_chain(self, topic: str) -> Dict:
        """
        并行 Chain：同时执行多个任务
        对应面试题："LangChain 如何处理并行任务？"
        """
        # 并行执行多个 Chain
        def_chain = ChatPromptTemplate.from_template("定义{topic}") | self.llm | StrOutputParser()
        app_chain = ChatPromptTemplate.from_template("{topic}的应用场景") | self.llm | StrOutputParser()
        adv_chain = ChatPromptTemplate.from_template("{topic}的优缺点") | self.llm | StrOutputParser()

        parallel = RunnableParallel(
            definition=def_chain,
            applications=app_chain,
            advantages=adv_chain,
        )
        return parallel.invoke({"topic": topic})


# ─── 方式二：Agent（动态决策）───────────────────────────

class AgentDemo:
    """
    Agent 演示：动态决策
    对应面试题："Agent 的执行流程是怎样的？"
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,
        ) if os.getenv("LLM_API_KEY") and os.getenv("LLM_API_KEY") != "your-llm-api-key" else None

    def simulate_decision(self, query: str) -> Dict:
        """
        模拟 Agent 的决策过程：
        1. 分析用户意图
        2. 决定是否需要工具
        3. 选择工具或直接回答
        4. 生成最终回复
        """
        from langchain.agents import create_react_agent, AgentExecutor
        from langchain_core.prompts import PromptTemplate

        @tool
        def search_web(query: str) -> str:
            """搜索网络信息"""
            return f"模拟搜索结果: {query} 的相关信息..."

        @tool
        def calculate(expr: str) -> str:
            """计算数学表达式"""
            try:
                return f"结果: {eval(expr, {'__builtins__': {}}, {})}"
            except Exception as e:
                return f"计算错误: {e}"

        tools = [search_web, calculate]

        prompt = PromptTemplate.from_template("""
你是一个智能 Agent。根据问题选择合适的工具。
可用工具: {tools}

问题: {input}
{agent_scratchpad}""")

        agent = create_react_agent(self.llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True,
                                  max_iterations=3)

        result = executor.invoke({"input": query})
        return {"input": query, "output": result["output"],
                "decision_type": "agent_dynamic"}


# ─── 方式三：LCEL 声明式 Chain ──────────────────────────

class LCELDemo:
    """
    LCEL（LangChain Expression Language）演示
    对应面试题："什么是 LCEL？有什么优势？"
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,
        ) if os.getenv("LLM_API_KEY") and os.getenv("LLM_API_KEY") != "your-llm-api-key" else None

    def demonstrate(self):
        """展示 LCEL 的各种用法"""
        print("\n" + "=" * 60)
        print("LCEL 声明式 Chain 演示")
        print("=" * 60)

        if not self.llm:
            print("⏭️  跳过（需配置 LLM_API_KEY）")
            return

        # 1. 最简单的 LCEL Chain
        print("\n1️⃣  | 操作符（Pipe）:")
        prompt = ChatPromptTemplate.from_template("翻译成英文：{text}")
        chain = prompt | self.llm | StrOutputParser()
        result = chain.invoke({"text": "人工智能正在改变世界"})
        print(f"   输入: 人工智能正在改变世界")
        print(f"   输出: {result}")

        # 2. RunnablePassthrough
        print("\n2️⃣  RunnablePassthrough（透传）:")
        chain = (
            {"context": RunnablePassthrough()}
            | ChatPromptTemplate.from_template("基于'{context}'写一句话")
            | self.llm | StrOutputParser()
        )
        result = chain.invoke("AI Agent")
        print(f"   输入: AI Agent")
        print(f"   输出: {result}")

        # 3. RunnableParallel（并行）
        print("\n3️⃣  RunnableParallel（并行执行）:")
        chain1 = ChatPromptTemplate.from_template("赞美{topic}") | self.llm | StrOutputParser()
        chain2 = ChatPromptTemplate.from_template("批评{topic}") | self.llm | StrOutputParser()
        parallel = RunnableParallel(praise=chain1, critique=chain2)
        result = parallel.invoke({"topic": "Python"})
        print(f"   赞美: {result['praise'][:50]}...")
        print(f"   批评: {result['critique'][:50]}...")

        # 4. RunnablePassthrough.assign（赋值）
        print("\n4️⃣  RunnablePassthrough.assign（扩展现有数据）:")
        chain = (
            RunnablePassthrough.assign(
                greeting=lambda x: f"你好，{x['name']}！",
                upper_name=lambda x: x['name'].upper()
            )
        )
        result = chain.invoke({"name": "张三"})
        print(f"   结果: {result}")

    @staticmethod
    def code_example():
        """面试时的代码示例"""
        print("""
📝 面试代码示例：如何用 LCEL 构建 Chain？

from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.prompts import ChatPromptTemplate

# 1. 基本 Chain（| 操作符）
chain = prompt | model | output_parser

# 2. 并行执行
parallel = RunnableParallel(
    task1=chain1,
    task2=chain2,
)

# 3. 数据流转换
chain = (
    {"context": RunnablePassthrough()}
    | prompt
    | model
    | output_parser
)
""")


# ─── 对比演示 ──────────────────────────────────────────

def comparison_table():
    """Chain vs Agent 对比"""
    print("=" * 60)
    print("📊 Chain vs Agent 对比表")
    print("=" * 60)
    print("""
| 维度 | Chain | Agent |
|------|-------|-------|
| **决策方式** | 预定义流程 | 动态决策 |
| **灵活性** | 低（固定步骤） | 高（LLM 自主选择） |
| **可预测性** | 高（输出稳定） | 低（每次可能不同） |
| **复杂度** | 适合简单流程 | 适合复杂场景 |
| **Token 消耗** | 低 | 高 |
| **调试难度** | 易 | 难 |
| **适用场景** | 翻译、分类、提取 | 搜索、推理、多步骤任务 |
| **代码示例** | `prompt \| llm \| parser` | `create_agent + executor` |
""")


def selection_guide():
    """选型指南"""
    print("📝 面试回答：如何选择 Chain vs Agent？")
    print("""
选型原则：

用 Chain 的场景（确定性强）：
  - 翻译任务：输入什么语言，输出什么翻译
  - 分类任务：输入文本，输出类别标签
  - 提取任务：输入文档，输出结构化数据
  - 格式转换：Markdown → HTML，JSON → CSV

用 Agent 的场景（不确定性强）：
  - 需要搜索外部信息才能回答的问题
  - 多步骤推理（需要中间结果决定下一步）
  - 需要调用多个不同工具的复杂任务
  - 用户意图不明确的开放性问题

生产环境的最佳实践：
  70% Chain + 20% Agent + 10% Human-in-the-Loop
  - 常规任务用 Chain（稳定可控）
  - 复杂任务用 Agent（灵活适应）
  - 关键决策让人工介入（安全可靠）
""")


if __name__ == "__main__":
    print("🔥 Agent 面试题实战 Demo #09: Chain vs Agent\n")

    chain_demo = ChainDemo()
    agent_demo = AgentDemo()

    # 对比表
    comparison_table()

    # Chain 演示
    print("\n" + "=" * 60)
    print("Chain 演示：确定性流水线")
    print("=" * 60)
    if chain_demo.llm:
        # 简单 Chain
        result = chain_demo.simple_chain("AI Agent")
        print(f"\n简单 Chain: {result}")

        # 顺序 Chain
        result = chain_demo.sequential_chain("RAG")
        print(f"\n顺序 Chain 结果:")
        for k, v in result.items():
            print(f"  {k}: {str(v)[:60]}...")

        # 并行 Chain
        print("\n并行 Chain:")
        result = chain_demo.parallel_chain("LangChain")
        for k, v in result.items():
            print(f"  {k}: {str(v)[:50]}...")
    else:
        print("\n⏭️  Chain 演示跳过（需配置 LLM_API_KEY）")

    # Agent 演示
    print("\n" + "=" * 60)
    print("Agent 演示：动态决策")
    print("=" * 60)
    if agent_demo.llm:
        result = agent_demo.simulate_decision("计算 123 * 456 的结果，然后搜索 LangChain 的最新动态")
        print(f"\nAgent 决策结果: {result['output'][:200]}...")
    else:
        print("\n⏭️  Agent 演示跳过（需配置 LLM_API_KEY）")

    # LCEL 演示
    lcel = LCELDemo()
    lcel.demonstrate()

    # 选型指南
    selection_guide()

    print("\n" + "=" * 60)
    print("📝 面试回答要点总结")
    print("=" * 60)
    print("""
1. Chain vs Agent 本质区别：
   - Chain：预定义路径，每一步固定
   - Agent：动态决策，每一步 LLM 选择

2. LangChain 5 大核心抽象：
   - Model I/O：模型输入输出
   - Retrieval：检索（文档加载、分割、存储、检索）
   - Chain：链（LCEL 声明式组合）
   - Agent：智能体
   - Callback：回调（日志、监控、追踪）

3. LCEL 优势：
   - 声明式：什么是做什么，而不是怎么做
   - 组合式：小 Chain 组合成大 Chain
   - 流式支持：原生支持 Stream
   - 并行执行：RunnableParallel
   - 可观测：LangSmith 自动追踪

4. 生产选型建议：
   - 确定任务用 Chain（高效可控）
   - 探索任务用 Agent（灵活适应）
   - 关键决策人工介入（安全可靠）
    """)
