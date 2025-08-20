"""
LangGraph 流式人机交互演示 - 支持实时打断和上下文更新

这个演示展示了如何在 LLM 输出过程中实现：
1. 流式输出
2. 用户实时打断
3. 上下文动态更新
4. 无缝恢复执行

基于 LangGraph 官方的 interrupt() 和 Command(resume=...) API
"""

import os
import asyncio
import threading
import time
from typing import Annotated, Dict, Any, List, Optional
from typing_extensions import TypedDict
from queue import Queue, Empty

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class StreamingInterruptState(TypedDict):
    """
    流式人机交互状态定义
    
    包含了整个流式交互过程中需要的所有状态：
    - user_input: 用户输入
    - ai_response: AI的回复
    - conversation_history: 对话历史
    - interrupt_requested: 是否请求了中断
    - user_interrupt: 用户中断的消息
    - streaming_content: 流式输出的内容
    - context_updated: 上下文是否已更新
    """
    user_input: str
    ai_response: str
    conversation_history: List[Dict[str, str]]
    interrupt_requested: bool
    user_interrupt: str
    streaming_content: str
    context_updated: bool


class StreamingInterruptDemo:
    """
    流式人机交互演示类
    
    实现了以下核心功能：
    1. 流式输出LLM响应
    2. 在输出过程中检测用户打断
    3. 根据用户输入更新上下文
    4. 无缝恢复或重新开始对话
    """
    
    def __init__(self):
        """初始化演示实例"""
        logger.info("初始化 StreamingInterruptDemo...")
        
        # 初始化大语言模型
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            streaming=True  # 启用流式输出
        )
        
        # 创建对话提示模板
        self.chat_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能助手，正在与用户进行对话。
你的回复会以流式方式输出，用户可能在你回复过程中打断你。
如果用户打断了你，请根据用户的新输入调整你的回复。

对话历史：
{conversation_history}

当前用户输入：{user_input}

请提供有用、详细的回复。如果用户提到了新的话题或问题，请相应地调整你的回复内容。"""),
        ])
        
        # 创建更新上下文的提示模板
        self.context_update_prompt = ChatPromptTemplate.from_messages([
            ("system", """用户在你回复过程中打断了你，并提供了新的信息或问题。
请根据用户的打断信息，重新组织你的回复。

原始用户输入：{original_input}
对话历史：{conversation_history}
你正在输出的内容：{streaming_content}
用户打断的消息：{user_interrupt}

