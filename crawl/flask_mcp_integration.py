"""
Flask Web API + MCP 集成示例
展示如何在 Flask API 中集成 MCP 工具

这个例子展示了如何构建一个 RESTful API，后端使用 MCP 进行网页操作
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from contextlib import AsyncExitStack

from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# MCP 相关导入
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPWebService:
    """MCP 网页服务类 - 在 Flask 中使用的单例服务"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.is_connected = False
        self.loop = None
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def start_background_loop(self):
        """启动后台事件循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 在后台线程中运行事件循环
        def run_loop():
            self.loop.run_forever()
        
        import threading
        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()
        
        return self.loop
    
    def run_async(self, coro):
        """在后台事件循环中运行异步函数"""
        if not self.loop:
            self.start_background_loop()
        
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=30)  # 30秒超时
    
    async def _initialize(self):
        """异步初始化方法"""
        try:
            print("🔄 初始化 MCP 连接...")
            
            server_params = StdioServerParameters(
                command="npx",
                args=["@playwright/mcp"],
                env=None
            )
            
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
            
            await self.session.initialize()
            self.is_connected = True
            
            print("✅ MCP 连接成功")
            return {"success": True, "message": "MCP连接初始化成功"}
            
        except Exception as e:
            error_msg = f"MCP 初始化失败: {str(e)}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
    
    def initialize(self):
        """同步的初始化方法"""
        return self.run_async(self._initialize())
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """异步调用 MCP 工具"""
        if not self.is_connected or not self.session:
            return {"success": False, "error": "MCP连接未初始化"}
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            return {
                "success": True,
                "data": result.content if hasattr(result, 'content') else result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """同步调用 MCP 工具"""
        return self.run_async(self._call_mcp_tool(tool_name, arguments))
    
    async def _get_available_tools(self):
        """异步获取可用工具"""
        if not self.is_connected or not self.session:
            return {"success": False, "error": "MCP连接未初始化"}
        
        try:
            response = await self.session.list_tools()
            tools = [{"name": tool.name, "description": tool.description} 
                    for tool in response.tools]
            return {"success": True, "tools": tools}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_available_tools(self):
        """同步获取可用工具"""
        return self.run_async(self._get_available_tools())


# 创建全局服务实例
mcp_service = MCPWebService()

# 创建 Flask 应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "mcp_connected": mcp_service.is_connected,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/mcp/initialize', methods=['POST'])
def initialize_mcp():
    """初始化 MCP 连接"""
    try:
        result = mcp_service.initialize()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"初始化失败: {str(e)}"
        }), 500


@app.route('/api/mcp/tools', methods=['GET'])
def get_tools():
    """获取可用的 MCP 工具列表"""
    try:
        result = mcp_service.get_available_tools()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"获取工具列表失败: {str(e)}"
        }), 500


@app.route('/api/web/navigate', methods=['POST'])
def navigate_to_page():
    """导航到指定页面"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({
                "success": False,
                "error": "缺少 URL 参数"
            }), 400
        
        result = mcp_service.call_mcp_tool("browser_navigate", {"url": url})
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"导航失败: {str(e)}"
        }), 500


@app.route('/api/web/snapshot', methods=['POST'])
def take_page_snapshot():
    """获取页面快照"""
    try:
        result = mcp_service.call_mcp_tool("browser_snapshot", {})
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"获取快照失败: {str(e)}"
        }), 500


@app.route('/api/web/screenshot', methods=['POST'])
def take_screenshot():
    """截图"""
    try:
        data = request.get_json() or {}
        filename = data.get('filename')
        
        args = {}
        if filename:
            args['filename'] = filename
        
        result = mcp_service.call_mcp_tool("browser_take_screenshot", args)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"截图失败: {str(e)}"
        }), 500


@app.route('/api/web/click', methods=['POST'])
def click_element():
    """点击页面元素"""
    try:
        data = request.get_json()
        element = data.get('element')
        ref = data.get('ref')
        
        if not element or not ref:
            return jsonify({
                "success": False,
                "error": "缺少 element 或 ref 参数"
            }), 400
        
        result = mcp_service.call_mcp_tool("browser_click", {
            "element": element,
            "ref": ref
        })
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"点击失败: {str(e)}"
        }), 500


