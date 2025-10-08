#!/usr/bin/env python3
"""
测试 MCP + LangChain 集成演示
验证基本功能是否正常工作
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_dependencies():
    """检查依赖包是否正确安装"""
    print("🔍 检查依赖包...")
    
    required_packages = [
        "mcp",
        "langchain", 
        "langchain_openai",
        "dotenv"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ 缺少以下包: {', '.join(missing_packages)}")
        print("请运行: pip install " + " ".join(missing_packages))
        return False
    
    return True

def check_environment():
    """检查环境变量配置"""
    print("\n🔍 检查环境变量...")
    
    required_env = ["LLM_API_KEY"]
    optional_env = ["LLM_BASE_URL"]
    
    missing_env = []
    
    for env_var in required_env:
        if os.getenv(env_var):
            print(f"  ✅ {env_var}")
        else:
            print(f"  ❌ {env_var} - 未设置")
            missing_env.append(env_var)
    
    for env_var in optional_env:
        if os.getenv(env_var):
            print(f"  ✅ {env_var}")
        else:
            print(f"  ⚪ {env_var} - 可选，未设置")
    
    if missing_env:
        print(f"\n⚠️ 请在 .env 文件中设置: {', '.join(missing_env)}")
        return False
    
    return True

async def test_basic_mcp():
    """测试基本的 MCP 功能"""
    print("\n🧪 测试基本 MCP 功能...")
    
    try:
        # 尝试导入 MCP 相关模块
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        print("  ✅ MCP 模块导入成功")
        
        # 创建一个简单的测试服务器参数
        server_params = StdioServerParameters(
            command="echo",
            args=["test"],
            env=None
        )
        print("  ✅ MCP 服务器参数创建成功")
        
        return True
        
    except Exception as e:
        print(f"  ❌ MCP 功能测试失败: {e}")
        return False

async def test_langchain_integration():
    """测试 LangChain 集成"""
    print("\n🧪 测试 LangChain 集成...")
    
    try:
        from langchain_openai import ChatOpenAI
        from langchain.tools import BaseTool
        from langchain.agents import AgentExecutor, create_openai_tools_agent
        from langchain.prompts import ChatPromptTemplate
        
        print("  ✅ LangChain 模块导入成功")
        
        # 测试 LLM 初始化（不实际调用）
        llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY", "test-key"),
            base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
            temperature=0
        )
        print("  ✅ LLM 初始化成功")
        
        # 测试工具创建
        class TestTool(BaseTool):
            name: str = "test_tool"
            description: str = "测试工具"
            
            def _run(self, **kwargs):
                return "测试成功"
        
        test_tool = TestTool()
        print("  ✅ 工具创建成功")
        
        return True
        
    except Exception as e:
        print(f"  ❌ LangChain 集成测试失败: {e}")
        return False

def test_demo_files():
    """检查演示文件是否存在"""
    print("\n🔍 检查演示文件...")
    
    demo_files = [
        "mcp_langchain_demo.py",
        "mcp_simple_demo.py", 
        "MCP_LANGCHAIN_README.md"
    ]
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    all_exist = True
    
    for file in demo_files:
        file_path = os.path.join(current_dir, file)
        if os.path.exists(file_path):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - 文件不存在")
            all_exist = False
    
    return all_exist

async def run_tests():
    """运行所有测试"""
    print("🚀 开始测试 MCP + LangChain 集成环境")
    print("=" * 50)
    
    tests = [
        ("依赖包检查", check_dependencies),
        ("环境变量检查", check_environment), 
        ("演示文件检查", test_demo_files),
        ("MCP 功能测试", test_basic_mcp),
        ("LangChain 集成测试", test_langchain_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 执行出错: {e}")
            results.append((test_name, False))
    
    # 显示测试结果摘要
    print("\n" + "=" * 50)
    print("📋 测试结果摘要:")
    print("-" * 30)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📊 总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！可以运行 MCP + LangChain 演示了。")
        print("\n🚀 运行演示:")
        print("  python mcp_simple_demo.py      # 简化版演示")
        print("  python mcp_langchain_demo.py   # 完整版演示")
    else:
        print("⚠️ 部分测试失败，请根据上述提示进行修复。")
    
    return passed == total

if __name__ == "__main__":
    try:
        result = asyncio.run(run_tests())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中出现未预期的错误: {e}")
        sys.exit(1)
