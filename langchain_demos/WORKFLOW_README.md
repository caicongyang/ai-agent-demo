# 🔄 工作流代码解释器

这是一个支持多工具协作的代码执行环境，专门解决"先调用其他工具获取数据，再将结果传递给代码解释器进行分析"的场景。

## 🎯 解决的问题

在实际业务中，我们经常遇到这样的需求：
1. 从 API 获取数据
2. 从数据库查询信息  
3. 读取文件内容
4. **将这些数据传递给代码解释器进行复杂分析**
5. 根据分析结果执行后续操作（如发送邮件、更新数据库等）

传统的单一工具无法很好地处理这种多步骤、有依赖关系的任务。

## 🏗️ 架构设计

### 核心组件

```
WorkflowEngine (工作流引擎)
    ├── WorkflowContext (上下文管理)
    ├── WorkflowTool (工具基类)
    │   ├── APIDataTool (API数据获取)
    │   ├── DatabaseTool (数据库查询)
    │   ├── FileDataTool (文件读取)
    │   ├── WorkflowCodeInterpreter (代码解释器)
    │   └── EmailSenderTool (邮件发送)
    └── Tool Registration (工具注册机制)
```

### 数据流转

```
Step 1: API/DB/File → WorkflowContext.data
Step 2: WorkflowContext.data → CodeInterpreter  
Step 3: CodeInterpreter → Analysis Results
Step 4: Results → Email/Report/Action
```

## 🚀 快速开始

### 基本使用

```python
from workflow_code_interpreter import WorkflowEngine

# 创建工作流引擎
engine = WorkflowEngine()

# 定义工作流步骤
workflow_steps = [
    {
        "tool": "api_data_fetcher",
        "description": "获取用户数据",
        "url": "https://jsonplaceholder.typicode.com/users",
        "data_key": "users_data"
    },
    {
        "tool": "workflow_code_interpreter", 
        "description": "分析用户数据",
        "code": """
# 分析用户数据
users = context_data.get('users_data', [])
print(f'用户数量: {len(users)}')

# 统计城市分布
cities = [user.get('address', {}).get('city', 'Unknown') for user in users]
city_count = {}
for city in cities:
    city_count[city] = city_count.get(city, 0) + 1

print('城市分布:')
for city, count in city_count.items():
    print(f'  {city}: {count} 人')
        """,
        "result_key": "analysis_result"
    }
]

# 执行工作流
result = engine.execute_workflow(workflow_steps)
```

### 高级用法：多数据源分析

```python
workflow_steps = [
    # 步骤1: 获取API数据
    {
        "tool": "api_data_fetcher",
        "url": "https://api.example.com/sales",
        "data_key": "sales_data"
    },
    # 步骤2: 查询数据库
    {
        "tool": "database_query", 
        "query": "SELECT * FROM customers",
        "data_key": "customer_data"
    },
    # 步骤3: 读取配置文件
    {
        "tool": "file_reader",
        "file_path": "/path/to/config.json",
        "data_key": "config_data"
    },
    # 步骤4: 综合分析
    {
        "tool": "workflow_code_interpreter",
        "code": """
# 获取所有数据源
sales = context_data.get('sales_data', [])
customers = context_data.get('customer_data', [])
config = context_data.get('config_data', {})

# 执行复杂的关联分析
print('=== 综合业务分析 ===')
# ... 你的分析逻辑
        """,
        "result_key": "comprehensive_analysis"
    },
    # 步骤5: 发送结果
    {
        "tool": "email_sender",
        "to_email": "manager@company.com", 
        "subject": "业务分析报告",
        "content": "请查看最新的业务分析结果"
    }
]
```

## 🛠️ 内置工具

### 1. APIDataTool - API数据获取

```python
{
    "tool": "api_data_fetcher",
    "url": "https://api.example.com/data",
    "method": "GET",  # GET/POST
    "headers": {"Authorization": "Bearer token"},
    "params": {"limit": 100},
    "data_key": "api_data"
}
```

### 2. DatabaseTool - 数据库查询

```python
{
    "tool": "database_query",
    "query": "SELECT * FROM users WHERE active = 1",
    "data_key": "active_users"
}
```

### 3. FileDataTool - 文件读取

```python
{
    "tool": "file_reader", 
    "file_path": "/path/to/data.json",
    "file_type": "json",  # json/csv/text/auto
    "data_key": "file_data"
}
```

### 4. WorkflowCodeInterpreter - 代码执行

