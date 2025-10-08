"""
LangChain 调用 MCP (Model Context Protocol) 数学服务器演示
结合了 LangChain 和 MCP 的强大功能，展示如何使用 MCP 数学工具与 LangChain Agent

🆕 新增功能：HTTP 风格的大模型交互日志
- 📤 HTTP REQUEST: 完整的请求 JSON（类似 OpenAI API 调用）
- 📥 HTTP RESPONSE: 完整的响应 JSON（类似 OpenAI API 返回）
- 🔧 TOOL CALL: 工具调用过程的简洁记录
- 🎯 AGENT ACTION: Agent 决策过程的可视化

日志格式说明：
1. 📤 HTTP REQUEST: 显示发送给大模型的完整请求 JSON
   - 包含 messages, model, temperature, tools, tool_choice 等
   - 类似 POST /v1/chat/completions 的请求体
2. 📥 HTTP RESPONSE: 显示大模型返回的完整响应 JSON
   - 包含 choices, message, tool_calls, finish_reason 等
   - 类似 OpenAI API 的响应格式
3. 🔧 TOOL CALL: 工具执行的输入输出
4. 🎯 AGENT ACTION: Agent 的决策和参数

依赖安装:
pip install mcp langchain langchain-openai langchain-mcp-adapters
"""

import asyncio
import os
import json
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv

# MCP 相关导入
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# LangChain MCP 官方适配器
from langchain_mcp_adapters.tools import load_mcp_tools

# LangChain 相关导入
from langchain_openai import AzureChatOpenAI
from langchain.tools import BaseTool
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.manager import CallbackManagerForLLMRun
from pydantic import BaseModel, Field

# 加载环境变量
load_dotenv()


