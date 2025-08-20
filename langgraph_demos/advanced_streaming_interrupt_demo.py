"""
高级流式人机交互演示

这个演示展示了一个更实用的实现，包括：
1. 非阻塞用户输入监听
2. 更好的用户界面
3. 多线程安全的实现
4. 完整的错误处理
5. 会话管理

适合在实际应用中使用的版本
"""

import os  # 导入操作系统接口模块，用于访问环境变量
import asyncio  # 导入异步IO库，用于处理异步操作
import threading  # 导入线程模块，用于多线程编程
import time  # 导入时间模块，用于时间相关操作
import json  # 导入JSON模块，用于JSON数据处理
from typing import Annotated, Dict, Any, List, Optional, Callable  # 导入类型注解相关模块
from typing_extensions import TypedDict  # 导入扩展类型注解，用于定义结构化字典类型
from queue import Queue, Empty  # 导入队列模块，用于线程间通信
from datetime import datetime  # 导入日期时间模块，用于时间戳处理

from langchain_core.prompts import ChatPromptTemplate  # 导入LangChain聊天提示模板
from langchain_core.messages import HumanMessage, AIMessage  # 导入LangChain消息类型
from langchain_openai import ChatOpenAI  # 导入OpenAI聊天模型
from langgraph.graph import StateGraph, START, END  # 导入LangGraph状态图和节点常量
from langgraph.checkpoint.memory import MemorySaver  # 导入内存检查点保存器
from langgraph.types import Command, interrupt  # 导入LangGraph中断和命令类型
from dotenv import load_dotenv  # 导入环境变量加载器
import logging  # 导入日志模块

# 配置日志系统，设置日志级别为INFO，定义日志格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)  # 创建当前模块的日志记录器

# 加载.env文件中的环境变量
load_dotenv()


class AdvancedStreamingState(TypedDict):
    """高级流式交互状态 - 定义工作流中传递的状态结构"""
    user_input: str  # 用户输入的消息内容
    ai_response: str  # AI生成的回复内容
    conversation_history: List[Dict[str, Any]]  # 对话历史记录列表
    interrupt_requested: bool  # 是否请求了中断标志
    user_interrupt: str  # 用户中断时输入的消息
    streaming_content: str  # 流式输出过程中已生成的内容
    context_updated: bool  # 上下文是否已更新标志
    session_id: str  # 会话ID标识符
    timestamp: str  # 时间戳
    metadata: Dict[str, Any]  # 元数据字典，存储额外信息


