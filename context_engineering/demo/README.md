# LangGraph 完整上下文工程演示

这个演示展示了 LangGraph 中上下文工程的四个核心概念：**写入（Write）**、**选择（Select）**、**压缩（Compress）**和**隔离（Isolate）**。

## 🎯 演示概述

本演示模拟一个智能研究助手，通过处理"人工智能在教育中的应用"这一研究主题，全面展示所有上下文工程技术：

### 1. 📝 Write Context - 写入上下文
- **草稿本（短期记忆）**：将信息写入 LangGraph 的 State 对象
- **长期记忆**：使用 InMemoryStore 跨会话保存信息
- **演示内容**：保存初始分析和研究计划

### 2. 🎯 Select Context - 选择上下文
- **从状态选择**：读取之前写入状态的信息
- **从记忆选择**：检索长期记忆中的相关信息
- **工具选择**：根据主题智能选择相关工具
- **知识检索**：使用 RAG 从知识库检索相关信息

### 3. 🗜️ Compress Context - 压缩上下文
- **对话压缩**：将长对话历史压缩成简洁摘要
- **工具输出压缩**：压缩详细的研究发现
- **Token 优化**：显著减少 token 使用量

### 4. 🏗️ Isolate Context - 隔离上下文
- **多智能体隔离**：使用不同专家（技术、教育、商业）进行隔离分析
- **沙盒隔离**：模拟在隔离环境中进行安全计算

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Anthropic API Key（用于 Claude）
- OpenAI API Key（用于嵌入）

### 安装步骤

1. **克隆项目并进入 demo 目录**
```bash
cd demo
```

2. **安装依赖包**
```bash
pip install -r requirements.txt
```

3. **设置环境变量**
```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key"
export OPENAI_API_KEY="your_openai_api_key"
```

或者在运行时输入（程序会提示）。

### 运行演示

#### 🌟 推荐：多轮对话演示（新功能）
```bash
python run_multi_round_demo.py
```
或
```bash
python complete_context_engineering_demo.py
```

#### 🚀 简化版演示
```bash
python simple_demo.py
```

#### 🔧 使用运行脚本
```bash
./run_demo.sh
```

## 📊 演示流程

### 🌟 多轮对话演示流程（新）

```
开始第1轮
  ↓
📝 写入初始分析（带日志） → 🛠️ 多工具调用（4个工具）
  ↓
🎯 综合上下文选择（智能过滤） → 🗜️ 压缩对话和发现
  ↓
🏗️ 多智能体隔离分析 → 🔄 准备下一轮
  ↓
第2轮：重复上述流程（新查询：技术挑战分析）
  ↓
第3轮：重复上述流程（新查询：市场前景分析）
  ↓
📈 最终总结和统计展示
```

### 🚀 简化演示流程

```
开始
  ↓
📝 写入分析 → 🎯 选择上下文 → 🗜️ 压缩内容 → 🏗️ 隔离处理
  ↓
结束并展示结果
```

## 🎨 输出展示

演示使用 Rich 库提供美观的控制台输出，包括：

- **彩色面板**：每个步骤都有清晰的视觉分隔
- **进度追踪**：实时显示处理步骤
- **结果表格**：结构化展示所有功能的实现结果
- **统计信息**：显示 token 使用、压缩率等关键指标
- **📝 上下文操作日志**：详细记录所有写入和选择操作（新功能）
- **🔄 多轮对话进度**：显示每轮对话的进展（新功能）
- **🛠️ 工具调用追踪**：记录每个工具的调用和结果（新功能）

## 🔧 技术实现详情

### 状态管理
```python
class ComprehensiveState(TypedDict):
    research_topic: str          # 研究主题
    initial_analysis: str        # 初始分析（Write）
    selected_memories: List[Dict] # 选择的记忆（Select）
    conversation_summary: str    # 压缩的对话（Compress）
    specialist_reports: Dict     # 专家报告（Isolate）
    # ... 更多字段
```

### 核心组件
- **LLM**: Anthropic Claude 3.5 Sonnet
- **检查点**: InMemorySaver（短期记忆）
- **存储**: InMemoryStore（长期记忆）
- **向量存储**: InMemoryVectorStore（知识检索）
- **嵌入**: OpenAI text-embedding-3-small

### 工作流架构
使用 LangGraph 的 StateGraph 构建，包含 8 个节点：
1. `write_analysis` - 写入初始分析
2. `write_plan` - 写入研究计划  
3. `select_memory` - 选择记忆
4. `select_tools` - 选择工具和知识
5. `compress_conv` - 压缩对话
6. `compress_findings` - 压缩发现
7. `isolate_specialists` - 多智能体隔离
8. `isolate_sandbox` - 沙盒隔离

## 📈 性能特点

- **内存效率**：通过压缩技术显著减少 token 使用
- **模块化设计**：每个功能独立实现，易于理解和修改
- **可扩展性**：容易添加新的专家或工具
- **观测性**：完整的步骤追踪和结果展示

## 🛠️ 自定义和扩展

### 添加新的专家
```python
specialists = {
    "技术专家": "分析技术实现和挑战",
    "教育专家": "评估教育影响和应用", 
    "商业专家": "分析市场前景和商业价值",
    "你的专家": "你的专家描述"  # 添加这里
}
```

### 修改研究主题
修改 `run_complete_demo()` 函数中的 `initial_state`：
```python
initial_state = {
    "research_topic": "你的研究主题",
    "user_query": "你的具体查询",
    # ...
}
```

### 添加真实的知识库
替换模拟的 `sample_docs` 为真实的文档：
```python
# 使用 WebBaseLoader 加载真实网页
from langchain_community.document_loaders import WebBaseLoader
docs = WebBaseLoader("https://example.com").load()
```

## 🐛 故障排除

### 常见问题

1. **API Key 错误**
   - 确保设置了正确的 ANTHROPIC_API_KEY 和 OPENAI_API_KEY
   - 检查 API key 是否有足够的配额

2. **依赖包问题**
   - 运行 `pip install -r requirements.txt` 安装所有依赖
   - 如果遇到版本冲突，尝试创建新的虚拟环境

3. **网络连接问题**
   - 确保网络连接正常，能够访问 API 服务
   - 如果在防火墙后面，可能需要配置代理

### 调试模式

在代码中添加调试信息：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 相关资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangChain 上下文工程博客](https://blog.langchain.com/context-engineering-for-agents/)
- [完整的上下文工程文档](../langgraph_context_engineering_summary.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个演示！

## 📄 许可证

本演示基于 MIT 许可证开源。