@dataclass
class MCPToolResult:
    """MCP 工具执行结果"""
    success: bool
    data: Any = None
    error: str = ""
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class DetailedInteractionLogger(BaseCallbackHandler):
    """HTTP 风格的交互日志记录器"""
    
    def __init__(self, tools=None):
        super().__init__()
        self.interaction_count = 0
        self.tools = tools or []
        self.current_messages = []  # 存储当前对话的消息历史
        
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """LLM 开始时的回调 - HTTP 请求风格"""
        self.interaction_count += 1
        
        # 解析提示信息构建消息
        self.current_messages = []
        for prompt in prompts:
            # 解析提示中的消息
            messages = self._parse_prompt_to_messages(prompt)
            self.current_messages.extend(messages)
        
        # 构建完整的请求 JSON
        request_json = {
            "messages": self.current_messages,
            "model": serialized.get('name', 'Unknown'),
            "temperature": 0,
            "stream": False,
            "tools": self._build_tools_definitions(),
            "tool_choice": "auto",
            "parallel_tool_calls": True
        }
        
        print(f"\n{'='*80}")
        print(f"📤 HTTP REQUEST #{self.interaction_count}")
        print(f"{'='*80}")
        print("POST /v1/chat/completions")
        print("Content-Type: application/json")
        print()
        print(json.dumps(request_json, indent=2, ensure_ascii=False))
        print(f"{'='*80}")
    
    def _parse_prompt_to_messages(self, prompt: str) -> List[Dict[str, Any]]:
        """解析提示文本为消息列表"""
        messages = []
        lines = prompt.split('\n')
        current_role = None
        current_content = []
        
        for line in lines:
            if line.startswith('System: '):
                if current_role and current_content:
                    messages.append({"role": current_role, "content": '\n'.join(current_content)})
                current_role = "system"
                current_content = [line[8:]]  # 去掉 "System: "
            elif line.startswith('Human: '):
                if current_role and current_content:
                    messages.append({"role": current_role, "content": '\n'.join(current_content)})
                current_role = "user"
                current_content = [line[7:]]  # 去掉 "Human: "
            elif line.startswith('AI: '):
                if current_role and current_content:
                    messages.append({"role": current_role, "content": '\n'.join(current_content)})
                current_role = "assistant"
                current_content = [line[4:]]  # 去掉 "AI: "
            elif line.startswith('Tool: '):
                # 工具结果，添加到当前消息
                if current_role == "assistant":
                    # 这是工具调用的结果，需要特殊处理
                    pass
                else:
                    current_content.append(line)
            else:
                if current_content:
                    current_content.append(line)
        
        # 添加最后一个消息
        if current_role and current_content:
            messages.append({"role": current_role, "content": '\n'.join(current_content)})
        
        return messages
    
    def _build_tools_definitions(self) -> List[Dict[str, Any]]:
        """构建工具定义"""
        tools_definitions = []
        for tool in self.tools:
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                }
            }
            
            # 尝试获取参数 schema
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    if hasattr(tool.args_schema, 'model_json_schema'):
                        schema = tool.args_schema.model_json_schema()
                        tool_def["function"]["parameters"] = schema
                    elif isinstance(tool.args_schema, dict):
                        tool_def["function"]["parameters"] = tool.args_schema
                    else:
                        schema = getattr(tool.args_schema, 'schema', None)
                        if schema:
                            tool_def["function"]["parameters"] = schema
                except:
                    pass
            
            tools_definitions.append(tool_def)
        
        return tools_definitions
    
    def on_llm_end(self, response, **kwargs: Any) -> None:
        """LLM 结束时的回调 - HTTP 响应风格"""
        
        # 构建响应 JSON
        response_json = {
            "id": f"chatcmpl-{self.interaction_count}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": "gpt-4o",
            "choices": []
        }
        
        # 处理响应内容
        if hasattr(response, 'generations') and response.generations:
            for i, generation_list in enumerate(response.generations):
                for j, generation in enumerate(generation_list):
                    choice = {
                        "index": i,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": None
                        },
                        "finish_reason": "stop"
                    }
                    
                    if hasattr(generation, 'message'):
                        message = generation.message
                        choice["message"]["content"] = message.content
                        
                        # 处理工具调用
                        if hasattr(message, 'tool_calls') and message.tool_calls:
                            choice["finish_reason"] = "tool_calls"
                            tool_calls_list = []
                            
                            for k, tc in enumerate(message.tool_calls):
                                try:
                                    if isinstance(tc, dict):
                                        tool_call_item = {
                                            "id": tc.get('id', f"call_{k}"),
                                            "type": "function",
                                            "function": {
                                                "name": tc.get('name', tc.get('function', {}).get('name', 'unknown')),
                                                "arguments": json.dumps(tc.get('arguments', tc.get('function', {}).get('arguments', {})))
                                            }
                                        }
                                    else:
                                        # 对象类型的 tool_call
                                        tool_name = getattr(tc, 'name', None)
                                        if not tool_name:
                                            func_attr = getattr(tc, 'function', None)
                                            if func_attr:
                                                tool_name = func_attr.get('name', 'unknown')
                                            else:
                                                tool_name = 'unknown'
                                        
                                        tool_args = getattr(tc, 'arguments', None)
                                        if tool_args is None:
                                            tool_args = getattr(tc, 'args', None)
                                        if tool_args is None:
                                            func_attr = getattr(tc, 'function', None)
                                            if func_attr:
                                                tool_args = func_attr.get('arguments', {})
                                        
                                        tool_call_item = {
                                            "id": getattr(tc, 'id', f"call_{k}"),
                                            "type": "function",
                                            "function": {
                                                "name": tool_name,
                                                "arguments": json.dumps(tool_args or {})
                                            }
                                        }
                                    tool_calls_list.append(tool_call_item)
                                except Exception as e:
                                    print(f"⚠️ 构建工具调用 #{k+1} JSON 时出错: {e}")
                            
                            choice["message"]["tool_calls"] = tool_calls_list
                    else:
                        choice["message"]["content"] = generation.text
                    
                    response_json["choices"].append(choice)
        
        # 添加使用统计
        response_json["usage"] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        
        print(f"\n{'='*80}")
        print(f"📥 HTTP RESPONSE #{self.interaction_count}")
        print(f"{'='*80}")
        print("200 OK")
        print("Content-Type: application/json")
        print()
        print(json.dumps(response_json, indent=2, ensure_ascii=False))
        print(f"{'='*80}")
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """工具开始执行时的回调"""
        tool_name = serialized.get('name', 'Unknown Tool')
        print(f"\n🔧 [TOOL CALL] {tool_name}")
        print(f"   Input: {input_str}")
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """工具执行结束时的回调"""
        print(f"   Output: {output}")
        print(f"✅ [TOOL CALL COMPLETED]")
    
    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """工具执行出错时的回调"""
        print(f"❌ [TOOL ERROR]: {error}")
    
    def on_agent_action(self, action, **kwargs: Any) -> None:
        """Agent 执行动作时的回调"""
        print(f"\n🎯 [AGENT ACTION] {action.tool}")
        print(f"   Parameters: {action.tool_input}")
    
    def on_agent_finish(self, finish, **kwargs: Any) -> None:
        """Agent 完成时的回调"""
        print(f"\n🏁 [AGENT FINISHED]")
        print(f"   Final Output: {finish.return_values.get('output', 'N/A')}")


