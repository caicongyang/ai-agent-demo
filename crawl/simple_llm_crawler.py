"""
使用官方 MCP Python SDK 直接调用 Playwright 工具
不需要复杂封装，直接在代码中使用 MCP 协议
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class DirectMCPClient:
    """直接使用官方 MCP Python SDK 的客户端"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.stdio = None
        self.write = None
    
    async def connect_to_playwright(self):
        """连接到 Playwright MCP 服务器"""
        try:
            # 设置服务器参数
            server_params = StdioServerParameters(
                command="npx",
                args=["@playwright/mcp"],
                env=None
            )
            
            # 建立连接
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            
            # 创建会话
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            
            # 初始化
            await self.session.initialize()
            
            print("✅ 成功连接到 Playwright MCP 服务器")
            
            # 列出可用工具
            response = await self.session.list_tools()
            tools = response.tools
            print(f"📋 发现 {len(tools)} 个工具:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            return True
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用 MCP 工具"""
        if not self.session:
            raise RuntimeError("请先连接到 MCP 服务器")
        
        try:
            print(f"🔧 调用工具: {tool_name} with {arguments}")
            result = await self.session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            print(f"❌ 工具调用失败: {e}")
            raise
    
    async def navigate(self, url: str) -> Any:
        """导航到指定URL"""
        return await self.call_tool("browser_navigate", {"url": url})
    
    async def take_snapshot(self) -> Any:
        """获取页面快照"""
        return await self.call_tool("browser_snapshot", {})
    
    async def take_screenshot(self, filename: Optional[str] = None) -> Any:
        """截图"""
        args = {}
        if filename:
            args["filename"] = filename
        return await self.call_tool("browser_take_screenshot", args)
    
    async def click_element(self, element: str, ref: str) -> Any:
        """点击页面元素"""
        return await self.call_tool("browser_click", {
            "element": element,
            "ref": ref
        })
    
    async def type_text(self, element: str, ref: str, text: str, submit: bool = False) -> Any:
        """在元素中输入文本"""
        return await self.call_tool("browser_type", {
            "element": element,
            "ref": ref,
            "text": text,
            "submit": submit
        })
    
    async def wait_for_element(self, text: Optional[str] = None, time: Optional[float] = None) -> Any:
        """等待元素或时间"""
        args = {}
        if text:
            args["text"] = text
        if time:
            args["time"] = time
        return await self.call_tool("browser_wait_for", args)
    
    async def get_available_tools(self) -> List:
        """获取所有可用工具"""
        if not self.session:
            return []
        
        response = await self.session.list_tools()
        return response.tools
    
    async def close(self):
        """关闭连接"""
        if self.exit_stack:
            await self.exit_stack.aclose()
            print("✅ MCP 连接已关闭")


class WebAutomationTasks:
    """基于 MCP 的网页自动化任务集合"""
    
    def __init__(self):
        self.client = DirectMCPClient()
    
    async def start(self):
        """启动客户端"""
        return await self.client.connect_to_playwright()
    
    async def simple_web_scraping(self, url: str, target_info: str = "页面内容") -> Dict[str, Any]:
        """简单的网页抓取任务"""
        try:
            print(f"\n🕷️ 开始抓取任务: {url}")
            
            # 1. 导航到页面
            nav_result = await self.client.navigate(url)
            print(f"导航结果: {nav_result.content if hasattr(nav_result, 'content') else nav_result}")
            
            # 2. 等待页面加载
            await self.client.wait_for_element(time=2)
            
            # 3. 获取页面快照
            snapshot = await self.client.take_snapshot()
            
            # 4. 截图
            screenshot_filename = f"screenshot_{url.replace('https://', '').replace('/', '_')}.png"
            screenshot_result = await self.client.take_screenshot(screenshot_filename)
            
            return {
                "url": url,
                "target_info": target_info,
                "navigation": nav_result,
                "snapshot": snapshot,
                "screenshot": screenshot_result,
                "success": True
            }
            
        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "success": False
            }
    
    async def search_and_extract(self, search_engine: str, query: str) -> Dict[str, Any]:
        """搜索并提取信息"""
        try:
            print(f"\n🔍 搜索任务: 在 {search_engine} 搜索 '{query}'")
            
            # 1. 导航到搜索引擎
            await self.client.navigate(search_engine)
            await self.client.wait_for_element(time=2)
            
            # 2. 获取页面结构，寻找搜索框
            snapshot = await self.client.take_snapshot()
            print("📸 已获取页面快照，可以分析页面结构")
            
            # 3. 截图记录
            await self.client.take_screenshot(f"search_page_{query.replace(' ', '_')}.png")
            
            # 注意：实际的搜索框点击和输入需要解析快照中的元素引用
            # 这里只是演示基本流程
            
            return {
                "search_engine": search_engine,
                "query": query,
                "snapshot_obtained": True,
                "success": True,
                "note": "需要解析快照中的元素引用来进行实际的搜索框操作"
            }
            
        except Exception as e:
            return {
                "search_engine": search_engine,
                "query": query,
                "error": str(e),
                "success": False
            }
    
    async def form_automation(self, form_url: str, form_data: Dict[str, str]) -> Dict[str, Any]:
        """表单自动化填写"""
        try:
            print(f"\n📝 表单填写任务: {form_url}")
            
            # 1. 导航到表单页面
            await self.client.navigate(form_url)
            await self.client.wait_for_element(time=2)
            
            # 2. 获取页面快照来分析表单结构
            snapshot = await self.client.take_snapshot()
            print("📋 已获取表单页面快照")
            
            # 3. 截图记录初始状态
            await self.client.take_screenshot("form_initial.png")
            
            # 注意：实际的表单填写需要解析快照中的表单元素引用
            # 然后使用 type_text 和 click_element 方法
            
            return {
                "form_url": form_url,
                "form_data": form_data,
                "snapshot_obtained": True,
                "success": True,
                "note": "需要解析快照中的表单元素引用来进行实际的填写操作"
            }
            
        except Exception as e:
            return {
                "form_url": form_url, 
                "error": str(e),
                "success": False
            }
    
    async def close(self):
        """关闭客户端"""
        await self.client.close()


async def demo_direct_mcp_usage():
    """演示直接使用 MCP 的完整流程"""
    print("🚀 直接使用 MCP Python SDK 演示")
    print("=" * 50)
    
    automation = WebAutomationTasks()
    
    try:
        # 连接到 MCP 服务器
        if not await automation.start():
            print("❌ 无法连接到 MCP 服务器")
            return
        
        # 演示1: 简单网页抓取
        print("\n" + "="*30 + " 演示1: 网页抓取 " + "="*30)
        result1 = await automation.simple_web_scraping(
            "https://httpbin.org/html",
            "HTML测试页面内容"
        )
        print(f"抓取结果: {result1['success']}")
        
        # 演示2: 搜索引擎模拟
        print("\n" + "="*30 + " 演示2: 搜索模拟 " + "="*30)
        result2 = await automation.search_and_extract(
            "https://duckduckgo.com",
            "MCP Model Context Protocol"
        )
        print(f"搜索结果: {result2['success']}")
        
        # 演示3: 表单页面分析
        print("\n" + "="*30 + " 演示3: 表单分析 " + "="*30)
        result3 = await automation.form_automation(
            "https://httpbin.org/forms/post",
            {"name": "测试用户", "email": "test@example.com"}
        )
        print(f"表单分析结果: {result3['success']}")
        
    except Exception as e:
        print(f"❌ 演示过程中出错: {e}")
    
    finally:
        await automation.close()


if __name__ == "__main__":
    print("📝 注意: 使用前请确保已安装:")
    print("  1. npm install -g @playwright/mcp")
    print("  2. pip install mcp")
    print("  3. playwright install")
    print()
    
    asyncio.run(demo_direct_mcp_usage())