请提供一个新的、更合适的回复，考虑用户的打断和新的上下文。"""),
        ])
        
        # 创建检查点保存器
        self.checkpointer = MemorySaver()
        
        # 创建工作流图
        self.workflow = self._create_workflow()
        
        # 用户输入队列（用于异步接收用户打断）
        self.user_input_queue = Queue()
        self.interrupt_event = threading.Event()
        
        logger.info("流式中断工作流创建完成")
    
    async def streaming_response_node(self, state: StreamingInterruptState) -> Dict:
        """
        流式响应节点
        
        生成流式AI回复，同时监听用户打断
        """
        try:
            logger.info("开始流式响应...")
            
            # 构建对话历史字符串
            history_str = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in state.get("conversation_history", [])
            ])
            
            # 创建响应链
            response_chain = self.chat_prompt | self.llm
            
            # 开始流式生成
            streaming_content = ""
            interrupt_detected = False
            user_interrupt_message = ""
            
            print(f"\n🤖 AI正在回复: ", end="", flush=True)
            print(f"\n💡 提示: 您可以直接输入新消息并按回车来打断AI回复")
            
            # 重置中断事件和队列
            self.interrupt_event.clear()
            while not self.user_input_queue.empty():
                try:
                    self.user_input_queue.get_nowait()
                except Empty:
                    break
            
            # 启动用户输入监听线程
            input_thread = threading.Thread(target=self._listen_for_user_input, daemon=True)
            input_thread.start()
            
            # 流式生成响应
            async for chunk in response_chain.astream({
                "conversation_history": history_str,
                "user_input": state["user_input"]
            }):
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    streaming_content += content
                    print(content, end="", flush=True)
                    
                    # 检查是否有用户打断
                    if self.interrupt_event.is_set():
                        try:
                            user_interrupt_message = self.user_input_queue.get_nowait()
                            interrupt_detected = True
                            # 不在这里打印，因为监听线程已经打印了
                            break
                        except Empty:
                            pass
                    
                    # 添加小延迟以模拟真实的流式输出，同时给中断检测更多机会
                    await asyncio.sleep(0.1)
            
            print()  # 换行
            
            if interrupt_detected:
                # 用户打断了，需要处理中断
                print("🔄 检测到用户打断，正在处理...")
                
                # 直接返回中断状态，不使用 interrupt() 函数
                # 因为我们要在应用层处理中断，而不是在图执行层
                return {
                    "ai_response": streaming_content,
                    "streaming_content": streaming_content,
                    "interrupt_requested": True,
                    "user_interrupt": user_interrupt_message,
                    "context_updated": False,
                    "interrupt_data": {
                        "type": "user_interrupt",
                        "original_input": state["user_input"],
                        "streaming_content": streaming_content,
                        "user_interrupt": user_interrupt_message,
                        "conversation_history": state.get("conversation_history", [])
                    }
                }
            else:
                # 正常完成回复
                return {
                    "ai_response": streaming_content,
                    "streaming_content": streaming_content,
                    "interrupt_requested": False,
                    "user_interrupt": "",
                    "context_updated": False
                }
                
        except Exception as e:
            logger.error(f"流式响应节点出错: {str(e)}")
            return {
                "ai_response": f"抱歉，生成回复时出现错误: {str(e)}",
                "streaming_content": "",
                "interrupt_requested": False,
                "user_interrupt": "",
                "context_updated": False
            }
    
    async def context_update_node(self, state: StreamingInterruptState) -> Dict:
        """
        上下文更新节点
        
        根据用户打断信息更新上下文并生成新的回复
        """
        try:
            logger.info("更新上下文并生成新回复...")
            
            # 构建对话历史字符串
            history_str = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in state.get("conversation_history", [])
            ])
            
            # 创建上下文更新链
            update_chain = self.context_update_prompt | self.llm
            
            # 生成新的回复
            result = await update_chain.ainvoke({
                "original_input": state["user_input"],
                "conversation_history": history_str,
                "streaming_content": state.get("streaming_content", ""),
                "user_interrupt": state.get("user_interrupt", "")
            })
            
            new_response = result.content if hasattr(result, 'content') else str(result)
            
            print(f"\n🔄 基于用户打断生成的新回复:")
            print(f"💬 {new_response}")
            
            return {
                "ai_response": new_response,
                "context_updated": True,
                "interrupt_requested": False
            }
            
        except Exception as e:
            logger.error(f"上下文更新节点出错: {str(e)}")
            return {
                "ai_response": f"更新上下文时出现错误: {str(e)}",
                "context_updated": True,
                "interrupt_requested": False
            }
    
    def conversation_update_node(self, state: StreamingInterruptState) -> Dict:
        """
        对话更新节点
        
        更新对话历史
        """
        conversation_history = state.get("conversation_history", []).copy()
        
        # 添加用户输入到历史
        conversation_history.append({
            "role": "user", 
            "content": state["user_input"]
        })
        
        # 添加AI回复到历史
        conversation_history.append({
            "role": "assistant", 
            "content": state["ai_response"]
        })
        
        # 如果有用户打断，也添加到历史
        if state.get("user_interrupt"):
            conversation_history.append({
                "role": "user", 
                "content": f"[打断] {state['user_interrupt']}"
            })
        
        return {
            "conversation_history": conversation_history
        }
    
    def decide_next_step(self, state: StreamingInterruptState) -> str:
        """
        决定下一步操作
        
        基于当前状态决定是否需要更新上下文
        """
        if state.get("interrupt_requested", False) and not state.get("context_updated", False):
            return "context_update"
        else:
            return "conversation_update"
    
    def _listen_for_user_input(self):
        """
        监听用户输入的后台线程函数
        持续监听用户输入，支持实时打断
        """
        import select
        import sys
        import tty
        import termios
        
        try:
            # 保存原始终端设置
            if sys.stdin.isatty():
                old_settings = termios.tcgetattr(sys.stdin.fileno())
                tty.setraw(sys.stdin.fileno())
            
            input_buffer = ""
            
            while not self.interrupt_event.is_set():
                try:
                    # 使用select检查是否有输入可用
                    if hasattr(select, 'select'):
                        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                        if ready:
                            # 读取单个字符
                            char = sys.stdin.read(1)
                            
                            if char == '\r' or char == '\n':  # 回车键
                                if input_buffer.strip():
                                    self.user_input_queue.put(input_buffer.strip())
                                    self.interrupt_event.set()
                                    print(f"\n\n⚠️  检测到用户打断: {input_buffer.strip()}")
                                    break
                                input_buffer = ""
                            elif char == '\x7f' or char == '\b':  # 退格键
                                if input_buffer:
                                    input_buffer = input_buffer[:-1]
                                    # 清除字符显示
                                    print('\b \b', end='', flush=True)
                            elif char.isprintable():  # 可打印字符
                                input_buffer += char
                                print(char, end='', flush=True)
                            elif char == '\x03':  # Ctrl+C
                                break
                    else:
                        # 如果不支持select，使用简单的阻塞input
                        time.sleep(0.1)
                        
                except (KeyboardInterrupt, EOFError):
                    break
                except Exception as e:
                    logger.debug(f"输入监听异常: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"设置终端模式失败: {e}")
        finally:
            # 恢复原始终端设置
            try:
                if sys.stdin.isatty() and 'old_settings' in locals():
                    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
            except:
                pass
    
    def _create_workflow(self) -> StateGraph:
        """
        创建流式中断工作流图
        """
        workflow = StateGraph(StreamingInterruptState)
        
        # 添加节点
        workflow.add_node("streaming_response", self.streaming_response_node)
        workflow.add_node("context_update", self.context_update_node)
        workflow.add_node("conversation_update", self.conversation_update_node)
        
        # 添加边
        workflow.add_edge(START, "streaming_response")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "streaming_response",
            self.decide_next_step,
            {
                "context_update": "context_update",
                "conversation_update": "conversation_update"
            }
        )
        
        workflow.add_edge("context_update", "conversation_update")
        workflow.add_edge("conversation_update", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    async def run_conversation(self, user_input: str, thread_id: str = "default") -> Dict[str, Any]:
        """
        运行对话
        
        支持流式输出和用户打断
        """
        # 重置中断状态
        self.interrupt_event.clear()
        while not self.user_input_queue.empty():
            try:
                self.user_input_queue.get_nowait()
            except Empty:
                break
        
        # 创建初始状态
        config = {"configurable": {"thread_id": thread_id}}
        
        # 获取当前对话历史
        try:
            current_state = self.workflow.get_state(config)
            conversation_history = current_state.values.get("conversation_history", []) if current_state.values else []
        except:
            conversation_history = []
        
        inputs = StreamingInterruptState(
            user_input=user_input,
            ai_response="",
            conversation_history=conversation_history,
            interrupt_requested=False,
            user_interrupt="",
            streaming_content="",
            context_updated=False
        )
        
        result_steps = []
        
        try:
            # 运行工作流
            async for event in self.workflow.astream(inputs, config):
                for k, v in event.items():
                    if k != "__end__":
                        result_steps.append({k: v})
                        
                        # 检查是否遇到了interrupt
                        if k == "streaming_response" and v.get("interrupt_requested"):
                            print("\n🔄 工作流检测到用户打断，准备处理...")
                            interrupt_data = v.get("interrupt_data", {})
                            return {
                                "status": "interrupted",
                                "thread_id": thread_id,
                                "interrupt_data": {
                                    "original_input": interrupt_data.get("original_input", user_input),
                                    "streaming_content": interrupt_data.get("streaming_content", v.get("streaming_content", "")),
                                    "user_interrupt": interrupt_data.get("user_interrupt", v.get("user_interrupt", ""))
                                },
                                "steps": result_steps
                            }
            
            return {
                "status": "completed",
                "thread_id": thread_id,
                "steps": result_steps
            }
            
        except Exception as e:
            logger.error(f"运行对话时出错: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "thread_id": thread_id,
                "steps": result_steps
            }
    
    async def resume_conversation(self, thread_id: str, user_interrupt: str) -> Dict[str, Any]:
        """
        恢复被中断的对话
        
        根据用户打断信息更新上下文并继续
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            # 使用Command恢复执行
            result_steps = []
            async for event in self.workflow.astream(
                Command(resume={
                    "type": "user_interrupt_processed",
                    "user_interrupt": user_interrupt
                }), 
                config
            ):
                for k, v in event.items():
                    if k != "__end__":
                        result_steps.append({k: v})
            
            return {
                "status": "resumed",
                "thread_id": thread_id,
                "steps": result_steps
            }
            
        except Exception as e:
            logger.error(f"恢复对话时出错: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "thread_id": thread_id
            }


