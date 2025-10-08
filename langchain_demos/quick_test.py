#!/usr/bin/env python3
"""
快速测试修复后的 MCP + LangChain 集成
"""

import asyncio
import os
from mcp_simple_demo import SimpleMCPDemo

async def quick_test():
    """快速测试"""
    print("🧪 快速测试 MCP + LangChain 集成")
    print("=" * 40)
    
    demo = SimpleMCPDemo()
    
    try:
        # 创建服务器文件
        server_file = demo.create_math_server_file()
        print(f"✅ 创建服务器文件: {server_file}")
        
        # 连接到 MCP 服务器
        if not await demo.connect_to_mcp(server_file):
            print("❌ 连接失败")
            return False
        
        # 创建 Agent
        demo.create_agent()
        print("✅ Agent 创建成功")
        
        # 测试一个简单查询
        print("\n🔍 测试查询: 计算 3 + 5")
        result = await demo.run_query("计算 3 + 5")
        print(f"💬 结果: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
    
    finally:
        await demo.cleanup()
        
        # 清理文件
        for file in ["simple_math_server.py"]:
            if os.path.exists(file):
                os.remove(file)

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    print(f"\n🎯 测试结果: {'成功' if success else '失败'}")
