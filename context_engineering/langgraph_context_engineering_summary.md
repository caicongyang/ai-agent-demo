# LangGraph 中的上下文工程实现

## 概述

上下文工程（Context Engineering）是在大型语言模型（LLM）应用中有效管理和操作上下文信息的关键技术。正如 Andrej Karpathy 所说，LLM 就像一种新的操作系统，LLM 是 CPU，其上下文窗口就是 RAM，作为模型的工作记忆。上下文工程就是"**用正确的信息填充上下文窗口以进行下一步操作的精妙艺术和科学**"。

本文档基于项目中的四个核心 Jupyter Notebook 和 [LangChain 官方博客](https://blog.langchain.com/context-engineering-for-agents/)，系统性地介绍了 LangGraph 框架中上下文工程的四个核心概念：**写入（Writing）**、**选择（Selecting）**、**压缩（Compressing）**和**隔离（Isolating）**。

### 为什么上下文工程对智能体如此重要？

智能体需要上下文来执行任务。智能体交替进行 LLM 调用和工具调用，通常用于长时间运行的任务。然而，长时间运行的任务和工具调用的累积反馈意味着智能体经常使用大量的 token。这可能导致众多问题：

- **超出上下文窗口大小**
- **成本和延迟激增**
- **智能体性能下降**

Drew Breunig 很好地概述了更长上下文可能导致的性能问题，包括：
- **上下文中毒（Context Poisoning）**：幻觉进入上下文时
- **上下文分散（Context Distraction）**：上下文压倒训练时
- **上下文混乱（Context Confusion）**：多余的上下文影响响应时
- **上下文冲突（Context Clash）**：上下文的各部分不一致时

正如 Cognition 指出的："**上下文工程实际上是构建 AI 智能体的工程师的第一要务**"。Anthropic 也明确指出："**智能体经常进行数百轮对话，需要仔细的上下文管理策略**"。

### 上下文类型

在构建 LLM 应用时，我们需要管理的上下文类型包括：

- **指令（Instructions）**：提示、记忆、少样本示例、工具描述等
- **知识（Knowledge）**：事实、记忆等
- **工具（Tools）**：工具调用的反馈

## 项目结构

```
context_engineering/
├── 1_write_context.ipynb      # 写入上下文
├── 2_select_context.ipynb     # 选择上下文
├── 3_compress_context.ipynb   # 压缩上下文
├── 4_isolate_context.ipynb    # 隔离上下文
├── utils.py                   # 工具函数
└── requirements.txt           # 依赖包
```

## 1. 写入上下文 (Writing Context)

### 核心概念
写入上下文是指将信息保存在上下文窗口之外，以帮助智能体执行任务。这包括两种主要方式：

### 1.1 草稿本 (Scratchpad) - 短期记忆

**实现原理：**
- 使用 LangGraph 的 `StateGraph` 和 `State` 对象
- 在单个执行会话（线程）内的节点之间传递信息
- 通过 `checkpointing` 机制持久化状态

**代码示例：**
```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    topic: str
    joke: str

def generate_joke(state: State) -> dict[str, str]:
    """生成笑话并写入状态"""
    msg = llm.invoke(f"Write a short joke about {state['topic']}")
    return {"joke": msg.content}

# 构建工作流
workflow = StateGraph(State)
workflow.add_node("generate_joke", generate_joke)
workflow.add_edge(START, "generate_joke")
workflow.add_edge("generate_joke", END)

chain = workflow.compile()
```

### 1.2 记忆 (Memory) - 长期记忆

**实现原理：**
- 使用 `BaseStore` 接口（如 `InMemoryStore`）
- 跨多个执行会话（线程）持久化信息
- 通过命名空间组织数据

**记忆类型：**
- **情节性记忆（Episodic Memories）**：少样本示例，用于展示期望的行为
- **程序性记忆（Procedural Memories）**：指令，用于引导行为
- **语义记忆（Semantic Memories）**：事实，为智能体提供任务相关的上下文

这些概念在流行产品中得到应用，如 ChatGPT、Cursor 和 Windsurf，它们都有基于用户-智能体交互自动生成长期记忆的机制。

**代码示例：**
```python
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import InMemorySaver

# 初始化存储组件
checkpointer = InMemorySaver()
memory_store = InMemoryStore()
namespace = ("user_id", "application_context")

def generate_joke_with_memory(state: State, store: BaseStore) -> dict[str, str]:
    """带记忆功能的笑话生成"""
    # 检查现有记忆
    existing_jokes = list(store.search(namespace))
    
    # 生成新笑话
    msg = llm.invoke(f"Write a short joke about {state['topic']}")
    
    # 保存到长期记忆
    store.put(namespace, "last_joke", {"joke": msg.content})
    
    return {"joke": msg.content}

# 编译时同时提供检查点和存储
chain = workflow.compile(checkpointer=checkpointer, store=memory_store)
```

## 2. 选择上下文 (Selecting Context)

### 核心概念
选择上下文是指将相关信息拉入上下文窗口，以帮助智能体执行特定任务。

### 2.1 从草稿本选择

**实现方式：**
- 直接从 `State` 对象中读取信息
- 在下游节点中使用上游节点的输出

**代码示例：**
```python
def improve_joke(state: State) -> dict[str, str]:
    """从状态中选择上下文来改进笑话"""
    # 选择现有笑话作为上下文
    existing_joke = state['joke']
    
    # 使用选择的上下文生成改进版本
    msg = llm.invoke(f"Make this joke funnier: {existing_joke}")
    return {"improved_joke": msg.content}
```

### 2.2 从记忆中选择

**实现方式：**
- 使用 `store.get()` 方法检索特定信息
- 使用 `store.search()` 方法查找相关信息

**记忆选择挑战：**
确保选择相关记忆是一个挑战。一些流行的智能体使用**总是**拉入上下文的窄文件集：
- **Claude Code** 使用 `CLAUDE.md`
- **Cursor** 和 **Windsurf** 使用规则文件

但如果智能体存储大量事实和关系（语义记忆），选择就更困难了。ChatGPT 是一个存储和选择大量用户特定记忆的流行产品例子。

**记忆选择问题：**
在 AIEngineer 世界博览会上，Simon Willison 分享了一个选择出错的例子：ChatGPT 从记忆中获取了他的位置并意外地将其注入到请求的图像中。这种意外或不希望的记忆检索可能让用户觉得上下文窗口"**不再属于他们**"！

**解决方案：**
- 使用嵌入（Embeddings）进行记忆索引
- 使用知识图谱（Knowledge Graphs）辅助选择

**代码示例：**
```python
def generate_with_memory_context(state: State, store: BaseStore) -> dict[str, str]:
    """从记忆中选择上下文"""
    # 选择先前的笑话
    prior_joke = store.get(namespace, "last_joke")
    
    if prior_joke:
        prior_context = prior_joke.value["joke"]
        prompt = f"Write a different joke about {state['topic']}, unlike: {prior_context}"
    else:
        prompt = f"Write a joke about {state['topic']}"
    
    msg = llm.invoke(prompt)
    return {"joke": msg.content}
```

### 2.3 工具选择

**工具过载问题：**
智能体使用工具，但如果提供太多工具可能会过载。这通常是因为工具描述重叠，导致模型对使用哪个工具感到困惑。

**解决方案：**
对工具描述应用 RAG（检索增强生成），根据语义相似性为任务获取最相关的工具。Drew Breunig 称之为"**工具装载（Tool Loadout）**"。一些最近的论文显示这将工具选择准确性提高了 **3 倍**。

**LangGraph BigTool 库：**
- 使用语义相似性搜索选择最相关的工具
- 避免工具过载问题
- 提高工具选择准确性

**代码示例：**
```python
from langgraph_bigtool import create_agent
from langgraph_bigtool.utils import convert_positional_only_function_to_tool

# 创建工具注册表
tool_registry = {str(uuid.uuid4()): tool for tool in all_tools}

# 建立工具索引
store = InMemoryStore(index={"embed": embeddings, "dims": 1536, "fields": ["description"]})
for tool_id, tool in tool_registry.items():
    store.put(("tools",), tool_id, {"description": f"{tool.name}: {tool.description}"})

# 创建智能体
builder = create_agent(llm, tool_registry)
agent = builder.compile(store=store)
```

### 2.4 知识选择 (RAG)

RAG 是一个丰富的主题，可能是上下文工程的核心挑战。代码智能体是大规模生产中 RAG 的最佳例子。来自 Windsurf 的 Varun 很好地捕捉了这些挑战：

> **索引代码 ≠ 上下文检索**... 我们进行索引和嵌入搜索... 通过 AST 解析代码并沿语义边界分块... 随着代码库规模增长，嵌入搜索作为检索启发式变得不可靠... 我们必须依赖技术组合，如 grep/文件搜索、基于知识图的检索，以及... 重新排序步骤，其中上下文按相关性排序。

**实现方式：**
- 构建检索工具
- 语义搜索相关文档
- 动态获取任务相关信息
- 结合多种检索技术（嵌入搜索、grep、知识图等）
- 实施重新排序机制

**代码示例：**
```python
from langchain.tools.retriever import create_retriever_tool
from langchain_core.vectorstores import InMemoryVectorStore

# 创建向量存储和检索器
vectorstore = InMemoryVectorStore.from_documents(documents=doc_splits, embedding=embeddings)
retriever = vectorstore.as_retriever()

# 创建检索工具
retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_blog_posts",
    "Search and return information about blog posts."
)
```

## 3. 压缩上下文 (Compressing Context)

### 核心概念
压缩上下文涉及仅保留执行任务所需的 token，以管理长对话、控制成本和避免上下文窗口限制。

### 3.1 摘要对话历史

**实现方式：**
- 在工作流末尾添加摘要节点
- 生成整个交互的简洁摘要

**代码示例：**
```python
def summary_node(state: MessagesState) -> dict:
    """生成对话摘要"""
    summarization_prompt = """Summarize the full chat history and all tool feedback 
    to give an overview of what the user asked about and what the agent did."""
    
    messages = [SystemMessage(content=summarization_prompt)] + state["messages"]
    result = llm.invoke(messages)
    return {"summary": result.content}
```

### 3.2 压缩工具输出

**实现方式：**
- 在工具调用后立即压缩结果
- 减少传递给主 LLM 的信息量

**代码示例：**
```python
def tool_node_with_summarization(state: dict):
    """带摘要功能的工具节点"""
    tool_summarization_prompt = """Summarize the docs, ensuring to retain 
    all relevant information while reducing token count."""
    
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        
        # 压缩工具输出
        summary = llm.invoke([
            {"role": "system", "content": tool_summarization_prompt},
            {"role": "user", "content": observation}
        ])
        
        result.append(ToolMessage(content=summary.content, tool_call_id=tool_call["id"]))
    
    return {"messages": result}
```

### 3.3 其他压缩技术

**上下文修剪 (Context Trimming)：**
与摘要通常使用 LLM 提取最相关的上下文片段不同，修剪通常可以过滤或"修剪"上下文。这可以使用硬编码启发式，如从列表中删除较旧的消息。Drew Breunig 还提到了 Provence，一个用于问答的训练上下文修剪器。

**消息修剪 (Message Trimming)：**
- 使用 `trim_messages()` 函数
- 保留最新消息，控制 token 数量
- 使用硬编码启发式方法

**LangMem 摘要：**
- 提供专门的摘要工具和节点
- 支持运行时摘要和历史管理

**实际应用示例：**
- **Claude Code** 在超过 95% 上下文窗口时运行"自动压缩"
- **Cognition** 在智能体-智能体边界使用摘要来减少知识交接期间的 token

## 4. 隔离上下文 (Isolating Context)

### 核心概念
隔离上下文涉及将上下文分割，以帮助智能体更有效地执行任务。

### 4.1 多智能体系统

隔离上下文最流行和直观的方式之一是将其分散到子智能体中。OpenAI Swarm 库的动机是"**关注点分离**"，其中智能体团队可以处理特定的子任务。每个智能体都有特定的工具集、指令和自己的上下文窗口。

**性能优势：**
Anthropic 的多智能体研究员为此提供了有力的证据：具有隔离上下文的多个智能体比单个智能体的性能提高了 **90.2%**，主要是因为每个子智能体的上下文窗口可以分配给更窄的子任务。正如博客所说：

> **[子智能体]** 使用自己的上下文窗口并行操作，同时探索问题的不同方面。

**挑战：**
- **Token 使用**：高达比聊天多 **15 倍**的 token（Anthropic 报告）
- **提示工程**：需要仔细的提示工程来规划子智能体工作
- **协调复杂性**：子智能体的协调

**监督者架构：**
- 使用 `langgraph-supervisor` 创建监督者
- 每个子智能体有独立的上下文窗口和专门工具
- 实现关注点分离

**代码示例：**
```python
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent

# 创建专门的智能体
math_agent = create_react_agent(
    model=llm,
    tools=[add, multiply],
    name="math_expert",
    prompt="You are a math expert."
)

research_agent = create_react_agent(
    model=llm,
    tools=[web_search],
    name="research_expert", 
    prompt="You are a researcher with web search access."
)

# 创建监督者工作流
workflow = create_supervisor(
    [research_agent, math_agent],
    model=llm,
    prompt="You are a team supervisor. Route tasks to appropriate experts."
)
```

### 4.2 沙盒环境隔离

**HuggingFace 的深度研究员示例：**
HuggingFace 的深度研究员展示了另一个有趣的上下文隔离例子。大多数智能体使用工具调用 API，返回 JSON 对象（工具参数），可以传递给工具（如搜索 API）以获取工具反馈（如搜索结果）。HuggingFace 使用 CodeAgent，它输出包含所需工具调用的代码。代码然后在沙盒中运行。来自工具调用的选定上下文（如返回值）然后传回 LLM。

这允许上下文在环境中与 LLM 隔离。Hugging Face 指出这是隔离 token 密集型对象的好方法：

> **[代码智能体允许]** 更好地处理状态... 需要存储这个图像/音频/其他供以后使用？没问题，只需将其分配为状态中的变量，你[稍后使用它]。

**LangChain Sandbox：**
- 使用 Pyodide (Python 编译为 WebAssembly)
- 安全执行不受信任的代码
- 隔离计算环境
- 特别适合隔离 token 密集型对象

**代码示例：**
```python
from langchain_sandbox import PyodideSandboxTool

# 创建沙盒工具
tool = PyodideSandboxTool(allow_net=True)

# 创建带沙盒的智能体
agent = create_react_agent(
    "anthropic:claude-3-7-sonnet-latest",
    tools=[tool]
)
```

### 4.3 状态隔离

**实现方式：**
- 设计具有多个字段的状态模式
- 选择性地向 LLM 暴露特定字段
- 在状态对象中隔离敏感或大量信息

**代码示例：**
```python
class IsolatedState(TypedDict):
    messages: list        # 暴露给 LLM 的消息
    internal_data: dict   # 内部处理数据
    cache: dict          # 缓存信息
    metadata: dict       # 元数据

def selective_exposure_node(state: IsolatedState):
    """选择性暴露状态字段"""
    # 只使用 messages 字段与 LLM 交互
    # internal_data, cache, metadata 保持隔离
    pass
```

## 工具函数 (utils.py)

项目包含一个 `utils.py` 文件，提供了用于格式化和显示消息的辅助函数：

```python
from rich.console import Console
from rich.panel import Panel

def format_messages(messages):
    """使用 Rich 格式化显示消息列表"""
    for m in messages:
        msg_type = m.__class__.__name__.replace('Message', '')
        content = format_message_content(m)
        
        if msg_type == 'Human':
            console.print(Panel(content, title="🧑 Human", border_style="blue"))
        elif msg_type == 'Ai':
            console.print(Panel(content, title="🤖 Assistant", border_style="green"))
        elif msg_type == 'Tool':
            console.print(Panel(content, title="🔧 Tool Output", border_style="yellow"))
```

## LangGraph 和 LangSmith 的上下文工程支持

### 基础工具

在开始上下文工程之前，有两个基础工具是有帮助的：

1. **LangSmith 观测性**：确保有方法查看数据并跟踪智能体的 token 使用情况。这有助于确定在哪里最好地应用上下文工程努力。
2. **LangSmith 评估**：确保有简单的方法测试上下文工程是否损害或改善智能体性能。

### LangGraph 对四种策略的支持

**写入上下文：**
- **短期记忆**：使用检查点在智能体的所有步骤中持久化状态
- **长期记忆**：跨多个会话持久化上下文，支持文件和记忆集合
- **LangMem**：提供广泛的抽象来辅助 LangGraph 记忆管理

**选择上下文：**
- **状态访问**：在每个节点中获取状态，精细控制向 LLM 呈现的上下文
- **长期记忆检索**：支持文件获取和基于嵌入的检索
- **LangGraph BigTool**：对工具描述应用语义搜索
- **RAG 支持**：多个教程和视频展示如何在 LangGraph 中使用各种 RAG

**压缩上下文：**
- **低级控制**：将智能体布局为节点集合，定义每个节点内的逻辑
- **内置工具**：使用消息列表作为状态并定期摘要或修剪
- **灵活摘要**：在特定点添加摘要节点或在工具调用节点中添加摘要逻辑

**隔离上下文：**
- **状态隔离**：设计状态模式并在每个步骤访问状态
- **沙盒支持**：支持使用沙盒进行上下文隔离
- **多智能体架构**：监督者和群体库的大量支持

## 最佳实践

### 1. 写入上下文
- 使用 `State` 对象进行会话内信息传递
- 使用 `Store` 进行跨会话信息持久化
- 合理设计命名空间组织长期记忆
- 考虑记忆类型（情节性、程序性、语义）

### 2. 选择上下文
- 根据任务需求选择相关上下文
- 使用语义搜索选择工具和知识
- 避免信息过载，保持上下文相关性
- 注意记忆选择的准确性，避免"上下文不再属于用户"的问题

### 3. 压缩上下文
- 在适当的节点插入摘要功能
- 压缩工具输出减少 token 使用
- 使用消息修剪管理长对话
- 考虑递归和层次摘要策略

### 4. 隔离上下文
- 使用多智能体实现关注点分离
- 利用沙盒环境隔离计算
- 通过状态设计实现信息隔离
- 权衡性能提升与 token 成本增加

## 技术优势

1. **灵活性：** LangGraph 的低级控制允许精确的上下文管理
2. **可扩展性：** 支持从简单到复杂的各种上下文工程模式
3. **效率：** 通过压缩和隔离技术优化 token 使用
4. **安全性：** 沙盒环境和状态隔离提供安全保障

## 应用场景

- **代码智能体：** 管理大型代码库上下文
- **研究助手：** 处理多源信息整合
- **客服系统：** 维护用户会话历史
- **教育平台：** 个性化学习上下文管理

## 总结

上下文工程正在成为智能体构建者应该掌握的一门手艺。本文档涵盖了当今许多流行智能体中常见的几种模式：

- **写入上下文** - 将其保存在上下文窗口之外以帮助智能体执行任务
- **选择上下文** - 将其拉入上下文窗口以帮助智能体执行任务  
- **压缩上下文** - 仅保留执行任务所需的 token
- **隔离上下文** - 将其分割以帮助智能体执行任务

LangGraph 使得实现每种策略都变得简单，LangSmith 提供了测试智能体和跟踪上下文使用的简便方法。LangGraph 和 LangSmith 共同实现了一个良性反馈循环：识别应用上下文工程的最佳机会、实施它、测试它，然后重复。

通过合理组合这些技术，开发者可以构建出能够处理复杂任务、维护长期记忆、并具有良好扩展性的智能体系统，同时有效管理复杂的上下文信息并优化性能和成本。

## 参考资料

- [LangChain 官方博客：智能体的上下文工程](https://blog.langchain.com/context-engineering-for-agents/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangMem 文档](https://langchain-ai.github.io/langmem/)
- [LangGraph BigTool 库](https://github.com/langchain-ai/langgraph-bigtool)
- [LangGraph Supervisor 库](https://github.com/langchain-ai/langgraph-supervisor-py)
- [LangChain Sandbox](https://github.com/langchain-ai/langchain-sandbox)
