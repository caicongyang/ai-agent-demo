"""
面试题：Plan-and-Execute 模式 / LangGraph 工作流
==================================================

来源：Agent面试真题01（题5）、面了阿里大模型Agent、微信/秋招复盘

面试回答要点：
  - Plan-and-Execute：先制定计划，再逐步执行
  - 与 ReAct 的区别：Plan-and-Execute 先规划再执行，ReAct 边想边做
  - 适用场景：复杂多步骤任务、可预见的子任务
  - LangGraph 状态图：StateGraph + 节点 + 边 + 状态管理
  - 条件分支：根据执行结果动态选择下一步

技术栈：LangGraph StateGraph + Plan-Execute + 条件分支 + 人工介入
"""

import os
import json
from typing import Any, Dict, List, Optional, TypedDict, Literal
from dotenv import load_dotenv
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()


# ─── Plan-and-Execute 状态定义 ──────────────────────────

class PlanState(TypedDict):
    """Plan-and-Execute 状态"""
    goal: str                          # 目标
    plan: List[str]                    # 计划步骤列表
    current_step: int                  # 当前步骤索引
    step_results: Dict[str, str]       # 步骤执行结果
    observations: List[str]            # 观察记录
    final_answer: str                  # 最终答案
    needs_replan: bool                 # 是否需要重新规划
    iterations: int                    # 迭代次数
    max_iterations: int               # 最大迭代次数


# ─── Plan-and-Execute Graph ─────────────────────────────

def create_plan_execute_workflow():
    """
    Plan-and-Execute：先规划后执行
    对应面试题："什么是 Plan-and-Execute？和 ReAct 的区别？"
    """
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )

    def planner(state: PlanState) -> Dict:
        """规划节点：制定执行计划"""
        prompt = f"""你是一个任务规划器。请将以下目标分解为具体的执行步骤。

目标: {state['goal']}

要求：
1. 将目标分解为 3-5 个步骤
2. 每个步骤应该是可执行的子任务
3. 步骤之间应该有逻辑顺序

请直接列出步骤，每行一个："""

        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            plan_text = response.content.strip()
            steps = [s.strip().lstrip("1234567890. ") for s in plan_text.split("\n") if s.strip()]
            print(f"\n📋 制定的计划:")
            for i, step in enumerate(steps, 1):
                print(f"  步骤 {i}: {step}")
            return {"plan": steps, "current_step": 0}
        except Exception as e:
            return {"plan": [f"直接执行: {state['goal']}"],
                    "current_step": 0}

    def executor(state: PlanState) -> Dict:
        """执行节点：执行当前步骤"""
        if state["current_step"] >= len(state["plan"]):
            return {"final_answer": "所有步骤执行完成", "current_step": state["current_step"]}

        step = state["plan"][state["current_step"]]
        print(f"\n▶️ 执行步骤 {state['current_step'] + 1}: {step}")

        prompt = f"""你是一个任务执行器。请执行以下步骤。

目标: {state['goal']}
当前步骤: {step}
之前步骤的结果: {json.dumps(state.get('step_results', {}), ensure_ascii=False)}

请执行这个步骤，返回执行结果。"""

        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            result = response.content
            step_key = f"step_{state['current_step']}"
            print(f"  ✅ 执行结果: {result[:100]}...")

            return {
                "step_results": {**state.get("step_results", {}), step_key: result},
                "current_step": state["current_step"] + 1,
                "observations": state.get("observations", [])
                + [f"步骤 {state['current_step'] + 1}: {result[:50]}..."],
            }
        except Exception as e:
            return {
                "step_results": {**state.get("step_results", {}),
                                 f"step_{state['current_step']}": f"错误: {str(e)}"},
                "current_step": state["current_step"] + 1,
            }

    def checker(state: PlanState) -> Dict:
        """检查节点：验证执行结果，决定是继续还是调整"""
        if state["current_step"] >= len(state["plan"]):
            prompt = f"""你是一个结果汇总器。请总结以下任务的全部执行结果。

目标: {state['goal']}
所有步骤结果: {json.dumps(state.get('step_results', {}), ensure_ascii=False)}

请给出完整的最终答案。"""

            try:
                response = llm.invoke([{"role": "user", "content": prompt}])
                return {"final_answer": response.content}
            except Exception:
                return {"final_answer": "结果汇总失败"}

        return {}

    def should_continue(state: PlanState) -> Literal["executor", "planner", "__end__"]:
        """决定下一步：继续执行、重新规划或结束"""
        if state.get("final_answer"):
            return "__end__"
        if state.get("iterations", 0) >= state.get("max_iterations", 5):
            return "__end__"
        if state.get("needs_replan"):
            return "planner"
        if state["current_step"] < len(state["plan"]):
            return "executor"
        return "executor"

    builder = StateGraph(PlanState)

    builder.add_node("planner", planner)
    builder.add_node("executor", executor)
    builder.add_node("checker", checker)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "executor")
    builder.add_edge("executor", "checker")
    builder.add_conditional_edges("checker", should_continue, {
        "executor": "executor",
        "planner": "planner",
        "__end__": END,
    })

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


