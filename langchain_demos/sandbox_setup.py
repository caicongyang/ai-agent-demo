#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沙箱环境设置脚本
自动安装和配置沙箱代码解释器的依赖
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """运行命令并显示结果"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} 完成")
            return True
        else:
            print(f"❌ {description} 失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} 出错: {e}")
        return False


def install_python_dependencies():
    """安装 Python 依赖"""
    dependencies = [
        "docker",
        "RestrictedPython", 
        "psutil",
        "pydantic"
    ]
    
    print("📦 安装 Python 依赖包...")
    for dep in dependencies:
        print(f"   安装 {dep}...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ {dep} 安装成功")
        else:
            print(f"   ❌ {dep} 安装失败: {result.stderr}")


def check_docker():
    """检查 Docker 是否可用"""
    print("🐳 检查 Docker 环境...")
    
    # 检查 Docker 是否安装
    if not run_command("docker --version", "检查 Docker 版本"):
        print("❌ Docker 未安装，请先安装 Docker Desktop")
        print("   下载地址: https://www.docker.com/products/docker-desktop")
        return False
    
    # 检查 Docker 是否运行
    if not run_command("docker ps", "检查 Docker 服务状态"):
        print("❌ Docker 服务未运行，请启动 Docker Desktop")
        return False
    
    print("✅ Docker 环境正常")
    return True


def build_sandbox_image():
    """构建沙箱镜像"""
    dockerfile_path = Path(__file__).parent / "Dockerfile.sandbox"
    
    if not dockerfile_path.exists():
        print("❌ Dockerfile.sandbox 不存在")
        return False
    
    print("🏗️  构建安全沙箱镜像...")
    command = f"docker build -f {dockerfile_path} -t python-sandbox:latest ."
    
    if run_command(command, "构建 Docker 镜像"):
        print("✅ 沙箱镜像构建完成")
        return True
    else:
        print("❌ 沙箱镜像构建失败")
        return False


def test_sandbox():
    """测试沙箱环境"""
    print("🧪 测试沙箱环境...")
    
    try:
        from sandboxed_code_interpreter import SandboxedCodeInterpreter, SandboxConfig
        
        # 创建配置
        config = SandboxConfig(
            use_docker=True,
            docker_image="python-sandbox:latest",
            docker_timeout=10
        )
        
        # 创建解释器
        interpreter = SandboxedCodeInterpreter(config)
        
        # 测试代码
        test_code = "print('Hello from sandbox!')"
        result = interpreter.execute_code(test_code, sandbox_type="docker")
        
        if result["success"]:
            print("✅ 沙箱测试通过")
            return True
        else:
            print(f"❌ 沙箱测试失败: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ 沙箱测试出错: {e}")
        return False


def create_example_config():
    """创建示例配置文件"""
    config_content = '''# 沙箱配置示例
# sandbox_config.py

from sandboxed_code_interpreter import SandboxConfig

# 高安全性配置 (生产环境推荐)
HIGH_SECURITY_CONFIG = SandboxConfig(
    use_docker=True,
    docker_image="python-sandbox:latest",
    docker_timeout=10,
    memory_limit="64m",
    cpu_limit=0.3,
    use_restricted_python=True,
    allowed_modules=["math", "json", "datetime"],
    blocked_functions=["open", "exec", "eval", "__import__", "compile"],
    max_execution_time=5,
    max_output_size=5000,
    disable_network=True,
    read_only_filesystem=True
)

# 中等安全性配置 (开发环境)
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

# 低安全性配置 (仅用于测试)
LOW_SECURITY_CONFIG = SandboxConfig(
    use_docker=False,
    use_restricted_python=True,
    allowed_modules=["math", "json", "datetime", "random", "statistics", "re"],
    max_execution_time=30,
    max_output_size=50000
)
'''
    
    config_file = Path(__file__).parent / "sandbox_config.py"
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print(f"✅ 配置示例文件已创建: {config_file}")


def main():
    """主函数"""
    print("🔒 沙箱化代码解释器安装程序")
    print("=" * 50)
    
    # 1. 安装 Python 依赖
    install_python_dependencies()
    
    # 2. 检查 Docker 环境
    docker_available = check_docker()
    
    # 3. 构建沙箱镜像 (如果 Docker 可用)
    if docker_available:
        build_sandbox_image()
        
        # 4. 测试沙箱
        test_sandbox()
    else:
        print("⚠️  Docker 不可用，将只能使用 RestrictedPython 沙箱")
    
    # 5. 创建配置示例
    create_example_config()
    
    print("\n🎉 安装完成!")
    print("\n📖 使用说明:")
    print("1. 运行基本演示: python sandboxed_code_interpreter.py")
    print("2. 查看配置示例: sandbox_config.py")
    print("3. 在代码中使用:")
    print("   from sandboxed_code_interpreter import SandboxedCodeInterpreter")
    print("   interpreter = SandboxedCodeInterpreter()")
    print("   result = interpreter.execute_code('print(\"Hello World!\")')")


if __name__ == "__main__":
    main()
