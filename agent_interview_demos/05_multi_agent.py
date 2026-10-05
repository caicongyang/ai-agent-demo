"""
面试题：Multi-Agent 协作常见模式？子 Agent 之间怎么通信？
============================================================

来源：Agent面试真题01（题6）、阿里Agent面经、快手面经、小红书/字节面经

面试回答要点：
  - 监督者模式（Supervisor）：中心化调度，一个 Supervisor 协调多个 Worker
  - 竞拍模式（Auction）：多个 Agent 竞标任务，最优者执行
  - 流水线模式（Pipeline）：任务分阶段，每个 Agent 处理一个阶段
  - 共享工作空间模式：多个 Agent 共享一个上下文空间，协作完成
  - 通信方式：共享状态、消息队列、函数调用、Event Bus

技术栈：LangGraph Supervisor + 团队协作 + 自定义通信协议
"""

import os
import json
from typing import Any, Dict, List, Optional, TypedDict, Literal
from dotenv import load_dotenv
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()


# ─── 模式一：监督者模式（Supervisor Pattern）────────────

class SupervisorState(TypedDict):
    """监督者模式的状态"""
    task: str
    plan: str
    worker_results: Dict[str, str]
    current_worker: str
    final_answer: str
    max_rounds: int
    round: int


def create_supervisor_workflow():
    """
    监督者模式：一个 Supervisor Agent 协调多个 Worker Agent
    对应面试题："Multi-Agent 协作常见模式有哪些？"
    """
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=0,
    )

    def planner(state: SupervisorState) -> Dict:
        """Supervisor：分析任务，制定计划"""
        prompt = f"""你是一个 Supervisor Agent。分析以下任务并制定执行计划。

任务: {state['task']}

请将任务分解为最多 3 个子任务，每个子任务指定一个 worker 角色。
格式：
## 计划
1. [worker名称]: [子任务描述]
2. [worker名称]: [子任务描述]"""

        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            plan = response.content
            print(f"\n🤖 Supervisor 计划:\n{plan}")
            return {"plan": plan}
        except Exception:
            return {"plan": "计划生成失败"}

    def research_worker(state: SupervisorState) -> Dict:
        """Worker 1：研究员"""
        prompt = f"""你是一个 Research Worker Agent。
任务: {state['task']}
计划: {state['plan']}

请负责研究任务中需要调研的部分，提供详细的分析和见解。"""
        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            result = response.content
            print(f"\n🔬 Research Worker:\n{result[:200]}...")
            return {"worker_results": {**state.get("worker_results", {}),
                                       "researcher": result}}
        except Exception as e:
            return {"worker_results": {**state.get("worker_results", {}),
                                       "researcher": f"错误: {str(e)}"}}

    def coding_worker(state: SupervisorState) -> Dict:
        """Worker 2：编码员"""
        prompt = f"""你是一个 Coding Worker Agent。
任务: {state['task']}

基于研究结果，提供具体的技术实现方案或代码示例。"""
        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            result = response.content
            print(f"\n💻 Coding Worker:\n{result[:200]}...")
            return {"worker_results": {**state.get("worker_results", {}),
                                       "coder": result}}
        except Exception:
            return {"worker_results": {**state.get("worker_results", {}),
                                       "coder": "编码方案生成失败"}}

    def reviewer(state: SupervisorState) -> Dict:
        """Worker 3：评审员"""
        results = state.get("worker_results", {})
        prompt = f"""你是一个 Reviewer Agent。
任务: {state['task']}

研究结果: {results.get('researcher', '无')}
编码方案: {results.get('coder', '无')}

请综合评估工作成果，给出最终答案和改进建议。"""
        try:
            response = llm.invoke([{"role": "user", "content": prompt}])
            print(f"\n✅ Reviewer 最终输出:\n{response.content[:200]}...")
            return {"final_answer": response.content,
                    "round": state.get("round", 0) + 1}
        except Exception:
            return {"final_answer": "评审失败"}

    def should_continue(state: SupervisorState) -> Literal["__end__", "researcher"]:
        """条件：决定是否继续或结束"""
        if state.get("final_answer") or state.get("round", 0) >= state.get("max_rounds", 1):
            return "__end__"
        return "researcher"

    builder = StateGraph(SupervisorState)
    builder.add_node("planner", planner)
    builder.add_node("researcher", research_worker)
    builder.add_node("coder", coding_worker)
    builder.add_node("reviewer", reviewer)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "researcher")
    builder.add_edge("researcher", "coder")
    builder.add_edge("coder", "reviewer")
    builder.add_conditional_edges("reviewer", should_continue)

    return builder.compile()


