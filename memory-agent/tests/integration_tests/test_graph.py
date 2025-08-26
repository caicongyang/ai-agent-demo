"""
记忆智能体图的集成测试

本测试文件验证记忆智能体的核心功能：
1. 从对话中提取和存储用户信息
2. 确保记忆按用户ID正确隔离
3. 测试不同长度对话的记忆存储能力

项目架构说明：
- State: 存储对话消息的状态管理
- Context: 运行时上下文，包含用户ID、模型配置等
- Graph: LangGraph状态图，定义了智能体的工作流程
  * call_model: 调用LLM分析对话并决定是否存储记忆
  * store_memory: 执行记忆存储操作
  * route_message: 路由决策，判断是否需要存储记忆
- Tools: upsert_memory工具，用于在存储中插入或更新记忆
- Store: 记忆存储后端，支持语义搜索
"""

from typing import List

import langsmith as ls
import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from memory_agent.context import Context
from memory_agent.graph import builder


@pytest.mark.asyncio  # 标记为异步测试
# @ls.unit  # LangSmith单元测试装饰器，用于测试跟踪和评估
@pytest.mark.parametrize(
    "conversation",  # 参数化测试，使用不同的对话场景
    [
        # 短对话场景：单条消息包含基本个人信息
        ["My name is Alice and I love pizza. Remember this."],
        
        # 中等长度对话场景：多条消息逐步建立用户档案
        [
            "Hi, I'm Bob and I enjoy playing tennis. Remember this.",
            "Yes, I also have a pet dog named Max.",
            "Max is a golden retriever and he's 5 years old. Please remember this too.",
        ],
        
        # 长对话场景：复杂的专业信息和详细背景
        [
            "Hello, I'm Charlie. I work as a software engineer and I'm passionate about AI. Remember this.",
            "I specialize in machine learning algorithms and I'm currently working on a project involving natural language processing.",
            "My main goal is to improve sentiment analysis accuracy in multi-lingual texts. It's challenging but exciting.",
            "We've made some progress using transformer models, but we're still working on handling context and idioms across languages.",
            "Chinese and English have been the most challenging pair so far due to their vast differences in structure and cultural contexts.",
        ],
    ],
    ids=["short", "medium", "long"],  # 测试场景标识符，用于测试报告
)
async def test_memory_storage(conversation: List[str]):
    """
    测试记忆存储功能
    
    此测试验证：
    1. 智能体能够从不同长度的对话中提取关键信息
    2. 记忆能够正确存储到指定用户的命名空间
    3. 用户间的记忆隔离功能正常工作
    
    Args:
        conversation: 参数化的对话列表，包含不同复杂度的对话场景
    """
    # 创建内存存储实例，用于测试环境
    mem_store = InMemoryStore()

    # 编译记忆智能体图，配置存储和检查点保存器
    # - store: 记忆存储后端
    # - checkpointer: 对话状态检查点，用于会话持久化
    graph = builder.compile(store=mem_store, checkpointer=MemorySaver())
    user_id = "test-user"  # 测试用户ID

    # 模拟用户对话，逐条发送消息给智能体
    for content in conversation:
        await graph.ainvoke(
            {"messages": [("user", content)]},  # 构造用户消息
            {"thread_id": "thread"},  # 对话线程ID
            context=Context(user_id=user_id, model="azure_openai/gpt-4o"),  # 明确使用Azure OpenAI模型
        )

    # 验证记忆存储：检查指定用户的记忆命名空间
    namespace = ("memories", user_id)  # 记忆存储的命名空间格式
    memories = mem_store.search(namespace)  # 搜索用户的所有记忆

    print(memories)  # 调试输出：显示存储的记忆内容

    # 断言1：验证至少存储了一条记忆
    # 这确保智能体从对话中成功提取了值得记住的信息
    # ls.expect(len(memories)).to_be_greater_than(0)  # 暂时注释掉LangSmith断言
    assert len(memories) > 0, f"应该至少存储一条记忆，但实际存储了 {len(memories)} 条"

    # 验证用户隔离：检查错误的用户ID不能访问其他用户的记忆
    bad_namespace = ("memories", "wrong-user")  # 使用错误的用户ID
    bad_memories = mem_store.search(bad_namespace)  # 搜索不存在用户的记忆
    
    # 断言2：验证用户记忆隔离功能
    # 确保使用错误用户ID无法访问到任何记忆，保证数据隔离性
    # ls.expect(len(bad_memories)).to_equal(0)  # 暂时注释掉LangSmith断言
    assert len(bad_memories) == 0, f"错误用户ID不应该能访问记忆，但找到了 {len(bad_memories)} 条"