class InterruptHandler:
    """中断处理器 - 负责管理用户输入和中断逻辑的核心类"""
    
    def __init__(self):
        """初始化中断处理器"""
        self.input_queue = Queue()  # 创建线程安全的队列，用于存储用户输入
        self.interrupt_event = threading.Event()  # 创建线程事件，用于通知中断发生
        self.listening = False  # 监听状态标志
        self.input_thread = None  # 输入监听线程引用
        self._stop_listening = threading.Event()  # 停止监听的事件信号
    
    def start_listening(self):
        """开始监听用户输入"""
        if self.listening:  # 如果已经在监听，直接返回
            return
        
        self.listening = True  # 设置监听状态为True
        self._stop_listening.clear()  # 清除停止监听信号
        self.interrupt_event.clear()  # 清除中断事件信号
        
        # 清空输入队列中的旧数据
        while not self.input_queue.empty():  # 循环直到队列为空
            try:
                self.input_queue.get_nowait()  # 非阻塞地获取并丢弃队列中的数据
            except Empty:  # 队列为空时抛出异常，跳出循环
                break
        
        # 启动后台监听线程
        self.input_thread = threading.Thread(target=self._listen_loop, daemon=True)  # 创建守护线程
        self.input_thread.start()  # 启动线程
    
    def stop_listening(self):
        """停止监听用户输入"""
        if not self.listening:  # 如果没有在监听，直接返回
            return
        
        self.listening = False  # 设置监听状态为False
        self._stop_listening.set()  # 发送停止监听信号
        
        # 等待监听线程结束
        if self.input_thread and self.input_thread.is_alive():  # 如果线程存在且还活着
            self.input_thread.join(timeout=1.0)  # 等待线程结束，最多等待1秒
    
    def check_interrupt(self) -> Optional[str]:
        """检查是否有用户中断"""
        if self.interrupt_event.is_set():  # 如果中断事件被设置
            try:
                user_input = self.input_queue.get_nowait()  # 非阻塞地从队列获取用户输入
                return user_input  # 返回用户输入内容
            except Empty:  # 队列为空时忽略异常
                pass
        return None  # 没有中断时返回None
    
    def _listen_loop(self):
        """监听循环（在后台线程中运行）"""
        print("\n💡 提示: 在AI回复过程中输入消息可以打断AI (按Enter确认)")
        
        while not self._stop_listening.is_set():
            try:
                import sys
                import platform
                
                if platform.system() == "Windows":
                    # Windows系统使用更可靠的输入方式
                    try:
                        import msvcrt
                        if msvcrt.kbhit():
                            chars = []
                            while msvcrt.kbhit():
                                char = msvcrt.getch().decode('utf-8', errors='ignore')
                                if char == '\r':  # 回车键
                                    break
                                elif char == '\b':  # 退格键
                                    if chars:
                                        chars.pop()
                                        print('\b \b', end='', flush=True)
                                elif ord(char) >= 32:  # 可打印字符
                                    chars.append(char)
                                    print(char, end='', flush=True)
                            
                            if chars or msvcrt.kbhit():  # 如果有输入或还有待读取的字符
                                user_input = ''.join(chars).strip()
                                if user_input:
                                    self.input_queue.put(user_input)
                                    self.interrupt_event.set()
                                    print()  # 换行
                                    break
                        time.sleep(0.1)
                    except ImportError:
                        # msvcrt不可用时的备用方案
                        time.sleep(0.1)
                else:
                    # Unix/Linux系统使用select
                    import select
                    if hasattr(select, 'select'):
                        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                        if ready and not self._stop_listening.is_set():
                            user_input = sys.stdin.readline().strip()
                            if user_input:
                                self.input_queue.put(user_input)
                                self.interrupt_event.set()
                                break
                    else:
                        time.sleep(0.1)
                    
            except Exception as e:
                logger.debug(f"监听输入时出错: {e}")
                time.sleep(0.1)


class AdvancedStreamingInterruptDemo:
    """高级流式人机交互演示类 - 核心功能实现类"""
    
    def __init__(self):
        """初始化演示实例"""
        logger.info("初始化 AdvancedStreamingInterruptDemo...")  # 记录初始化开始日志
        
        # 初始化大语言模型配置
        self.llm = ChatOpenAI(
            model="deepseek-chat",  # 指定使用的模型名称
            openai_api_key=os.getenv("LLM_API_KEY"),  # 从环境变量获取API密钥
            base_url=os.getenv("LLM_BASE_URL"),  # 从环境变量获取API基础URL
            streaming=True,  # 启用流式输出模式
            temperature=0.2  # 设置生成温度，较低值使输出更确定性
        )
        
        # 创建聊天提示模板 - 用于正常对话
        self.chat_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能助手，正在与用户进行流式对话。

对话规则：
1. 提供详细、有用的回复
2. 如果用户打断了你，请优雅地处理并根据新信息调整回复
3. 保持对话的连贯性和上下文

对话历史：
{conversation_history}

当前时间：{timestamp}
用户输入：{user_input}"""),  # 系统提示，定义AI的行为和上下文
        ])
        
        # 创建中断处理提示模板 - 用于处理用户打断后的回复
        self.interrupt_prompt = ChatPromptTemplate.from_messages([
            ("system", """用户在你回复过程中打断了你。请根据以下信息重新组织回复：

原始问题：{original_input}
已输出内容：{streaming_content}
用户打断：{user_interrupt}
对话历史：{conversation_history}

请根据用户的打断要求重新组织回复：
1. 如果用户说“简单点”，请用更简洁的方式回答原始问题
2. 如果用户说“详细点”，请提供更详细的信息
3. 如果用户提出了新问题，请回答新问题
4. 如果用户要求修正或补充，请相应调整内容

