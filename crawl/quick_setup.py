#!/usr/bin/env python3
"""
快速安装和测试脚本

这个脚本会自动安装依赖并测试 MCP 连接
"""

import subprocess
import sys
import os
import asyncio
from pathlib import Path


def run_command(command, description=""):
    """运行命令并显示结果"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description}完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败: {e}")
        if e.stderr:
            print(f"错误详情: {e.stderr}")
        return False


def check_node():
    """检查 Node.js 是否安装"""
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js 已安装: {result.stdout.strip()}")
            return True
        else:
            print("❌ Node.js 未安装")
            return False
    except FileNotFoundError:
        print("❌ Node.js 未安装")
        return False


def install_dependencies():
    """安装所有依赖"""
    print("\n📦 安装依赖...")
    
    steps = [
        ("pip install -r requirements.txt", "安装 Python 依赖"),
        ("npm install -g @playwright/mcp", "安装 Playwright MCP 服务器"),
        ("playwright install", "安装 Playwright 浏览器")
    ]
    
    success_count = 0
    for command, description in steps:
        if run_command(command, description):
            success_count += 1
    
    return success_count == len(steps)


async def test_mcp_connection():
    """测试 MCP 连接"""
    print("\n🔍 测试 MCP 连接...")
    
    try:
        from simple_llm_crawler import DirectMCPClient
        
        client = DirectMCPClient()
        if await client.connect_to_playwright():
            tools = await client.get_available_tools()
            print(f"✅ MCP 连接成功，发现 {len(tools)} 个工具")
            await client.close()
            return True
        else:
            print("❌ MCP 连接失败")
            return False
            
    except Exception as e:
        print(f"❌ MCP 测试失败: {e}")
        return False


def create_env_file():
    """创建环境变量文件"""
    env_file = Path(".env")
    if not env_file.exists():
        print("\n📝 创建 .env 文件...")
        env_content = """# Azure OpenAI 配置（推荐）
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_api_key_here
AZURE_OPENAI_MODEL=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# 备用 OpenAI API Key（可选）
OPENAI_API_KEY=your_openai_api_key_here

# MCP 服务器配置
MCP_SERVER_URL=ws://localhost:8080
MCP_SERVER_PORT=8080

# 日志级别
LOG_LEVEL=INFO

# 导出设置
OUTPUT_DIR=output
EXPORT_FORMAT=csv,json
"""
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("✅ .env 文件已创建")
        print("💡 提示: 如需使用 LLM 功能，请在 .env 文件中设置 OPENAI_API_KEY")
    else:
        print("ℹ️ .env 文件已存在")


def show_usage_examples():
    """显示使用示例"""
    print("\n🚀 使用示例:")
    print("-" * 40)
    
    examples = [
        ("基础使用", "python simple_llm_crawler.py"),
        ("完整集成示例", "python mcp_integration_example.py"),
        ("Flask API 服务", "python flask_mcp_integration.py"),
        ("智能亚马逊抓取", "python amazon_scraper_with_llm.py"),
        ("亚马逊抓取演示", "python amazon_demo.py")
    ]
    
    for name, command in examples:
        print(f"📋 {name}:")
        print(f"   {command}")
        print()


async def main():
    """主函数"""
    print("🚀 MCP Web Automation 快速安装脚本")
    print("=" * 50)
    
    # 检查 Python 版本
    python_version = sys.version_info
    if python_version.major < 3 or python_version.minor < 8:
        print("❌ 需要 Python 3.8 或更高版本")
        return False
    
    print(f"✅ Python 版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查 Node.js
    if not check_node():
        print("\n⚠️ 请先安装 Node.js:")
        print("   https://nodejs.org/")
        print("   安装后重新运行此脚本")
        return False
    
    # 安装依赖
    if not install_dependencies():
        print("\n❌ 依赖安装失败，请检查错误信息")
        return False
    
    # 创建环境文件
    create_env_file()
    
    # 测试 MCP 连接
    if await test_mcp_connection():
        print("\n🎉 安装和测试完成!")
        show_usage_examples()
        return True
    else:
        print("\n⚠️ 安装完成但 MCP 测试失败")
        print("请检查:")
        print("1. Node.js 是否正确安装")
        print("2. @playwright/mcp 是否安装成功")
        print("3. playwright 浏览器是否安装")
        return False


if __name__ == "__main__":
    print("📋 这个脚本将:")
    print("  1. 检查系统环境")
    print("  2. 安装 Python 和 Node.js 依赖")
    print("  3. 测试 MCP 连接")
    print("  4. 创建配置文件")
    print()
    
    try:
        success = asyncio.run(main())
        if success:
            print("\n✅ 安装完成！现在你可以开始使用 MCP Web Automation 了！")
        else:
            print("\n❌ 安装过程中遇到问题，请查看上方的错误信息")
    except KeyboardInterrupt:
        print("\n⚠️ 安装被用户中断")
    except Exception as e:
        print(f"\n❌ 安装过程中发生错误: {e}")