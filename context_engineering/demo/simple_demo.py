"""
简化版上下文工程演示
用于快速测试和理解核心概念
"""

import os
from typing import TypedDict
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from rich.console import Console

console = Console()

class SimpleState(TypedDict):
    topic: str
    analysis: str
    summary: str
    step_count: int

def setup_simple_demo():
    """设置简单演示"""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        api_key = input("请输入您的 ANTHROPIC_API_KEY: ")
        os.environ["ANTHROPIC_API_KEY"] = api_key
    
    llm = init_chat_model("anthropic:claude-3-5-sonnet-20241022", temperature=0.7)
    checkpointer = InMemorySaver()
    memory_store = InMemoryStore()
    namespace = ("simple_demo", "test")
    
    return llm, checkpointer, memory_store, namespace

def write_step(state: SimpleState, store) -> dict:
    """写入上下文演示"""
    console.print("📝 [bold blue]Write Context[/bold blue] - 写入分析到状态和记忆")
    
    llm, _, _, namespace = setup_simple_demo()
    
    prompt = f"请简单分析主题：{state['topic']}"
    response = llm.invoke(prompt)
    analysis = response.content
    
    # 写入长期记忆
    store.put(namespace, "analysis", {"content": analysis})
    
    console.print(f"✅ 写入完成：{analysis[:50]}...")
    
    return {"analysis": analysis, "step_count": state.get("step_count", 0) + 1}

def select_step(state: SimpleState, store) -> dict:
    """选择上下文演示"""
    console.print("🎯 [bold green]Select Context[/bold green] - 从记忆中选择信息")
    
    _, _, _, namespace = setup_simple_demo()
    
    # 从记忆中选择
    stored_analysis = store.get(namespace, "analysis")
    selected_content = stored_analysis.value["content"] if stored_analysis else "无记忆"
    
    console.print(f"✅ 选择完成：{selected_content[:50]}...")
    
    return {"step_count": state["step_count"] + 1}

def compress_step(state: SimpleState) -> dict:
    """压缩上下文演示"""
    console.print("🗜️ [bold yellow]Compress Context[/bold yellow] - 压缩长文本")
    
    llm, _, _, _ = setup_simple_demo()
    
    long_text = f"主题：{state['topic']}\n分析：{state['analysis']}"
    prompt = f"请将以下内容压缩成一句话：\n{long_text}"
    
    response = llm.invoke(prompt)
    summary = response.content
    
    console.print(f"✅ 压缩完成：{summary}")
    console.print(f"压缩率：{(1-len(summary)/len(long_text))*100:.1f}%")
    
    return {"summary": summary, "step_count": state["step_count"] + 1}

def isolate_step(state: SimpleState) -> dict:
    """隔离上下文演示"""
    console.print("🏗️ [bold purple]Isolate Context[/bold purple] - 隔离处理")
    
    console.print("✅ 模拟多智能体隔离分析")
    console.print("✅ 模拟沙盒环境隔离")
    
    return {"step_count": state["step_count"] + 1}

def run_simple_demo():
    """运行简化演示"""
    console.print("[bold blue]🚀 LangGraph 上下文工程简化演示[/bold blue]\n")
    
    llm, checkpointer, memory_store, namespace = setup_simple_demo()
    
    # 构建工作流
    workflow = StateGraph(SimpleState)
    workflow.add_node("write", write_step)
    workflow.add_node("select", select_step)
    workflow.add_node("compress", compress_step)
    workflow.add_node("isolate", isolate_step)
    
    workflow.add_edge(START, "write")
    workflow.add_edge("write", "select")
    workflow.add_edge("select", "compress")
    workflow.add_edge("compress", "isolate")
    workflow.add_edge("isolate", END)
    
    app = workflow.compile(checkpointer=checkpointer, store=memory_store)
    
    # 运行
    result = app.invoke({
        "topic": "人工智能",
        "step_count": 0
    }, {"configurable": {"thread_id": "simple_1"}})
    
    console.print(f"\n[bold green]✨ 演示完成！执行了 {result['step_count']} 个步骤[/bold green]")
    console.print(f"主题：{result['topic']}")
    console.print(f"最终摘要：{result['summary']}")
    
    return result

if __name__ == "__main__":
    run_simple_demo()
