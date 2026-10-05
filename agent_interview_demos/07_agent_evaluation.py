"""
面试题：如何评估 Agent 的效果？
================================

来源：Agent面试真题01（题10）、面试官视角/Agent 工程师面试、微信/秋招复盘

面试回答要点：
  - 任务完成率（Success Rate）：Agent 成功完成任务的占比
  - 工具选择准确率（Tool Selection Accuracy）：正确选择工具的比率
  - Token 效率（Token Efficiency）：完成任务消耗的 Token 数
  - 响应延迟（Latency）：从输入到输出的时间
  - 鲁棒性（Robustness）：异常场景下的表现
  - Eval 体系：离线评估 + 在线评估 + A/B 测试

技术栈：LangChain Agent + 自定义 Eval 框架 + 统计指标
"""

import os
import json
import time
import random
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

load_dotenv()


# ─── 评估指标定义 ────────────────────────────────────────

class EvalMetric(Enum):
    """评估指标类型"""
    SUCCESS_RATE = "success_rate"               # 任务完成率
    TOOL_ACCURACY = "tool_accuracy"              # 工具选择准确率
    TOKEN_EFFICIENCY = "token_efficiency"        # Token 效率
    LATENCY = "latency"                          # 响应延迟
    COST_PER_TASK = "cost_per_task"              # 单任务成本
    ROBUSTNESS = "robustness"                    # 鲁棒性


@dataclass
class EvalResult:
    """单个评估结果"""
    task_id: str
    task_description: str
    success: bool
    tool_calls: int
    correct_tool_calls: int
    total_tokens: int
    latency_ms: float
    error_message: str = ""
    expected_tools: List[str] = field(default_factory=list)
    actual_tools: List[str] = field(default_factory=list)


# ─── Agent Eval 框架 ────────────────────────────────────

