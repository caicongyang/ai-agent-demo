"""
完整的 MCP 集成示例 - 在你的应用中直接使用 MCP 工具

这个例子展示了如何在实际项目中集成 MCP Playwright 工具
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import datetime

# MCP 相关导入
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    data: Any = None
    error: str = ""
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MCPWebAutomation:
    """基于 MCP 的网页自动化系统"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.is_connected = False
        self.available_tools = []
    
    async def initialize(self) -> TaskResult:
        """初始化 MCP 连接"""
        try:
            print("🔄 正在初始化 MCP 连接...")
            
            # 配置 Playwright MCP 服务器
            server_params = StdioServerParameters(
                command="npx",
                args=["@playwright/mcp"],
                env=None
            )
            
            # 建立 stdio 传输连接
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            
            # 创建客户端会话
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
            
            # 初始化会话
            await self.session.initialize()
            
            # 获取可用工具列表
            response = await self.session.list_tools()
            self.available_tools = response.tools
            
            self.is_connected = True
            
            print("✅ MCP 连接初始化成功")
            print(f"📋 发现 {len(self.available_tools)} 个可用工具:")
            for tool in self.available_tools[:5]:  # 只显示前5个
                print(f"  - {tool.name}")
            
            return TaskResult(
                success=True,
                data={
                    "tools_count": len(self.available_tools),
                    "tools": [tool.name for tool in self.available_tools]
                }
            )
            
        except Exception as e:
            error_msg = f"MCP 连接初始化失败: {str(e)}"
            print(f"❌ {error_msg}")
            return TaskResult(success=False, error=error_msg)
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> TaskResult:
        """调用 MCP 工具的通用方法"""
        if not self.is_connected or not self.session:
            return TaskResult(success=False, error="MCP 连接未初始化")
        
        try:
            print(f"🔧 调用工具: {tool_name}")
            result = await self.session.call_tool(tool_name, arguments)
            
            return TaskResult(
                success=True,
                data=result
            )
            
        except Exception as e:
            error_msg = f"工具调用失败: {str(e)}"
            print(f"❌ {error_msg}")
            return TaskResult(success=False, error=error_msg)
    
    # === 具体的业务方法 ===
    
    async def navigate_to_page(self, url: str) -> TaskResult:
        """导航到指定页面"""
        return await self.call_tool("browser_navigate", {"url": url})
    
    async def capture_page_info(self, include_screenshot: bool = True) -> TaskResult:
        """捕获页面信息（快照 + 截图）"""
        try:
            results = {}
            
            # 获取页面快照
            snapshot_result = await self.call_tool("browser_snapshot", {})
            if snapshot_result.success:
                results["snapshot"] = snapshot_result.data
            
            # 截图（如果需要）
            if include_screenshot:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_result = await self.call_tool(
                    "browser_take_screenshot", 
                    {"filename": f"page_capture_{timestamp}.png"}
                )
                if screenshot_result.success:
                    results["screenshot"] = screenshot_result.data
            
            return TaskResult(success=True, data=results)
            
        except Exception as e:
            return TaskResult(success=False, error=str(e))
    
    async def interact_with_element(self, action: str, element_desc: str, 
                                  element_ref: str, text: str = "") -> TaskResult:
        """与页面元素交互"""
        try:
            if action == "click":
                return await self.call_tool("browser_click", {
                    "element": element_desc,
                    "ref": element_ref
                })
            elif action == "type":
                return await self.call_tool("browser_type", {
                    "element": element_desc,
                    "ref": element_ref,
                    "text": text,
                    "submit": False
                })
            elif action == "type_and_submit":
                return await self.call_tool("browser_type", {
                    "element": element_desc,
                    "ref": element_ref,
                    "text": text,
                    "submit": True
                })
            else:
                return TaskResult(success=False, error=f"不支持的操作: {action}")
                
        except Exception as e:
            return TaskResult(success=False, error=str(e))
    
    async def wait_for_condition(self, condition_type: str, value: Any) -> TaskResult:
        """等待特定条件"""
        try:
            args = {}
            if condition_type == "time":
                args["time"] = value
            elif condition_type == "text":
                args["text"] = value
            
            return await self.call_tool("browser_wait_for", args)
            
        except Exception as e:
            return TaskResult(success=False, error=str(e))
    
    # === 高级业务流程 ===
    
    async def scrape_website_data(self, url: str, wait_time: float = 2) -> TaskResult:
        """完整的网站数据抓取流程"""
        try:
            print(f"\n🕷️ 开始抓取网站: {url}")
            
            # 1. 导航到页面
            nav_result = await self.navigate_to_page(url)
            if not nav_result.success:
                return nav_result
            
            # 2. 等待页面加载
            await self.wait_for_condition("time", wait_time)
            
            # 3. 捕获页面信息
            page_info = await self.capture_page_info(include_screenshot=True)
            if not page_info.success:
                return page_info
            
            # 4. 整理结果
            scraped_data = {
                "url": url,
                "navigation_result": nav_result.data,
                "page_snapshot": page_info.data.get("snapshot"),
                "screenshot_info": page_info.data.get("screenshot"),
                "scrape_timestamp": datetime.now().isoformat()
            }
            
            print("✅ 网站抓取完成")
            return TaskResult(success=True, data=scraped_data)
            
        except Exception as e:
            return TaskResult(success=False, error=f"网站抓取失败: {str(e)}")
    
    async def automated_form_filling(self, form_url: str, 
                                   form_fields: Dict[str, str]) -> TaskResult:
        """自动化表单填写流程"""
        try:
            print(f"\n📝 开始自动化表单填写: {form_url}")
            
            # 1. 导航到表单页面
            nav_result = await self.navigate_to_page(form_url)
            if not nav_result.success:
                return nav_result
            
            # 2. 等待页面加载
            await self.wait_for_condition("time", 2)
            
            # 3. 获取页面快照来分析表单结构
            snapshot_result = await self.capture_page_info(include_screenshot=False)
            if not snapshot_result.success:
                return snapshot_result
            
            # 4. 解析快照，找到表单元素（这里需要具体的解析逻辑）
            snapshot_data = snapshot_result.data.get("snapshot")
            
            # 注意：实际项目中，你需要解析 snapshot_data 来找到表单元素的引用
            # 这里只是演示结构
            
            form_results = {
                "form_url": form_url,
                "form_fields": form_fields,
                "snapshot_obtained": True,
                "page_analyzed": True,
                "note": "需要实现快照解析逻辑来自动找到表单元素"
            }
            
            print("⚠️ 表单分析完成，需要实现元素解析逻辑")
            return TaskResult(success=True, data=form_results)
            
        except Exception as e:
            return TaskResult(success=False, error=f"表单填写失败: {str(e)}")
    
    async def monitor_page_changes(self, url: str, check_interval: int = 30, 
                                 max_checks: int = 5) -> TaskResult:
        """监控页面变化"""
        try:
            print(f"\n📊 开始监控页面变化: {url}")
            
            changes_log = []
            
            for i in range(max_checks):
                print(f"🔍 第 {i+1}/{max_checks} 次检查...")
                
                # 导航到页面
                await self.navigate_to_page(url)
                await self.wait_for_condition("time", 2)
                
                # 捕获当前状态
                page_info = await self.capture_page_info(include_screenshot=True)
                
                check_record = {
                    "check_number": i + 1,
                    "timestamp": datetime.now().isoformat(),
                    "success": page_info.success,
                    "data": page_info.data if page_info.success else None,
                    "error": page_info.error if not page_info.success else None
                }
                
                changes_log.append(check_record)
                
                if i < max_checks - 1:
                    print(f"⏳ 等待 {check_interval} 秒...")
                    await self.wait_for_condition("time", check_interval)
            
            print("✅ 页面监控完成")
            return TaskResult(success=True, data={
                "url": url,
                "total_checks": max_checks,
                "changes_log": changes_log
            })
            
        except Exception as e:
            return TaskResult(success=False, error=f"页面监控失败: {str(e)}")
    
    async def cleanup(self):
        """清理资源"""
        if self.exit_stack:
            await self.exit_stack.aclose()
            self.is_connected = False
            print("✅ MCP 连接已关闭")


