#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沙箱化代码解释器
结合 LangChain 和多种沙箱技术，提供安全的代码执行环境

支持的沙箱技术：
1. Docker 容器沙箱
2. RestrictedPython 代码限制
3. 资源监控和限制
4. 网络隔离
5. 文件系统限制
"""

import os
import sys
import json
import time
import docker
import tempfile
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

try:
    from RestrictedPython import compile_restricted
    from RestrictedPython.Guards import safe_globals, safe_builtins
    RESTRICTED_PYTHON_AVAILABLE = True
except ImportError:
    RESTRICTED_PYTHON_AVAILABLE = False
    print("⚠️  RestrictedPython 未安装，将跳过 RestrictedPython 沙箱功能")

from langchain_experimental.tools import PythonAstREPLTool
from langchain.tools.base import BaseTool
from langchain.schema import BaseModel
from pydantic import Field


class SandboxConfig(BaseModel):
    """沙箱配置"""
    # Docker 配置
    use_docker: bool = True
    docker_image: str = "python:3.11-slim"
    docker_timeout: int = 30
    memory_limit: str = "128m"
    cpu_limit: float = 0.5
    
    # RestrictedPython 配置
    use_restricted_python: bool = True
    allowed_modules: List[str] = ["math", "json", "datetime", "random", "statistics"]
    blocked_functions: List[str] = ["open", "exec", "eval", "__import__"]
    
    # 资源限制
    max_execution_time: int = 10
    max_output_size: int = 10000
    max_memory_mb: int = 128
    
    # 网络和文件系统
    disable_network: bool = True
    read_only_filesystem: bool = True
    allowed_paths: List[str] = ["/tmp"]


class DockerSandbox:
    """Docker 沙箱实现"""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.client = None
        if config.use_docker:
            try:
                self.client = docker.from_env()
                # 检查 Docker 是否运行
                self.client.ping()
                print("✅ Docker 连接成功")
            except Exception as e:
                print(f"❌ Docker 连接失败: {e}")
                self.client = None
    
    def execute_code(self, code: str) -> Dict[str, Any]:
        """在 Docker 容器中执行代码"""
        if not self.client:
            return {
                "success": False,
                "error": "Docker 不可用",
                "output": ""
            }
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Docker 运行参数
            run_kwargs = {
                'image': self.config.docker_image,
                'command': ['python', '/code/script.py'],
                'volumes': {temp_file: {'bind': '/code/script.py', 'mode': 'ro'}},
                'mem_limit': self.config.memory_limit,
                'cpu_period': 100000,
                'cpu_quota': int(100000 * self.config.cpu_limit),
                'network_disabled': self.config.disable_network,
                'read_only': self.config.read_only_filesystem,
                'remove': True,
                'stdout': True,
                'stderr': True,
            }
            
            # 执行容器
            start_time = time.time()
            try:
                result = self.client.containers.run(
                    timeout=self.config.docker_timeout,
                    **run_kwargs
                )
                execution_time = time.time() - start_time
                
                output = result.decode('utf-8')
                if len(output) > self.config.max_output_size:
                    output = output[:self.config.max_output_size] + "\n... (输出被截断)"
                
                return {
                    "success": True,
                    "output": output,
                    "execution_time": execution_time,
                    "error": None
                }
                
            except docker.errors.ContainerError as e:
                return {
                    "success": False,
                    "error": f"容器执行错误: {e.stderr.decode('utf-8') if e.stderr else str(e)}",
                    "output": e.stdout.decode('utf-8') if e.stdout else "",
                    "execution_time": time.time() - start_time
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Docker 执行失败: {str(e)}",
                "output": ""
            }
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except:
                pass


class RestrictedPythonSandbox:
    """RestrictedPython 沙箱实现"""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.available = RESTRICTED_PYTHON_AVAILABLE
        
        if self.available:
            # 设置安全的全局环境
            self.safe_globals = safe_globals.copy()
            self.safe_globals['_getattr_'] = getattr
            self.safe_globals['_getitem_'] = lambda obj, index: obj[index]
            self.safe_globals['_getiter_'] = iter
            self.safe_globals['_write_'] = lambda x: x
            
            # 添加允许的模块
            for module_name in config.allowed_modules:
                try:
                    module = __import__(module_name)
                    self.safe_globals[module_name] = module
                except ImportError:
                    print(f"⚠️  模块 {module_name} 导入失败")
    
    def execute_code(self, code: str) -> Dict[str, Any]:
        """使用 RestrictedPython 执行代码"""
        if not self.available:
            return {
                "success": False,
                "error": "RestrictedPython 不可用",
                "output": ""
            }
        
        try:
            # 检查被阻止的函数
            for blocked_func in self.config.blocked_functions:
                if blocked_func in code:
                    return {
                        "success": False,
                        "error": f"禁止使用函数: {blocked_func}",
                        "output": ""
                    }
            
            # 编译受限代码
            byte_code = compile_restricted(code, '<string>', 'exec')
            if byte_code is None:
                return {
                    "success": False,
                    "error": "代码编译失败 - 可能包含不安全操作",
                    "output": ""
                }
            
            # 创建执行环境
            local_vars = {}
            restricted_globals = self.safe_globals.copy()
            restricted_globals['__builtins__'] = safe_builtins
            
            # 重定向输出
            from io import StringIO
            old_stdout = sys.stdout
            sys.stdout = captured_output = StringIO()
            
            start_time = time.time()
            
            try:
                # 执行代码
                exec(byte_code, restricted_globals, local_vars)
                execution_time = time.time() - start_time
                
                # 获取输出
                output = captured_output.getvalue()
                if len(output) > self.config.max_output_size:
                    output = output[:self.config.max_output_size] + "\n... (输出被截断)"
                
                return {
                    "success": True,
                    "output": output,
                    "execution_time": execution_time,
                    "error": None,
                    "local_vars": {k: str(v) for k, v in local_vars.items() if not k.startswith('_')}
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "output": captured_output.getvalue(),
                    "execution_time": time.time() - start_time
                }
            finally:
                sys.stdout = old_stdout
                
        except Exception as e:
            return {
                "success": False,
                "error": f"RestrictedPython 执行失败: {str(e)}",
                "output": ""
            }


class SandboxedCodeInterpreter:
    """沙箱化代码解释器"""
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self.execution_history = []
        
        # 初始化沙箱
        self.docker_sandbox = DockerSandbox(self.config) if self.config.use_docker else None
        self.restricted_sandbox = RestrictedPythonSandbox(self.config) if self.config.use_restricted_python else None
        self.fallback_tool = PythonAstREPLTool()
        
        print("🔒 沙箱化代码解释器初始化完成")
        print(f"   Docker 沙箱: {'✅' if self.docker_sandbox and self.docker_sandbox.client else '❌'}")
        print(f"   RestrictedPython: {'✅' if self.restricted_sandbox and self.restricted_sandbox.available else '❌'}")
    
    def execute_code(self, code: str, sandbox_type: str = "auto") -> Dict[str, Any]:
        """
        执行代码
        
        Args:
            code: 要执行的代码
            sandbox_type: 沙箱类型 ("docker", "restricted", "fallback", "auto")
        """
        execution_record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "code": code,
            "sandbox_type": sandbox_type,
            "success": False,
            "result": None,
            "error": None,
            "execution_time": 0
        }
        
        try:
            # 自动选择沙箱类型
            if sandbox_type == "auto":
                if self.docker_sandbox and self.docker_sandbox.client:
                    sandbox_type = "docker"
                elif self.restricted_sandbox and self.restricted_sandbox.available:
                    sandbox_type = "restricted"
                else:
                    sandbox_type = "fallback"
            
            # 执行代码
            if sandbox_type == "docker" and self.docker_sandbox:
                result = self.docker_sandbox.execute_code(code)
            elif sandbox_type == "restricted" and self.restricted_sandbox:
                result = self.restricted_sandbox.execute_code(code)
            else:
                # 回退到 PythonAstREPLTool
                try:
                    output = self.fallback_tool.run(code)
                    result = {
                        "success": True,
                        "output": output,
                        "error": None,
                        "execution_time": 0
                    }
                except Exception as e:
                    result = {
                        "success": False,
                        "output": "",
                        "error": str(e),
                        "execution_time": 0
                    }
                sandbox_type = "fallback"
            
            # 更新记录
            execution_record.update(result)
            execution_record["sandbox_type"] = sandbox_type
            
            # 显示结果
            status = "✅" if result["success"] else "❌"
            print(f"\n{status} 代码执行 [{sandbox_type.upper()} 沙箱]")
            print(f"代码: {code[:100]}{'...' if len(code) > 100 else ''}")
            if result["success"]:
                print(f"输出: {result['output']}")
                if 'execution_time' in result:
                    print(f"执行时间: {result['execution_time']:.3f}s")
            else:
                print(f"错误: {result['error']}")
            
        except Exception as e:
            execution_record["error"] = str(e)
            print(f"❌ 执行失败: {e}")
        
        # 添加到历史记录
        self.execution_history.append(execution_record)
        return execution_record
    
    def get_sandbox_status(self) -> Dict[str, Any]:
        """获取沙箱状态"""
        return {
            "docker_available": bool(self.docker_sandbox and self.docker_sandbox.client),
            "restricted_python_available": bool(self.restricted_sandbox and self.restricted_sandbox.available),
            "config": self.config.dict(),
            "execution_count": len(self.execution_history)
        }
    
    def clear_history(self):
        """清除执行历史"""
        self.execution_history.clear()
        print("📝 执行历史已清除")


class SandboxedPythonTool(BaseTool):
    """LangChain 工具包装器"""
    
    name: str = "sandboxed_python"
    description: str = "在安全沙箱环境中执行 Python 代码"
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        super().__init__()
        self.interpreter = SandboxedCodeInterpreter(config)
    
    def _run(self, code: str) -> str:
        """执行代码并返回结果"""
        result = self.interpreter.execute_code(code)
        if result["success"]:
            return result.get("output", "")
        else:
            return f"Error: {result.get('error', 'Unknown error')}"
    
    async def _arun(self, code: str) -> str:
        """异步执行"""
        return self._run(code)


def demo_docker_sandbox():
    """Docker 沙箱演示"""
    print("\n" + "="*60)
    print("🐳 Docker 沙箱演示")
    print("="*60)
    
    config = SandboxConfig(
        use_docker=True,
        use_restricted_python=False,
        docker_timeout=15,
        memory_limit="64m"
    )
    
    interpreter = SandboxedCodeInterpreter(config)
    
    if not interpreter.docker_sandbox or not interpreter.docker_sandbox.client:
        print("❌ Docker 不可用，跳过演示")
        return
    
    # 测试代码
    test_codes = [
        "print('Hello from Docker sandbox!')",
        "import math\nprint(f'π = {math.pi}')",
        "import os\ntry:\n    print(f'Current dir: {os.getcwd()}')\nexcept:\n    print('Directory access restricted')",
        # 危险操作测试
        "import subprocess\ntry:\n    result = subprocess.run(['ls'], capture_output=True, text=True)\n    print(result.stdout)\nexcept Exception as e:\n    print(f'Blocked: {e}')"
    ]
    
    for i, code in enumerate(test_codes, 1):
        print(f"\n🧪 测试 {i}:")
        interpreter.execute_code(code, sandbox_type="docker")


def demo_restricted_python():
    """RestrictedPython 演示"""
    print("\n" + "="*60)
    print("🔒 RestrictedPython 演示")
    print("="*60)
    
    if not RESTRICTED_PYTHON_AVAILABLE:
        print("❌ RestrictedPython 不可用，跳过演示")
        return
    
    config = SandboxConfig(
        use_docker=False,
        use_restricted_python=True,
        allowed_modules=["math", "json", "random"]
    )
    
    interpreter = SandboxedCodeInterpreter(config)
    
    # 测试代码
    test_codes = [
        "print('Hello from RestrictedPython!')",
        "import math\nprint(f'sqrt(16) = {math.sqrt(16)}')",
        "import json\ndata = {'name': 'test'}\nprint(json.dumps(data))",
        # 被限制的操作
        "open('/etc/passwd', 'r')",  # 文件访问
        "exec('print(\"dangerous\")')",  # exec 调用
        "__import__('os').system('ls')",  # 系统调用
    ]
    
    for i, code in enumerate(test_codes, 1):
        print(f"\n🧪 测试 {i}:")
        interpreter.execute_code(code, sandbox_type="restricted")


def demo_comparison():
    """沙箱对比演示"""
    print("\n" + "="*60)
    print("⚖️  沙箱安全性对比")
    print("="*60)
    
    # 危险代码测试
    dangerous_code = """