# 注意：现在使用 langchain_mcp_adapters.tools.load_mcp_tools 官方适配器
# 不再需要自定义的 MCPToolWrapper 和 create_mcp_tool


class MCPLangChainDemo:
    """MCP + LangChain 集成演示"""
    
    def __init__(self):
        """初始化演示"""
        print("🎯 启动 MCP + LangChain 数学服务器演示")
        print("=" * 40)
        
        # 创建详细交互日志记录器（稍后会设置工具）
        self.interaction_logger = DetailedInteractionLogger()
        
        # Azure OpenAI 配置
        model_name = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")
        print(f"🤖 使用模型: {model_name}")
        
        # 检查必需的环境变量
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        
        if not api_key or not endpoint:
            missing = []
            if not api_key:
                missing.append("AZURE_OPENAI_API_KEY")
            if not endpoint:
                missing.append("AZURE_OPENAI_ENDPOINT")
            print(f"❌ 缺少必需的环境变量: {', '.join(missing)}")
            raise ValueError(f"请设置环境变量: {', '.join(missing)}")
        
        print("✅ Azure OpenAI 环境变量检查通过")
        print(f"🔗 端点: {endpoint}")
        print(f"🔢 API版本: {api_version}")
        
        try:
            self.llm = AzureChatOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version,
                model=model_name,
                temperature=0,
                callbacks=[self.interaction_logger]  # 添加交互日志记录器
            )
            print("✅ Azure OpenAI 客户端初始化成功（已启用详细交互日志）")
        except Exception as e:
            print(f"❌ Azure OpenAI 初始化失败: {e}")
            raise
        self.mcp_session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.tools = []
        self.agent = None
    
    async def initialize_mcp(self, server_command: str = None, server_args: List[str] = None) -> MCPToolResult:
        """
        初始化 MCP 连接
        
        :param server_command: MCP 服务器命令 (默认自动检测)
        :param server_args: MCP 服务器参数 (默认: ["math_mcp_server.py"] 或 ["-m", "mcp_server_time"])
        :return: 初始化结果
        """
        import subprocess
        import shutil
        
        # 自动检测可用的命令和创建数学服务器
        if server_command is None:
            # 首先尝试创建数学 MCP 服务器
            math_server = SimpleMathMCPServer()
            server_file = math_server.create_server_script()
            
            if shutil.which("python") or shutil.which("python3"):
                server_command = "python"
                if server_args is None:
                    server_args = [server_file]
                print(f"✅ 创建了数学 MCP 服务器: {server_file}")
            else:
                error_msg = "未找到可用的 Python 命令"
                print(f"❌ {error_msg}")
                return MCPToolResult(success=False, error=error_msg)
        
        if server_args is None:
            # 默认使用数学服务器
            math_server = SimpleMathMCPServer()
            server_file = math_server.create_server_script()
            server_args = [server_file]
        
        try:
            print(f"🔄 正在初始化 MCP 连接... (使用 {server_command})")
            
            # 配置 MCP 服务器参数
            server_params = StdioServerParameters(
                command=server_command,
                args=server_args,
                env=None
            )
            
            # 建立 stdio 传输连接
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            
            # 创建客户端会话
            self.mcp_session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
            
            # 初始化会话
            await self.mcp_session.initialize()
            
            # 获取可用工具列表
            response = await self.mcp_session.list_tools()
            available_tools = response.tools
            
            print(f"✅ 成功连接，发现 {len(available_tools)} 个工具:")
            for tool in available_tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # 使用官方适配器加载工具
            self.tools = await load_mcp_tools(self.mcp_session)
            print(f"✅ 使用官方适配器加载了 {len(self.tools)} 个工具")
            
            # 更新交互日志记录器的工具列表
            self.interaction_logger.tools = self.tools
            
            # 打印工具的详细定义
            self.print_tools_definition()
            
            return MCPToolResult(
                success=True,
                data={
                    "tools_count": len(available_tools),
                    "tools": [tool.name for tool in available_tools]
                }
            )
            
        except Exception as e:
            error_msg = f"MCP 初始化失败: {str(e)}"
            print(f"❌ {error_msg}")
            return MCPToolResult(success=False, error=error_msg)
    
    def print_tools_definition(self):
        """打印工具定义的详细信息"""
        if not self.tools:
            return
            
        print(f"\n🔧 工具定义详情:")
        print("=" * 50)
        
        tools_json = []
        for tool in self.tools:
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                }
            }
            
            # 尝试获取参数 schema
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    # 检查 args_schema 的类型
                    if hasattr(tool.args_schema, 'model_json_schema'):
                        # Pydantic 模型
                        schema = tool.args_schema.model_json_schema()
                        tool_def["function"]["parameters"] = schema
                    elif isinstance(tool.args_schema, dict):
                        # 已经是字典格式的 schema
                        tool_def["function"]["parameters"] = tool.args_schema
                    else:
                        # 尝试其他方式获取 schema
                        schema = getattr(tool.args_schema, 'schema', None)
                        if schema:
                            tool_def["function"]["parameters"] = schema
                        else:
                            print(f"⚠️ 无法识别工具 {tool.name} 的参数 schema 格式: {type(tool.args_schema)}")
                except Exception as e:
                    print(f"⚠️ 获取工具 {tool.name} 的参数 schema 失败: {e}")
            
            tools_json.append(tool_def)
            
            print(f"\n📋 工具: {tool.name}")
            print(f"描述: {tool.description}")
            if "parameters" in tool_def["function"]:
                print(f"参数 Schema:")
                print(json.dumps(tool_def["function"]["parameters"], indent=2, ensure_ascii=False))
        
        print(f"\n📊 完整工具定义 JSON:")
        print(json.dumps(tools_json, indent=2, ensure_ascii=False))
        print("=" * 50)
    
    def create_agent(self) -> None:
        """创建 LangChain Agent"""
        if not self.tools:
            raise ValueError("请先初始化 MCP 工具")
        
        # 创建 Agent 提示模板（针对数学工具优化）
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个智能数学助手，可以使用数学工具来进行计算。你可以进行加法、乘法、计算矩形面积、生成斐波那契数列等操作。请用中文回答用户的数学问题。"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        # 创建 Agent
        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        self.agent = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            callbacks=[self.interaction_logger]  # 添加交互日志记录器
        )
        print("✅ 创建了数学 OpenAI Tools Agent（支持 JSON schema，已启用详细交互日志）")
    
    async def run_query(self, query: str) -> Dict[str, Any]:
        """
        运行查询
        
        :param query: 用户查询
        :return: 查询结果
        """
        if not self.agent:
            raise ValueError("请先创建 Agent")
        
        try:
            print(f"\n❓ 查询: {query}")
            print("🚀 开始执行查询...")
            print()
            
            # 运行 Agent（使用异步调用）
            result = await self.agent.ainvoke(
                {"input": query},
                config={"callbacks": [self.interaction_logger]}
            )
            
            print(f"\n🎯 最终结果:")
            print(f"输出: {result.get('output', 'N/A')}")
            
            return {
                "success": True,
                "query": query,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"查询执行失败: {str(e)}"
            print(f"🔍 详细错误信息: {e}")
            return {
                "success": False,
                "query": query,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
    
    async def cleanup(self):
        """清理资源"""
        try:
            await self.exit_stack.aclose()
            print("🧹 资源清理完成")
        except Exception as e:
            print(f"⚠️ 资源清理时出现警告: {e}")


# 数学工具的简单 MCP 服务器示例
class SimpleMathMCPServer:
    """简单的数学运算 MCP 服务器（用于演示）"""
    
    @staticmethod
    def create_server_script():
        """创建一个简单的 MCP 服务器脚本"""
        server_code = '''#!/usr/bin/env python3
"""
简单的数学 MCP 服务器
提供基本的数学计算功能
"""

import asyncio
from mcp.server.fastmcp import FastMCP

# 创建 MCP 服务器
mcp = FastMCP("Simple Math Server")

@mcp.tool()
def add(a: int, b: int) -> int:
    """将两个整数相加"""
    result = a + b
    print(f"📊 计算: {a} + {b} = {result}")
    return result

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """将两个整数相乘"""
    result = a * b
    print(f"📊 计算: {a} × {b} = {result}")
    return result

@mcp.tool()
def calculate_area(length: float, width: float) -> float:
    """计算矩形面积"""
    area = length * width
    print(f"📊 计算矩形面积: {length} × {width} = {area} 平方米")
    return area

@mcp.tool()
def fibonacci(n: int) -> list:
    """生成斐波那契数列的前n项"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    
    print(f"📊 生成斐波那契数列前 {n} 项: {fib}")
    return fib

@mcp.tool()
def power(base: int, exponent: int) -> int:
    """计算幂次方"""
    result = base ** exponent
    print(f"📊 计算: {base}^{exponent} = {result}")
    return result

if __name__ == "__main__":
    print("🚀 启动数学 MCP 服务器...")
    mcp.run()
'''
        
        with open("math_mcp_server.py", "w", encoding="utf-8") as f:
            f.write(server_code)
        
        print("📝 已创建增强版 math_mcp_server.py")
        return "math_mcp_server.py"


async def main():
    """主函数 - 演示完整的 MCP + LangChain 集成"""
    
    # 创建演示实例
    demo = MCPLangChainDemo()
    
    try:
        # 初始化 MCP 连接（使用数学服务器）
        result = await demo.initialize_mcp()
        
        if not result.success:
            print(f"❌ MCP 初始化失败: {result.error}")
            return
        
        # 创建 Agent
        demo.create_agent()
        
        # 测试查询列表（数学相关）
        test_queries = [
            "计算 15 + 27"
        ]
        
        print("\n🧪 开始测试:")
        print("-" * 30)
        
        # 执行测试查询
        for query in test_queries:
            result = await demo.run_query(query)
            
            if result["success"]:
                print(f"💬 回答: {result['result']['output']}")
            else:
                print(f"💬 回答: 查询失败: {result['error']}")
            
            print()  # 空行分隔
        
        print("🎉 演示完成!")
        print("\n" + "="*60)
        print("📋 交互日志说明:")
        print("- 每次 LLM 交互都有详细的开始/结束标记")
        print("- 🔧 表示工具调用请求和执行")
        print("- 📊 完整请求 JSON 包含了所有工具定义")
        print("- 🎯 Agent 动作展示了决策过程")
        print("- 💬 最终响应是用户看到的结果")
        print("="*60)
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        
    finally:
        # 清理资源
        await demo.cleanup()


def run_demo():
    """运行演示的便捷函数"""
    asyncio.run(main())


if __name__ == "__main__":
    run_demo()
