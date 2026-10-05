"""
面试题：什么是 ReAct 范式？它的优缺点？
========================================

来源：Agent面试真题01、AI高频面试题、小红书/AI Agent 面试八股文

面试回答要点：
  - ReAct = Reasoning + Acting，让 LLM 边推理边行动
  - 核心循环：Thought（思考）→ Action（行动）→ Observation（观察）
  - 优势：可解释性强、能纠错、能利用外部工具
  - 劣势：Token 消耗大、延迟高、复杂任务可能陷入循环

技术栈：LangChain ReAct Agent + LangGraph 自定义实现
"""

import os
import json
from typing import Any, Dict, List, Optional, TypedDict, Literal
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.utilities import SerpAPIWrapper
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

# ─── 工具定义 ─────────────────────────────────────────────

def calculate(expression: str) -> str:
    """安全计算数学表达式"""
    try:
        # 只允许基本运算
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return "错误：表达式包含非法字符"
        result = eval(expression, {"__builtins__": {}}, {})
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"


def get_weather(city: str) -> str:
    """模拟天气查询"""
    weather_data = {
        "北京": "晴，25°C，空气质量良",
        "上海": "多云，28°C，空气质量优",
        "深圳": "阵雨，30°C，空气质量优",
        "杭州": "阴，26°C，空气质量良",
    }
    return weather_data.get(city, f"暂无{city}的天气数据")


# ─── 方式一：LangChain ReAct Agent ───────────────────────

def create_react_agent():
    """
    使用 LangChain 的 ReAct Agent（方式一）
    对应面试题：ReAct 范式在框架中的实现
    """
    from langchain.agents import create_react_agent, AgentExecutor
    from langchain_core.prompts import PromptTemplate

    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )

    tools = [
        Tool(name="calculator", func=calculate,
             description="计算数学表达式，输入：数学表达式字符串"),
        Tool(name="weather", func=get_weather,
             description="查询城市天气，输入：城市名"),
    ]

    template = """你是一个擅长推理和行动的助手。请一步步思考。

可用工具：
{tools}

工具名称格式：{tool_names}

对于每一步，请用以下格式回答：
思考：分析当前状况
行动：工具名称("输入")
观察：工具返回的结果
...（重复思考-行动-观察循环）
最终答案：给出最终回答

问题：{input}

{agent_scratchpad}"""

    prompt = PromptTemplate.from_template(template)
    agent = create_react_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True,
                             handle_parsing_errors=True, max_iterations=5)
    return executor


def demo_react_agent():
    """演示 LangChain ReAct Agent"""
    print("=" * 60)
    print("面试题：什么是 ReAct 范式？")
    print("Demo 1: LangChain ReAct Agent")
    print("=" * 60)

    executor = create_react_agent()
    query = "北京和上海的天气怎么样？顺便算一下 125 * 37 等于多少？"

    print(f"\n用户问题: {query}")
    print("\n--- Agent 执行过程（思考→行动→观察循环）---\n")

    result = executor.invoke({"input": query})

    print(f"\n最终回答:\n{result['output']}")


# ─── 方式二：LangGraph 手写 ReAct ─────────────────────────

class ReActState(TypedDict):
    """ReAct 状态定义"""
    question: str
    thoughts: List[str]
    actions: List[str]
    observations: List[str]
    final_answer: str
    step_count: int
    max_steps: int


def think_step(state: ReActState) -> Dict:
    """思考节点：分析当前状态，决定下一步行动"""
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )

    history = ""
    for i in range(len(state["thoughts"])):
        history += f"思考: {state['thoughts'][i]}\n"
        if i < len(state["actions"]):
            history += f"行动: {state['actions'][i]}\n"
        if i < len(state["observations"]):
            history += f"观察: {state['observations'][i]}\n"

    prompt = f"""你是一个 ReAct 智能体。可用工具：
- calculator(expression): 计算数学表达式
- weather(city): 查询城市天气

当前问题: {state['question']}

历史记录:
{history}

请用以下格式继续（只输出思考内容，不要输出行动）：
思考：<你的分析>"""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        thought = response.content.strip()
    except Exception:
        thought = "思考：根据已有信息，尝试给出最终答案。"

    return {"thoughts": state["thoughts"] + [thought],
            "step_count": state["step_count"] + 1}