import os
try:
    files = os.listdir('/')
    print(f'Root directory files: {files[:5]}...')
except Exception as e:
    print(f'Access denied: {e}')
"""
    
    config = SandboxConfig()
    interpreter = SandboxedCodeInterpreter(config)
    
    print("🔍 测试危险代码在不同沙箱中的表现:")
    print(f"代码:\n{dangerous_code}")
    
    # 在不同沙箱中测试
    sandboxes = ["docker", "restricted", "fallback"]
    for sandbox in sandboxes:
        print(f"\n📦 {sandbox.upper()} 沙箱:")
        interpreter.execute_code(dangerous_code, sandbox_type=sandbox)


def interactive_sandbox():
    """交互式沙箱模式"""
    print("\n" + "="*60)
    print("🎮 交互式沙箱代码解释器")
    print("="*60)
    
    config = SandboxConfig()
    interpreter = SandboxedCodeInterpreter(config)
    
    # 显示状态
    status = interpreter.get_sandbox_status()
    print("🔧 沙箱状态:")
    print(f"   Docker: {'✅' if status['docker_available'] else '❌'}")
    print(f"   RestrictedPython: {'✅' if status['restricted_python_available'] else '❌'}")
    
    print("\n💡 命令:")
    print("   直接输入 Python 代码执行")
    print("   /docker <code> - 强制使用 Docker 沙箱")
    print("   /restricted <code> - 强制使用 RestrictedPython")
    print("   /status - 显示沙箱状态")
    print("   /history - 显示执行历史")
    print("   /quit - 退出")
    
    while True:
        try:
            user_input = input("\n🔒 sandbox>>> ").strip()
            
            if user_input == "/quit":
                break
            elif user_input == "/status":
                status = interpreter.get_sandbox_status()
                print(json.dumps(status, indent=2, ensure_ascii=False))
                continue
            elif user_input == "/history":
                history = interpreter.execution_history
                if not history:
                    print("📝 暂无执行历史")
                else:
                    for i, record in enumerate(history[-5:], 1):  # 显示最后5条
                        status = "✅" if record["success"] else "❌"
                        print(f"{i}. {status} [{record['sandbox_type']}] {record['timestamp']}")
                        print(f"   {record['code'][:50]}...")
                continue
            elif user_input.startswith("/docker "):
                code = user_input[8:]
                interpreter.execute_code(code, sandbox_type="docker")
                continue
            elif user_input.startswith("/restricted "):
                code = user_input[12:]
                interpreter.execute_code(code, sandbox_type="restricted")
                continue
            elif user_input == "":
                continue
            
            # 执行代码
            interpreter.execute_code(user_input)
            
        except KeyboardInterrupt:
            print("\n👋 再见!")
            break
        except EOFError:
            print("\n👋 再见!")
            break


def main():
    """主函数"""
    print("🔒 LangChain 沙箱化代码解释器")
    print("=" * 60)
    
    while True:
        print("\n请选择演示模式:")
        print("1. Docker 沙箱演示")
        print("2. RestrictedPython 演示") 
        print("3. 沙箱安全性对比")
        print("4. 交互式沙箱模式")
        print("0. 退出")
        
        choice = input("\n请输入选择 (0-4): ").strip()
        
        if choice == "1":
            demo_docker_sandbox()
        elif choice == "2":
            demo_restricted_python()
        elif choice == "3":
            demo_comparison()
        elif choice == "4":
            interactive_sandbox()
        elif choice == "0":
            print("👋 再见!")
            break
        else:
            print("❌ 无效选择，请重新输入")


if __name__ == "__main__":
    main()
