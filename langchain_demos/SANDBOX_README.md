# 🔒 沙箱化代码解释器

这是一个结合 LangChain 和多种沙箱技术的安全代码执行环境，提供生产级别的安全保障。

## 🚀 核心特性

### 🐳 多层沙箱保护
- **Docker 容器沙箱**: 完全隔离的执行环境
- **RestrictedPython**: Python 级别的代码限制
- **资源监控**: CPU、内存、执行时间限制
- **网络隔离**: 可选的网络访问控制
- **文件系统保护**: 只读文件系统和路径限制

### 🛡️ 安全特性
- **代码静态分析**: 执行前检查危险函数
- **运行时监控**: 实时资源使用监控
- **输出限制**: 防止输出洪水攻击
- **超时保护**: 防止无限循环和长时间执行
- **权限隔离**: 非 root 用户执行

### 🔧 灵活配置
- **多种安全级别**: 高/中/低安全性预设
- **自定义配置**: 详细的沙箱参数控制
- **回退机制**: 多个沙箱环境自动切换
- **LangChain 集成**: 可作为 LangChain 工具使用

## 📦 安装和设置

### 1. 自动安装 (推荐)

```bash
python sandbox_setup.py
```

这将自动：
- 安装所有 Python 依赖
- 检查 Docker 环境
- 构建安全沙箱镜像
- 创建配置示例
- 运行测试验证

### 2. 手动安装

```bash
# 安装 Python 依赖
pip install docker RestrictedPython psutil pydantic

# 检查 Docker (可选)
docker --version
docker ps

# 构建沙箱镜像 (可选)
docker build -f Dockerfile.sandbox -t python-sandbox:latest .
```

## 🎯 使用方法

### 基本使用

```python
from sandboxed_code_interpreter import SandboxedCodeInterpreter, SandboxConfig

# 使用默认配置
interpreter = SandboxedCodeInterpreter()

# 执行代码
result = interpreter.execute_code("print('Hello, Sandbox!')")
print(result)
```

### 自定义配置

```python
# 高安全性配置
config = SandboxConfig(
    use_docker=True,
    docker_image="python-sandbox:latest",
    docker_timeout=10,
    memory_limit="64m",
    cpu_limit=0.3,
    use_restricted_python=True,
    allowed_modules=["math", "json"],
    max_execution_time=5,
    disable_network=True,
    read_only_filesystem=True
)

interpreter = SandboxedCodeInterpreter(config)
```

### LangChain 集成

```python
from sandboxed_code_interpreter import SandboxedPythonTool
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI

# 创建沙箱工具
sandbox_tool = SandboxedPythonTool()

# 集成到 LangChain 代理
llm = ChatOpenAI(temperature=0)
agent = initialize_agent(
    tools=[sandbox_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# 使用代理执行代码
response = agent.run("计算 1 到 100 的平方和")
```

## 🔧 配置选项

### Docker 沙箱配置

```python
SandboxConfig(
    use_docker=True,              # 启用 Docker 沙箱
    docker_image="python:3.11-slim",  # Docker 镜像
    docker_timeout=30,            # 超时时间 (秒)
    memory_limit="128m",          # 内存限制
    cpu_limit=0.5,               # CPU 限制 (0-1)
    disable_network=True,         # 禁用网络
    read_only_filesystem=True     # 只读文件系统
)
```

### RestrictedPython 配置

```python
SandboxConfig(
    use_restricted_python=True,   # 启用 RestrictedPython
    allowed_modules=[             # 允许的模块
        "math", "json", "datetime", "random"
    ],
    blocked_functions=[           # 禁止的函数
        "open", "exec", "eval", "__import__"
    ]
)
```

### 资源限制配置

```python
SandboxConfig(
    max_execution_time=10,        # 最大执行时间 (秒)
    max_output_size=10000,        # 最大输出大小 (字符)
    max_memory_mb=128             # 最大内存使用 (MB)
)
```

## 🛡️ 安全级别

### 高安全性 (生产环境推荐)

```python
HIGH_SECURITY_CONFIG = SandboxConfig(
    use_docker=True,
    docker_image="python-sandbox:latest",
    docker_timeout=10,
    memory_limit="64m",
    cpu_limit=0.3,
    use_restricted_python=True,
    allowed_modules=["math", "json", "datetime"],
    blocked_functions=["open", "exec", "eval", "__import__"],
    max_execution_time=5,
    max_output_size=5000,
    disable_network=True,
    read_only_filesystem=True
)
```

### 中等安全性 (开发环境)

```python
MEDIUM_SECURITY_CONFIG = SandboxConfig(
    use_docker=True,
    docker_image="python:3.11-slim",
    docker_timeout=30,
    memory_limit="128m",
    cpu_limit=0.5,
    use_restricted_python=False,
    max_execution_time=15,
    max_output_size=10000,
    disable_network=False,
    read_only_filesystem=False
)
```