请提供一个完整的、符合用户要求的回复。"""),
        ])
        
        # 创建检查点保存器 - 用于保存工作流状态
        self.checkpointer = MemorySaver()  # 使用内存保存器存储状态
        
        # 创建工作流图
        self.workflow = self._create_workflow()  # 调用私有方法创建LangGraph工作流
        
        # 初始化中断处理器
        self.interrupt_handler = InterruptHandler()  # 创建中断处理器实例
        
        # 初始化会话管理字典
        self.sessions = {}  # 用于存储所有会话的信息
        
        logger.info("高级流式中断工作流创建完成")  # 记录初始化完成日志
    
    async def streaming_response_node(self, state: AdvancedStreamingState) -> Dict:
        """流式响应节点 - 负责生成流式AI回复并监听用户中断"""
        try:
            logger.info(f"开始为会话 {state['session_id']} 生成流式响应...")  # 记录开始生成响应的日志
            
            # 构建格式化的对话历史字符串
            history_str = self._format_conversation_history(state.get("conversation_history", []))
            
            # 创建LLM调用链：提示模板 + 大语言模型
            response_chain = self.chat_prompt | self.llm
            
            # 初始化流式生成相关变量
            streaming_content = ""  # 存储已生成的内容
            interrupt_detected = False  # 中断检测标志
            user_interrupt_message = ""  # 用户中断消息
            
            print(f"\n🤖 AI: ", end="", flush=True)  # 显示AI回复标识，不换行
            
            # 启动用户输入监听
            self.interrupt_handler.start_listening()  # 开始在后台监听用户输入
            
            try:
                # 开始流式生成AI响应
                async for chunk in response_chain.astream({  # 异步流式调用LLM
                    "conversation_history": history_str,  # 传入对话历史
                    "user_input": state["user_input"],  # 传入用户输入
                    "timestamp": state.get("timestamp", datetime.now().isoformat())  # 传入时间戳
                }):
                    if hasattr(chunk, 'content') and chunk.content:  # 检查chunk是否有内容
                        content = chunk.content  # 获取当前生成的内容片段
                        streaming_content += content  # 累积到完整内容中
                        print(content, end="", flush=True)  # 实时显示内容，立即刷新输出
                        
                        # 检查是否有用户中断
                        user_interrupt = self.interrupt_handler.check_interrupt()  # 检查中断队列
                        if user_interrupt:  # 如果检测到用户中断
                            user_interrupt_message = user_interrupt  # 保存中断消息
                            interrupt_detected = True  # 设置中断标志
                            print(f"\n\n⚠️  用户打断: {user_interrupt_message}")  # 显示中断信息
                            break  # 跳出生成循环
                        
                        # 控制流式输出速度，避免过快显示
                        await asyncio.sleep(0.03)  # 暂停30毫秒
            
            finally:
                # 无论如何都要停止监听用户输入
                self.interrupt_handler.stop_listening()  # 确保监听线程正确关闭
            
            print()  # 输出换行符，结束当前行
            
            if interrupt_detected:  # 如果检测到用户中断
                # 处理用户中断情况
                print("🔄 检测到用户打断，正在处理...")  # 提示用户中断被检测到
                
                # 直接返回中断状态，在应用层处理中断逻辑
                # 不使用interrupt()函数，避免复杂的异常处理
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
                        "conversation_history": state.get("conversation_history", []),
                        "timestamp": datetime.now().isoformat()
                    },
                    "metadata": {
                        "interrupted_at": datetime.now().isoformat(),
                        "interrupt_reason": "user_input"
                    }
                }
            else:
                # 正常完成流式生成
                return {
                    "ai_response": streaming_content,  # 完整的AI回复内容
                    "streaming_content": streaming_content,  # 流式内容副本
                    "interrupt_requested": False,  # 未请求中断
                    "user_interrupt": "",  # 无中断消息
                    "context_updated": False,  # 上下文无需更新
                    "metadata": {  # 元数据信息
                        "completed_at": datetime.now().isoformat(),  # 完成时间
                        "response_length": len(streaming_content)  # 回复内容长度
                    }
                }
                
        except Exception as e:  # 捕获所有异常
            logger.error(f"流式响应节点出错: {str(e)}")
            return {
                "ai_response": f"抱歉，生成回复时出现错误: {str(e)}",
                "streaming_content": "",
                "interrupt_requested": False,
                "user_interrupt": "",
                "context_updated": False,
                "metadata": {"error": str(e)}
            }
    
    async def context_update_node(self, state: AdvancedStreamingState) -> Dict:
        """上下文更新节点 - 根据用户中断更新AI回复"""
        try:
            logger.info(f"为会话 {state['session_id']} 更新上下文...")  # 记录开始更新上下文
            
            # 构建格式化的对话历史
            history_str = self._format_conversation_history(state.get("conversation_history", []))
            
            # 创建上下文更新调用链：中断提示模板 + LLM
            update_chain = self.interrupt_prompt | self.llm
            
            # 基于中断信息生成新的回复
            result = await update_chain.ainvoke({  # 异步调用LLM
                "original_input": state["user_input"],  # 原始用户输入
                "conversation_history": history_str,  # 对话历史
                "streaming_content": state.get("streaming_content", ""),  # 已生成的内容
                "user_interrupt": state.get("user_interrupt", "")  # 用户中断消息
            })
            
            # 提取生成的新回复内容
            new_response = result.content if hasattr(result, 'content') else str(result)
            
            # 显示更新后的回复
            print(f"\n🔄 基于您的打断生成的新回复:")  # 提示用户这是更新后的回复
            print(f"🤖 AI: {new_response}")  # 显示新的AI回复
            
            # 返回更新后的状态
            return {
                "ai_response": new_response,  # 新生成的AI回复
                "context_updated": True,  # 标记上下文已更新
                "interrupt_requested": False,  # 重置中断请求标志
                "metadata": {  # 元数据信息
                    "context_updated_at": datetime.now().isoformat(),  # 更新时间
                    "update_reason": "user_interrupt"  # 更新原因
                }
            }
            
        except Exception as e:
            logger.error(f"上下文更新节点出错: {str(e)}")
            return {
                "ai_response": f"更新上下文时出现错误: {str(e)}",
                "context_updated": True,
                "interrupt_requested": False,
                "metadata": {"error": str(e)}
            }
    
    def conversation_update_node(self, state: AdvancedStreamingState) -> Dict:
        """对话更新节点 - 改进版"""
        conversation_history = state.get("conversation_history", []).copy()
        
        # 添加用户输入
        conversation_history.append({
            "role": "user",
            "content": state["user_input"],
            "timestamp": state.get("timestamp", datetime.now().isoformat())
        })
        
        # 添加AI回复
        conversation_history.append({
            "role": "assistant", 
            "content": state["ai_response"],
            "timestamp": datetime.now().isoformat(),
            "metadata": state.get("metadata", {})
        })
        
        # 如果有用户打断，添加打断信息
        if state.get("user_interrupt"):
            conversation_history.append({
                "role": "user",
                "content": state["user_interrupt"],
                "timestamp": datetime.now().isoformat(),
                "type": "interrupt"
            })
        
        # 限制历史长度（保留最近20条消息）
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        return {
            "conversation_history": conversation_history
        }
    
    def decide_next_step(self, state: AdvancedStreamingState) -> str:
        """决定工作流的下一步操作 - 路由决策函数"""
        if state.get("interrupt_requested", False) and not state.get("context_updated", False):
            # 如果请求了中断且上下文尚未更新，则进入上下文更新节点
            return "context_update"
        else:
            # 否则进入对话更新节点（正常流程或已完成上下文更新）
            return "conversation_update"
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """格式化对话历史为字符串 - 供LLM理解的格式"""
        if not history:  # 如果没有对话历史
            return "暂无对话历史"  # 返回提示信息
        
        formatted = []  # 存储格式化后的消息列表
        for msg in history[-10:]:  # 只处理最近10条消息，避免上下文过长
            role = msg.get("role", "unknown")  # 获取消息角色
            content = msg.get("content", "")  # 获取消息内容
            msg_type = msg.get("type", "")  # 获取消息类型（如中断消息）
            
            if msg_type == "interrupt":  # 如果是中断消息
                formatted.append(f"[用户打断] {content}")  # 特殊标记中断消息
            elif role == "user":  # 如果是用户消息
                formatted.append(f"用户: {content}")  # 格式化用户消息
            elif role == "assistant":  # 如果是助手消息
                formatted.append(f"助手: {content}")  # 格式化助手消息
        
        return "\n".join(formatted)  # 用换行符连接所有消息
    
    def _create_workflow(self) -> StateGraph:
        """创建高级流式中断工作流图 - 定义节点和连接关系"""
        workflow = StateGraph(AdvancedStreamingState)  # 创建状态图实例
        
        # 添加工作流节点
        workflow.add_node("streaming_response", self.streaming_response_node)  # 流式响应节点
        workflow.add_node("context_update", self.context_update_node)  # 上下文更新节点
        workflow.add_node("conversation_update", self.conversation_update_node)  # 对话更新节点
        
        # 添加起始边：从开始节点到流式响应节点
        workflow.add_edge(START, "streaming_response")  # 工作流从流式响应开始
        
        # 添加条件边：根据决策函数选择下一步
        workflow.add_conditional_edges(
            "streaming_response",  # 从流式响应节点出发
            self.decide_next_step,  # 使用决策函数判断下一步
            {  # 映射决策结果到目标节点
                "context_update": "context_update",  # 需要更新上下文
                "conversation_update": "conversation_update"  # 直接更新对话历史
            }
        )
        
        # 添加固定边：上下文更新后必须更新对话历史
        workflow.add_edge("context_update", "conversation_update")
        # 添加结束边：对话更新后结束工作流
        workflow.add_edge("conversation_update", END)
        
        # 编译工作流图并返回可执行实例
        return workflow.compile(checkpointer=self.checkpointer)  # 使用检查点保存器编译
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """创建新的对话会话 - 会话管理功能"""
        if not session_id:  # 如果未提供会话ID
            session_id = f"session_{int(time.time())}"  # 使用时间戳生成唯一ID
        
        # 在会话字典中记录新会话的信息
        self.sessions[session_id] = {
            "created_at": datetime.now().isoformat(),  # 会话创建时间
            "message_count": 0,  # 消息计数器，初始为0
            "last_activity": datetime.now().isoformat()  # 最后活动时间
        }
        
        return session_id  # 返回会话ID
    
    async def chat(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """进行对话 - 主要的聊天接口方法"""
        # 更新会话活动信息
        if session_id in self.sessions:  # 如果会话存在
            self.sessions[session_id]["message_count"] += 1  # 增加消息计数
            self.sessions[session_id]["last_activity"] = datetime.now().isoformat()  # 更新最后活动时间
        
        # 配置工作流的线程ID（用于状态持久化）
        config = {"configurable": {"thread_id": session_id}}
        
        # 获取当前会话的对话历史
        try:
            current_state = self.workflow.get_state(config)  # 从检查点获取状态
            conversation_history = current_state.values.get("conversation_history", []) if current_state.values else []
        except:  # 如果获取失败（如新会话）
            conversation_history = []  # 使用空的对话历史
        
        # 创建初始状态
        inputs = AdvancedStreamingState(
            user_input=user_input,
            ai_response="",
            conversation_history=conversation_history,
            interrupt_requested=False,
            user_interrupt="",
            streaming_content="",
            context_updated=False,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            metadata={}
        )
        
        result_steps = []
        
        try:
            # 运行工作流
            async for event in self.workflow.astream(inputs, config):
                for k, v in event.items():
                    if k != "__end__":
                        result_steps.append({k: v})
                        
                        # 检查是否遇到了中断
                        if k == "streaming_response" and v.get("interrupt_requested"):
                            return {
                                "status": "interrupted",
                                "session_id": session_id,
                                "interrupt_data": {
                                    "original_input": user_input,
                                    "streaming_content": v.get("streaming_content", ""),
                                    "user_interrupt": v.get("user_interrupt", "")
                                },
                                "steps": result_steps
                            }
            
            return {
                "status": "completed",
                "session_id": session_id,
                "steps": result_steps
            }
            
        except Exception as e:
            logger.error(f"对话出错: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "session_id": session_id,
                "steps": result_steps
            }
    
    async def resume_chat(self, session_id: str, user_interrupt: str) -> Dict[str, Any]:
        """恢复被中断的对话 - 基于中断上下文更新回复"""
        config = {"configurable": {"thread_id": session_id}}
        
        try:
            # 获取当前状态
            current_state = self.workflow.get_state(config)
            if not current_state or not current_state.values:
                # 如果没有状态，就当作新对话处理
                return await self.chat(user_interrupt, session_id)
            
            # 更新状态，设置中断信息
            state_values = current_state.values.copy()
            state_values["user_interrupt"] = user_interrupt
            state_values["interrupt_requested"] = True
            state_values["context_updated"] = False  # 重设上下文更新标志
            
            # 直接调用上下文更新节点
            context_result = await self.context_update_node(state_values)
            
            # 然后更新对话历史
            updated_state = state_values.copy()
            updated_state.update(context_result)
            conversation_result = self.conversation_update_node(updated_state)
            
            # 合并结果
            final_state = updated_state.copy()
            final_state.update(conversation_result)
            
            # 保存更新后的状态
            self.workflow.update_state(config, final_state)
            
            return {
                "status": "completed",
                "session_id": session_id,
                "ai_response": context_result.get("ai_response", ""),
                "steps": [
                    {"context_update": context_result},
                    {"conversation_update": conversation_result}
                ]
            }
            
        except Exception as e:
            logger.error(f"恢复对话出错: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "session_id": session_id
            }
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[str]:
        """列出所有会话"""
        return list(self.sessions.keys())


async def advanced_interactive_demo():
    """高级交互式演示 - 主要的用户交互入口函数"""
    # 显示演示介绍和功能特点
    print("🎯 高级流式人机交互演示")
    print("💡 功能特点:")
    print("   - 流式输出AI回复")  # 实时显示AI生成内容
    print("   - 实时用户打断")  # 支持在AI回复过程中打断
    print("   - 智能上下文更新")  # 根据用户打断调整回复
    print("   - 会话管理")  # 多会话支持
    print("   - 完整错误处理")  # 健壮的错误处理机制
    print("\n💡 使用说明:")
    print("   - 在AI回复过程中输入消息可以打断AI")  # 核心功能说明
    print("   - 输入 'new' 开始新会话")  # 会话管理命令
    print("   - 输入 'sessions' 查看所有会话")  # 会话列表命令
    print("   - 输入 'quit' 退出")  # 退出命令
    print("="*60)  # 分隔线
    
    # 创建演示实例和初始会话
    demo = AdvancedStreamingInterruptDemo()  # 实例化演示类
    current_session = demo.create_session()  # 创建默认会话
    
    print(f"🆕 已创建会话: {current_session}")  # 显示会话创建成功
    
    while True:
        try:
            user_input = input(f"\n👤 您 [{current_session}]: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                break
            elif user_input.lower() == 'new':
                current_session = demo.create_session()
                print(f"🆕 已创建新会话: {current_session}")
                continue
            elif user_input.lower() == 'sessions':
                sessions = demo.list_sessions()
                print(f"📋 当前会话列表: {sessions}")
                for sid in sessions:
                    info = demo.get_session_info(sid)
                    print(f"   {sid}: {info['message_count']} 条消息, 最后活动: {info['last_activity']}")
                continue
            elif not user_input:
                continue
            
            # 进行对话
            result = await demo.chat(user_input, current_session)
            
            if result["status"] == "interrupted":
                print(f"\n⚠️  对话被中断!")
                print(f"💬 用户打断: {result['interrupt_data']['user_interrupt']}")
                
                # 基于中断上下文更新回复
                print("\n🔄 正在根据您的打断更新回复...")
                resume_result = await demo.resume_chat(
                    current_session,
                    result['interrupt_data']['user_interrupt']
                )
                
                if resume_result["status"] == "completed":
                    # 不需要额外的成功提示，因为在context_update_node中已经显示了新回复
                    pass
                elif resume_result["status"] == "error":
                    print(f"❌ 更新回复失败: {resume_result.get('error', '未知错误')}")
            
            elif result["status"] == "completed":
                pass  # 正常完成，不需要额外提示
            
            else:
                print(f"\n❌ 对话出错: {result.get('error', '未知错误')}")
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            logger.error(f"演示出错: {str(e)}")
            print(f"❌ 错误: {e}")


async def main():
    """主函数 - 程序入口点"""
    await advanced_interactive_demo()  # 启动高级交互式演示


if __name__ == "__main__":  # 如果直接运行此文件
    asyncio.run(main())  # 使用asyncio运行异步主函数