```python
{
    "tool": "workflow_code_interpreter",
    "code": """
# 在这里编写分析代码
# 可以通过 context_data 访问之前步骤的数据
data = context_data.get('my_data', [])
# 进行分析...
    """,
    "result_key": "analysis_result"
}
```

### 5. EmailSenderTool - 邮件发送

```python
{
    "tool": "email_sender",
    "to_email": "user@example.com",
    "subject": "分析报告", 
    "content": "分析已完成，请查看结果"
}
```

## 🔧 自定义工具

### 创建自定义工具

```python
from workflow_code_interpreter import WorkflowTool, WorkflowContext

class CustomDataTool(WorkflowTool):
    def __init__(self):
        super().__init__(
            name="custom_data_fetcher",
            description="自定义数据获取工具"
        )
    
    def execute(self, context: WorkflowContext, **kwargs) -> dict:
        # 实现你的逻辑
        data = self.fetch_custom_data(**kwargs)
        
        # 将数据添加到上下文
        data_key = kwargs.get('data_key', 'custom_data')
        context.add_data(data_key, data, source="CustomAPI")
        
        return {
            "success": True,
            "data": data,
            "message": "自定义数据获取成功"
        }
    
    def fetch_custom_data(self, **kwargs):
        # 你的数据获取逻辑
        return {"example": "data"}

# 注册自定义工具
engine = WorkflowEngine()
engine.register_tool(CustomDataTool())
```

### 扩展代码解释器

```python
class EnhancedCodeInterpreter(WorkflowCodeInterpreter):
    def execute(self, context: WorkflowContext, **kwargs) -> dict:
        # 添加额外的预处理逻辑
        code = kwargs.get('code', '')
        
        # 注入额外的工具函数
        enhanced_code = """
# 工具函数
def safe_divide(a, b):
    return a / b if b != 0 else 0

def format_currency(amount):
    return f"${amount:,.2f}"

# 用户代码:
""" + code
        
        kwargs['code'] = enhanced_code
        return super().execute(context, **kwargs)
```

## 📊 实际应用示例

### 1. 股票分析工作流

```python
# 获取股票数据 → 技术分析 → 生成报告 → 发送邮件
workflow_steps = [
    {
        "tool": "stock_data_fetcher",
        "symbol": "AAPL", 
        "days": 30,
        "data_key": "stock_data"
    },
    {
        "tool": "workflow_code_interpreter",
        "code": """
# 技术分析代码
stock_data = context_data.get('stock_data', [])
# 计算移动平均线、RSI等技术指标
# 生成买卖信号
        """
    },
    {
        "tool": "email_sender",
        "to_email": "trader@fund.com",
        "subject": "股票分析报告"
    }
]
```

### 2. 业务数据管道

```python
# 读取原始数据 → 数据清洗 → 统计分析 → 保存结果
workflow_steps = [
    {
        "tool": "file_reader",
        "file_path": "raw_transactions.csv",
        "data_key": "raw_data"
    },
    {
        "tool": "workflow_code_interpreter", 
        "code": """
# 数据清洗
raw_data = context_data.get('raw_data', [])
cleaned_data = []
for record in raw_data:
    if self.validate_record(record):
        cleaned_data.append(self.clean_record(record))
        """,
        "result_key": "cleaned_data"
    },
    {
        "tool": "workflow_code_interpreter",
        "code": """
# 统计分析
cleaned_data = context_data.get('cleaned_data', [])
# 生成各种统计指标和图表
        """,
        "result_key": "analysis_report"
    }
]
```

### 3. 智能监控告警

```python
# 监控数据获取 → 异常检测 → 告警发送
workflow_steps = [
    {
        "tool": "api_data_fetcher",
        "url": "https://monitoring.api.com/metrics",
        "data_key": "metrics"
    },
    {
        "tool": "workflow_code_interpreter",
        "code": """
# 异常检测算法
metrics = context_data.get('metrics', [])
anomalies = []
for metric in metrics:
    if self.detect_anomaly(metric):
        anomalies.append(metric)
        
if anomalies:
    print(f"检测到 {len(anomalies)} 个异常")
        """,
        "result_key": "anomaly_detection"
    },
    {
        "tool": "email_sender",
        "to_email": "ops@company.com",
        "subject": "系统异常告警"
    }
]
```

## 🔒 安全性和沙箱

工作流代码解释器支持沙箱执行：