def demo_supervisor():
    """演示监督者模式"""
    print("=" * 60)
    print("模式一：监督者模式（Supervisor Pattern）")
    print("=" * 60)

    if not os.getenv("LLM_API_KEY") or os.getenv("LLM_API_KEY") == "your-llm-api-key":
        print("\n⏭️  跳过（需配置 LLM_API_KEY）")
        return

    workflow = create_supervisor_workflow()
    result = workflow.invoke({
        "task": "设计一个 AI Agent 系统，包含工具调用和记忆功能",
        "plan": "",
        "worker_results": {},
        "current_worker": "",
        "final_answer": "",
        "max_rounds": 1,
        "round": 0,
    })
    print(f"\n最终输出:\n{result.get('final_answer', '无输出')[:300]}...")


# ─── 模式二：Agent 通信协议 ──────────────────────────────

class Message(TypedDict):
    """Agent 之间的消息结构"""
    sender: str
    receiver: str
    content: str
    msg_type: Literal["task", "result", "query", "response", "broadcast"]
    timestamp: str


class CommunicationProtocol:
    """
    Agent 之间的通信协议
    对应面试题："子 Agent 之间怎么通信"
    """

    def __init__(self):
        self.message_queue: List[Message] = []
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,
        ) if os.getenv("LLM_API_KEY") and os.getenv("LLM_API_KEY") != "your-llm-api-key" else None

    def send(self, msg: Message):
        """发送消息"""
        self.message_queue.append(msg)
        print(f"📨 {msg['sender']} → {msg['receiver']}: {msg['content'][:60]}...")

    def receive(self, agent_name: str) -> List[Message]:
        """接收发送给指定 Agent 的消息"""
        msgs = [m for m in self.message_queue if m["receiver"] == agent_name]
        return msgs

    def broadcast(self, sender: str, content: str, msg_type: str = "broadcast"):
        """广播消息给所有 Agent"""
        msg = Message(
            sender=sender,
            receiver="*ALL*",
            content=content,
            msg_type=msg_type,
            timestamp=datetime.now().isoformat(),
        )
        self.message_queue.append(msg)
        print(f"📢 {sender} 广播: {content[:60]}...")

    def demonstrate(self):
        """演示通信流程"""
        print("=" * 60)
        print("模式二：Agent 通信协议")
        print("=" * 60)

        print("\n1. 点对点通信（Direct Message）")
        self.send({
            "sender": "Supervisor",
            "receiver": "Worker_A",
            "content": "请搜索关于 Multi-Agent 系统的资料",
            "msg_type": "task",
            "timestamp": datetime.now().isoformat(),
        })
        self.send({
            "sender": "Worker_A",
            "receiver": "Supervisor",
            "content": "已找到相关资料：Multi-Agent 系统有3种常见模式...",
            "msg_type": "result",
            "timestamp": datetime.now().isoformat(),
        })

        print("\n2. 广播通信（Broadcast）")
        self.broadcast("Supervisor", "所有 Worker 请注意，任务难度升级")

        print("\n3. Agent 间协作（Agent-to-Agent）")
        self.send({
            "sender": "Worker_A",
            "receiver": "Worker_B",
            "content": "我找到了架构设计资料，需要你的代码实现配合",
            "msg_type": "query",
            "timestamp": datetime.now().isoformat(),
        })
        self.send({
            "sender": "Worker_B",
            "receiver": "Worker_A",
            "content": "收到，我已准备好进行编码实现",
            "msg_type": "response",
            "timestamp": datetime.now().isoformat(),
        })

        print(f"\n📊 通信统计: 共 {len(self.message_queue)} 条消息")

        # 如果 LLM 可用，展示 Agent 如何处理通信
        if self.llm:
            print("\n4. AI 模拟通信处理")
            prompt = f"""你是一个 Agent 通信处理器。
消息队列中的最新消息：{json.dumps(self.message_queue[-1], ensure_ascii=False)}

请分析这条消息的意图，并决定如何响应。"""
            response = self.llm.invoke([{"role": "user", "content": prompt}])
            print(f"🤖 通信分析结果: {response.content}")


