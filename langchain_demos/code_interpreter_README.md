# 代码解释器演示

这个演示展示了如何使用 LangChain 的 `PythonREPLTool` 和 `PythonAstREPLTool` 创建一个小型代码解释器。

## 功能特性

### 🔧 核心功能
- **PythonREPLTool**: 完整的 Python 代码执行环境
- **PythonAstREPLTool**: 安全的 Python 代码执行环境 (推荐)
- **交互式界面**: 类似 Jupyter Notebook 的交互体验
- **执行历史**: 记录所有代码执行历史
- **错误处理**: 完善的异常捕获和错误提示

### 🤖 AI 增强功能
- **智能代理**: 集成 OpenAI GPT 模型
- **自然语言查询**: 用自然语言描述需求，AI 自动生成并执行代码
- **对话记忆**: 支持多轮对话上下文

## 安装依赖

```bash
pip install langchain langchain-openai langchain-experimental
```

## 使用方法

### 1. 基本使用

```python
from langchain_demos.code_interpreter_demo import CodeInterpreter

# 创建代码解释器 (使用安全的 AST 模式)
interpreter = CodeInterpreter(use_ast_repl=True)

# 执行 Python 代码
result = interpreter.execute_code("print('Hello, World!')")
```

### 2. 交互式模式

```bash
cd /Users/caicongyang/IdeaProjects/github/ai-agent-demo/langchain_demos
python code_interpreter_demo.py
```

选择 "4. 交互式模式" 进入交互式代码解释器。

### 3. AI 增强模式

```python
import os
os.environ["OPENAI_API_KEY"] = "your-api-key-here"

interpreter = CodeInterpreter(use_ast_repl=True, openai_api_key="your-api-key")
response = interpreter.execute_with_ai("计算斐波那契数列的前10项")
```

## 演示模式

### 1. 基本使用演示
展示基本的 Python 代码执行功能：
- 简单的 print 语句
- 数学计算
- 列表操作
- 数据统计

### 2. 工具对比演示
对比 `PythonREPLTool` 和 `PythonAstREPLTool` 的区别：
- 安全性差异
- 功能限制
- 使用场景

### 3. 高级功能演示
展示复杂的代码执行场景：
- JSON 数据处理
- 递归算法实现
- 字符串处理
- 数据分析

### 4. 交互式模式
提供完整的交互式代码解释器体验：
- 实时代码执行
- 历史记录查看
- AI 智能查询
- 命令行界面

## 交互式命令

在交互式模式下，支持以下命令：

- **直接输入 Python 代码**: 立即执行
- `/help`: 显示帮助信息
- `/history`: 查看执行历史
- `/clear`: 清除历史记录
- `/quit` 或 `/exit`: 退出程序
- `ai: <查询>`: 使用 AI 处理自然语言查询

## 安全性说明

### PythonAstREPLTool (推荐)
- ✅ 限制危险的系统操作
- ✅ 禁止文件系统访问
- ✅ 阻止网络请求
- ✅ 适合生产环境

### PythonREPLTool (谨慎使用)
- ⚠️ 完整的 Python 功能
- ⚠️ 可以执行系统命令
- ⚠️ 可以访问文件系统
- ⚠️ 仅适合受控环境

## 示例代码

### 基本数学计算
```python
import math
result = math.sqrt(16)
print(f'sqrt(16) = {result}')
```

### 数据处理
```python
import statistics
data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
mean = statistics.mean(data)
print(f'平均值: {mean}')
```

### 斐波那契数列
```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

fib_sequence = [fibonacci(i) for i in range(8)]
print(f'斐波那契数列: {fib_sequence}')
```

## AI 查询示例

```
ai: 计算1到100的所有偶数的和
ai: 创建一个函数来判断是否为质数
ai: 生成一个包含随机数的列表并排序
```

## 注意事项

1. **API 密钥**: 使用 AI 功能需要设置 `OPENAI_API_KEY` 环境变量
2. **安全性**: 生产环境建议使用 `PythonAstREPLTool`
3. **依赖管理**: 确保安装了所有必要的依赖包
4. **错误处理**: 代码执行错误会被捕获并显示详细信息

## 扩展功能

可以进一步扩展的功能：
- 支持更多编程语言 (JavaScript, R, SQL 等)
- 集成可视化库 (matplotlib, plotly)
- 添加代码补全功能
- 支持 Jupyter Notebook 格式导出
- 集成版本控制功能