def action_step(state: ReActState) -> Dict:
    """行动节点：执行工具调用"""
    last_thought = state["thoughts"][-1] if state["thoughts"] else ""
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )

    prompt = f"""根据思考内容，决定调用哪个工具。
思考: {last_thought}

可用工具：
- calculator(expression) - 返回计算结果
- weather(city) - 返回天气信息

如果思考已经给出最终答案，回复 "FINAL: <答案>"。
否则，回复格式为: ACTION: calculator("表达式") 或 ACTION: weather("城市名")"""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        action_text = response.content.strip()
    except Exception:
        action_text = "FINAL: 抱歉，无法处理该请求。"

    if action_text.startswith("FINAL:"):
        answer = action_text.replace("FINAL:", "").strip()
        return {"actions": state["actions"] + [action_text],
                "final_answer": answer}

    if "calculator" in action_text:
        import re
        match = re.search(r'calculator\(["\']?(.+?)["\']?\)', action_text)
        expr = match.group(1) if match else "0"
        result = calculate(expr)
        return {"actions": state["actions"] + [action_text],
                "observations": state["observations"] + [f"观察: {result}"]}
    elif "weather" in action_text:
        import re
        match = re.search(r'weather\(["\']?(.+?)["\']?\)', action_text)
        city = match.group(1) if match else "北京"
        result = get_weather(city)
        return {"actions": state["actions"] + [action_text],
                "observations": state["observations"] + [f"观察: {result}"]}

    return {"actions": state["actions"] + [action_text]}


def should_continue(state: ReActState) -> Literal["action", "__end__"]:
    """条件边：判断是否继续循环"""
    if state["final_answer"]:
        return "__end__"
    if state["step_count"] >= state["max_steps"]:
        return "__end__"
    return "action"


def create_langgraph_react():
    """使用 LangGraph 构建 ReAct 循环"""
    builder = StateGraph(ReActState)

    builder.add_node("think", think_step)
    builder.add_node("action", action_step)

    builder.add_edge(START, "think")
    builder.add_edge("think", "action")
    builder.add_conditional_edges("action", should_continue)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


def demo_langgraph_react():
    """演示 LangGraph 实现的 ReAct"""
    print("\n" + "=" * 60)
    print("Demo 2: LangGraph 手写 ReAct 循环")
    print("=" * 60)

    graph = create_langgraph_react()
    config = {"configurable": {"thread_id": "react-demo-1"}}

    question = "北京今天多少度？再算一下 256 / 8 等于多少？"
    print(f"\n用户问题: {question}\n")

    initial_state = {
        "question": question,
        "thoughts": [],
        "actions": [],
        "observations": [],
        "final_answer": "",
        "step_count": 0,
        "max_steps": 3,
    }

    for event in graph.stream(initial_state, config):
        for node, data in event.items():
            if node == "think" and data.get("thoughts"):
                print(f"🤔 思考: {data['thoughts'][-1]}")
            elif node == "action":
                if data.get("actions"):
                    last_action = data["actions"][-1]
                    if not last_action.startswith("FINAL:"):
                        print(f"🔧 行动: {last_action}")
                if data.get("observations"):
                    print(f"👀 {data['observations'][-1]}")
                    print()

    # 获取最终状态
    final_state = graph.get_state(config)
    if final_state and final_state.values.get("final_answer"):
        print(f"\n✅ 最终答案: {final_state.values['final_answer']}")
    else:
        print("\n✅ 任务完成")


if __name__ == "__main__":
    print("🔥 Agent 面试题实战 Demo #01: ReAct 范式\n")

    demo_react_agent()

    if os.getenv("LLM_API_KEY") and os.getenv("LLM_API_KEY") != "your-llm-api-key":
        demo_langgraph_react()
    else:
        print("\n⏭️  LangGraph ReAct 跳过（需配置 LLM_API_KEY）")

    print("\n" + "=" * 60)
    print("📝 面试回答要点总结")
    print("=" * 60)
    print("""
1. ReAct = Reasoning + Acting，让 LLM 边思考边行动
2. 核心循环：Thought → Action → Observation → 继续或结束
3. 优势：
   - 可解释性强（每一步都有思考过程）
   - 能纠错（观察结果可以纠正下一步推理）
   - 能利用外部工具（搜索、计算、API）
4. 劣势：
   - Token 消耗大（每次推理都要输出思考过程）
   - 延迟高（多步循环需要多次 LLM 调用）
   - 复杂任务可能陷入死循环（需要 max_iterations 限制）
5. 框架实现：
   - LangChain: create_react_agent + AgentExecutor
   - LangGraph: StateGraph + 条件边实现循环
    """)