# ─── LangGraph 条件分支演示 ─────────────────────────────

class BranchState(TypedDict):
    """条件分支状态"""
    input_data: str
    analysis: str
    difficulty: Literal["easy", "medium", "hard"]
    route: str
    output: str


def create_branching_workflow():
    """
    条件分支图：根据任务难度走不同路径
    对应面试题："LangGraph 如何处理条件分支？"
    """
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )

    def classifier(state: BranchState) -> Dict:
        """分类节点：判断任务难度"""
        prompt = f"""分析以下任务的难度。只回复 "easy"、"medium" 或 "hard"。

任务: {state['input_data']}

难度判断标准：
- easy: 单步任务，只需直接回答
- medium: 需要多步推理或工具调用
- hard: 需要复杂推理、多个工具和外部知识"""

        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            difficulty = response.content.strip().lower()
            difficulty = "easy" if difficulty not in ["easy", "medium", "hard"] else difficulty
        except Exception:
            difficulty = "easy"

        print(f"\n📊 任务难度分析: {difficulty}")
        return {"analysis": f"任务难度: {difficulty}", "difficulty": difficulty}

    def easy_handler(state: BranchState) -> Dict:
        """简单任务处理"""
        llm_local = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,
        )
        prompt = f"这是一个简单任务。请直接回答：{state['input_data']}"
        response = llm_local.invoke([{"role": "user", "content": prompt}])
        print(f"  🟢 简单路径处理完成")
        return {"route": "easy", "output": response.content}

    def medium_handler(state: BranchState) -> Dict:
        """中等任务处理"""
        llm_local = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,
        )
        prompt = f"""这是一个中等难度任务。请分步骤解答。
任务: {state['input_data']}
分析: {state['analysis']}

请先拆解问题，再逐步回答。"""
        response = llm_local.invoke([{"role": "user", "content": prompt}])
        print(f"  🟡 中等路径处理完成")
        return {"route": "medium", "output": response.content}

    def hard_handler(state: BranchState) -> Dict:
        """复杂任务处理"""
        llm_local = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,
        )
        prompt = f"""这是一个复杂任务。请按以下框架回答：
1. 问题分析
2. 方法论
3. 详细解答
4. 总结

任务: {state['input_data']}"""
        response = llm_local.invoke([{"role": "user", "content": prompt}])
        print(f"  🔴 复杂路径处理完成")
        return {"route": "hard", "output": response.content}

    def route_by_difficulty(state: BranchState) -> Literal["easy_handler", "medium_handler", "hard_handler"]:
        """根据难度路由"""
        return f"{state['difficulty']}_handler"

    builder = StateGraph(BranchState)
    builder.add_node("classifier", classifier)
    builder.add_node("easy_handler", easy_handler)
    builder.add_node("medium_handler", medium_handler)
    builder.add_node("hard_handler", hard_handler)

    builder.add_edge(START, "classifier")
    builder.add_conditional_edges(
        "classifier",
        route_by_difficulty,
        {
            "easy_handler": "easy_handler",
            "medium_handler": "medium_handler",
            "hard_handler": "hard_handler",
        },
    )
    for handler in ["easy_handler", "medium_handler", "hard_handler"]:
        builder.add_edge(handler, END)

    return builder.compile()


