# LangGraph Context 快速入门

## 5分钟理解Context系统

### 🎯 什么是Context？

Context（上下文）是智能体获取和使用信息的核心机制。它让AI能够：
- 🔍 **了解用户**: "这是Alice，她喜欢简洁回答"
- 🔧 **使用工具**: "这是数据库连接，这是API密钥"
- 💾 **记住状态**: "我们刚才讨论到哪里了"
- 🌐 **跨会话学习**: "用户历史上喜欢什么风格"

### 🚫 Context ≠ LLM Context

⚠️ **重要区别**：
```python
# Runtime Context - 代码运行时需要的数据
context = Context(user_id="alice", api_key="sk-...")

# LLM Context - 传给AI的提示词
llm_prompt = f"用户ID: {context.user_id}, 请回答: Hello"
```

## 📊 Context的分类体系

### 按可变性分类
```
静态Context                    动态Context
┌─────────────────┐           ┌─────────────────┐
│ 不变的配置信息   │           │ 会变化的数据     │
│ • 用户ID        │           │ • 对话历史       │
│ • API密钥       │           │ • 中间结果       │
│ • 数据库连接     │           │ • 计算状态       │
└─────────────────┘           └─────────────────┘
```

### 按生命周期分类
```
单次运行                      跨会话持久化
┌─────────────────┐           ┌─────────────────┐
│ 一次对话范围     │           │ 多次对话范围     │
│ • 当前消息       │           │ • 用户偏好       │
│ • 临时变量       │           │ • 历史记忆       │
│ • 工具结果       │           │ • 学习经验       │
└─────────────────┘           └─────────────────┘
```

## 🎮 三种Context类型

| 类型 | 用途 | 示例 | 访问方式 |
|------|------|------|----------|
| **静态运行时** | 配置信息 | 用户ID、模型名 | `context`参数 |
| **动态运行时** | 对话状态 | 消息历史、中间结果 | State对象 |
| **跨会话存储** | 长期记忆 | 用户偏好、历史经验 | Store存储 |

## 🚀 实战示例

### 1. 静态运行时Context

```python
from dataclasses import dataclass

@dataclass
class MyContext:
    user_name: str
    user_id: str
    preferred_language: str

# 使用Context
await graph.ainvoke(
    {"messages": [("user", "Hello")]},
    context={
        "user_name": "Alice",
        "user_id": "alice-123",
        "preferred_language": "中文"
    }
)
```

**在节点中访问**：
```python
from langgraph.runtime import Runtime

def my_node(state, runtime: Runtime[MyContext]):
    user_name = runtime.context.user_name
    language = runtime.context.preferred_language
    
    response = f"你好 {user_name}！我会用{language}回答。"
    return {"response": response}
```

### 2. 动态运行时Context (状态)

```python
from typing_extensions import TypedDict

class MyState(TypedDict):
    messages: list
    user_mood: str        # 用户情绪
    step_count: int       # 对话步数
    tool_results: list    # 工具结果

def analyze_mood(state: MyState):
    last_message = state["messages"][-1]
    
    # 分析用户情绪（简化示例）
    if "开心" in last_message.content:
        mood = "happy"
    elif "沮丧" in last_message.content:
        mood = "sad"
    else:
        mood = "neutral"
    
    return {
        "user_mood": mood,
        "step_count": state.get("step_count", 0) + 1
    }
```

### 3. 跨会话存储Context

```python
from langgraph.store.memory import InMemoryStore

async def save_user_preference(user_id: str, preference: dict):
    store = InMemoryStore()
    
    # 存储用户偏好
    await store.aput(
        namespace=("preferences", user_id),
        key="communication_style",
        value=preference
    )

async def get_user_preference(user_id: str):
    store = InMemoryStore()
    
    # 获取用户偏好
    result = await store.aget(
        namespace=("preferences", user_id),
        key="communication_style"
    )
    return result.value if result else {}
```

## 🔧 项目中的Context实现

### Context定义

```python
# src/memory_agent/context.py
@dataclass(kw_only=True)
class Context:
    user_id: str = "default"
    model: str = "anthropic/claude-3-5-sonnet-20240620"
    system_prompt: str = SYSTEM_PROMPT
    
    def __post_init__(self):
        # 自动从环境变量加载
        for f in fields(self):
            env_value = os.environ.get(f.name.upper(), getattr(self, f.name))
            setattr(self, f.name, env_value)
```

### Context使用流程

