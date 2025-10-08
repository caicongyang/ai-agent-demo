#!/usr/bin/env python3
"""
测试 MCP + LangChain 详细交互日志功能
展示大模型与工具的完整交互过程
"""

import asyncio
from langchain_demos.mcp_langchain_demo import MCPLangChainDemo


async def test_detailed_logging():
    """测试详细的交互日志记录"""
    print("🚀 开始测试详细交互日志功能")
    print("="*50)
    
    demo = MCPLangChainDemo()
    
    try:
        # 初始化 MCP 连接
        result = await demo.initialize_mcp()
        
        if not result.success:
            print(f"❌ MCP 初始化失败: {result.error}")
            return
        
        # 创建 Agent
        demo.create_agent()
        
        # 测试一个简单的数学计算
        print("\n🧪 测试查询: 计算 25 + 17")
        print("注意观察以下输出中的详细交互过程:")
        print("- LLM 交互开始/结束标记")
        print("- 工具调用请求和执行过程")
        print("- 完整的 JSON 请求格式")
        print("-" * 50)
        
        result = await demo.run_query("计算 25 + 17")
        
        if result["success"]:
            print(f"\n✅ 测试成功完成")
        else:
            print(f"\n❌ 测试失败: {result['error']}")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        
    finally:
        # 清理资源
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(test_detailed_logging())