# ─── 演示 ──────────────────────────────────────────────

def demo_plan_execute():
    """演示 Plan-and-Execute 模式"""
    print("=" * 60)
    print("面试题：Plan-and-Execute 模式")
    print("=" * 60)

    if not os.getenv("LLM_API_KEY") or os.getenv("LLM_API_KEY") == "your-llm-api-key":
        print("\n⏭️  跳过（需配置 LLM_API_KEY）")
        return

    workflow = create_plan_execute_workflow()
    config = {"configurable": {"thread_id": "plan-demo-1"}}

    goal = "比较 Python 和 Java 两种编程语言在 AI 开发中的优劣"
    print(f"\n🎯 目标: {goal}")

    result = workflow.invoke({
        "goal": goal,
        "plan": [],
        "current_step": 0,
        "step_results": {},
        "observations": [],
        "final_answer": "",
        "needs_replan": False,
        "iterations": 0,
        "max_iterations": 5,
    }, config)

    print(f"\n✅ 最终答案:")
    print(result.get('final_answer', '无输出')[:500])


def demo_branching():
    """演示条件分支"""
    print("\n" + "=" * 60)
    print("LangGraph 条件分支演示")
    print("=" * 60)

    if not os.getenv("LLM_API_KEY") or os.getenv("LLM_API_KEY") == "your-llm-api-key":
        print("\n⏭️  跳过（需配置 LLM_API_KEY）")
        return

    workflow = create_branching_workflow()

    test_cases = [
        "今天几号？",
        "比较 ReAct 和 Plan-and-Execute 的区别",
        "设计一个生产级的 Multi-Agent 系统，支持高并发和故障恢复",
    ]

    for case in test_cases:
        print(f"\n📝 任务: {case[:40]}...")
        result = workflow.invoke({"input_data": case, "analysis": "",
                                   "difficulty": "easy", "route": "", "output": ""})
        print(f"  路径: {result.get('route', 'N/A')}")
        print(f"  输出: {result.get('output', '')[:100]}...")


def architecture_diagram():
    """面试时画架构图"""
    print("\n" + "=" * 60)
    print("📐 LangGraph Plan-Execute 架构图")
    print("=" * 60)
    print("""
        ┌──────────┐
        │  START   │
        └────┬─────┘
             │
        ┌────▼─────┐
        │ Planner  │  ← 制定计划（LLM 分解任务）
        │ (规划)   │
        └────┬─────┘
             │
        ┌────▼─────┐
        │ Executor │  ← 执行当前步骤（循环）
        │ (执行)   │
        └────┬─────┘
             │
        ┌────▼─────┐
        │ Checker  │  ← 检查结果，决定下一步
        │ (检查)   │
        └────┬─────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
 继续执行  重新规划  结束
                         
    """)


if __name__ == "__main__":
    print("🔥 Agent 面试题实战 Demo #08: LangGraph 工作流\n")

    if os.getenv("LLM_API_KEY") and os.getenv("LLM_API_KEY") != "your-llm-api-key":
        demo_plan_execute()
        demo_branching()
    else:
        print("⏭️  Demo 跳过（需配置 LLM_API_KEY）")

    architecture_diagram()

    print("\n" + "=" * 60)
    print("📝 面试回答要点总结")
    print("=" * 60)
    print("""
1. Plan-and-Execute vs ReAct：
   - Plan-and-Execute：先规划再执行，适合结构化任务
   - ReAct：边推理边行动，适合探索性任务
   - 选型：已知步骤用 Plan-Execute，未知探索用 ReAct

2. LangGraph 核心概念：
   - StateGraph：状态驱动的图
   - Node：处理节点（planner, executor, checker）
   - Edge：连接节点的边
   - Conditional Edge：条件分支
   - Checkpoint：状态持久化（MemorySaver）

3. 条件分支实现：
   - add_conditional_edges：动态路由
   - 根据节点输出决定下一步
   - 支持循环、分支、合并

4. 生产级考虑：
   - 最大迭代次数防止死循环
   - 人工介入（Human-in-the-Loop）
   - 状态持久化（断点续跑）
   - 监控和日志
    """)
