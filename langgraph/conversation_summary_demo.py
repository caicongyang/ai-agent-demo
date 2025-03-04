from typing import Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, StateGraph, START, END

# 初始化内存保存器，用于保存对话历史
memory = MemorySaver()

# 扩展 MessagesState 类，添加 summary 属性用于存储对话摘要
class State(MessagesState):
    """
    状态类，继承自 MessagesState
    添加 summary 属性用于存储对话历史的摘要
    """
    summary: str

# 初始化 Claude 3 模型
model = ChatAnthropic(model_name="claude-3-haiku-20240307")

def call_model(state: State):
    """
    调用 LLM 模型处理对话
    
    Args:
        state: 当前状态对象，包含消息历史和摘要
    
    Returns:
        dict: 包含模型响应的消息
    """
    # 如果存在摘要，将其作为系统消息添加到上下文
    summary = state.get("summary", "")
    if summary:
        system_message = f"Summary of conversation earlier: {summary}"
        messages = [SystemMessage(content=system_message)] + state["messages"]
    else:
        messages = state["messages"]
    
    # 调用模型获取响应
    response = model.invoke(messages)
    return {"messages": [response]}

def should_continue(state: State) -> Literal["summarize_conversation", END]:
    """
    决定是否需要生成摘要
    
    Args:
        state: 当前状态对象
    
    Returns:
        str: 'summarize_conversation' 或 END 标记
    """
    messages = state["messages"]
    # 如果消息数量超过6条，进行摘要
    if len(messages) > 6:
        return "summarize_conversation"
    return END

def summarize_conversation(state: State):
    """
    生成对话摘要
    
    Args:
        state: 当前状态对象
    
    Returns:
        dict: 包含新的摘要和需要删除的消息
    """
    summary = state.get("summary", "")
    
    # 根据是否存在之前的摘要，使用不同的提示语
    if summary:
        summary_message = (
            f"This is summary of the conversation to date: {summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )
    else:
        summary_message = "Create a summary of the conversation above:"

    # 添加摘要请求消息并调用模型
    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = model.invoke(messages)
    
    # 保留最后两条消息，删除其他消息
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    
    return {
        "summary": response.content,
        "messages": delete_messages
    }

def create_conversation_graph():
    """
    创建对话图结构
    
    Returns:
        StateGraph: 编译后的对话图
    """
    # 创建状态图
    workflow = StateGraph(State)
    
    # 添加对话节点和摘要节点
    workflow.add_node("conversation", call_model)
    workflow.add_node(summarize_conversation)
    
    # 设置入口点为对话节点
    workflow.add_edge(START, "conversation")
    
    # 添加条件边，用于决定是否需要生成摘要
    workflow.add_conditional_edges(
        "conversation",
        should_continue,
    )
    
    # 添加从摘要节点到结束的边
    workflow.add_edge("summarize_conversation", END)
    
    # 编译图结构
    return workflow.compile(checkpointer=memory)

def main():
    """
    主函数，演示对话系统的使用
    """
    # 创建对话图
    app = create_conversation_graph()
    
    # 配置会话ID
    config = {"configurable": {"thread_id": "demo_conversation"}}
    
    # 测试对话
    messages = [
        "你好！我是小明",
        "我喜欢打篮球",
        "我最喜欢的球星是库里",
        "你觉得他怎么样？",
        "对了，我还喜欢足球",
        "梅西是我的偶像",
        "你觉得他和C罗谁更厉害？"
    ]
    
    # 逐条发送消息并打印响应
    for msg in messages:
        print(f"\n用户: {msg}")
        input_message = HumanMessage(content=msg)
        for event in app.stream(
            {"messages": [input_message]}, 
            config, 
            stream_mode="updates"
        ):
            for k, v in event.items():
                if "messages" in v:
                    for m in v["messages"]:
                        if not isinstance(m, RemoveMessage):
                            print(f"助手: {m.content}")
                if "summary" in v:
                    print(f"\n摘要更新:\n{v['summary']}\n")

if __name__ == "__main__":
    main()