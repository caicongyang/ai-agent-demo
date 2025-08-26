# 🧱 Context Engineering with LangGraph
# 🧱 基于LangGraph的上下文工程 

Agents need context (e.g., instructions, external knowledge, tool feedback) to perform tasks. Context engineering is the art and science of filling the context window with just the right information at each step of an agent's trajectory. This repository has a set of notebooks in the `context_engineering` folder that cover different strategies for context engineering, including **write, select, compress, and isolate**. For each, we explain how LangGraph is designed to support it with examples.

智能体需要上下文（例如指令、外部知识、工具反馈）来执行任务。上下文工程是在智能体轨迹的每个步骤中，用恰当的信息填充上下文窗口的艺术和科学。本仓库在`context_engineering`文件夹中提供了一系列笔记本，涵盖了上下文工程的不同策略，包括**写入、选择、压缩和隔离**。对于每种策略，我们都解释了LangGraph是如何设计来支持它的，并提供了示例。 

<img width="1231" height="448" alt="Screenshot 2025-07-13 at 2 57 28 PM" src="https://github.com/user-attachments/assets/8e7b59e0-4bb0-48f6-aeba-2d789ada55e3" />

## 🚀 Quickstart
## 🚀 快速开始 

### Prerequisites
### 前提条件
- Python 3.9 or higher
- Python 3.9 或更高版本
- [uv](https://docs.astral.sh/uv/) package manager
- [uv](https://docs.astral.sh/uv/) 包管理器
- [Deno](https://docs.deno.com/runtime/getting_started/installation/) required for the sandboxed environment in the `4_isolate_context.ipynb` notebook
- [Deno](https://docs.deno.com/runtime/getting_started/installation/) 用于`4_isolate_context.ipynb`笔记本中的沙盒环境

### Installation
### 安装
1. Clone the repository and activate a virtual environment:
1. 克隆仓库并激活虚拟环境：
```bash
git clone https://github.com/langchain-ai/context_engineering
cd context_engineering
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
2. 安装依赖：
```bash
uv pip install -r requirements.txt
```

3. Set up environment variables for the model provider(s) you want to use:
3. 为要使用的模型提供商设置环境变量：
```bash
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

4. You can then run the notebooks in the `context_engineering` folder:
4. 然后可以运行`context_engineering`文件夹中的笔记本：

```
context_engineering/
├── 1_write_context.ipynb      # Examples of saving context externally
├── 2_select_context.ipynb     # Examples of retrieving relevant context
├── 3_compress_context.ipynb   # Examples of context compression techniques
└── 4_isolate_context.ipynb    # Examples of context isolation methods
```

```
context_engineering/
├── 1_write_context.ipynb      # 外部保存上下文的示例
├── 2_select_context.ipynb     # 检索相关上下文的示例
├── 3_compress_context.ipynb   # 上下文压缩技术的示例
└── 4_isolate_context.ipynb    # 上下文隔离方法的示例
```

## 📚 Background
## 📚 背景 

As Andrej Karpathy puts it, LLMs are like a [new kind of operating system](https://www.youtube.com/watch?si=-aKY-x57ILAmWTdw&t=620&v=LCEmiRjPEtQ&feature=youtu.be). The LLM is like the CPU and its [context window](https://docs.anthropic.com/en/docs/build-with-claude/context-windows) is like the RAM, serving as the model's working memory. Just like RAM, the LLM context window has limited [capacity](https://lilianweng.github.io/posts/2023-06-23-agent/) to handle various sources of context. And just as an operating system curates what fits into a CPU's RAM, we can think about "context engineering" playing a similar role. [Karpathy summarizes this well](https://x.com/karpathy/status/1937902205765607626):

正如Andrej Karpathy所说，大语言模型就像一种[新型操作系统](https://www.youtube.com/watch?si=-aKY-x57ILAmWTdw&t=620&v=LCEmiRjPEtQ&feature=youtu.be)。大语言模型就像CPU，而它的[上下文窗口](https://docs.anthropic.com/en/docs/build-with-claude/context-windows)就像RAM，作为模型的工作内存。就像RAM一样，大语言模型的上下文窗口在处理各种上下文来源时有着有限的[容量](https://lilianweng.github.io/posts/2023-06-23-agent/)。正如操作系统策划什么适合放入CPU的RAM一样，我们可以认为"上下文工程"扮演着类似的角色。[Karpathy很好地总结了这一点](https://x.com/karpathy/status/1937902205765607626)：

> [Context engineering is the] "…delicate art and science of filling the context window with just the right information for the next step."

> [上下文工程是]"...用恰当的信息为下一步填充上下文窗口的精妙艺术和科学。"

What are the types of context that we need to manage when building LLM applications? We can think of context engineering as an [umbrella](https://x.com/dexhorthy/status/1933283008863482067) that applies across a few different context types:

在构建大语言模型应用时，我们需要管理哪些类型的上下文？我们可以将上下文工程视为一个[总括概念](https://x.com/dexhorthy/status/1933283008863482067)，适用于几种不同的上下文类型：

- **Instructions** – prompts, memories, few‑shot examples, tool descriptions, etc
- **Knowledge** – facts, memories, etc
- **Tools** – feedback from tool calls

- **指令** – 提示词、记忆、少样本示例、工具描述等
- **知识** – 事实、记忆等
- **工具** – 工具调用的反馈

## Agent Challenges
## 智能体挑战

However, long-running tasks and accumulating feedback from tool calls mean that agents often utilize a large number of tokens. This can cause numerous problems: it can [exceed the size of the context window](https://cognition.ai/blog/kevin-32b), balloon cost / latency, or degrade agent performance. Drew Breunig [nicely outlined](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html) a number of specific ways that longer context can cause perform problems.

然而，长时间运行的任务和工具调用的累积反馈意味着智能体经常使用大量的token。这可能导致许多问题：可能会[超过上下文窗口的大小](https://cognition.ai/blog/kevin-32b)，成本/延迟激增，或降低智能体性能。Drew Breunig [很好地概述了](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html)更长上下文可能导致性能问题的几种具体方式。 

With this in mind, [Cognition](https://cognition.ai/blog/dont-build-multi-agents) called out the importance of context engineering with agents:

考虑到这一点，[Cognition](https://cognition.ai/blog/dont-build-multi-agents)强调了智能体上下文工程的重要性：

> "Context engineering" … is effectively the #1 job of engineers building AI agents.

> "上下文工程"...实际上是构建AI智能体工程师的首要工作。

[Anthropic](https://www.anthropic.com/engineering/built-multi-agent-research-system) also laid it out clearly:

[Anthropic](https://www.anthropic.com/engineering/built-multi-agent-research-system)也清楚地阐述了这一点：

> *Agents often engage in conversations spanning hundreds of turns, requiring careful context management strategies.*

> *智能体经常进行跨越数百轮的对话，需要仔细的上下文管理策略。*
>

## Context Engineering Strategies
## 上下文工程策略

In this repo, we cover some common strategies — write, select, compress, and isolate — for agent context engineering by reviewing various popular agents and papers. We then explain how LangGraph is designed to support them!

在这个仓库中，我们通过审查各种流行的智能体和论文，涵盖了智能体上下文工程的一些常见策略——写入、选择、压缩和隔离。然后我们解释了LangGraph是如何设计来支持它们的！

* **Writing context** - saving it outside the context window to help an agent perform a task.
* **Selecting context** - pulling it into the context window to help an agent perform a task.
* **Compressing context** - retaining only the tokens required to perform a task.
* **Isolating context** - splitting it up to help an agent perform a task.

* **写入上下文** - 将其保存在上下文窗口之外，以帮助智能体执行任务。
* **选择上下文** - 将其拉入上下文窗口，以帮助智能体执行任务。
* **压缩上下文** - 仅保留执行任务所需的token。
* **隔离上下文** - 将其分割以帮助智能体执行任务。

### 1. Write Context
### 1. 写入上下文
**Description**: Saving information outside the context window to help an agent perform a task.
**描述**：在上下文窗口之外保存信息，以帮助智能体执行任务。

### 📚 **What's Covered in [1_write_context.ipynb](context_engineering/1_write_context.ipynb)**
### 📚 **[1_write_context.ipynb](context_engineering/1_write_context.ipynb)中涵盖的内容**
- **Scratchpads in LangGraph**: Using state objects to persist information during agent sessions
  - StateGraph implementation with TypedDict for structured data
  - Writing context to state and accessing it across nodes
  - Checkpointing for fault tolerance and pause/resume workflows
- **Memory Systems**: Long-term persistence across multiple sessions
  - InMemoryStore for storing memories with namespaces
  - Integration with checkpointing for comprehensive memory management
  - Examples of storing and retrieving jokes with user context

- **LangGraph中的草稿本**：使用状态对象在智能体会话期间持久化信息
  - 使用TypedDict实现StateGraph进行结构化数据处理
  - 将上下文写入状态并在节点间访问
  - 用于容错和暂停/恢复工作流的检查点
- **内存系统**：跨多个会话的长期持久化
  - 使用命名空间存储记忆的InMemoryStore
  - 与检查点集成进行全面的内存管理
  - 存储和检索带有用户上下文的笑话示例

## 2. Select Context
## 2. 选择上下文
**Description**: Pulling information into the context window to help an agent perform a task.
**描述**：将信息拉入上下文窗口，以帮助智能体执行任务。

### 📚 **What's Covered in [2_select_context.ipynb](context_engineering/2_select_context.ipynb)**
### 📚 **[2_select_context.ipynb](context_engineering/2_select_context.ipynb)中涵盖的内容**
- **Scratchpad Selection**: Fetching specific context from agent state
  - Selective state access in LangGraph nodes
  - Multi-step workflows with context passing between nodes
- **Memory Retrieval**: Selecting relevant memories for current tasks
  - Namespace-based memory retrieval
  - Context-aware memory selection to avoid irrelevant information
- **Tool Selection**: RAG-based tool retrieval for large tool sets
  - LangGraph Bigtool library for semantic tool search
  - Embedding-based tool description matching
  - Examples with math library functions and semantic retrieval
- **Knowledge Retrieval**: RAG implementation for external knowledge
  - Vector store creation with document splitting
  - Retriever tools integrated with LangGraph agents
  - Multi-turn conversations with context-aware retrieval

- **草稿本选择**：从智能体状态中获取特定上下文
  - LangGraph节点中的选择性状态访问
  - 在节点间传递上下文的多步工作流
- **内存检索**：为当前任务选择相关记忆
  - 基于命名空间的内存检索
  - 上下文感知的内存选择，避免不相关信息
- **工具选择**：针对大型工具集的基于RAG的工具检索
  - 用于语义工具搜索的LangGraph Bigtool库
  - 基于嵌入的工具描述匹配
  - 数学库函数和语义检索的示例
- **知识检索**：针对外部知识的RAG实现
  - 使用文档分割创建向量存储
  - 与LangGraph智能体集成的检索器工具
  - 具有上下文感知检索的多轮对话

## 3. Compress Context
## 3. 压缩上下文
**Description**: Retaining only the tokens required to perform a task.
**描述**：仅保留执行任务所需的token。

### 📚 **What's Covered in [3_compress_context.ipynb](context_engineering/3_compress_context.ipynb)**
### 📚 **[3_compress_context.ipynb](context_engineering/3_compress_context.ipynb)中涵盖的内容**
- **Conversation Summarization**: Managing long agent trajectories
  - End-to-end conversation summarization after task completion
  - Token usage optimization (demonstrated reduction from 115k to 60k tokens)
- **Tool Output Compression**: Reducing token-heavy tool responses
  - Summarization of RAG retrieval results
  - Integration with LangGraph tool nodes
  - Practical examples with blog post retrieval and summarization
- **State-based Compression**: Using LangGraph state for context management
  - Custom state schemas with summary fields
  - Conditional summarization based on context length

- **对话摘要**：管理长期智能体轨迹
  - 任务完成后的端到端对话摘要
  - Token使用优化（演示从115k个 token减少到60k个）
- **工具输出压缩**：减少token密集的工具响应
  - RAG检索结果的摘要
  - 与LangGraph工具节点的集成
  - 博客文章检索和摘要的实际示例
- **基于状态的压缩**：使用LangGraph状态进行上下文管理
  - 带有摘要字段的自定义状态模式
  - 基于上下文长度的条件性摘要

## 4. Isolate Context
## 4. 隔离上下文
**Description**: Splitting up context to help an agent perform a task.
**描述**：分割上下文以帮助智能体执行任务。

### 📚 **What's Covered in [4_isolate_context.ipynb](context_engineering/4_isolate_context.ipynb)**
### 📚 **[4_isolate_context.ipynb](context_engineering/4_isolate_context.ipynb)中涵盖的内容**
- **Multi-Agent Systems**: Separating concerns across specialized agents
  - Supervisor architecture for task delegation
  - Specialized agents with isolated context windows (math expert, research expert)
  - LangGraph Supervisor library implementation
- **Sandboxed Environments**: Isolating context in execution environments
  - PyodideSandboxTool for secure code execution
  - State isolation outside the LLM context window
  - Examples of context storage in sandbox variables
- **State-based Isolation**: Using LangGraph state schemas for context separation
  - Structured state design for selective context exposure
  - Field-based isolation within agent state objects

- **多智能体系统**：在专业化智能体间分离关注点
  - 用于任务委托的监督器架构
  - 具有隔离上下文窗口的专业化智能体（数学专家、研究专家）
  - LangGraph Supervisor库实现
- **沙盒环境**：在执行环境中隔离上下文
  - 用于安全代码执行的PyodideSandboxTool
  - 在大语言模型上下文窗口之外的状态隔离
  - 在沙盒变量中存储上下文的示例
- **基于状态的隔离**：使用LangGraph状态模式进行上下文分离
  - 用于选择性上下文暴露的结构化状态设计
  - 智能体状态对象内的基于字段的隔离

