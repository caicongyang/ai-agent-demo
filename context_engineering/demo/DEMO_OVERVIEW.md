# LangGraph 上下文工程演示总览

本目录包含了完整的 LangGraph 上下文工程演示，展示了四个核心概念的实际应用。

## 📁 文件结构

```
demo/
├── complete_context_engineering_demo.py  # 🌟 主要的完整演示
├── simple_demo.py                        # 🚀 简化版演示
├── write_context_demo.py                 # 📝 写入上下文专项演示
├── requirements.txt                      # 📦 依赖包列表
├── README.md                            # 📖 详细说明文档
├── run_demo.sh                          # 🔧 运行脚本
└── DEMO_OVERVIEW.md                     # 📋 本文档
```

## 🎯 演示类型

### 1. 🌟 完整演示 (`complete_context_engineering_demo.py`)
- **推荐使用** - 最全面的演示
- 展示所有四个上下文工程概念
- 包含美观的控制台输出
- 完整的工作流程和结果分析
- 适合深入学习和理解

### 2. 🚀 简化演示 (`simple_demo.py`)
- **快速入门** - 最简单的演示
- 核心概念的基本实现
- 运行时间短，依赖少
- 适合初次接触和快速验证

### 3. 📝 写入上下文专项演示 (`write_context_demo.py`)
- 专注于写入上下文功能
- 详细展示草稿本和长期记忆
- 适合深入理解状态管理

## 🚀 快速开始

### 方法 1：使用运行脚本（推荐）
```bash
cd demo
./run_demo.sh
```

### 方法 2：直接运行
```bash
cd demo
pip install -r requirements.txt
python complete_context_engineering_demo.py
```

## 🔧 环境配置

### 必需的 API Keys
- `ANTHROPIC_API_KEY` - 用于 Claude LLM
- `OPENAI_API_KEY` - 用于嵌入功能

### 设置方法
```bash
export ANTHROPIC_API_KEY="your_key_here"
export OPENAI_API_KEY="your_key_here"
```

或在运行时输入（程序会提示）。

## 📊 演示内容对比

| 特性 | 完整演示 | 简化演示 | 写入专项 |
|------|----------|----------|----------|
| Write Context | ✅ | ✅ | ✅ |
| Select Context | ✅ | ✅ | ❌ |
| Compress Context | ✅ | ✅ | ❌ |
| Isolate Context | ✅ | ✅ | ❌ |
| 美观输出 | ✅ | ✅ | ✅ |
| 详细分析 | ✅ | ❌ | ✅ |
| 运行时间 | 长 | 短 | 中等 |
| 学习价值 | 最高 | 中等 | 专项深入 |

## 🎨 输出示例

### 完整演示输出
```
🚀 LangGraph 完整上下文工程演示

📝 WRITE CONTEXT - 写入上下文
🧠 正在生成初始分析...
✅ 初始分析已写入

🎯 SELECT CONTEXT - 选择上下文  
🔍 正在从长期记忆中选择相关信息...
✅ 记忆选择完成

🗜️ COMPRESS CONTEXT - 压缩上下文
📄 正在压缩对话历史...
✅ 对话历史压缩完成

🏗️ ISOLATE CONTEXT - 隔离上下文
👥 正在创建专门的智能体进行隔离分析...
✅ 专家隔离分析完成

🎉 完整的上下文工程演示结果
```

## 🔍 核心概念说明

### 📝 Write Context - 写入上下文
将信息保存在上下文窗口之外，包括：
- **状态写入**：信息写入 LangGraph State
- **记忆写入**：信息保存到长期存储

### 🎯 Select Context - 选择上下文
将相关信息拉入上下文窗口，包括：
- **状态选择**：从当前状态读取信息
- **记忆选择**：从长期存储检索信息
- **工具选择**：智能选择相关工具
- **知识检索**：RAG 方式检索知识

### 🗜️ Compress Context - 压缩上下文
减少 token 使用，包括：
- **对话压缩**：压缩长对话历史
- **内容摘要**：提取关键信息

### 🏗️ Isolate Context - 隔离上下文
分离不同类型的处理，包括：
- **多智能体**：使用专门的智能体
- **沙盒隔离**：在隔离环境中处理

## 🛠️ 自定义选项

### 修改研究主题
在演示脚本中修改：
```python
"research_topic": "你的主题"
```

### 添加新的专家
在 `isolate_with_specialists` 函数中添加：
```python
specialists = {
    "现有专家": "描述",
    "你的专家": "你的专家描述"
}
```

### 使用真实数据源
替换模拟数据为真实的文档或 API。

## 🐛 常见问题

1. **API Key 错误**：确保设置正确的 API keys
2. **依赖包问题**：运行 `pip install -r requirements.txt`
3. **网络问题**：确保能访问 Anthropic 和 OpenAI API

## 📚 学习路径

1. **入门**：先运行 `simple_demo.py` 了解基本概念
2. **深入**：运行 `complete_context_engineering_demo.py` 看完整实现
3. **专项**：运行 `write_context_demo.py` 深入特定功能
4. **自定义**：修改代码实现自己的用例

## 🤝 贡献

欢迎提交改进建议和新的演示示例！

---

*这个演示是 LangGraph 上下文工程学习的最佳起点。从简单开始，逐步深入！*