@app.route('/api/web/type', methods=['POST'])
def type_text():
    """在元素中输入文本"""
    try:
        data = request.get_json()
        element = data.get('element')
        ref = data.get('ref')
        text = data.get('text')
        submit = data.get('submit', False)
        
        if not element or not ref or not text:
            return jsonify({
                "success": False,
                "error": "缺少必要参数 (element, ref, text)"
            }), 400
        
        result = mcp_service.call_mcp_tool("browser_type", {
            "element": element,
            "ref": ref,
            "text": text,
            "submit": submit
        })
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"输入文本失败: {str(e)}"
        }), 500


@app.route('/api/web/scrape', methods=['POST'])
def scrape_website():
    """完整的网站抓取流程"""
    try:
        data = request.get_json()
        url = data.get('url')
        wait_time = data.get('wait_time', 2)
        include_screenshot = data.get('include_screenshot', True)
        
        if not url:
            return jsonify({
                "success": False,
                "error": "缺少 URL 参数"
            }), 400
        
        # 执行抓取流程
        results = {}
        
        # 1. 导航
        nav_result = mcp_service.call_mcp_tool("browser_navigate", {"url": url})
        if not nav_result.get("success"):
            return jsonify(nav_result), 500
        results["navigation"] = nav_result
        
        # 2. 等待
        wait_result = mcp_service.call_mcp_tool("browser_wait_for", {"time": wait_time})
        results["wait"] = wait_result
        
        # 3. 获取快照
        snapshot_result = mcp_service.call_mcp_tool("browser_snapshot", {})
        results["snapshot"] = snapshot_result
        
        # 4. 截图（可选）
        if include_screenshot:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_result = mcp_service.call_mcp_tool(
                "browser_take_screenshot", 
                {"filename": f"scrape_{timestamp}.png"}
            )
            results["screenshot"] = screenshot_result
        
        return jsonify({
            "success": True,
            "data": {
                "url": url,
                "scrape_results": results,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"网站抓取失败: {str(e)}"
        }), 500


@app.route('/api/web/custom-task', methods=['POST'])
def execute_custom_task():
    """执行自定义任务序列"""
    try:
        data = request.get_json()
        tasks = data.get('tasks', [])
        
        if not tasks:
            return jsonify({
                "success": False,
                "error": "缺少任务列表"
            }), 400
        
        results = []
        
        for i, task in enumerate(tasks):
            tool_name = task.get('tool')
            arguments = task.get('arguments', {})
            
            if not tool_name:
                results.append({
                    "task_index": i,
                    "success": False,
                    "error": "任务缺少工具名称"
                })
                continue
            
            result = mcp_service.call_mcp_tool(tool_name, arguments)
            results.append({
                "task_index": i,
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result
            })
        
        return jsonify({
            "success": True,
            "data": {
                "total_tasks": len(tasks),
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"自定义任务执行失败: {str(e)}"
        }), 500


if __name__ == '__main__':
    print("🚀 启动 Flask + MCP 集成服务")
    print("=" * 50)
    print("📋 API 端点:")
    print("  GET  /api/health          - 健康检查")
    print("  POST /api/mcp/initialize  - 初始化 MCP")
    print("  GET  /api/mcp/tools       - 获取工具列表")
    print("  POST /api/web/navigate    - 导航到页面")
    print("  POST /api/web/snapshot    - 获取页面快照")
    print("  POST /api/web/screenshot  - 截图")
    print("  POST /api/web/click       - 点击元素")
    print("  POST /api/web/type        - 输入文本")
    print("  POST /api/web/scrape      - 网站抓取")
    print("  POST /api/web/custom-task - 自定义任务")
    print("=" * 50)
    print()
    print("📝 使用前请确保已安装:")
    print("  1. npm install -g @playwright/mcp")
    print("  2. pip install mcp flask flask-cors")
    print("  3. playwright install")
    print()
    
    # 自动初始化 MCP 连接
    try:
        print("🔄 自动初始化 MCP 连接...")
        init_result = mcp_service.initialize()
        if init_result.get("success"):
            print("✅ MCP 自动初始化成功")
        else:
            print(f"⚠️ MCP 自动初始化失败: {init_result.get('error')}")
            print("可以稍后通过 /api/mcp/initialize 手动初始化")
    except Exception as e:
        print(f"⚠️ MCP 自动初始化异常: {e}")
    
    # 启动 Flask 服务器
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)