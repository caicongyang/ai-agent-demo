#!/usr/bin/env python3
"""
测试时间 MCP 服务器集成
"""

import asyncio
import os
from mcp_simple_demo import SimpleMCPDemo

async def test_time_mcp():
    """测试时间 MCP 服务器"""
    print("🕐 测试时间 MCP 服务器集成")
    print("=" * 40)
    
    demo = SimpleMCPDemo()
    
    try:
        print("🔍 检查 uvx 是否可用...")
        import subprocess
        try:
            result = subprocess.run(["uvx", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ uvx 可用")
            else:
                print("❌ uvx 不可用，请先安装 uvx")
                print("安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ uvx 命令未找到，请先安装 uvx")
            return False
        
        print("\n🔍 检查 mcp-server-time 是否可用...")
        try:
            # 测试是否可以运行时间服务器
            result = subprocess.run(
                ["uvx", "mcp-server-time", "--help"], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            if result.returncode == 0:
                print("✅ mcp-server-time 可用")
            else:
                print("⚠️ mcp-server-time 可能需要安装，首次运行时会自动安装")
        except subprocess.TimeoutExpired:
            print("⚠️ mcp-server-time 检查超时，但这是正常的")
        
        print("\n🔗 尝试连接到时间 MCP 服务器...")
        
        # 连接到时间服务器
        if not await demo.connect_to_mcp():
            print("❌ 连接失败")
            return False
        
        print("✅ 连接成功")
        
        # 创建 Agent
        demo.create_agent()
        print("✅ Agent 创建成功")
        
        # 测试时间相关查询
        test_queries = [
            "现在几点了？",
            "今天是什么日期？"
        ]
        
        print("\n🧪 开始测试查询:")
        print("-" * 30)
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 测试 {i}/{len(test_queries)}: {query}")
            try:
                result = await demo.run_query(query)
                print(f"💬 结果: {result}")
            except Exception as e:
                print(f"❌ 查询失败: {e}")
            
            if i < len(test_queries):
                await asyncio.sleep(2)  # 避免请求过快
        
        print(f"\n🎉 时间服务器测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
    
    finally:
        await demo.cleanup()

async def main():
    """主函数"""
    print("🚀 启动时间 MCP 服务器测试")
    
    # 检查环境变量
    if not os.getenv("LLM_API_KEY"):
        print("⚠️ 请设置 LLM_API_KEY 环境变量")
        return False
    
    success = await test_time_mcp()
    
    if success:
        print("\n✅ 所有测试通过！时间 MCP 服务器集成正常工作。")
        print("\n🚀 现在你可以运行完整演示:")
        print("  python mcp_simple_demo.py      # 简化版")
        print("  python mcp_langchain_demo.py   # 完整版")
    else:
        print("\n❌ 测试失败，请检查上述错误信息。")
    
    return success

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中出现未预期的错误: {e}")
        exit(1)
