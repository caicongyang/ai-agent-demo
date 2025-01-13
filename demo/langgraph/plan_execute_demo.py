from typing import Annotated, List, Tuple, Dict, Any, Union
from typing_extensions import TypedDict
import operator
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from langchain_community.utilities import SerpAPIWrapper
from langchain.tools import Tool
from langgraph.graph import StateGraph, END, START
from dotenv import load_dotenv
import os
import logging

# 加载环境变量配置
load_dotenv()

# 初始化搜索工具
def init_search_tool():
    """初始化搜索工具，添加错误处理和重试机制"""
    try:
        # 从环境变量获取 API key
        serpapi_key = os.getenv("SERPAPI_API_KEY")
        if not serpapi_key:
            logger.error("未找到 SERPAPI_API_KEY 环境变量")
            return None

        # 配置 SerpAPIWrapper
        search = SerpAPIWrapper(
            params={
                "engine": "google",
                "api_key": serpapi_key  # 通过 params 传入 API key
            }
        )

        # 创建搜索工具
        return Tool(
            name="Search",
            func=search.run,
            description="用于搜索最新信息的工具。输入应该是一个搜索查询。"
        )
    except Exception as e:
        logger.error(f"初始化搜索工具失败: {str(e)}")
        return None

# 初始化搜索工具
search_tool = init_search_tool()
tools = [search_tool] if search_tool else []

# 配置日志
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

"""
这个示例展示了如何使用 LangGraph 实现一个规划-执行模式的系统：
1. 如何定义状态类型（PlanExecuteState）
2. 如何实现规划、执行和重新规划的节点
3. 如何处理执行结果和动态调整计划
4. 如何管理执行流程和终止条件

工作流程：
1. 接收用户查询
2. 规划步骤：制定初始执行计划
3. 执行步骤：执行当前计划的一个步骤
4. 重新规划：根据执行结果调整计划
5. 循环执行直到：
   - 得到最终答案
   - 达到最大步骤数
   - 无法继续执行

这个例子展示了如何构建一个动态规划和执行的智能系统。
"""

class PlanExecuteState(TypedDict):
    """
    规划执行状态定义
    
    这是 LangGraph 工作流的状态类型定义，包含了整个执行过程中需要的所有状态：
    - input: 用户输入的查询
    - plan: 当前的执行计划
    - past_steps: 已执行步骤的历史记录
    - response: 最终的响应结果
    """
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str

class Plan(BaseModel):
    """
    执行计划模型
    
    Attributes:
        steps: 按顺序排列的执行步骤列表
    """
    steps: List[str] = Field(description="按顺序排列的执行步骤")

class Response(BaseModel):
    """
    用户响应模型
    
    Attributes:
        response: 响应内容
    """
    response: str

class Action(BaseModel):
    """
    执行动作模型，用于决定下一步操作
    
    Attributes:
        action: 可以是 Response（结束并返回结果）或 Plan（继续执行新的计划）
    """
    action: Union[Response, Plan] = Field(
        description="要执行的动作。如果要响应用户，使用 Response；如果需要继续使用工具获取答案，使用 Plan"
    )

class PlanExecuteDemo:
    """
    规划执行演示类
    
    这个类展示了如何使用 LangGraph 构建一个规划执行系统。
    系统包含三个主要步骤：
    1. 规划：制定执行计划
    2. 执行：执行计划中的步骤
    3. 重新规划：根据执行结果调整计划
    """
    
    def __init__(self):
        """
        初始化演示实例
        
        设置：
        1. 初始化大语言模型
        2. 创建规划和执行的提示模板
        3. 创建工作流图
        """
        logger.info("初始化 PlanExecuteDemo...")
        # 初始化大语言模型
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        # 创建解析器
        self.plan_parser = PydanticOutputParser(pydantic_object=Plan)
        self.action_parser = PydanticOutputParser(pydantic_object=Action)
        
        # 创建规划提示模板
        self.planner_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个任务规划专家。请根据用户目标制定执行计划。
请严格按照以下 JSON 格式返回，不要添加任何其他内容：

{{
    "steps": [
        "第一个步骤",
        "第二个步骤",
        "第三个步骤"
    ]
}}

