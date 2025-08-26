"""
写入上下文演示 (Write Context Demo)
演示如何在 LangGraph 中写入上下文，包括草稿本（短期记忆）和记忆（长期记忆）
"""

import os
from typing import TypedDict
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore
from rich.console import Console
from rich.panel import Panel

console = Console()

# 设置环境变量
def setup_environment():
    """设置必要的环境变量"""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        api_key = input("请输入您的 ANTHROPIC_API_KEY: ")
        os.environ["ANTHROPIC_API_KEY"] = api_key

# 状态定义
class ResearchState(TypedDict):
    """研究任务的状态定义"""
    topic: str           # 研究主题
    initial_thoughts: str # 初始想法
    research_plan: str   # 研究计划
    findings: str        # 研究发现
    summary: str         # 最终总结

# 初始化组件
def initialize_components():
    """初始化 LLM、检查点和存储"""
    setup_environment()
    
    llm = init_chat_model("anthropic:claude-3-5-sonnet-20241022", temperature=0.7)
    checkpointer = InMemorySaver()  # 短期记忆（草稿本）
    memory_store = InMemoryStore()  # 长期记忆
    namespace = ("user_demo", "research_assistant")
    
    return llm, checkpointer, memory_store, namespace

# 节点函数
def generate_initial_thoughts(state: ResearchState) -> dict:
    """生成初始想法并写入状态（草稿本）"""
    llm, _, _, _ = initialize_components()
    
    console.print(Panel(
        f"🧠 正在为主题 '{state['topic']}' 生成初始想法...",
        title="写入上下文 - 草稿本",
        border_style="blue"
    ))
    
    prompt = f"""作为一个研究助手，请为主题 "{state['topic']}" 生成一些初始的研究想法和方向。
    请提供 3-5 个具体的研究角度或问题。"""
    
    response = llm.invoke(prompt)
    thoughts = response.content
    
    console.print(Panel(
        thoughts,
        title="✅ 初始想法已写入状态",
        border_style="green"
    ))
    
    # 写入状态（草稿本）
    return {"initial_thoughts": thoughts}

def create_research_plan(state: ResearchState, store: BaseStore) -> dict:
    """基于初始想法创建研究计划，并保存到长期记忆"""
    llm, _, _, namespace = initialize_components()
    
    console.print(Panel(
        "📋 正在创建详细的研究计划...",
        title="写入上下文 - 长期记忆",
        border_style="blue"
    ))
    
    # 检查是否有历史研究计划
    existing_plans = list(store.search(namespace))
    history_context = ""
    if existing_plans:
        history_context = f"\n历史研究记录：\n{existing_plans[0].value.get('plan', '')}"
    
    prompt = f"""基于以下初始想法创建一个详细的研究计划：

初始想法：
{state['initial_thoughts']}

{history_context}

请创建一个包含以下要素的研究计划：
1. 研究目标
2. 研究方法
3. 预期成果
4. 时间安排"""
    
    response = llm.invoke(prompt)
    plan = response.content
    
    # 保存到长期记忆
    store.put(
        namespace,
        f"research_plan_{state['topic'].replace(' ', '_')}",
        {
            "topic": state['topic'],
            "plan": plan,
            "timestamp": "2024-01-01",  # 实际应用中使用真实时间戳
            "type": "research_plan"
        }
    )
    
    console.print(Panel(
        plan,
        title="✅ 研究计划已保存到长期记忆",
        border_style="green"
    ))
    
    return {"research_plan": plan}

def conduct_research(state: ResearchState) -> dict:
    """模拟进行研究并记录发现"""
    llm, _, _, _ = initialize_components()
    
    console.print(Panel(
        "🔍 正在进行研究并记录发现...",
        title="写入上下文 - 草稿本更新",
        border_style="blue"
    ))
    
    prompt = f"""基于以下研究计划进行模拟研究：

研究计划：
{state['research_plan']}

请模拟研究过程并提供一些关键发现和洞察。"""
    
    response = llm.invoke(prompt)
    findings = response.content
    
    console.print(Panel(
        findings,
        title="✅ 研究发现已写入状态",
        border_style="green"
    ))
    
    return {"findings": findings}

