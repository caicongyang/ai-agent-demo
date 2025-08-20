from typing import Dict, Any, List, TypedDict
from typing_extensions import Annotated
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from dotenv import load_dotenv
import os
import logging





# 加载环境变量配置
load_dotenv()

"""
这个示例展示了如何使用 LangGraph 实现一个代理-监督者模式的系统：
1. 如何定义状态类型（AgentSupervisorState）
2. 如何创建代理和监督者节点
3. 如何实现节点间的交互和反馈循环
4. 如何处理条件分支和终止条件

工作流程：
1. 接收任务和上下文
2. 代理步骤：分析任务并提出行动方案
3. 监督者步骤：评估方案并给出反馈
4. 根据反馈决定：
   - 如果同意方案，则结束流程
   - 如果不同意，则返回代理步骤重新规划

这个例子展示了如何构建一个具有反馈循环的多智能体系统。
"""

class AgentSupervisorState(TypedDict):
    """
    代理-监督者状态定义
    """
    task: str
    context: str
    agent_action: str
    supervisor_feedback: str
    final_output: str
    steps: List[Dict]

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentSupervisorDemo:
    """
    代理-监督者演示类
    
    这个类展示了如何使用 LangGraph 构建一个具有监督机制的智能体系统。
    系统包含两个主要角色：
    1. 代理：负责分析任务并提出行动方案
    2. 监督者：负责评估方案并提供反馈
    """
    
    def __init__(self):
        """
        初始化演示实例
        
        设置：
        1. 初始化大语言模型
        2. 创建代理和监督者的提示模板
        3. 创建工作流图
        """
        logger.info("初始化 AgentSupervisorDemo...")
        
        # 初始化大语言模型
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        # 创建代理提示模板
        self.agent_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能代理，负责执行具体的任务。
你将收到一个任务描述和一些上下文信息。请根据这些信息，给出你的行动方案。
如果你认为信息不足以给出行动方案，请说明还需要什么信息。"""),
            ("user", "{task}\n\n上下文：{context}")
        ])
        
        # 创建监督者提示模板
        self.supervisor_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能监督者，负责协调和指导代理的行为。
你将收到代理的行动方案和当前的任务状态。请根据这些信息，给出你的反馈和建议。
如果你认为代理的行动方案可以接受，请说"同意"。否则，请给出具体的改进建议。"""),
            ("user", "任务：{task}\n\n代理的行动方案：{agent_action}\n\n当前状态：{state}")
        ])
        
        # 创建工作流图
        self.workflow = self._create_workflow()
        logger.info("工作流创建完成")
        
    async def agent_step(self, state: AgentSupervisorState) -> Dict:
        """
        代理行动步骤
        
        这是工作流的执行节点，负责：
        1. 接收任务和上下文信息
        2. 分析任务要求
        3. 提出具体的行动方案
        """
        logger.info(f"执行代理步骤，任务: {state['task']}")
        try:
            # 直接使用 LLM 而不是 prompt template
            result = await self.llm.ainvoke([
                {"role": "system", "content": """你是一个智能代理，负责执行具体的任务。
你将收到一个任务描述和一些上下文信息。请根据这些信息，给出你的行动方案。
如果你认为信息不足以给出行动方案，请说明还需要什么信息。"""},
                {"role": "user", "content": f"{state['task']}\n\n上下文：{state.get('context', '')}"}
            ])
            
            action = result.content
            logger.info(f"代理生成的行动方案: {action}")
            return {"agent_action": action}
            
        except Exception as e:
            logger.error(f"代理步骤出错: {str(e)}")
            return {"agent_action": "代理无法给出行动方案。"}
        
    async def supervisor_step(self, state: AgentSupervisorState) -> Dict:
        """监督者反馈步骤"""
        logger.info(f"执行监督步骤，评估代理行动: {state.get('agent_action', '')}")
        try:
            result = await self.llm.ainvoke([
                {"role": "system", "content": """你是一个智能监督者。
你的任务是评估代理的行动方案。
如果方案完整且合理，请回复"同意"。
如果方案有问题，请指出具体需要改进的地方。
请确保你的反馈清晰明确。"""},
                {"role": "user", "content": f"任务：{state['task']}\n\n代理的行动方案：{state['agent_action']}"}
            ])
            
            feedback = result.content
            logger.info(f"监督者的反馈: {feedback}")
            
            response = {"supervisor_feedback": feedback}
            if "同意" in feedback:
                response["final_output"] = state["agent_action"]
                logger.info(f"监督者同意方案，设置最终输出: {state['agent_action']}")
            
            return response
            
        except Exception as e:
            logger.error(f"监督步骤出错: {str(e)}")
            return {"supervisor_feedback": "监督者无法给出反馈。"}
        
    def should_end(self, state: AgentSupervisorState) -> str:
        """判断是否应该结束工作流"""
        logger.info(f"检查是否结束工作流，当前状态: {state}")
        # 检查 supervisor_feedback 中是否包含"同意"
        if state.get("supervisor_feedback") and "同意" in state["supervisor_feedback"]:
            logger.info("监督者同意方案，结束工作流")
            return END
        elif len(state.get("steps", [])) >= 10:
            logger.info("达到最大步骤数，结束工作流")
            return END
        else:
            logger.info("继续执行代理步骤")
            return "agent"
        
    def _create_workflow(self) -> StateGraph:
        """创建工作流图"""
        workflow = StateGraph(AgentSupervisorState)
        
        # 添加节点
        workflow.add_node("agent", self.agent_step)
        workflow.add_node("supervisor", self.supervisor_step)
        
        # 添加边
        workflow.add_edge(START, "agent")
        workflow.add_edge("agent", "supervisor")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "supervisor",
            self.should_end,
            {END: END, "agent": "agent"}
        )
        
        return workflow.compile()
    
    async def run(self, task: str, context: str = "") -> Dict[str, Any]:
        """运行工作流"""
        logger.info(f"开始执行任务: {task}")
        
        # 创建初始状态
        inputs = {
            "task": task,
            "context": context,
            "steps": [],
            "agent_action": "",
            "supervisor_feedback": "",
            "final_output": ""
        }
        
        steps = []
        final_output = None
        
        async for event in self.workflow.astream(inputs):
            for k, v in event.items():
                if k != "__end__":
                    logger.info(f"执行步骤 {k}: {v}")
                    steps.append({k: v})
                    if isinstance(v, dict):
                        logger.info(f"步骤 {k} 的结果: {v}")
                        if "final_output" in v:
                            final_output = v["final_output"]
                            logger.info(f"获取到最终输出: {final_output}")
            inputs["steps"] = steps
        
        result = {
            "task": task,
            "steps": steps,
            "final_output": final_output if final_output else "未能生成最终输出"
        }
        logger.info(f"任务执行完成，结果: {result}")
        return result

async def main():
    """主函数"""
    logger.info("开始运行演示...")
    demo = AgentSupervisorDemo()
    
    # 测试任务
    task = "帮我订一张从北京到上海的机票，下周二出发，尽量选择早上的航班。"
    context = "预算：2000元以内\n身份信息：张三，身份证号330124199001011234\n舱位偏好：经济舱"
    
    logger.info(f"执行任务: {task}")
    result = await demo.run(task, context)
    
    print(f"\n任务: {task}")
    print("\n执行步骤:")
    for step in result["steps"]:
        print(f"\n{list(step.keys())[0]}:")
        print(list(step.values())[0])
    
    print("\n最终输出:")
    print(result["final_output"])
    print("-" * 50)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 