```python
# src/memory_agent/graph.py
async def call_model(state: State, runtime: Runtime[Context]) -> dict:
    # 1. 获取静态Context
    user_id = runtime.context.user_id
    model = runtime.context.model
    
    # 2. 获取跨会话数据
    memories = await runtime.store.asearch(
        ("memories", user_id),
        query="最近对话内容"
    )
    
    # 3. 结合所有Context
    system_prompt = f"""
    用户ID: {user_id}
    相关记忆: {format_memories(memories)}
    当前时间: {datetime.now()}
    """
    
    # 4. 调用LLM
    response = await get_model(model).ainvoke([
        {"role": "system", "content": system_prompt},
        *state["messages"]  # 动态状态
    ])
    
    return {"messages": [response]}
```

### 实际调用示例

```python
# 测试中的使用
async def test_context():
    # 创建存储（跨会话）
    store = InMemoryStore()
    
    # 编译图（状态管理）
    graph = builder.compile(store=store, checkpointer=MemorySaver())
    
    # 调用时传入静态Context
    result = await graph.ainvoke(
        {"messages": [("user", "我叫Alice")]},    # 动态状态
        {"thread_id": "conversation-1"},         # 状态标识
        context=Context(                         # 静态Context
            user_id="alice-123",
            model="azure_openai/gpt-4o"
        )
    )
```

## 💡 最佳实践

### 1. Context设计原则

```python
# ✅ 好的Context设计
@dataclass
class GoodContext:
    # 必需字段
    user_id: str
    
    # 可选配置
    model: str = "gpt-4"
    language: str = "zh-CN"
    
    # 功能开关
    enable_memory: bool = True
    enable_tools: bool = True

# ❌ 避免的设计
@dataclass
class BadContext:
    everything: dict  # 太宽泛
    config: str      # 类型不明确
```

### 2. 安全访问Context

```python
def safe_get_context(runtime: Runtime[Context]):
    try:
        user_id = runtime.context.user_id
        model = getattr(runtime.context, 'model', 'default')
        return user_id, model
    except AttributeError:
        return "default-user", "default-model"
```

### 3. Context验证

```python
def validate_context(context: Context):
    if not context.user_id:
        raise ValueError("user_id不能为空")
    
    if not context.model:
        raise ValueError("model不能为空")
    
    return True
```

## 🐛 常见问题

### Q: Context信息没有传递到工具中？
**A**: 使用`get_runtime()`获取Context：
```python
from langgraph.runtime import get_runtime

@tool
def my_tool():
    runtime = get_runtime(MyContext)
    user_id = runtime.context.user_id
    return f"处理用户 {user_id} 的请求"
```

### Q: 不同组件中Context不一致？
**A**: 确保使用相同的Context Schema：
```python
# 在所有组件中使用相同的Schema
from langgraph.runtime import Runtime

def node1(state, runtime: Runtime[Context]): pass
def node2(state, runtime: Runtime[Context]): pass  # 相同的Context类型
```

### Q: Context数据过大影响性能？
**A**: 使用延迟加载：
```python
@dataclass
class LazyContext:
    user_id: str
    _user_profile: Optional[dict] = None
    
    async def get_user_profile(self):
        if self._user_profile is None:
            self._user_profile = await load_profile(self.user_id)
        return self._user_profile
```

## 🎯 Context组合使用

### 完整示例：个性化智能助手

```python
@dataclass
class AssistantContext:
    user_id: str
    language: str = "zh-CN"
    tone: str = "friendly"

class AssistantState(TypedDict):
    messages: list
    user_mood: str
    conversation_summary: str

async def personalized_assistant():
    # 1. 设置静态Context
    context = AssistantContext(
        user_id="alice-123",
        language="中文",
        tone="professional"
    )
    
    # 2. 创建跨会话存储
    store = InMemoryStore()
    await store.aput(
        ("preferences", "alice-123"),
        "style",
        {"detail_level": "concise", "examples": True}
    )
    
    # 3. 运行图
    result = await graph.ainvoke(
        {
            "messages": [("user", "解释一下机器学习")],
            "user_mood": "curious"
        },
        context=context,
        store=store
    )
    
    return result
```

## 🔗 进一步学习

- 📖 [详细指南](./LangGraph_Context_深入指南.md) - 完整的Context系统文档
- 🌐 [官方文档](https://langchain-ai.github.io/langgraph/agents/context/) - LangGraph Context概念
- 💻 [项目源码](../src/memory_agent/context.py) - 实际实现示例
- 🧠 [Memory系统](./快速入门_Memory系统.md) - Context与Memory的结合使用

---

**记住**: Context是智能体的"感知器官"，让AI能够理解和适应不同的使用场景。从简单的用户ID开始，逐步构建更丰富的上下文感知能力！