计划应该：
1. 包含独立的任务步骤
2. 步骤清晰可执行
3. 避免冗余步骤
4. 最后一步应得出最终结论

示例查询：分析某公司股票表现
示例输出：
{{
    "steps": [
        "搜索该公司的股票代码和基本信息",
        "查询目标时期的股价数据",
        "分析股价走势和关键变动",
        "总结表现并给出结论"
    ]
}}

请确保：
1. 只返回 JSON 格式的内容
2. 不要添加任何解释或额外文本
3. 保持格式完全一致"""),
            ("user", "{input}")
        ])
        
        # 创建重新规划提示模板
        self.replanner_prompt = ChatPromptTemplate.from_template(
"""你是一个任务规划专家。请根据已执行步骤更新计划。

目标：{input}

原始计划：{plan}

已执行步骤：{past_steps}

请严格按照以下格式之一返回，不要添加任何其他内容：

如果已收集足够信息可以回答：
{{
    "action": {{
        "response": "这里是完整的回答..."
    }}
}}

如果需要继续执行：
{{
    "action": {{
        "steps": [
            "下一步具体任务1",
            "下一步具体任务2"
        ]
    }}
}}

请确保：
1. 只返回 JSON 格式的内容
2. 不要添加任何解释或额外文本
3. 保持格式完全一致""")
        
        # 创建工作流图
        self.workflow = self._create_workflow()
    
    async def execute_step(self, state: PlanExecuteState) -> Dict:
        """执行单个计划步骤"""
        plan = state["plan"]
        logger.info(f"开始执行步骤，当前计划: {plan}")
        
        task = plan[0]  # 获取当前要执行的任务
        logger.info(f"当前执行任务: {task}")
        
        # 检查是否需要搜索
        if ("搜索" in task.lower() or "查询" in task.lower()) and tools:
            try:
                # 执行搜索操作
                search_query = task.replace("搜索", "").replace("查询", "").strip()
                logger.info(f"执行搜索查询: {search_query}")
                
                search_result = tools[0].run(search_query)
                logger.info(f"搜索结果: {search_result}")
                result_content = f"搜索结果: {search_result}"
            except Exception as e:
                logger.error(f"搜索失败: {str(e)}")
                # 使用 LLM 作为备选方案
                result = await self.llm.ainvoke([
                    {"role": "system", "content": "由于搜索失败，请基于你的知识提供相关信息。"},
                    {"role": "user", "content": task}
                ])
                result_content = f"搜索失败，使用 AI 知识回答: {result.content}"
        else:
            # 使用 LLM 执行任务
            task_formatted = f"""对于以下计划：
{plan}

