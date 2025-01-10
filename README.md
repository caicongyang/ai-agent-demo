# AI Agent Demo

这是一个基于 LangChain 的 AI 智能代理演示项目，展示了多种 AI 应用场景。

## 功能特点

### 1. MySQL 自然语言查询 (mysql_chain_demo.py)
- 支持使用自然语言查询 MySQL 数据库
- 自动获取数据库表结构
- 智能 SQL 生成
- 查询结果格式化展示

### 2. ReAct 模式演示 (react_chain_demo.py)
- 结合推理和行动的 AI 代理
- 集成搜索工具
- 支持多轮对话
- 工具调用示例

### 3. 路由链演示 (route_chain_demo.py)
- 智能查询分类
- 多场景处理链路由
- 支持翻译、代码、数学等多种查询类型

### 4. 工具调用演示 (tool_calling_demo.py)
- 自定义工具集成
- 工具调用流程展示
- 结构化输出解析

### 5. 链式调用演示 (chain_runnables_demo.py)
- 链式处理流程
- 并行执行示例
- 结果组合处理

## 环境要求

```bash
Python 3.11+
MySQL 8.0+
```

## 安装

1. 创建虚拟环境：
```bash
conda create -n ai-agent-demo python=3.11
conda activate ai-agent-demo
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

## 配置说明

在 `.env` 文件中配置以下信息：

```ini
# LLM API 配置
LLM_API_KEY=your-llm-api-key
LLM_BASE_URL=your-llm-base-url

# Embedding API 配置
EMBEDDING_API_KEY=your-embedding-api-key
EMBEDDING_BASE_URL=your-embedding-base-url

# Search API 配置
SERPAPI_API_KEY=your-serpapi-key
GOOGLE_PLACES_API_KEY=your-google-places-key

# MySQL 配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database
```

## 使用示例

### MySQL 自然语言查询：
```python
from demo.langchain.mysql_chain_demo import MySQLChainDemo

# 创建演示实例
demo = MySQLChainDemo()

# 执行查询
result = demo.execute_query("查询t_stock_min_trade表中最新的交易时间")
print(result)
```

### ReAct 模式演示：
```python
from demo.langchain.react_chain_demo import ReActChainDemo

# 创建演示实例
demo = ReActChainDemo()

# 执行查询
result = demo.process_query("2023年诺贝尔物理学奖获得者是谁？")
print(result)
```

## 项目结构

```
ai-agent-demo/
├── demo/
│   ├── langchain/
│   │   ├── mysql_chain_demo.py    # MySQL 查询演示
│   │   ├── react_chain_demo.py    # ReAct 模式演示
│   │   ├── route_chain_demo.py    # 路由链演示
│   │   ├── tool_calling_demo.py   # 工具调用演示
│   │   └── chain_runnables_demo.py # 链式调用演示
│   └── langgraph/
│       └── google_search.py       # Google 搜索集成
├── requirements.txt               # 项目依赖
├── setup.py                      # 安装配置
├── .env.example                  # 环境变量示例
└── README.md                     # 项目说明
```

## 注意事项

1. 确保所有必要的 API 密钥都已正确配置
2. MySQL 数据库需要预先创建并授予适当的访问权限
3. 部分功能可能需要网络访问（如搜索功能）

## 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 许可证

MIT License
