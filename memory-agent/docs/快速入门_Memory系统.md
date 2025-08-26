# LangGraph Memory 快速入门

## 5分钟理解Memory系统

### 🧠 什么是Memory？

Memory让AI智能体能够"记住"信息，就像人类一样：
- 记住用户偏好："Alice喜欢简洁的回答"
- 记住对话历史："我们刚才讨论了什么"
- 记住学到的经验："这种问题用这个方法解决"

### 📊 Memory的两种类型

```
短期记忆 (Short-term)          长期记忆 (Long-term)
┌─────────────────┐           ┌─────────────────┐
│   单个对话内     │           │   跨对话/跨会话  │
│   Thread范围     │           │   全局范围       │
│   Checkpointer   │           │   Store         │
└─────────────────┘           └─────────────────┘
        ↓                            ↓
   "你刚才说什么？"              "记住我喜欢中文"
```

## 🚀 核心组件

### 1. Store - 长期记忆存储

```python
from langgraph.store.memory import InMemoryStore

# 创建存储
store = InMemoryStore()

# 存储记忆 (命名空间, 键, 值)
store.put(
    ("memories", "user-123"),        # 命名空间：按用户隔离
    "preference-1",                  # 键：唯一标识
    {"content": "喜欢简洁回答"}       # 值：JSON数据
)

# 检索记忆
memories = store.search(("memories", "user-123"))
print(memories)  # 输出存储的记忆
```

### 2. Checkpointer - 短期记忆持久化

```python
from langgraph.checkpoint.memory import MemorySaver

# 创建检查点保存器
checkpointer = MemorySaver()

# 编译图时配置
graph = builder.compile(checkpointer=checkpointer)

# 使用thread_id来区分不同对话
await graph.ainvoke(
    {"messages": [("user", "我叫Alice")]},
    {"thread_id": "conversation-1"}  # 对话1
)

await graph.ainvoke(
    {"messages": [("user", "我叫Bob")]},
    {"thread_id": "conversation-2"}   # 对话2 - 独立的记忆
)
```

### 3. Context - 运行时配置

```python
from memory_agent.context import Context

# 创建上下文
context = Context(
    user_id="alice-123",
    model="azure_openai/gpt-4o"
)

# 在图调用中使用
await graph.ainvoke(
    {"messages": [("user", "Hello")]},
    {"thread_id": "thread-1"},
    context=context  # 传入上下文
)
```

## 💡 实际应用示例

### 场景1: 记住用户偏好

```python
# 用户第一次交互
await graph.ainvoke(
    {"messages": [("user", "请用简洁的中文回答我")]},
    {"thread_id": "chat-1"},
    context=Context(user_id="alice")
)
# → 智能体存储: "用户Alice喜欢简洁的中文回答"

# 用户第二次交互（新对话）
await graph.ainvoke(
    {"messages": [("user", "什么是AI？")]},
    {"thread_id": "chat-2"},  # 新的thread_id
    context=Context(user_id="alice")  # 相同的user_id
)
# → 智能体检索到之前的偏好，用简洁中文回答
```

### 场景2: 对话上下文

```python
# 同一对话中的多轮交互
thread_id = "long-conversation"

# 第一轮
await graph.ainvoke(
    {"messages": [("user", "我正在学习Python")]},
    {"thread_id": thread_id}
)

# 第二轮 - 智能体记得上一轮内容
await graph.ainvoke(
    {"messages": [("user", "有什么好的学习资源？")]},
    {"thread_id": thread_id}
)
# → 智能体知道用户问的是Python学习资源
```

## 🔧 项目中的实现

### Memory工具定义

```python
# src/memory_agent/tools.py
async def upsert_memory(
    content: str,    # 记忆内容："用户Alice喜欢简洁回答"
    context: str,    # 记忆上下文："在技术讨论中提到"
    user_id: str,    # 自动注入的用户ID
    store: BaseStore # 自动注入的存储
):
    # 存储到 ("memories", user_id) 命名空间
    await store.aput(
        ("memories", user_id),
        str(uuid.uuid4()),
        {"content": content, "context": context}
    )
```

### 智能体决策流程

```python
# src/memory_agent/graph.py
async def call_model(state, runtime):
    user_id = runtime.context.user_id
    
    # 1. 检索相关记忆
    memories = await runtime.store.asearch(
        ("memories", user_id),
        query="最近的对话内容",
        limit=10
    )
    
    # 2. 将记忆加入系统提示
    memory_context = format_memories(memories)
    system_prompt = f"用户信息: {memory_context}\n{base_prompt}"
    
    # 3. 调用LLM，绑定记忆工具
    response = await llm.bind_tools([upsert_memory]).ainvoke([
        {"role": "system", "content": system_prompt},
        *state.messages
    ])
    
    return {"messages": [response]}
```

## 🎯 最佳实践

### 1. 命名空间设计

```python
# ✅ 好的设计
("memories", user_id)                    # 按用户隔离
("memories", user_id, "preferences")     # 按类型分类
("org", org_id, "users", user_id)       # 层次化结构

# ❌ 避免的设计
("all_memories",)                        # 没有隔离
```

### 2. 记忆内容结构

```python
# ✅ 结构化内容
{
    "content": "用户喜欢简洁回答",
    "context": "在技术讨论中提到",
    "category": "preference",
    "confidence": 0.9
}

# ❌ 简单字符串
"用户喜欢简洁回答"
```

### 3. 错误处理

```python
# ✅ 优雅降级
try:
    memories = await store.asearch(namespace, query=query)
except Exception as e:
    logger.error(f"Memory retrieval failed: {e}")
    memories = []  # 使用空列表继续执行
```

## 🐛 常见问题

### Q: 记忆没有被存储？
**A**: 检查LLM是否调用了`upsert_memory`工具：
```python
# 查看最后一条消息是否包含工具调用
last_message = state.messages[-1]
tool_calls = getattr(last_message, "tool_calls", [])
print(f"工具调用: {tool_calls}")
```

### Q: 检索不到相关记忆？
**A**: 确认命名空间和查询条件：
```python
# 调试记忆检索
memories = store.search(("memories", user_id))
print(f"用户 {user_id} 的所有记忆: {memories}")
```

### Q: 不同对话间记忆混乱？
**A**: 确保正确使用thread_id和user_id：
- `thread_id`: 区分不同对话（短期记忆）
- `user_id`: 区分不同用户（长期记忆）

## 🎉 运行测试

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行记忆测试
python -m pytest tests/integration_tests/test_graph.py -v -s

# 查看记忆存储输出
# [Item(namespace=['memories', 'test-user'], 
#  key='abc-123', 
#  value={'content': "User's name is Alice and she loves pizza.", 
#         'context': 'Alice introduced herself...'})]
```

## 🔗 进一步学习

- 📖 [详细指南](./LangGraph_Memory_深入指南.md) - 完整的Memory系统文档
- 🌐 [官方文档](https://langchain-ai.github.io/langgraph/concepts/memory/) - LangGraph Memory概念
- 💻 [项目源码](../src/memory_agent/) - 实际实现示例

---

**记住**: Memory系统的核心是让AI智能体能够学习和适应。从简单的用户偏好存储开始，逐步构建更复杂的记忆能力！
