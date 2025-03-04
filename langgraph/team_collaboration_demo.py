"""
这个示例展示了如何使用 LangGraph 实现一个简单的多智能体协作系统：
1. 如何定义多个智能体角色
2. 如何实现智能体之间的协作
3. 如何管理团队工作流程
4. 如何组织最终输出

工作流程：
1. 接收任务
2. 研究员收集和分析信息
3. 作家根据研究结果撰写内容
4. 审核员审查并提供修改建议
5. 根据反馈决定：
   - 如果通过审核，完成任务
   - 如果需要修改，返回相应步骤
"""

from typing import Dict, Any, TypedDict, List, Annotated
from typing_extensions import TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from dotenv import load_dotenv
import os

# 加载环境变量配置
load_dotenv()

class TeamState(TypedDict):
    """
    团队协作状态定义
    
    包含了整个协作过程中需要的所有状态：
    - task: 团队任务
    - research: 研究结果
    - draft: 初稿内容
    - feedback: 审核反馈
    - final_output: 最终输出
    - steps: 执行步骤的历史记录
    """
    task: str
    research: str
    draft: str
    feedback: str
    final_output: str
    steps: List[Dict]

class TeamCollaborationDemo:
    """
    团队协作演示类
    
    展示了如何使用 LangGraph 构建一个多智能体协作系统。
    系统包含三个智能体：
    1. 研究员：收集和分析信息
    2. 作家：组织和撰写内容
    3. 审核员：审查和改进内容
    """
    
    def __init__(self):
        """
        初始化演示实例
        
        设置：
        1. 初始化大语言模型
        2. 创建各角色的提示模板
        3. 创建工作流图
        """
        # 初始化大语言模型
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        # 创建研究员提示模板
        self.researcher_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的研究员。
你的任务是收集和分析与给定主题相关的信息。
请提供详细的研究发现，包括关键点和重要数据。"""),
            ("user", "请研究以下主题：{task}")
        ])
        
        # 创建作家提示模板
        self.writer_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的内容作家。
根据研究结果，创作清晰、结构良好的内容。
注重逻辑性和可读性。"""),
            ("user", "任务：{task}\n\n研究结果：{research}")
        ])
        
        # 创建审核员提示模板
        self.reviewer_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个严格的内容审核员。
审查内容的准确性、完整性和质量。
如果内容令人满意，请回复"通过"。
否则，请提供具体的改进建议。"""),
            ("user", "任务：{task}\n\n当前内容：{draft}")
        ])
        
        # 创建工作流图
        self.workflow = self._create_workflow()
    
    async def research_step(self, state: TeamState) -> Dict:
        """研究步骤"""
        try:
            # 使用 llm 直接处理而不是使用 prompt
            result = await self.llm.ainvoke([
                {"role": "system", "content": """你是一个专业的研究员。
你的任务是收集和分析与给定主题相关的信息。
请提供详细的研究发现，包括关键点和重要数据。"""},
                {"role": "user", "content": f"请研究以下主题：{state['task']}"}
            ])
            return {"research": result.content}  # 直接使用 content
        except Exception as e:
            print(f"研究步骤出错: {str(e)}")
            return {"research": "无法完成研究。"}
    
    async def write_step(self, state: TeamState) -> Dict:
        """写作步骤"""
        try:
            # 使用 llm 直接处理
            result = await self.llm.ainvoke([
                {"role": "system", "content": """你是一个专业的内容作家。
根据研究结果，创作清晰、结构良好的内容。
注重逻辑性和可读性。"""},
                {"role": "user", "content": f"任务：{state['task']}\n\n研究结果：{state['research']}"}
            ])
            return {"draft": result.content}  # 直接使用 content
        except Exception as e:
            print(f"写作步骤出错: {str(e)}")
            return {"draft": "无法完成写作。"}
    
    async def review_step(self, state: TeamState) -> Dict:
        """审核步骤"""
        try:
            # 使用 llm 直接处理
            result = await self.llm.ainvoke([
                {"role": "system", "content": """你是一个严格的内容审核员。
审查内容的准确性、完整性和质量。
如果内容令人满意，请回复"通过"。
否则，请提供具体的改进建议。"""},
                {"role": "user", "content": f"任务：{state['task']}\n\n当前内容：{state['draft']}"}
            ])
            feedback = result.content
            
            if "通过" in feedback:
                return {
                    "feedback": feedback,
                    "final_output": state["draft"]  # 使用已经审核通过的草稿作为最终输出
                }
            return {"feedback": feedback}
        except Exception as e:
            print(f"审核步骤出错: {str(e)}")
            return {"feedback": "无法完成审核。"}
    
    def should_continue(self, state: TeamState) -> str:
        """
        决定工作流程去向
        
        根据当前状态决定：
        1. 如果审核通过，结束工作流
        2. 如果需要修改，返回写作步骤
        3. 如果执行次数过多，结束工作流
        """
        if "final_output" in state:
            return END
        if len(state.get("steps", [])) >= 5:
            return END
        return "writer"
    
    def _create_workflow(self) -> StateGraph:
        """
        创建工作流图
        
        定义了团队协作的流程：
        1. 研究 -> 写作 -> 审核
        2. 根据审核结果决定是否需要修改
        3. 最终输出成果
        """
        workflow = StateGraph(TeamState)
        
        # 添加节点 - 使用更具体的节点名称避免与状态键冲突
        workflow.add_node("researcher", self.research_step)  # 改为 "researcher"
        workflow.add_node("writer", self.write_step)        # 改为 "writer"
        workflow.add_node("reviewer", self.review_step)     # 改为 "reviewer"
        
        # 添加边 - 更新边的连接关系
        workflow.add_edge(START, "researcher")
        workflow.add_edge("researcher", "writer")
        workflow.add_edge("writer", "reviewer")
        
        # 添加条件边 - 更新节点名称
        workflow.add_conditional_edges(
            "reviewer",
            self.should_continue,
            {END: END, "writer": "writer"}  # 更新为新的节点名
        )
        
        return workflow.compile()
    
    async def run(self, task: str) -> Dict[str, Any]:
        """
        运行工作流
        
        执行团队协作流程：
        1. 初始化任务
        2. 执行工作流
        3. 记录过程
        4. 返回结果
        """
        # 创建初始状态
        inputs = TeamState(
            task=task,
            research="",
            draft="",
            feedback="",
            final_output="",
            steps=[]
        )
        
        steps = []
        final_output = "未能生成最终输出"  # 默认值
        
        async for event in self.workflow.astream(inputs):
            for k, v in event.items():
                if k != "__end__":
                    steps.append({k: v})
                    # 如果这个步骤包含了最终输出，就更新 final_output
                    if isinstance(v, dict) and "final_output" in v:
                        final_output = v["final_output"]
            inputs["steps"] = steps
        
        return {
            "task": task,
            "steps": steps,
            "final_output": final_output  # 直接使用保存的最终输出
        }

async def main():
    """
    主函数
    
    用于演示如何使用 TeamCollaborationDemo：
    1. 创建团队协作实例
    2. 定义示例任务
    3. 运行协作流程
    4. 展示执行结果
    """
    demo = TeamCollaborationDemo()
    
    # 测试任务
    tasks = [
        "解释量子计算的基本原理"    ]
    
    for task in tasks:
        print(f"\n任务: {task}")
        result = await demo.run(task)
        
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