class AgentEvalFramework:
    """
    Agent 评估框架
    对应面试题："如何评估 Agent 的效果"
    """

    def __init__(self):
        self.results: List[EvalResult] = []
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,
        ) if os.getenv("LLM_API_KEY") and os.getenv("LLM_API_KEY") != "your-llm-api-key" else None

    # ─── 测试用例 ──────────────────────────────────────
    @staticmethod
    def get_test_cases() -> List[Dict]:
        """标准测试用例集"""
        return [
            {
                "id": "T001",
                "task": "搜索天气并计算温度差",
                "expected_tools": ["weather", "calculator"],
                "complexity": "medium",
            },
            {
                "id": "T002",
                "task": "计算 256 * 48 等于多少",
                "expected_tools": ["calculator"],
                "complexity": "easy",
            },
            {
                "id": "T003",
                "task": "解释什么是 ReAct 范式",
                "expected_tools": ["knowledge_base"],
                "complexity": "easy",
            },
            {
                "id": "T004",
                "task": "先搜索北京天气，再计算和上海的温度差",
                "expected_tools": ["weather", "calculator"],
                "complexity": "hard",
            },
            {
                "id": "T005",
                "task": "查询不存在的API接口返回什么",
                "expected_tools": ["api_query"],
                "complexity": "error_case",
            },
            {
                "id": "T006",
                "task": "先在知识库搜索 Agent 定义，再搜索 Multi-Agent 协作模式",
                "expected_tools": ["knowledge_base", "knowledge_base"],
                "complexity": "medium",
            },
        ]

    # ─── 模拟 Agent 执行 ───────────────────────────────
    def simulate_agent_execution(self, task: Dict) -> EvalResult:
        """
        模拟 Agent 执行并收集指标
        在实际场景中，这里会调用真实的 Agent
        """
        tools_used = []
        tool_accuracy = 0
        start_time = time.time()

        # 模拟工具调用
        complexity_multiplier = {"easy": 1, "medium": 2, "hard": 3, "error_case": 1}
        n_calls = complexity_multiplier.get(task["complexity"], 1)

        for i in range(n_calls):
            # 模拟工具选择（有概率选错）
            if random.random() < 0.85:  # 85% 正确率
                if i < len(task["expected_tools"]):
                    tools_used.append(task["expected_tools"][i])
                else:
                    tools_used.append("knowledge_base")
            else:
                # 选错了
                wrong_choices = ["weather", "calculator", "knowledge_base", "api_query"]
                wrong = random.choice([t for t in wrong_choices if t not in task["expected_tools"]])
                tools_used.append(wrong)

            time.sleep(0.01)  # 模拟延迟

        latency = (time.time() - start_time) * 1000

        # 计算指标
        correct = sum(1 for t in tools_used if t in task["expected_tools"])
        total = max(len(tools_used), 1)
        success = correct == len(task["expected_tools"]) and len(tools_used) == len(task["expected_tools"])

        return EvalResult(
            task_id=task["id"],
            task_description=task["task"],
            success=success,
            tool_calls=len(tools_used),
            correct_tool_calls=correct,
            total_tokens=random.randint(500, 2000),
            latency_ms=round(latency, 2),
            expected_tools=task["expected_tools"],
            actual_tools=tools_used,
        )

    # ─── LLM 评估 ──────────────────────────────────────
    def llm_evaluate(self, task: str, response: str) -> Dict:
        """使用 LLM 评估回答质量"""
        if not self.llm:
            return {"quality_score": "N/A", "analysis": "需要配置 LLM_API_KEY"}

        prompt = f"""你是一个 Agent 评估专家。请评估以下 AI Agent 的回答质量。

任务: {task}
Agent 回答: {response}

请从以下维度打分（1-10）：
1. 相关性：回答是否针对问题
2. 完整性：是否覆盖所有要点
3. 准确性：信息是否准确
4. 清晰度：表达是否清晰

返回 JSON 格式：{{"score": 8, "analysis": "..."}}"""

        try:
            result = self.llm.invoke([{"role": "user", "content": prompt}])
            return {"quality_score": result.content, "analyzer": "LLM"}
        except Exception as e:
            return {"quality_score": "error", "analysis": str(e)}

    # ─── 运行评估 ──────────────────────────────────────
    def run_evaluation(self, n_runs: int = 3) -> Dict[str, Any]:
        """
        运行完整的评估流程
        """
        print("=" * 60)
        print("面试题：如何评估 Agent 的效果？")
        print("=" * 60)

        test_cases = self.get_test_cases()

        # 多次运行取平均值
        for run in range(n_runs):
            print(f"\n--- Run {run + 1}/{n_runs} ---")
            random.seed(run)  # 每次运行结果不同

            for case in test_cases:
                result = self.simulate_agent_execution(case)
                self.results.append(result)

                status = "✅" if result.success else "❌"
                acc = f"{result.correct_tool_calls}/{result.tool_calls}"
                print(f"  {status} {result.task_id}: {result.task_description[:30]}... "
                      f"工具准确率={acc}, 延迟={result.latency_ms}ms")

        # 计算统计数据
        stats = self.calculate_stats()
        self.print_report(stats)
        return stats

    # ─── 统计分析 ──────────────────────────────────────
    def calculate_stats(self) -> Dict[str, Any]:
        """计算统计指标"""
        if not self.results:
            return {}

        total = len(self.results)
        successes = sum(1 for r in self.results if r.success)

        # 工具准确率
        total_tool_calls = sum(r.tool_calls for r in self.results)
        total_correct_tools = sum(r.correct_tool_calls for r in self.results)

        # 延迟和 Token
        avg_latency = sum(r.latency_ms for r in self.results) / total
        avg_tokens = sum(r.total_tokens for r in self.results) / total

        # 按复杂度分组
        easy_results = [r for r in self.results if "easy" in str(r.task_id) or len(r.expected_tools) <= 1]
        hard_results = [r for r in self.results if r.tool_calls >= 2]

        return {
            "total_tasks": total,
            "success_rate": successes / total * 100,
            "success_count": successes,
            "failed_count": total - successes,
            "tool_accuracy": total_correct_tools / total_tool_calls * 100
            if total_tool_calls > 0 else 0,
            "avg_latency_ms": round(avg_latency, 2),
            "avg_tokens_per_task": round(avg_tokens, 0),
            "simple_task_success": round(
                (sum(1 for r in easy_results if r.success) / len(easy_results) * 100)
                if easy_results else 0, 1),
            "complex_task_success": round(
                (sum(1 for r in hard_results if r.success) / len(hard_results) * 100)
                if hard_results else 0, 1),
        }

    def print_report(self, stats: Dict[str, Any]):
        """打印评估报告"""
        print("\n" + "=" * 50)
        print("📊 Agent 评估报告")
        print("=" * 50)

        print(f"""
## 核心指标

| 指标 | 数值 |
|------|------|
| 测试任务数 | {stats.get('total_tasks', 0)} |
| 任务完成率 | {stats.get('success_rate', 0):.1f}% ✅ |
| 工具选择准确率 | {stats.get('tool_accuracy', 0):.1f}% |
| 平均响应延迟 | {stats.get('avg_latency_ms', 0)} ms |
| 单任务平均 Token | {stats.get('avg_tokens_per_task', 0)} |
""")

        print("## 场景分析")
        print(f"""
| 场景 | 成功率 |
|------|--------|
| 简单任务 | {stats.get('simple_task_success', 0):.1f}% |
| 复杂任务 | {stats.get('complex_task_success', 0):.1f}% |
""")

        # 失败分析
        failed = [r for r in self.results if not r.success]
        if failed:
            print("## 失败任务分析")
            for f in failed:
                print(f"- {f.task_id}: {f.task_description}")
                print(f"  期望工具: {f.expected_tools} → 实际使用: {f.actual_tools}")
                print()

    def to_markdown(self) -> str:
        """导出 Markdown 格式报告"""
        stats = self.calculate_stats()
        lines = ["# Agent 评估报告", "", "## 概述", ""]
        lines.append(f"- 测试任务数: {stats.get('total_tasks', 0)}")
        lines.append(f"- 任务完成率: {stats.get('success_rate', 0):.1f}%")
        lines.append(f"- 工具准确率: {stats.get('tool_accuracy', 0):.1f}%")
        lines.append(f"- 平均延迟: {stats.get('avg_latency_ms', 0)}ms")
        lines.append("")
        lines.append("## 详细结果")
        lines.append("")
        lines.append("| ID | 任务 | 状态 | 工具准确率 | 延迟 |")
        lines.append("|-----|------|------|-----------|------|")
        for r in self.results:
            status = "✅" if r.success else "❌"
            acc = f"{r.correct_tool_calls}/{r.tool_calls}"
            lines.append(f"| {r.task_id} | {r.task_description[:20]}... | {status} | {acc} | {r.latency_ms}ms |")
        lines.append("")
        return "\n".join(lines)