### 低安全性 (仅用于测试)

```python
LOW_SECURITY_CONFIG = SandboxConfig(
    use_docker=False,
    use_restricted_python=True,
    allowed_modules=["math", "json", "datetime", "random", "statistics"],
    max_execution_time=30,
    max_output_size=50000
)
```

## 🧪 演示和测试

### 运行演示程序

```bash
python sandboxed_code_interpreter.py
```

选择不同的演示模式：
1. **Docker 沙箱演示** - 展示 Docker 容器隔离效果
2. **RestrictedPython 演示** - 展示代码限制功能
3. **沙箱安全性对比** - 对比不同沙箱的安全性
4. **交互式沙箱模式** - 提供交互式代码执行环境

### 交互式命令

在交互式模式下：
- 直接输入 Python 代码执行
- `/docker <code>` - 强制使用 Docker 沙箱
- `/restricted <code>` - 强制使用 RestrictedPython
- `/status` - 显示沙箱状态
- `/history` - 显示执行历史
- `/quit` - 退出

## 🔍 安全测试

### 测试危险操作

```python
# 这些操作在沙箱中会被阻止或限制
dangerous_codes = [
    "import os; os.system('rm -rf /')",           # 系统命令
    "open('/etc/passwd', 'r').read()",            # 文件访问
    "import subprocess; subprocess.run(['ls'])",   # 子进程
    "__import__('os').listdir('/')",              # 动态导入
    "exec('print(\"dangerous\")')",               # 代码执行
    "while True: pass",                           # 无限循环
]

for code in dangerous_codes:
    result = interpreter.execute_code(code)
    print(f"Code: {code}")
    print(f"Blocked: {not result['success']}")
```

## 📊 监控和日志

### 执行历史

```python
# 获取执行历史
history = interpreter.execution_history
for record in history:
    print(f"Time: {record['timestamp']}")
    print(f"Sandbox: {record['sandbox_type']}")
    print(f"Success: {record['success']}")
    print(f"Execution Time: {record.get('execution_time', 0)}s")
```

### 沙箱状态

```python
# 获取沙箱状态
status = interpreter.get_sandbox_status()
print(f"Docker Available: {status['docker_available']}")
print(f"RestrictedPython Available: {status['restricted_python_available']}")
print(f"Execution Count: {status['execution_count']}")
```

## ⚠️ 注意事项

### Docker 要求
- 需要安装 Docker Desktop
- Docker 服务必须运行
- 需要足够的权限构建镜像

### 性能考虑
- Docker 沙箱有启动开销 (~1-2秒)
- RestrictedPython 性能更好但限制较少
- 建议根据安全需求选择合适的沙箱

### 限制说明
- Docker 沙箱无法在某些云环境中使用
- RestrictedPython 无法阻止所有危险操作
- 网络隔离可能影响某些库的功能

## 🔗 扩展和集成

### 自定义沙箱

```python
class CustomSandbox:
    def execute_code(self, code: str) -> Dict[str, Any]:
        # 实现自定义沙箱逻辑
        pass

# 集成到解释器
interpreter.custom_sandbox = CustomSandbox()
```

### 与其他框架集成

```python
# 与 Jupyter 集成
from IPython.core.magic import Magics, line_magic, magics_class

@magics_class
class SandboxMagics(Magics):
    @line_magic
    def sandbox(self, line):
        interpreter = SandboxedCodeInterpreter()
        result = interpreter.execute_code(line)
        return result['output'] if result['success'] else result['error']

# 注册魔法命令
get_ipython().register_magic_function(SandboxMagics().sandbox, 'line', 'sandbox')
```

## 🆘 故障排除

### 常见问题

1. **Docker 连接失败**
   ```bash
   # 检查 Docker 状态
   docker ps
   # 重启 Docker Desktop
   ```

2. **权限问题**
   ```bash
   # 添加用户到 docker 组
   sudo usermod -aG docker $USER
   ```

3. **镜像构建失败**
   ```bash
   # 清理 Docker 缓存
   docker system prune -a
   ```

4. **RestrictedPython 导入失败**
   ```bash
   pip install RestrictedPython
   ```

### 调试模式

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 启用详细日志
config = SandboxConfig(verbose=True)
interpreter = SandboxedCodeInterpreter(config)
```

## 📚 相关资源

- [Docker 官方文档](https://docs.docker.com/)
- [RestrictedPython 文档](https://restrictedpython.readthedocs.io/)
- [LangChain 工具文档](https://python.langchain.com/docs/modules/tools/)
- [Python 安全最佳实践](https://python.org/dev/security/)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！

## 📄 许可证

MIT License - 详见 LICENSE 文件
