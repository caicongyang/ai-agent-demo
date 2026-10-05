"""
面试题：Agent 如何选择工具？/ Function Calling 的实现机制？
=========================================================

来源：Agent面试真题01（题4）、AI高频面试题、小红书/字节面经

面试回答要点：
  - Tool Schema：定义工具的输入输出格式（name, description, parameters）
  - 工具注册：Agent 启动时注册所有可用工具
  - 动态路由：LLM 根据用户意图选择合适的工具
  - 冲突解决：多个工具匹配时，由 LLM 根据 description 判断
  - 关键设计：description 越精确，工具选择越准确

技术栈：LangChain Tool API + @tool 装饰器 + Pydantic Schema
"""

import os
import json
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool, StructuredTool, BaseTool
from langchain_core.tools import tool as lc_tool
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor

load_dotenv()


# ─── 方式一：用 @tool 装饰器定义工具（最常用）────────────

@lc_tool
def search_knowledge_base(query: str) -> str:
    """搜索内部知识库，输入搜索关键词，返回相关知识片段"""
    knowledge = {
        "agent": "AI Agent 是一种能自主决策和行动的智能系统，核心组件包括 LLM、工具集、记忆模块。",
        "react": "ReAct 范式让 LLM 交替进行推理（Reasoning）和行动（Acting），形成思考-行动-观察循环。",
        "rag": "RAG（检索增强生成）结合信息检索和文本生成，让 LLM 能利用外部知识回答问题。",
        "langgraph": "LangGraph 是 LangChain 的图框架，用于构建有状态的多步骤 Agent 工作流。",
        "memory": "Agent 记忆分为：短期记忆（对话历史）、长期记忆（外部存储）、感觉记忆（原始输入缓存）。",
        "mcp": "MCP（Model Context Protocol）是模型与外部工具交互的统一协议标准。",
    }
    results = []
    for key, value in knowledge.items():
        if query.lower() in key.lower() or query.lower() in value.lower():
            results.append(f"[{key}] {value}")
    return "\n".join(results) if results else f"未找到与 '{query}' 相关的知识"


@lc_tool
def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """获取指定时区的当前时间，输入时区名称（如 Asia/Shanghai, America/New_York）"""
    try:
        import pytz
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return f"{timezone} 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    except ImportError:
        return f"当前系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e:
        return f"时区错误: {str(e)}"


# ─── 方式二：用 Pydantic Schema 精确定义工具 ─────────────

class WeatherInput(BaseModel):
    """天气查询工具的输入 Schema"""
    city: str = Field(description="城市名称，如：北京、上海")
    date: str = Field(default="today", description="查询日期，格式：YYYY-MM-DD 或 today")


class WeatherTool(BaseTool):
    """用 BaseTool + Pydantic Schema 定义的结构化工具"""
    name: str = "get_weather_info"
    description: str = "查询指定城市在指定日期的天气信息"
    args_schema: Type[BaseModel] = WeatherInput

    def _run(self, city: str, date: str = "today") -> str:
        """模拟天气查询"""
        weather_db = {
            ("北京", "today"): "晴，25°C，空气质量：良",
            ("上海", "today"): "多云，28°C，空气质量：优",
            ("深圳", "today"): "阵雨，30°C，空气质量：优",
            ("杭州", "today"): "阴，26°C，空气质量：良",
            ("北京", "2026-06-27"): "晴转多云，24-32°C",
            ("上海", "2026-06-27"): "小雨，22-26°C",
        }
        result = weather_db.get((city, date))
        if result:
            return f"{city}{'今日' if date == 'today' else date}天气：{result}"
        return f"暂无{city}在{date}的天气数据"


# ─── 方式三：手写 Tool Router（展示工具选择的核心逻辑）───

class ToolRouter:
    """
    手写工具选择器：展示 LLM 如何根据用户输入选择工具
    对应面试题："Agent 如何选择工具"
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,
        )
        self.tools_registry = {
            "search_knowledge_base": {
                "description": "搜索知识库，获取 Agent、RAG、LangGraph 等技术概念的解释",
                "func": search_knowledge_base,
            },
            "get_weather_info": {
                "description": "查询城市天气信息",
                "func": WeatherTool()._run,
            },
            "get_current_time": {
                "description": "获取指定时区的当前时间",
                "func": get_current_time,
            },
        }

    def route(self, query: str) -> str:
        """根据用户输入，LLM 选择合适的工具"""
        tools_desc = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.tools_registry.items()
        ])
        prompt = f"""你是一个工具路由选择器。用户输入: "{query}"

