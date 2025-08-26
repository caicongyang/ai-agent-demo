# LangGraph ReAct 记忆智能体

[![CI](https://github.com/langchain-ai/memory-agent/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/langchain-ai/memory-agent/actions/workflows/unit-tests.yml)
[![Integration Tests](https://github.com/langchain-ai/memory-agent/actions/workflows/integration-tests.yml/badge.svg)](https://github.com/langchain-ai/memory-agent/actions/workflows/integration-tests.yml)
[![Open in - LangGraph Studio](https://img.shields.io/badge/Open_in-LangGraph_Studio-00324d.svg?logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4NS4zMzMiIGhlaWdodD0iODUuMzMzIiB2ZXJzaW9uPSIxLjAiIHZpZXdCb3g9IjAgMCA2NCA2NCI+PHBhdGggZD0iTTEzIDcuOGMtNi4zIDMuMS03LjEgNi4zLTYuOCAyNS43LjQgMjQuNi4zIDI0LjUgMjUuOSAyNC41QzU3LjUgNTggNTggNTcuNSA1OCAzMi4zIDU4IDcuMyA1Ni43IDYgMzIgNmMtMTIuOCAwLTE2LjEuMy0xOSAxLjhtMzcuNiAxNi42YzIuOCAyLjggMy40IDQuMiAzLjQgNy42cy0uNiA0LjgtMy40IDcuNkw0Ny4yIDQzSDE2LjhsLTMuNC0zLjRjLTQuOC00LjgtNC44LTEwLjQgMC0xNS4ybDMuNC0zLjRoMzAuNHoiLz48cGF0aCBkPSJNMTguOSAyNS42Yy0xLjEgMS4zLTEgMS43LjQgMi41LjkuNiAxLjcgMS44IDEuNyAyLjcgMCAxIC43IDIuOCAxLjYgNC4xIDEuNCAxLjkgMS40IDIuNS4zIDMuMi0xIC42LS42LjkgMS40LjkgMS41IDAgMi43LS41IDIuNy0xIDAtLjYgMS4xLS44IDIuNi0uNGwyLjYuNy0xLjgtMi45Yy01LjktOS4zLTkuNC0xMi4zLTExLjUtOS44TTM5IDI2YzAgMS4xLS45IDIuNS0yIDMuMi0yLjQgMS41LTIuNiAzLjQtLjUgNC4yLjguMyAyIDEuNyAyLjUgMy4xLjYgMS41IDEuNCAyLjMgMiAyIDEuNS0uOSAxLjItMy41LS40LTMuNS0yLjEgMC0yLjgtMi44LS44LTMuMyAxLjYtLjQgMS42LS41IDAtLjYtMS4xLS4xLTEuNS0uNi0xLjItMS42LjctMS43IDMuMy0yLjEgMy41LS41LjEuNS4yIDEuNi4zIDIuMiAwIC43LjkgMS40IDEuOSAxLjYgMi4xLjQgMi4zLTIuMy4yLTMuMi0uOC0uMy0yLTEuNy0yLjUtMy4xLTEuMS0zLTMtMy4zLTMtLjUiLz48L3N2Zz4=)](https://langgraph-studio.vercel.app/templates/open?githubUrl=https://github.com/langchain-ai/memory-agent)

本仓库提供了一个简单的 ReAct 风格智能体示例，该智能体具有保存记忆的工具。这是让智能体持久化重要信息以便后续重复使用的简单方法。在此案例中，我们将所有记忆保存在可配置的 `user_id` 作用域内，这使得机器人能够跨对话线程学习用户偏好。

![记忆图表](./static/memory_graph.png)

## 快速开始

本快速入门指南将帮助您在 [LangGraph Cloud](https://langchain-ai.github.io/langgraph/cloud/) 上部署记忆服务。创建完成后，您可以从任何 API 与其交互。

### 环境准备

#### 1. 创建虚拟环境

建议使用虚拟环境来隔离项目依赖：

##### 使用 uv（推荐）

```bash
# 使用 uv 创建虚拟环境（自动选择合适的 Python 版本）
uv venv 

# 激活虚拟环境
# 在 macOS/Linux 上：
source .venv/bin/activate

# 在 Windows 上：
memory-agent-env\Scripts\activate
```

##### 使用 venv

```bash
# 使用 venv 创建虚拟环境
python -m venv memory-agent-env

# 激活虚拟环境
# 在 macOS/Linux 上：
source memory-agent-env/bin/activate

# 在 Windows 上：
memory-agent-env\Scripts\activate
```

##### 使用 conda

```bash
# 创建 conda 环境
conda create -n memory-agent python=3.9

# 激活环境
conda activate memory-agent
```

#### 2. 安装项目依赖

本项目使用 `pyproject.toml` 文件管理依赖。您可以通过以下方式安装：

##### 使用 uv（推荐，更快）

[uv](https://github.com/astral-sh/uv) 是一个极快的Python包管理器，推荐使用：

```bash
# 安装 uv（如果尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或者使用 pip 安装 uv
pip install uv

# 使用 uv 创建虚拟环境并安装依赖
uv venv memory-agent-env
source memory-agent-env/bin/activate  # macOS/Linux
# 或 memory-agent-env\Scripts\activate  # Windows

# 安装项目依赖
uv pip install -e .

# 如果需要开发依赖
uv pip install -e ".[dev]"
```

##### 使用传统 pip 方式

```bash
# 方式一：使用 pip 安装
pip install -e .

# 方式二：如果您需要开发依赖
pip install -e ".[dev]"

# 方式三：直接从 pyproject.toml 安装
pip install .
```

**注意：** 项目需要 Python 3.9 或更高版本。

#### 3. 验证安装

安装完成后，您可以验证主要依赖是否正确安装：

```bash
python -c "import langgraph; print('LangGraph version:', langgraph.__version__)"
```

#### 4. 验证 Azure 配置（可选）

如果您使用 Azure OpenAI，可以运行测试脚本验证配置：

```bash
# 查看配置模板
python test_azure_config.py --template

# 测试 Azure OpenAI 配置
python test_azure_config.py
```

### 配置设置

假设您已经[安装了 LangGraph Studio](https://github.com/langchain-ai/langgraph-studio?tab=readme-ov-file#download)，设置步骤如下：

1. 创建 `.env` 文件。

```bash
cp .env.example .env
```

2. 在您的 `.env` 文件中定义必需的 API 密钥。

### 设置模型

`model` 的默认值如下所示：

```yaml
model: anthropic/claude-3-5-sonnet-20240620
```

您可以选择以下任一模型提供商：

**支持的模型格式**：
- Anthropic: `anthropic/claude-3-5-sonnet-20240620`
- OpenAI: `openai/gpt-4`, `openai/gpt-3.5-turbo`
- Azure OpenAI: `azure_openai/gpt-4`, `azure_openai/gpt-35-turbo`

按照以下说明进行设置，或选择其他选项之一。

#### Anthropic

使用 Anthropic 的聊天模型：

1. 如果您还没有 [Anthropic API 密钥](https://console.anthropic.com/)，请先注册获取。
2. 获得 API 密钥后，将其添加到您的 `.env` 文件中：

```
ANTHROPIC_API_KEY=your-api-key
```

#### OpenAI

使用 OpenAI 的聊天模型：

1. 注册获取 [OpenAI API 密钥](https://platform.openai.com/signup)。
2. 获得 API 密钥后，将其添加到您的 `.env` 文件中：

```
OPENAI_API_KEY=your-api-key
MODEL=openai/gpt-4
```

#### Azure OpenAI

使用 Azure OpenAI 服务：

1. 在 [Azure 门户](https://portal.azure.com/) 中创建 Azure OpenAI 资源。
2. 部署您需要的模型（如 GPT-4、GPT-3.5-turbo）。
3. 获取以下信息并添加到您的 `.env` 文件中：

```
# Azure OpenAI 配置
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# 模型配置（使用您在 Azure 中部署的模型名称）
MODEL=azure_openai/gpt-4

# 可选：如果部署名称与模型名称不同
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=your-gpt4-deployment-name
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME=your-embedding-deployment-name
```

**注意**：
- 请将 `your-resource-name` 替换为您的 Azure OpenAI 资源名称
- 确保在 Azure 中部署了相应的模型
- API 版本可能会更新，请参考 [Azure OpenAI 文档](https://learn.microsoft.com/azure/ai-services/openai/)
- 详细的 Azure 配置步骤请参考：[Azure OpenAI 配置指南](./AZURE_SETUP_zh.md)

3. 在 LangGraph Studio 中打开。导航到 `memory_agent` 图表并与其对话！尝试发送一些包含您姓名和其他机器人应该记住的信息的消息。

假设机器人保存了一些记忆，使用 `+` 图标创建一个_新_线程。然后再次与机器人聊天 - 如果您已正确完成设置，机器人现在应该能够访问您保存的记忆！

您可以通过点击"记忆"按钮来查看保存的记忆。

![记忆浏览器](./static/memories.png)

## 工作原理

这个聊天机器人从您的记忆图表的 `Store` 中读取数据，轻松列出提取的记忆。如果它调用工具，LangGraph 将路由到 `store_memory` 节点将信息保存到存储中。

## 如何评估

记忆管理可能很难做好，特别是如果您为机器人添加了额外的工具供其选择。
为了调整机器人保存记忆的频率和质量，我们建议从评估集开始，随着时间的推移不断添加内容，以发现和解决服务中的常见错误。

我们在[这里的测试文件](./tests/integration_tests/test_graph.py)中提供了一些示例评估案例。如您所见，指标本身不必过于复杂，特别是在开始阶段。

我们使用 [LangSmith 的 @unit 装饰器](https://docs.smith.langchain.com/how_to_guides/evaluation/unit_testing#write-a-test)将所有评估同步到 LangSmith，以便您更好地优化系统并识别可能出现的任何问题的根本原因。

## 项目结构

```
memory-agent/
├── src/memory_agent/          # 主要源代码
│   ├── __init__.py
│   ├── context.py            # 上下文处理
│   ├── graph.py              # LangGraph 图定义
│   ├── prompts.py            # 提示词模板
│   ├── state.py              # 状态管理
│   ├── tools.py              # 工具定义
│   └── utils.py              # 工具函数
├── tests/                    # 测试文件
├── static/                   # 静态资源
├── pyproject.toml            # 项目配置和依赖
├── langgraph.json            # LangGraph 配置
├── docs/                     # 📚 详细文档目录
│   ├── README.md             #   文档导航和学习路径
│   ├── 快速入门_Memory系统.md  #   5分钟理解Memory概念
│   └── LangGraph_Memory_深入指南.md #  完整的Memory系统文档
├── README.md                 # 英文说明文档
├── README_zh.md              # 中文说明文档
├── AZURE_SETUP_zh.md         # Azure OpenAI 配置指南
├── test_azure_config.py      # Azure 配置测试脚本
└── .env.example              # 环境变量示例（需要创建）
```

## 开发环境

如果您需要进行开发工作，建议安装开发依赖：

### 使用 uv 进行开发（推荐）

```bash
# 使用 uv 安装开发依赖
uv pip install -e ".[dev]"

# 或者一步到位：创建环境并安装开发依赖
uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"

# 运行代码格式检查
uv run ruff check .

# 运行类型检查  
uv run mypy src/

# 运行测试
uv run pytest tests/
```

### 使用传统 pip 进行开发

```bash
# 安装开发依赖（包含 mypy, ruff, pytest-asyncio）
pip install -e ".[dev]"

# 运行代码格式检查
ruff check .

# 运行类型检查
mypy src/

# 运行测试
pytest tests/
```

## 如何自定义

1. **自定义记忆内容**：我们为每个记忆定义了简单的记忆结构 `content: str, context: str`，但您可以用其他方式构建它们。
2. **提供额外工具**：如果您将机器人连接到其他功能，它会更有用。
3. **选择不同模型**：我们默认使用 anthropic/claude-3-5-sonnet-20240620。您可以通过配置使用 provider/model-name 选择兼容的聊天模型。例如：
   - OpenAI: `openai/gpt-4`
   - Azure OpenAI: `azure_openai/gpt-4`
   - Anthropic: `anthropic/claude-3-5-sonnet-20240620`
4. **自定义提示词**：我们在 [prompts.py](src/memory_agent/prompts.py) 文件中提供了默认提示词。您可以通过配置轻松更新。

## 依赖说明

### 主要依赖包括：
- **langgraph** (>=0.6.0): 核心图执行框架
- **langchain-openai** (>=0.2.1): OpenAI 和 Azure OpenAI 模型集成
- **langchain-anthropic** (>=0.2.1): Anthropic 模型集成
- **langchain** & **langchain-core** (>=0.3.8): 基础 LangChain 组件
- **python-dotenv** (>=1.0.1): 环境变量管理
- **langgraph-sdk** (>=0.1.32): LangGraph SDK

### 开发依赖：
- **mypy**: 静态类型检查
- **ruff**: 代码格式化和 linting
- **pytest-asyncio**: 异步测试支持

### 包管理器选择：

**推荐使用 uv**：
- ⚡ **极快的安装速度**：比 pip 快 10-100 倍
- 🔒 **可靠的依赖解析**：更好的冲突检测和解决
- 🐍 **Python 版本管理**：自动处理 Python 版本要求
- 💾 **全局缓存**：避免重复下载相同包
- 🔧 **完全兼容 pip**：无需修改现有工作流程

**传统 pip**：
- ✅ **广泛支持**：所有环境都可用
- 📚 **文档丰富**：大量教程和资源
- 🔄 **稳定可靠**：经过长期验证的工具

## 📚 详细文档

我们提供了完整的LangGraph Memory系统文档，帮助您深入理解和使用记忆功能：

### 🚀 快速开始
- **[Memory系统快速入门](./docs/快速入门_Memory系统.md)** - 5分钟理解Memory核心概念
- **[文档导航](./docs/README.md)** - 完整的学习路径和资源指引

### 📖 深入学习  
- **[LangGraph Memory深入指南](./docs/LangGraph_Memory_深入指南.md)** - 完整的Memory系统实现指南
- 结合[官方文档](https://langchain-ai.github.io/langgraph/concepts/memory/)和项目实际代码的详细解释
- 包含最佳实践、性能优化和问题排查

### 💡 主要内容
- ✅ **核心概念**: Store、Checkpointer、Context详解
- ✅ **实战案例**: 基于本项目的完整分析
- ✅ **最佳实践**: 命名空间设计、错误处理、性能优化
- ✅ **问题解决**: 常见问题和解决方案
- ✅ **代码示例**: 可直接运行的示例代码

**开始学习**: [📖 快速入门文档](./docs/快速入门_Memory系统.md)
