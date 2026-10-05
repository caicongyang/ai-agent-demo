"""
面试题：Agent 工具调用失败怎么处理？
====================================

来源：字节面试官问Agent工具调用失败怎么办、微信/阿里面经、小红书/字节面经

面试回答要点：
  - 错误类型：参数错误、网络超时、服务不可用、权限不足
  - 重试策略：指数退避、最大重试次数、可重试 vs 不可重试
  - 降级策略：备用工具、简化功能、人工介入
  - 超时控制：connect timeout, read timeout, overall timeout
  - 错误反馈：将错误信息反馈给 LLM，让其重新规划

技术栈：LangChain Tool + 自定义错误处理 + 重试/降级模式
"""

import os
import time
import random
from typing import Any, Dict, List, Optional, Type
from enum import Enum
from dataclasses import dataclass, field
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool, tool
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor

load_dotenv()


# ─── 错误类型定义 ────────────────────────────────────────

class ErrorType(Enum):
    """工具错误类型"""
    PARAMETER_ERROR = "parameter_error"       # 参数错误
    NETWORK_TIMEOUT = "network_timeout"       # 网络超时
    SERVICE_UNAVAILABLE = "service_unavailable"  # 服务不可用
    PERMISSION_DENIED = "permission_denied"   # 权限不足
    RATE_LIMIT = "rate_limit"                 # 频率限制
    UNKNOWN_ERROR = "unknown_error"           # 未知错误


@dataclass
class ToolResult:
    """工具调用结果"""
    success: bool
    data: Optional[Any] = None
    error_type: Optional[ErrorType] = None
    error_message: str = ""
    retry_count: int = 0


# ─── 重试机制 ────────────────────────────────────────────

class RetryStrategy:
    """
    重试策略
    对应面试题："什么错误该重试？什么错误不该重试？"
    """

    RETRYABLE_ERRORS = {
        ErrorType.NETWORK_TIMEOUT,
        ErrorType.RATE_LIMIT,
        ErrorType.SERVICE_UNAVAILABLE,
    }

    NON_RETRYABLE_ERRORS = {
        ErrorType.PARAMETER_ERROR,
        ErrorType.PERMISSION_DENIED,
    }

    @staticmethod
    def should_retry(error_type: ErrorType) -> bool:
        """判断是否应该重试"""
        if error_type in RetryStrategy.RETRYABLE_ERRORS:
            return True
        if error_type in RetryStrategy.NON_RETRYABLE_ERRORS:
            return False
        # 未知错误：安全起见不重试
        return False

    @staticmethod
    def get_wait_time(retry_count: int) -> float:
        """指数退避计算等待时间"""
        base_wait = 1.0  # 初始等待 1 秒
        max_wait = 30.0  # 最大等待 30 秒
        wait = min(base_wait * (2 ** retry_count), max_wait)
        # 加入随机抖动
        wait *= (1 + random.random() * 0.5)
        return wait

    @staticmethod
    def max_retries(error_type: ErrorType) -> int:
        """根据错误类型决定最大重试次数"""
        if error_type == ErrorType.NETWORK_TIMEOUT:
            return 3
        if error_type == ErrorType.RATE_LIMIT:
            return 2
        if error_type == ErrorType.SERVICE_UNAVAILABLE:
            return 2
        return 0


# ─── 降级策略 ────────────────────────────────────────────

class FallbackStrategy:
    """
    降级策略
    对应面试题："如果工具超时，降级策略是什么？"
    """

    @staticmethod
    def get_fallback(error_type: ErrorType, tool_name: str) -> str:
        """根据错误获取降级方案"""
        fallbacks = {
            ("data_api", ErrorType.NETWORK_TIMEOUT):
                "尝试使用本地缓存数据代替",
            ("data_api", ErrorType.SERVICE_UNAVAILABLE):
                "使用备用数据源 API 进行查询",
            ("search", ErrorType.RATE_LIMIT):
                "降低请求频率，使用上次缓存的搜索结果",
        }
        return fallbacks.get((tool_name, error_type), "进行人工介入处理")


