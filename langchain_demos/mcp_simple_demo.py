"""
简化版 MCP + LangChain + Azure OpenAI 演示
更容易理解和运行的版本

依赖安装:
pip install mcp langchain langchain-openai python-dotenv langchain-mcp-adapters

Azure OpenAI 环境变量配置 (.env 文件):
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_MODEL=gpt-4  # 或者你的部署名称

如果需要使用 FastMCP:
pip install fastmcp
"""

import asyncio
import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# MCP 相关导入
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# LangChain MCP 官方适配器
from langchain_mcp_adapters.tools import load_mcp_tools

# LangChain 相关导入
from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate

# 根据官方文档，使用正确的导入路径
try:
    # 尝试从 langgraph.prebuilt 导入（推荐）
    from langgraph.prebuilt import create_react_agent
    LANGGRAPH_AVAILABLE = True
    print("✅ 使用 LangGraph create_react_agent")
except ImportError:
    try:
        # 回退到传统的 LangChain 版本
        from langchain.agents.react.agent import create_react_agent
        LANGGRAPH_AVAILABLE = False
        print("ℹ️ 使用传统的 LangChain create_react_agent")
    except ImportError:
        LANGGRAPH_AVAILABLE = False
        create_react_agent = None
        print("⚠️ create_react_agent 不可用，使用 AgentExecutor")

# 加载环境变量
load_dotenv()


# 删除了自定义的工具包装器，使用官方的 langchain-mcp-adapters