def create_summary(state: ResearchState, store: BaseStore) -> dict:
    """创建最终总结并更新长期记忆"""
    llm, _, _, namespace = initialize_components()
    
    console.print(Panel(
        "📝 正在创建最终总结...",
        title="写入上下文 - 综合记忆",
        border_style="blue"
    ))
    
    prompt = f"""基于整个研究过程创建一个综合总结：

主题：{state['topic']}
初始想法：{state['initial_thoughts']}
研究计划：{state['research_plan']}
研究发现：{state['findings']}

请创建一个包含关键洞察和结论的总结。"""
    
    response = llm.invoke(prompt)
    summary = response.content
    
    # 更新长期记忆中的研究记录
    store.put(
        namespace,
        f"research_summary_{state['topic'].replace(' ', '_')}",
        {
            "topic": state['topic'],
            "summary": summary,
            "full_research": {
                "initial_thoughts": state['initial_thoughts'],
                "plan": state['research_plan'],
                "findings": state['findings'],
                "summary": summary
            },
            "timestamp": "2024-01-01",
            "type": "research_summary"
        }
    )
    
    console.print(Panel(
        summary,
        title="✅ 最终总结已保存到长期记忆",
        border_style="green"
    ))
    
    return {"summary": summary}

def build_write_context_workflow():
    """构建写入上下文的工作流"""
    llm, checkpointer, memory_store, namespace = initialize_components()
    
    # 创建状态图
    workflow = StateGraph(ResearchState)
    
    # 添加节点
    workflow.add_node("generate_thoughts", generate_initial_thoughts)
    workflow.add_node("create_plan", create_research_plan)
    workflow.add_node("conduct_research", conduct_research)
    workflow.add_node("create_summary", create_summary)
    
    # 添加边
    workflow.add_edge(START, "generate_thoughts")
    workflow.add_edge("generate_thoughts", "create_plan")
    workflow.add_edge("create_plan", "conduct_research")
    workflow.add_edge("conduct_research", "create_summary")
    workflow.add_edge("create_summary", END)
    
    # 编译工作流（包含检查点和存储）
    app = workflow.compile(checkpointer=checkpointer, store=memory_store)
    
    return app, memory_store, namespace

def demonstrate_write_context():
    """演示写入上下文功能"""
    console.print(Panel(
        "🚀 LangGraph 写入上下文演示",
        title="Context Engineering Demo",
        border_style="bold blue"
    ))
    
    app, memory_store, namespace = build_write_context_workflow()
    
    # 配置会话
    config = {"configurable": {"thread_id": "write_demo_1"}}
    
    # 运行工作流
    topic = "人工智能在教育中的应用"
    console.print(f"\n📚 开始研究主题: {topic}\n")
    
    result = app.invoke({"topic": topic}, config)
    
    # 显示最终状态
    console.print(Panel(
        f"""主题: {result['topic']}
        
状态中的信息（草稿本）:
• 初始想法: {len(result['initial_thoughts'])} 字符
• 研究计划: {len(result['research_plan'])} 字符  
• 研究发现: {len(result['findings'])} 字符
• 最终总结: {len(result['summary'])} 字符""",
        title="📊 写入上下文总结",
        border_style="bold green"
    ))
    
    # 显示长期记忆中的内容
    stored_items = list(memory_store.search(namespace))
    console.print(Panel(
        f"长期记忆中保存了 {len(stored_items)} 项记录:\n" + 
        "\n".join([f"• {item.key}: {item.value['type']}" for item in stored_items]),
        title="🧠 长期记忆状态",
        border_style="bold purple"
    ))
    
    return result, memory_store

if __name__ == "__main__":
    result, store = demonstrate_write_context()