# ─── 模拟有错误的工具 ────────────────────────────────────

class UnreliableAPI(BaseTool):
    """
    不稳定的 API 工具：模拟各种错误
    用于演示工具调用失败处理
    """
    name: str = "unreliable_data_api"
    description: str = "一个不稳定的数据查询 API，可能返回各种错误"
    args_schema: Type[BaseModel]

    failure_rate: float = 0.4  # 40% 失败率
    _call_count: int = 0

    class InputSchema(BaseModel):
        query: str = Field(description="查询关键词")

    def _run(self, query: str) -> str:
        self._call_count += 1

        # 模拟各种错误
        rand = random.random()
        if rand < 0.15:
            raise TimeoutError("API 连接超时（15s）")
        elif rand < 0.25:
            raise ConnectionError("服务暂时不可用（503）")
        elif rand < 0.35:
            raise ValueError(f"参数 '{query}' 格式错误")
        elif rand < self.failure_rate:
            raise Exception("未知服务器错误")

        # 成功返回数据
        data = {
            "Agent面试题": "ReAct、RAG、Memory、Multi-Agent 是最高频考点",
            "技术栈": "LangChain + LangGraph + ChromaDB + OpenAI",
            "学习方法": "概念 → Demo → 项目实战 → 复盘总结",
        }
        for key, value in data.items():
            if query in key or query in value:
                return f"找到数据: {key}: {value}"
        return f"查询 '{query}' 未找到匹配数据"


# ─── 带重试的工具包装器 ──────────────────────────────────

class RetryableToolWrapper:
    """
    带重试和降级能力的工具包装器
    对应面试题完整的错误处理方案
    """

    def __init__(self, tool: BaseTool, tool_name: str):
        self.tool = tool
        self.tool_name = tool_name
        self.total_calls = 0
        self.successful_calls = 0

    def execute(self, **kwargs) -> ToolResult:
        """
        执行工具调用，包含完整的重试和降级逻辑
        """
        self.total_calls += 1
        last_error = None

        for attempt in range(4):  # 最多尝试 3 次
            try:
                result = self.tool._run(**kwargs)
                self.successful_calls += 1
                return ToolResult(success=True, data=result)

            except TimeoutError as e:
                error_type = ErrorType.NETWORK_TIMEOUT
                error_msg = str(e)
            except ConnectionError as e:
                error_type = ErrorType.SERVICE_UNAVAILABLE
                error_msg = str(e)
            except ValueError as e:
                error_type = ErrorType.PARAMETER_ERROR
                error_msg = str(e)
            except PermissionError as e:
                error_type = ErrorType.PERMISSION_DENIED
                error_msg = str(e)
            except Exception as e:
                error_type = ErrorType.UNKNOWN_ERROR
                error_msg = str(e)

            last_error = ToolResult(
                success=False,
                error_type=error_type,
                error_message=error_msg,
                retry_count=attempt,
            )

            # 判断是否应该重试
            if not RetryStrategy.should_retry(error_type):
                print(f"  ❌ 不可重试错误 ({error_type.value})，放弃重试")
                fallback = FallbackStrategy.get_fallback(error_type, self.tool_name)
                print(f"  🔄 降级策略: {fallback}")
                return last_error

            if attempt >= RetryStrategy.max_retries(error_type):
                print(f"  ⚠️ 已达最大重试次数 ({attempt + 1})，放弃")
                return last_error

            # 指数退避等待
            wait_time = RetryStrategy.get_wait_time(attempt)
            print(f"  🔄 第 {attempt + 1} 次重试，等待 {wait_time:.1f}s...")
            time.sleep(wait_time)

        return last_error

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "success_rate": f"{(self.successful_calls / self.total_calls * 100):.1f}%"
            if self.total_calls > 0 else "N/A",
        }


# ─── 演示 ──────────────────────────────────────────────