def demo_eval_framework():
    """演示 Eval 框架"""
    framework = AgentEvalFramework()
    stats = framework.run_evaluation(n_runs=2)

    # 导出报告
    report = framework.to_markdown()
    report_path = "./.agent_eval_report.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\n📄 完整报告已导出: {report_path}")

    return framework


def demo_llm_eval():
    """演示 LLM 评估"""
    print("\n" + "=" * 60)
    print("Demo: LLM 评估回答质量")
    print("=" * 60)

    framework = AgentEvalFramework()
    result = framework.llm_evaluate(
        "什么是 ReAct 范式？",
        "ReAct 是 Reasoning + Acting 的缩写，让 LLM 在推理的同时采取行动。"
        "核心是 Thought → Action → Observation 循环。",
    )
    print(f"\nLLM 评估结果:\n{result['quality_score']}")


def interview_answer():
    """面试回答框架"""
    print("\n" + "=" * 60)
    print("📝 面试回答框架")
    print("=" * 60)
    print("""
"如何评估 Agent 的效果" 的回答框架：

1️⃣ 先说维度（展示知识广度）
   "Agent 评估从五个维度进行：
    - 任务完成率（Success Rate）
    - 工具选择准确率（Tool Selection Accuracy）
    - Token 效率（Efficiency）
    - 响应延迟（Latency）
    - 鲁棒性（Robustness）"

2️⃣ 再说方法（展示系统设计能力）
   "评估方法论：
    - 离线评估：构造测试集，自动化跑分
    - 在线评估：A/B 测试，用户反馈
    - LLM-as-Judge：用更强的模型评估输出质量
    - 人工评估：抽样标注"

3️⃣ 最后举例子（展示实战经验）
   "我设计过一个 Eval 框架：
    - 6 个标准测试用例（简单/复杂/异常场景）
    - 自动化跑分 + 统计报告
    - 每次代码变更后自动回归
    - 和 CI/CD 集成，设置质量门禁"
    """)


if __name__ == "__main__":
    print("🔥 Agent 面试题实战 Demo #07: Agent 评估体系\n")

    demo_eval_framework()
    demo_llm_eval()
    interview_answer()
