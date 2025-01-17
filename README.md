# LangChain Demo

[English](README_EN.md) | [中文](README.md)

这是一个 LangChain 应用示例集合，展示了各种 LangChain 的使用场景。

### 项目结构

```
langchain-demo/
├── demo/
│   ├── langchain/           # LangChain 基础功能演示
│   │   ├── callback_demo.py     # 回调功能示例
│   │   ├── json_parser_demo.py  # JSON 解析示例
│   │   ├── memory_chain_demo.py # 记忆链示例
│   │   ├── mysql_chain_demo.py  # MySQL 查询示例
│   │   ├── react_chain_demo.py  # ReAct 模式示例
│   │   ├── route_chain_demo.py  # 路由链示例
│   │   └── tool_calling_demo.py # 工具调用示例
│   ├── langgraph/           # LangGraph 功能演示
│   │   ├── visualization_demo.py    # 图可视化示例
│   │   ├── simple_qa_demo.py       # 简单问答示例
│   │   └── team_collaboration_demo.py # 团队协作示例
│   └── langsmith/           # LangSmith 功能演示
│       └── stock_analysis_demo.py   # 股票分析评估示例
└── rag/                    # RAG 应用示例
    └── rag_web_app.py      # RAG Web 应用
```

### 环境配置

1. 创建环境：
```bash
conda create -n langchain-demo python=3.11
conda activate langchain-demo
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置信息
```

### 运行示例

每个示例都可以独立运行，例如：

```bash
python demo/langchain/mysql_chain_demo.py
python demo/langgraph/simple_qa_demo.py
python demo/langsmith/stock_analysis_demo.py
```

### 许可证

MIT License