# === 使用示例 ===

class WebScrapingService:
    """基于 MCP 的网页抓取服务"""
    
    def __init__(self):
        self.automation = MCPWebAutomation()
    
    async def initialize(self) -> bool:
        """初始化服务"""
        result = await self.automation.initialize()
        return result.success
    
    async def scrape_multiple_sites(self, urls: List[str]) -> List[TaskResult]:
        """批量抓取多个网站"""
        results = []
        
        for url in urls:
            print(f"\n{'='*60}")
            print(f"抓取网站: {url}")
            print('='*60)
            
            result = await self.automation.scrape_website_data(url)
            results.append(result)
            
            # 每个网站之间等待一下
            await self.automation.wait_for_condition("time", 1)
        
        return results
    
    async def scrape_with_form_interaction(self, form_url: str, 
                                         form_data: Dict[str, str]) -> TaskResult:
        """抓取需要表单交互的网站"""
        return await self.automation.automated_form_filling(form_url, form_data)
    
    async def monitor_website(self, url: str, interval: int = 60, 
                            checks: int = 10) -> TaskResult:
        """监控网站变化"""
        return await self.automation.monitor_page_changes(url, interval, checks)
    
    async def cleanup(self):
        """清理资源"""
        await self.automation.cleanup()


async def main():
    """主函数 - 演示如何在实际应用中使用"""
    print("🚀 MCP 集成示例 - 在你的代码中直接使用 MCP 工具")
    print("=" * 70)
    
    # 创建服务实例
    scraping_service = WebScrapingService()
    
    try:
        # 初始化服务
        if not await scraping_service.initialize():
            print("❌ 服务初始化失败")
            return
        
        # 示例1: 批量抓取网站
        print("\n" + "="*50 + " 示例1: 批量网站抓取 " + "="*50)
        urls_to_scrape = [
            "https://httpbin.org/html",
            "https://httpbin.org/json",
            "https://httpbin.org/user-agent"
        ]
        
        scrape_results = await scraping_service.scrape_multiple_sites(urls_to_scrape)
        
        print(f"\n📊 抓取结果汇总:")
        for i, result in enumerate(scrape_results):
            status = "✅ 成功" if result.success else "❌ 失败"
            print(f"  {i+1}. {urls_to_scrape[i]}: {status}")
        
        # 示例2: 表单交互抓取
        print("\n" + "="*50 + " 示例2: 表单交互 " + "="*50)
        form_result = await scraping_service.scrape_with_form_interaction(
            "https://httpbin.org/forms/post",
            {"name": "测试用户", "email": "test@example.com"}
        )
        
        print(f"表单交互结果: {'✅ 成功' if form_result.success else '❌ 失败'}")
        
        # 示例3: 网站监控（短时间演示）
        print("\n" + "="*50 + " 示例3: 网站监控 " + "="*50)
        monitor_result = await scraping_service.monitor_website(
            "https://httpbin.org/uuid",  # 每次访问返回不同UUID
            interval=5,  # 5秒间隔
            checks=3     # 只检查3次
        )
        
        print(f"网站监控结果: {'✅ 成功' if monitor_result.success else '❌ 失败'}")
        
    except Exception as e:
        print(f"❌ 运行过程中出错: {e}")
    
    finally:
        # 清理资源
        await scraping_service.cleanup()


if __name__ == "__main__":
    print("📋 使用前请确保已安装:")
    print("  1. npm install -g @playwright/mcp")
    print("  2. pip install mcp")
    print("  3. playwright install")
    print()
    
    asyncio.run(main())