#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沙箱化代码解释器使用示例
展示如何在实际项目中使用沙箱化代码执行
"""

import os
from sandboxed_code_interpreter import (
    SandboxedCodeInterpreter, 
    SandboxConfig, 
    SandboxedPythonTool
)


def example_basic_usage():
    """基本使用示例"""
    print("🔒 基本沙箱使用示例")
    print("=" * 40)
    
    # 创建默认配置的解释器
    interpreter = SandboxedCodeInterpreter()
    
    # 执行一些示例代码
    examples = [
        "print('Hello from Sandbox!')",
        "import math; print(f'π = {math.pi:.4f}')",
        "numbers = [1, 2, 3, 4, 5]; print(f'Sum: {sum(numbers)}')",
        "import json; data = {'name': 'test', 'value': 42}; print(json.dumps(data))"
    ]
    
    for code in examples:
        print(f"\n📝 执行: {code}")
        result = interpreter.execute_code(code)
        if result['success']:
            print(f"✅ 输出: {result.get('output', '').strip()}")
        else:
            print(f"❌ 错误: {result.get('error', '')}")


def example_security_levels():
    """不同安全级别示例"""
    print("\n🛡️  安全级别对比示例")
    print("=" * 40)
    
    # 高安全性配置
    high_security = SandboxConfig(
        use_docker=True,
        docker_image="python:3.11-slim",
        docker_timeout=10,
        memory_limit="64m",
        use_restricted_python=True,
        allowed_modules=["math", "json"],
        blocked_functions=["open", "exec", "eval"],
        max_execution_time=5,
        disable_network=True
    )
    
    # 低安全性配置
    low_security = SandboxConfig(
        use_docker=False,
        use_restricted_python=False,
        max_execution_time=30
    )
    
    # 测试危险代码
    dangerous_code = "import os; print('Current directory:', os.getcwd())"
    
    print(f"🧪 测试代码: {dangerous_code}")
    
    # 高安全性测试
    print("\n🔒 高安全性沙箱:")
    high_interpreter = SandboxedCodeInterpreter(high_security)
    result = high_interpreter.execute_code(dangerous_code)
    print(f"   结果: {'✅ 允许' if result['success'] else '❌ 阻止'}")
    if not result['success']:
        print(f"   原因: {result['error']}")
    
    # 低安全性测试
    print("\n🔓 低安全性沙箱:")
    low_interpreter = SandboxedCodeInterpreter(low_security)
    result = low_interpreter.execute_code(dangerous_code)
    print(f"   结果: {'✅ 允许' if result['success'] else '❌ 阻止'}")
    if result['success']:
        print(f"   输出: {result.get('output', '').strip()}")


def example_langchain_integration():
    """LangChain 集成示例"""
    print("\n🦜 LangChain 集成示例")
    print("=" * 40)
    
    # 创建沙箱工具
    config = SandboxConfig(
        use_docker=False,  # 为了演示方便，不使用 Docker
        use_restricted_python=True,
        allowed_modules=["math", "statistics", "json", "datetime"]
    )
    
    sandbox_tool = SandboxedPythonTool(config)
    
    # 测试工具
    test_codes = [
        "print('LangChain + Sandbox 集成测试')",
        "import math; result = math.factorial(5); print(f'5! = {result}')",
        "import statistics; data = [1,2,3,4,5]; print(f'Mean: {statistics.mean(data)}')"
    ]
    
    for code in test_codes:
        print(f"\n📝 执行: {code}")
        try:
            output = sandbox_tool._run(code)
            print(f"✅ 输出: {output.strip()}")
        except Exception as e:
            print(f"❌ 错误: {e}")


def example_resource_monitoring():
    """资源监控示例"""
    print("\n📊 资源监控示例")
    print("=" * 40)
    
    # 配置资源限制
    config = SandboxConfig(
        use_docker=False,
        max_execution_time=5,
        max_output_size=1000
    )
    
    interpreter = SandboxedCodeInterpreter(config)
    
    # 测试执行时间限制
    print("🕐 测试执行时间限制:")
    long_running_code = """
import time
print("开始长时间任务...")
for i in range(10):
    print(f"步骤 {i+1}/10")
    time.sleep(0.5)
print("任务完成!")
"""
    
    result = interpreter.execute_code(long_running_code)
    print(f"   结果: {'✅ 完成' if result['success'] else '❌ 超时'}")
    if 'execution_time' in result:
        print(f"   执行时间: {result['execution_time']:.2f}s")
    
    # 测试输出大小限制
    print("\n📄 测试输出大小限制:")
    large_output_code = """
for i in range(1000):
    print(f"这是第 {i} 行输出，用于测试输出大小限制")
"""
    
    result = interpreter.execute_code(large_output_code)
    output_size = len(result.get('output', ''))
    print(f"   输出大小: {output_size} 字符")
    print(f"   是否被截断: {'是' if '截断' in result.get('output', '') else '否'}")


def example_custom_sandbox():
    """自定义沙箱示例"""
    print("\n🛠️  自定义沙箱示例")
    print("=" * 40)
    
    # 创建自定义配置
    custom_config = SandboxConfig(
        use_docker=False,
        use_restricted_python=True,
        allowed_modules=["math", "random", "string"],
        blocked_functions=["open", "input", "raw_input"],
        max_execution_time=10,
        max_output_size=5000
    )
    
    interpreter = SandboxedCodeInterpreter(custom_config)
    
    # 测试允许的操作
    allowed_codes = [
        "import math; print(f'sin(π/2) = {math.sin(math.pi/2)}')",
        "import random; print(f'Random number: {random.randint(1, 100)}')",
        "import string; print(f'ASCII letters: {string.ascii_letters[:10]}')"
    ]
    
    print("✅ 允许的操作:")
    for code in allowed_codes:
        result = interpreter.execute_code(code)
        if result['success']:
            print(f"   {code} → {result['output'].strip()}")
    
    # 测试被阻止的操作
    blocked_codes = [
        "open('/etc/passwd', 'r')",
        "import subprocess; subprocess.run(['ls'])",
        "exec('print(\"dangerous\")')"
    ]
    
    print("\n❌ 被阻止的操作:")
    for code in blocked_codes:
        result = interpreter.execute_code(code)
        if not result['success']:
            print(f"   {code} → 被阻止: {result['error']}")


def main():
    """主函数"""
    print("🔒 沙箱化代码解释器使用示例")
    print("=" * 60)
    
    try:
        # 基本使用
        example_basic_usage()
        
        # 安全级别对比
        example_security_levels()
        
        # LangChain 集成
        example_langchain_integration()
        
        # 资源监控
        example_resource_monitoring()
        
        # 自定义沙箱
        example_custom_sandbox()
        
        print("\n🎉 所有示例执行完成!")
        print("\n💡 提示:")
        print("   - 在生产环境中建议使用 Docker 沙箱")
        print("   - 根据安全需求调整配置参数")
        print("   - 定期监控和审计代码执行日志")
        
    except Exception as e:
        print(f"❌ 示例执行出错: {e}")
        print("请确保已正确安装所有依赖包")


if __name__ == "__main__":
    main()