class SimpleMCPDemo:
    """简化的 MCP + LangChain 演示"""
    
    def __init__(self):
        """初始化"""
        # 检查 Azure OpenAI 环境变量 (新版本简化配置)
        required_env_vars = [
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT", 
            "AZURE_OPENAI_API_VERSION"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        # 检查模型名称，支持新的配置方式
        model_name = os.getenv("AZURE_OPENAI_MODEL") or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or "gpt-4"
        print(f"🤖 使用模型: {model_name}")
        
        if missing_vars:
            print(f"⚠️ 请在 .env 文件中设置以下环境变量: {', '.join(missing_vars)}")
            print("示例配置:")
            print("AZURE_OPENAI_API_KEY=your_api_key")
            print("AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/")
            print("AZURE_OPENAI_API_VERSION=2024-12-01-preview")
            print("AZURE_OPENAI_MODEL=gpt-4  # 或者你的部署名称")
        else:
            print("✅ Azure OpenAI 环境变量检查通过")
            print(f"🔗 端点: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
            print(f"🔢 API版本: {os.getenv('AZURE_OPENAI_API_VERSION')}")
            
        try:
            # 使用新版本的简化配置
            self.llm = AzureChatOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                model=model_name,  # 使用 model 参数而不是 deployment_name
                temperature=0.1
            )
            print("✅ Azure OpenAI 客户端初始化成功")
        except Exception as e:
            print(f"❌ Azure OpenAI 客户端初始化失败: {e}")
            print("请检查环境变量配置是否正确")
        self.mcp_session: Optional[ClientSession] = None
        self.tools = []
        self.agent = None
    
    def create_math_server_file(self) -> str:
        """创建数学运算 MCP 服务器文件"""
        server_code = '''#!/usr/bin/env python3
"""
简单的数学运算 MCP 服务器
"""

import asyncio
import json
import sys
from typing import Any, Dict

# 简单的 MCP 服务器实现
class SimpleMCPServer:
    def __init__(self):
        self.tools = {
            "add": {
                "name": "add",
                "description": "将两个数字相加",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "第一个数字"},
                        "b": {"type": "number", "description": "第二个数字"}
                    },
                    "required": ["a", "b"]
                }
            },
            "multiply": {
                "name": "multiply", 
                "description": "将两个数字相乘",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "第一个数字"},
                        "b": {"type": "number", "description": "第二个数字"}
                    },
                    "required": ["a", "b"]
                }
            }
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理 MCP 请求"""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "simple-math",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0", 
                "id": request.get("id"),
                "result": {
                    "tools": list(self.tools.values())
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "add":
                result = float(arguments["a"]) + float(arguments["b"])
            elif tool_name == "multiply":
                result = float(arguments["a"]) * float(arguments["b"])
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {"code": -1, "message": f"Unknown tool: {tool_name}"}
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [{"type": "text", "text": str(result)}]
                }
            }
        
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {"code": -1, "message": f"Unknown method: {method}"}
        }
    
    async def run(self):
        """运行服务器"""
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                request = json.loads(line.strip())
                response = await self.handle_request(request)
                
                print(json.dumps(response), flush=True)
                
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -1, "message": str(e)}
                }
                print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    server = SimpleMCPServer()
    asyncio.run(server.run())
'''
        
        with open("simple_math_server.py", "w", encoding="utf-8") as f:
            f.write(server_code)
        
        # 使文件可执行
        os.chmod("simple_math_server.py", 0o755)
        
        print("📝 已创建 simple_math_server.py")
        return "simple_math_server.py"
    
    async def connect_to_mcp(self, server_command: str = None, server_args: List[str] = None) -> bool:
        """连接到 MCP 服务器"""
        import subprocess
        import shutil
        
        # 自动检测可用的命令
        if server_command is None:
            if shutil.which("uvx"):
                server_command = "uvx"
                if server_args is None:
                    server_args = ["mcp-server-time", "--local-timezone=America/New_York"]
            elif shutil.which("python") or shutil.which("python3"):
                # 尝试使用 pip 安装并运行
                print("🔍 uvx 不可用，尝试使用 pip 安装 mcp-server-time...")
                try:
                    # 安装 mcp-server-time
                    subprocess.run([
                        "pip", "install", "mcp-server-time"
                    ], check=True, capture_output=True)
                    
                    server_command = "python"
                    server_args = ["-m", "mcp_server_time", "--local-timezone=America/New_York"]
                    print("✅ 使用 pip 安装成功")
                except subprocess.CalledProcessError as e:
                    print(f"❌ pip 安装失败: {e}")
                    return False
            else:
                print("❌ 未找到可用的 Python 或 uvx 命令")
                return False
        
        if server_args is None:
            server_args = ["mcp-server-time", "--local-timezone=America/New_York"]
            
        try:
            print(f"🔄 正在连接到 MCP 服务器... (使用 {server_command})")
            
            # 配置服务器参数
            server_params = StdioServerParameters(
                command=server_command,
                args=server_args,
                env=None
            )
            
            # 建立连接
            from contextlib import AsyncExitStack
            self.exit_stack = AsyncExitStack()
            
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            
            # 创建会话
            self.mcp_session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
            
            # 初始化
            await self.mcp_session.initialize()
            
            # 获取工具列表
            response = await self.mcp_session.list_tools()
            tools = response.tools
            
            print(f"✅ 成功连接，发现 {len(tools)} 个工具:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # 使用官方适配器加载 MCP 工具
            self.tools = await load_mcp_tools(self.mcp_session)
            print(f"✅ 使用官方适配器加载了 {len(self.tools)} 个工具")
            
            return True
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def create_agent(self):
        """创建 Agent"""
        if LANGGRAPH_AVAILABLE and create_react_agent is not None:
            # 使用 LangGraph 的 create_react_agent
            self.agent = create_react_agent(
                self.llm, 
                self.tools,
                state_modifier="你是一个智能时间助手，可以使用时间工具来获取时间信息。请用中文回答用户的时间相关问题。"
            )
            self.use_langgraph = True
            print("✅ 创建了 LangGraph ReAct Agent")
        elif create_react_agent is not None:
            # 对于具有 JSON schema 的 MCP 工具，使用 OpenAI Tools Agent 更合适
            print("ℹ️ 检测到 JSON schema 工具，使用 OpenAI Tools Agent")
            prompt = ChatPromptTemplate.from_messages([
                ("system", "你是一个智能时间助手，可以使用时间工具来获取时间信息。请用中文回答用户的时间相关问题。"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ])
            
            agent = create_openai_tools_agent(self.llm, self.tools, prompt)
            self.agent = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True
            )
            self.use_langgraph = False
            print("✅ 创建了 OpenAI Tools Agent（支持 JSON schema）")
        else:
            # 回退到 OpenAI Tools Agent
            prompt = ChatPromptTemplate.from_messages([
                ("system", "你是一个智能时间助手，可以使用时间工具来获取时间信息。请用中文回答用户的时间相关问题。"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ])
            
            agent = create_openai_tools_agent(self.llm, self.tools, prompt)
            self.agent = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True
            )
            self.use_langgraph = False
            print("✅ 创建了 OpenAI Tools Agent")
    
    async def run_query(self, query: str) -> str:
        """运行查询"""
        try:
            if hasattr(self, 'use_langgraph') and self.use_langgraph:
                # LangGraph ReAct Agent 使用 messages 格式
                result = await self.agent.ainvoke({"messages": [("user", query)]})
                
                # 从 messages 中获取最后的 AI 响应
                if "messages" in result and result["messages"]:
                    last_message = result["messages"][-1]
                    if hasattr(last_message, 'content'):
                        return last_message.content
                    else:
                        return str(last_message)
                
                return str(result)
            else:
                # 传统 LangChain Agent 使用 input 格式
                result = await self.agent.ainvoke({"input": query})
                return result.get("output", str(result))
            
        except Exception as e:
            error_msg = str(e)
            print(f"🔍 详细错误信息: {error_msg}")
            
            # 提供针对性的建议
            if "404" in error_msg:
                print("💡 建议检查:")
                print("  1. AZURE_OPENAI_MODEL 是否正确")
                print("  2. 部署是否存在且已激活")
                print("  3. AZURE_OPENAI_ENDPOINT 格式是否正确")
            elif "401" in error_msg:
                print("💡 建议检查:")
                print("  1. AZURE_OPENAI_API_KEY 是否正确")
                print("  2. API密钥是否已过期")
            elif "403" in error_msg:
                print("💡 建议检查:")
                print("  1. 是否有访问该部署的权限")
                print("  2. 配额是否已用完")
                
            return f"查询失败: {error_msg}"
    
    async def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, 'exit_stack'):
                await self.exit_stack.aclose()
        except Exception as e:
            print(f"清理时出现错误: {e}")


async def run_simple_demo():
    """运行简化演示"""
    print("🎯 启动简化版 MCP + LangChain 时间服务器演示")
    print("=" * 40)
    
    demo = SimpleMCPDemo()
    
    try:
        # 连接到时间 MCP 服务器
        if not await demo.connect_to_mcp():
            return
        
        # 创建 Agent
        demo.create_agent()
        
        # 测试查询（时间相关）
        test_queries = [
            "现在几点了？",
            "今天是什么日期？",
            "获取当前时间戳"
        ]
        
        print("\n🧪 开始测试:")
        print("-" * 30)
        
        for query in test_queries:
            print(f"\n❓ 查询: {query}")
            result = await demo.run_query(query)
            print(f"💬 回答: {result}")
            await asyncio.sleep(1)
        
        print("\n🎉 演示完成!")
        
    except Exception as e:
        print(f"❌ 演示出错: {e}")
    
    finally:
        await demo.cleanup()
        
        # 不需要清理文件，因为我们使用的是外部时间服务器
        pass


if __name__ == "__main__":
    asyncio.run(run_simple_demo())