你需要执行第 1 步：{task}"""
            logger.info(f"发送给 LLM 的任务: {task_formatted}")
            
            result = await self.llm.ainvoke([
                {"role": "user", "content": task_formatted}
            ])
            result_content = result.content
            logger.info(f"LLM 执行结果: {result_content}")
        
        return {
            "past_steps": [(task, result_content)],
        }
    
    async def plan_step(self, state: PlanExecuteState) -> Dict:
        """创建初始执行计划"""
        logger.info(f"开始规划步骤，输入: {state['input']}")
        try:
            # 获取格式化的消息
            messages = await self.planner_prompt.aformat_messages(
                input=state["input"]
            )
            logger.info(f"格式化的提示消息: {messages}")
            
            # 使用 LLM 获取响应
            result = await self.llm.ainvoke(messages)
            logger.info(f"LLM 响应: {result.content}")

            # 尝试解析 JSON
            try:
                import json
                plan_dict = json.loads(result.content)
                if "steps" in plan_dict:
                    logger.info(f"成功解析计划步骤: {plan_dict['steps']}")
                    return {"plan": plan_dict["steps"]}
                else:
                    logger.warning("未找到 steps 字段，使用默认计划")
                    return {"plan": ["搜索平安银行2023年股价数据", "分析股价走势", "总结表现"]}
            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析失败: {e}")
                return {"plan": ["搜索平安银行2023年股价数据", "分析股价走势", "总结表现"]}

        except Exception as e:
            logger.error(f"规划步骤出错: {str(e)}")
            return {"plan": ["搜索平安银行2023年股价数据", "分析股价走势", "总结表现"]}
    
    async def replan_step(self, state: PlanExecuteState) -> Dict:
        """重新规划"""
        logger.info(f"开始重新规划，当前状态: {state}")
        replan_count = state.get("replan_count", 0)
        
        if replan_count > 3:
            logger.warning("超过最大重新规划次数")
            return {"response": "由于多次重新规划，流程已终止。"}

        try:
            # 获取格式化的消息
            messages = await self.replanner_prompt.aformat_messages(
                input=state["input"],
                plan=state["plan"],
                past_steps=state["past_steps"]
            )
            
            # 使用 LLM 获取响应
            result = await self.llm.ainvoke(messages)
            response_content = result.content
            logger.info(f"重新规划的响应: {response_content}")
            
            # 如果响应中包含明确的答案标记，则返回为最终响应
            if "答案：" in response_content or "结论：" in response_content:
                return {"response": response_content}
            
            # 否则，提取新的计划步骤
            remaining_steps = [step for step in state["plan"][1:] if step]  # 移除已执行的第一个步骤
            if not remaining_steps:
                # 如果没有剩余步骤，将 LLM 的响应作为新计划
                new_steps = [response_content]
            else:
                new_steps = remaining_steps
                
            logger.info(f"新的执行计划: {new_steps}")
            return {
                "plan": new_steps,
                "replan_count": replan_count + 1
            }

        except Exception as e:
            logger.error(f"重新规划步骤出错: {str(e)}")
            # 如果出错，尝试继续执行剩余计划
            remaining_steps = state["plan"][1:] if len(state["plan"]) > 1 else []
            if remaining_steps:
                return {
                    "plan": remaining_steps,
                    "replan_count": replan_count + 1
                }
            else:
                return {"response": "无法继续执行，流程终止。"}

    def should_end(self, state: PlanExecuteState):
        """判断是否应该结束工作流"""
        logger.info(f"检查是否结束工作流，当前状态: {state}")
        
        # 如果有最终响应，结束工作流
        if "response" in state and state["response"]:
            logger.info(f"已有最终响应: {state['response']}")
            return END
        
        # 如果执行步骤过多，结束工作流
        if len(state.get("past_steps", [])) >= 5:
            logger.info("达到最大步骤数")
            return END
        
        # 如果没有剩余计划，结束工作流
        if not state.get("plan"):
            logger.info("没有剩余计划")
            return END
        
        # 继续执行
        logger.info("继续执行下一步")
        return "agent"
    
    def _create_workflow(self) -> StateGraph:
        """创建工作流图"""
        workflow = StateGraph(PlanExecuteState)

        # 添加节点
        workflow.add_node("planner", self.plan_step)
        workflow.add_node("agent", self.execute_step)
        workflow.add_node("replan", self.replan_step)

        # 添加边
        workflow.add_edge(START, "planner")  # 从 START 到 planner
        workflow.add_edge("planner", "agent")  # 从 planner 到 agent
        workflow.add_edge("agent", "replan")  # 从 agent 到 replan

        # 添加条件边
        workflow.add_conditional_edges(
            "replan",
            self.should_end,
            {
                END: END,
                "agent": "agent"  # 添加从 replan 到 agent 的边
            }
        )

        return workflow.compile()
    
    async def run(self, query: str) -> Dict[str, Any]:
        """运行工作流"""
        inputs = {"input": query}
        config = {"recursion_limit": 50, "max_iterations": 10}  # 添加最大迭代次数限制

        steps = []
        async for event in self.workflow.astream(inputs, config=config):
            for k, v in event.items():
                if k != "__end__":
                    # 更新 replan_count
                    if k == "replan" and isinstance(v, dict) and "replan_count" in v:
                        inputs["replan_count"] = v["replan_count"]
                    steps.append({k: v})

        return {
            "query": query,
            "steps": steps
        }

async def main():
    """主函数"""
    demo = PlanExecuteDemo()
    
    # 测试查询
    queries = [
        "分析平安银行2023年的股价表现"    ]
    
    for query in queries:
        print(f"\n查询: {query}")
        result = await demo.run(query)
        
        print("\n执行步骤:")
        for step in result["steps"]:
            for k, v in step.items():
                print(f"\n{k}:")
                print(v)
        print("-" * 50)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 