async def interactive_streaming_demo():
    """
    交互式流式演示
    
    展示实时打断功能
    """
    print("🎯 流式人机交互演示 - 支持实时打断")
    print("💡 提示: 在AI回复过程中，您可以输入新的消息来打断AI")
    print("输入 'quit' 退出")
    print("="*60)
    
    demo = StreamingInterruptDemo()
    thread_id = "interactive_demo"
    
    while True:
        try:
            user_input = input("\n👤 您: ").strip()
            if user_input.lower() in ['quit', 'exit', '退出']:
                break
            
            if not user_input:
                continue
            
            print(f"\n🔄 处理中...")
            print(f"💡 重要提示: 当AI开始回复时，您可以直接输入新消息并按回车来实时打断!")
            
            # 运行对话
            result = await demo.run_conversation(user_input, thread_id)
            
            if result["status"] == "interrupted":
                print(f"\n⚠️  对话被中断!")
                print(f"📝 原始输入: {user_input}")
                print(f"🔄 已输出内容: {result['interrupt_data']['streaming_content']}")
                print(f"💬 用户打断: {result['interrupt_data']['user_interrupt']}")
                
                # 恢复对话
                print("\n🔄 正在根据您的打断更新回复...")
                resume_result = await demo.resume_conversation(
                    thread_id, 
                    result['interrupt_data']['user_interrupt']
                )
                
                if resume_result["status"] == "resumed":
                    print("✅ 对话已恢复并更新!")
                else:
                    print(f"❌ 恢复对话失败: {resume_result.get('error', '未知错误')}")
            
            elif result["status"] == "completed":
                print("\n✅ 对话完成!")
            
            else:
                print(f"\n❌ 对话出错: {result.get('error', '未知错误')}")
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            logger.error(f"交互演示出错: {str(e)}")
            print(f"❌ 错误: {e}")


async def simple_demo():
    """
    简单演示
    
    展示基本的流式输出功能
    """
    print("🚀 简单流式演示")
    print("="*50)
    
    demo = StreamingInterruptDemo()
    
    test_inputs = [
        "请介绍一下人工智能的发展历史",
        "什么是机器学习？它有哪些应用？",
        "请详细解释深度学习的工作原理"
    ]
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n📝 测试 {i}: {user_input}")
        print("-" * 50)
        
        try:
            result = await demo.run_conversation(user_input, f"demo_thread_{i}")
            
            if result["status"] == "completed":
                print(f"\n✅ 测试 {i} 完成!")
            else:
                print(f"\n❌ 测试 {i} 失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            logger.error(f"简单演示出错: {str(e)}")
            print(f"❌ 测试 {i} 出错: {e}")


async def main():
    """主函数"""
    print("选择演示模式:")
    print("1. 简单演示 (展示基本流式输出)")
    print("2. 交互式演示 (支持实时打断)")
    
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "1":
        await simple_demo()
    elif choice == "2":
        await interactive_streaming_demo()
    else:
        print("无效选择，运行简单演示...")
        await simple_demo()


if __name__ == "__main__":
    asyncio.run(main())