def demo_error_classification():
    """演示错误分类逻辑"""
    print("=" * 60)
    print("面试题：Agent 工具调用失败怎么处理？")
    print("Demo 1: 错误分类与重试策略")
    print("=" * 60)

    print("\n📋 错误类型与重试策略:")
    for error_type in ErrorType:
        should = "✅ 应该重试" if RetryStrategy.should_retry(error_type) else "❌ 不应该重试"
        max_r = RetryStrategy.max_retries(error_type)
        print(f"  {error_type.value}: {should} (最多 {max_r} 次)")


def demo_retry_mechanism():
    """演示重试机制"""
    print("\n" + "=" * 60)
    print("Demo 2: 重试与降级实战")
    print("=" * 60)

    random.seed(42)  # 固定随机种子，结果可复现
    tool = UnreliableAPI()
    wrapper = RetryableToolWrapper(tool, "data_api")

    queries = ["Agent面试题", "深度学习", "Python编程"]

    for query in queries:
        print(f"\n📝 查询: '{query}'")
        result = wrapper.execute(query=query)
        if result.success:
            print(f"  ✅ 成功: {result.data}")
        else:
            print(f"  ❌ 失败: [{result.error_type.value}] {result.error_message}")
        print("-" * 40)

    print(f"\n📊 工具调用统计: {wrapper.get_stats()}")


def demo_langchain_agent():
    """在 LangChain Agent 中处理工具错误"""
    print("\n" + "=" * 60)
    print("Demo 3: LangChain Agent 错误处理")
    print("=" * 60)

    if not os.getenv("LLM_API_KEY") or os.getenv("LLM_API_KEY") == "your-llm-api-key":
        print("\n⏭️  跳过（需配置 LLM_API_KEY）")
        return

    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )

    @tool
    def safe_search(query: str) -> str:
        """安全搜索工具，带错误处理"""
        try:
            # 模拟可能失败的搜索
            if "error" in query.lower():
                raise ConnectionError("搜索服务暂时不可用")
            return f"搜索结果: {query} 的相关信息..."
        except ConnectionError as e:
            return f"⚠️ 搜索失败: {str(e)}，请重试或换一个关键词"

    tools = [safe_search]
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个智能助手。当工具返回错误时，请分析错误原因：
1. 如果是临时错误（网络、超时），告诉用户重试
2. 如果是参数错误，修正参数后重试
3. 如果是服务不可用，建议使用其他方式
4. 始终给用户一个有用的回应，不要只返回错误信息"""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    queries = [
        "搜索一下 Agent 面试题",
        "搜索一下 error 案例",
    ]

    for q in queries:
        print(f"\n用户: {q}")
        result = executor.invoke({"input": q})
        print(f"回答: {result['output']}")


# ─── 面试回答模板 ──────────────────────────────────────

def interview_answer():
    """面试时如何回答这个问题"""
    print("\n" + "=" * 60)
    print("📝 面试回答框架")
    print("=" * 60)
    print("""
面试官问"Agent 工具调用失败怎么处理"时，建议按这个框架回答：

1️⃣ 先分类（展示知识广度）
   "工具调用失败可以分为几类：参数错误（前端可修复）、
    网络超时（临时性问题）、服务不可用（需要降级）、
    权限不足（需要人工介入）。"

2️⃣ 后策略（展示系统设计能力）
   "对于可重试的错误（超时、限流），采用指数退避策略，
    初始等待 1s，每次翻倍，最大 30s，加随机抖动避免雪崩。
    对于不可重试的错误（参数错、权限），直接返回错误给 LLM。"

3️⃣ 再降级（展示工程经验）
   "如果重试仍失败，执行降级方案：
    - 主 API 超时 → 切换到备用 API
    - 搜索服务不可用 → 使用本地缓存
    - 所有服务都失败 → 返回清晰错误 + 建议，让人工介入"

4️⃣ 最后给出代码示例（展示实战能力）
   "我会在工具层统一包装 try-catch，在 Agent 层配置
    max_iterations 和 handle_parsing_errors，
    在 LLM 层通过 prompt 告诉模型如何处理工具错误。"
    """)


if __name__ == "__main__":
    print("🔥 Agent 面试题实战 Demo #06: 工具调用失败处理\n")

    demo_error_classification()
    demo_retry_mechanism()
    demo_langchain_agent()
    interview_answer()