可用工具:
{tools_desc}

请选择最合适的工具，只回复工具名称。
如果不需要工具，回复 "none"。
如果多个工具合适，回复最相关的那个。"""

        try:
            choice = self.llm.invoke([{"role": "user", "content": prompt}])
            tool_name = choice.content.strip().lower()
        except Exception:
            tool_name = "none"

        if tool_name in self.tools_registry:
            # 简化处理：直接传递用户输入
            result = self.tools_registry[tool_name]["func"](query)
            return f"选择了工具 [{tool_name}]\n结果: {result}"
        else:
            return "无需调用工具，直接回答即可。"


# ─── 方式四：LangChain create_tool_calling_agent ────────

def create_agent_with_tools():
    """标准的 LangChain 工具调用 Agent"""
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )

    tools = [
        search_knowledge_base,
        WeatherTool(),
        get_current_time,
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个智能助手，可以根据问题选择合适的工具来回答。"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return executor


# ─── 演示 ──────────────────────────────────────────────

def demo_tool_router():
    """演示工具路由选择的核心逻辑"""
    print("=" * 60)
    print("面试题：Agent 如何选择工具？")
    print("Demo 1: 手写 Tool Router（展示核心选择逻辑）")
    print("=" * 60)

    router = ToolRouter()
    queries = [
        "什么是 RAG 技术？",
        "上海今天天气怎么样？",
        "现在几点了？",
        "你好，今天有什么新闻？",
    ]

    for q in queries:
        print(f"\n用户: {q}")
        result = router.route(q)
        print(f"系统: {result}")
        print("-" * 40)


def demo_structured_tool():
    """演示结构化工具定义"""
    print("\n" + "=" * 60)
    print("Demo 2: Pydantic Schema 精确定义工具")
    print("=" * 60)

    tool = WeatherTool()
    print(f"\n工具名称: {tool.name}")
    print(f"工具描述: {tool.description}")
    print(f"输入 Schema: {tool.args_schema.schema_json(indent=2)}")

    result = tool.run({"city": "深圳", "date": "today"})
    print(f"\n调用结果: {result}")


def demo_langchain_agent():
    """演示 LangChain Agent 自动工具调用"""
    print("\n" + "=" * 60)
    print("Demo 3: LangChain Tool Calling Agent")
    print("=" * 60)

    if not os.getenv("LLM_API_KEY") or os.getenv("LLM_API_KEY") == "your-llm-api-key":
        print("\n⏭️  跳过（需配置 LLM_API_KEY）")
        return

    executor = create_agent_with_tools()
    queries = [
        "解释一下什么是 Agent 的核心组件？",
        "查询北京的天气情况",
    ]

    for q in queries:
        print(f"\n用户: {q}")
        result = executor.invoke({"input": q})
        print(f"回答: {result['output']}")
        print("-" * 40)


if __name__ == "__main__":
    print("🔥 Agent 面试题实战 Demo #02: 工具调用 / Function Calling\n")

    demo_tool_router()
    demo_structured_tool()
    demo_langchain_agent()

    print("\n" + "=" * 60)
    print("📝 面试回答要点总结")
    print("=" * 60)
    print("""
1. Tool Schema 设计（name, description, parameters）：
   - description 要精确：LLM 依赖它来选择工具
   - parameters 要明确类型和约束
2. 工具注册与发现：
   - 启动时注册所有工具到 Agent
   - Agent 将工具列表传给 LLM 作为上下文
3. 工具选择机制：
   - LLM 根据用户意图 + 工具 description 匹配
   - 多工具匹配时由 LLM 判断最合适的
4. 核心设计原则：
   - 工具描述越精确，选择越准确
   - 输入参数 Schema 要清晰
   - 错误处理要健壮（工具可能失败）
5. 框架支持：
   - LangChain: @tool, StructuredTool, BaseTool, create_tool_calling_agent
   - 自定义: 可以手写 Router 做更精细的控制
    """)