# ─── 模式三：共享工作空间（演示架构）────────────────────

class SharedWorkspace:
    """
    共享工作空间模式
    对应面试题："Multi-Agent 如何共享上下文"
    """

    def __init__(self):
        self.shared_context: Dict[str, Any] = {
            "task_description": "",
            "progress": 0.0,
            "artifacts": [],
            "decisions": [],
        }

    def read(self, agent_name: str) -> Dict:
        """Agent 读取共享空间"""
        print(f"👀 {agent_name} 读取工作空间状态")
        return dict(self.shared_context)

    def write(self, agent_name: str, key: str, value: Any):
        """Agent 写入共享空间"""
        self.shared_context[key] = value
        print(f"✍️ {agent_name} 更新了 '{key}': {str(value)[:50]}...")

    def add_artifact(self, agent_name: str, artifact: Dict):
        """Agent 添加产出物"""
        self.shared_context["artifacts"].append({
            **artifact,
            "creator": agent_name,
            "timestamp": datetime.now().isoformat(),
        })
        print(f"📦 {agent_name} 添加了产出物: {artifact.get('name', 'unnamed')}")

    def demonstrate(self):
        """演示共享工作空间"""
        print("\n" + "=" * 60)
        print("模式三：共享工作空间模式")
        print("=" * 60)

        agents = ["架构师Agent", "开发者Agent", "测试Agent"]

        # 架构师规划
        self.write("架构师Agent", "task_description",
                    "设计一个 Agent 面试题 Demo 系统")
        self.add_artifact("架构师Agent", {
            "name": "Architecture Design",
            "type": "设计文档",
            "content": "采用 LangGraph Supervisor 模式",
        })

        # 开发者实现
        workspace = self.read("开发者Agent")
        self.add_artifact("开发者Agent", {
            "name": "ReAct Agent Implementation",
            "type": "代码",
            "content": "实现 ReAct 循环的核心逻辑",
        })

        # 测试验证
        self.read("测试Agent")
        self.write("测试Agent", "progress", 0.75)
        self.add_artifact("测试Agent", {
            "name": "Test Report",
            "type": "报告",
            "content": "所有测试用例通过",
        })

        print(f"\n📊 最终工作空间:")
        print(json.dumps(self.shared_context, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    print("🔥 Agent 面试题实战 Demo #05: Multi-Agent 协作模式\n")

    # 模式一
    if os.getenv("LLM_API_KEY") and os.getenv("LLM_API_KEY") != "your-llm-api-key":
        demo_supervisor()
    else:
        print("⏭️  Supervisor 模式跳过（需配置 LLM_API_KEY）")

    # 模式二
    protocol = CommunicationProtocol()
    protocol.demonstrate()

    # 模式三
    workspace = SharedWorkspace()
    workspace.demonstrate()

    print("\n" + "=" * 60)
    print("📝 面试回答要点总结")
    print("=" * 60)
    print("""
1. 四种常见协作模式：
   - 监督者模式：中心化调度，适合确定性任务
   - 竞拍模式：市场化分配，适合竞争性任务
   - 流水线模式：阶段化处理，适合流程性任务
   - 共享工作空间：去中心化协作，适合创意性任务

2. 通信方式：
   - 直接消息（点对点）：确定性通信
   - 广播（一对多）：状态通知
   - 共享状态：工作空间/黑板模式
   - 消息队列：异步解耦

3. 面试关键点：
   - 理解不同模式的适用场景
   - 能分析通信开销和性能影响
   - 有实际 Multi-Agent 项目经验
    """)