```python
from sandboxed_code_interpreter import SandboxConfig

# 配置安全的代码执行环境
config = SandboxConfig(
    use_docker=True,
    use_restricted_python=True,
    allowed_modules=["math", "json", "statistics"],
    max_execution_time=30
)

# 创建沙箱化的工作流解释器
interpreter = WorkflowCodeInterpreter(use_sandbox=True)
```

## 🎮 交互式模式

支持交互式工作流构建：

```python
python workflow_code_interpreter.py
# 选择 "4. 交互式工作流模式"

# 在交互式模式中：
workflow>>> api_data_fetcher url=https://api.example.com data_key=my_data
workflow>>> workflow_code_interpreter code="print(context_data.get('my_data'))"
workflow>>> summary  # 查看上下文摘要
workflow>>> quit
```

## 🔄 与 LangChain 集成

```python
from workflow_code_interpreter import WorkflowCodeInterpreterTool
from langchain.agents import initialize_agent
from langchain_openai import ChatOpenAI

# 创建 LangChain 工具
workflow_tool = WorkflowCodeInterpreterTool()

# 集成到智能代理
llm = ChatOpenAI(temperature=0)
agent = initialize_agent(
    tools=[workflow_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)

# 使用自然语言描述工作流
response = agent.run("""
请执行以下工作流:
1. 从 https://api.example.com/users 获取用户数据
2. 分析用户的地理分布
3. 生成统计报告
""")
```

## 🚀 最佳实践

### 1. 错误处理

```python
workflow_steps = [
    {
        "tool": "api_data_fetcher",
        "url": "https://api.example.com/data",
        "data_key": "api_data",
        "stop_on_error": True  # 失败时停止工作流
    },
    # 后续步骤...
]
```

### 2. 数据验证

```python
{
    "tool": "workflow_code_interpreter",
    "code": """
# 数据验证
data = context_data.get('api_data', [])
if not data:
    raise ValueError("API 数据为空")
    
if len(data) < 10:
    print("⚠️  数据量较少，分析结果可能不准确")
    """
}
```

### 3. 性能优化

```python
# 对于大数据量，分批处理
{
    "tool": "workflow_code_interpreter", 
    "code": """
data = context_data.get('large_dataset', [])
batch_size = 1000

for i in range(0, len(data), batch_size):
    batch = data[i:i+batch_size]
    # 处理批次数据
    process_batch(batch)
    """
}
```

### 4. 结果缓存

```python
# 缓存中间结果，避免重复计算
{
    "tool": "workflow_code_interpreter",
    "code": """
import hashlib
import pickle

# 生成数据哈希
data = context_data.get('input_data')
data_hash = hashlib.md5(str(data).encode()).hexdigest()
cache_key = f"analysis_{data_hash}"

# 检查缓存
if cache_key in context_data:
    result = context_data[cache_key]
    print("使用缓存结果")
else:
    # 执行分析
    result = expensive_analysis(data)
    context_data[cache_key] = result
    """
}
```

## 🔧 配置和部署

### 环境变量配置

```bash
# API 配置
export API_BASE_URL=https://api.company.com
export API_TOKEN=your_api_token

# 数据库配置  
export DB_HOST=localhost
export DB_USER=workflow_user
export DB_PASSWORD=secure_password

# 邮件配置
export SMTP_HOST=smtp.company.com
export SMTP_USER=workflow@company.com
export SMTP_PASSWORD=email_password
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY workflow_code_interpreter.py .
COPY workflow_examples.py .

CMD ["python", "workflow_code_interpreter.py"]
```

## 📈 监控和日志

### 执行监控

```python
# 获取工作流执行统计
engine = WorkflowEngine()
result = engine.execute_workflow(steps)

print("执行统计:")
print(f"总步骤: {len(result['results'])}")
print(f"成功步骤: {sum(1 for r in result['results'] if r.get('success'))}")
print(f"执行时间: {total_execution_time}s")
```

### 日志记录

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 在工具中添加日志
class CustomTool(WorkflowTool):
    def execute(self, context, **kwargs):
        logger.info(f"执行工具: {self.name}")
        result = super().execute(context, **kwargs)
        logger.info(f"工具执行{'成功' if result['success'] else '失败'}")
        return result
```

## 🤝 贡献指南

欢迎贡献新的工具和功能！

1. Fork 项目
2. 创建功能分支
3. 实现新工具或功能
4. 添加测试和文档
5. 提交 Pull Request

## 📄 许可证

MIT License - 详见 LICENSE 文件
