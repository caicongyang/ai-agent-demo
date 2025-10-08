#!/usr/bin/env python3
"""
测试修复后的 MCP + LangChain 详细交互日志功能
"""

import asyncio
import os
from langchain_demos.mcp_langchain_demo import MCPLangChainDemo


async def test_simple_calculation():
    """测试一个简单的计算，验证错误修复"""
    print("🚀 测试修复后的交互日志功能")
    print("="*50)
    
    # 检查环境变量
    if not os.getenv("AZURE_OPENAI_API_KEY") or not os.getenv("AZURE_OPENAI_ENDPOINT"):
        print("⚠️ 请设置 Azure OpenAI 环境变量")
        print("需要的环境变量:")
        print("- AZURE_OPENAI_API_KEY")
        print("- AZURE_OPENAI_ENDPOINT") 
        print("- AZURE_OPENAI_MODEL (可选，默认 gpt-4o)")
        return
    
    demo = MCPLangChainDemo()
    
    try:
        # 初始化 MCP 连接
        print("\n🔧 初始化 MCP 连接...")
        result = await demo.initialize_mcp()
        
        if not result.success:
            print(f"❌ MCP 初始化失败: {result.error}")
            return
        
        # 创建 Agent
        print("🤖 创建 Agent...")
        demo.create_agent()
        
        # 测试一个简单的计算
        print("\n" + "="*60)
        print("🧪 测试查询: 计算 12 + 8")
        print("注意观察修复后的日志输出:")
        print("="*60)
        
        result = await demo.run_query("计算 12 + 8")
        
        if result["success"]:
            print(f"\n✅ 测试成功! 结果: {result['result']['output']}")
        else:
            print(f"\n❌ 测试失败: {result['error']}")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 清理资源
        await demo.cleanup()
        print("🧹 测试完成，资源已清理")


if __name__ == "__main__":
    asyncio.run(test_simple_calculation())
