"""
这个示例展示了如何使用 LangGraph 的可视化功能：
1. 如何使用 graphviz 生成工作流图
2. 如何自定义图表样式
"""

from typing import Dict, List, Annotated
from typing_extensions import TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
import graphviz
from dotenv import load_dotenv
import os
import logging
import asyncio

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class GraphState(TypedDict):
    """工作流状态定义"""
    messages: Annotated[List[Dict], add_messages]
    current_step: str
    step_count: int

class VisualizationDemo:
    """可视化演示类"""
    
    def __init__(self):
        """初始化可视化演示实例"""
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        # 创建工作流图
        self.workflow = self._create_workflow()
        logger.info("可视化演示实例初始化完成")

    async def process_step(self, state: GraphState, step_name: str) -> Dict:
        """处理工作流步骤"""
        logger.info(f"执行步骤: {step_name}")
        try:
            # 根据步骤类型设置不同的系统提示
            system_prompt = {
                "data_collection": """你是一个数据收集专家。
请说明如何收集股票市场数据，包括：
1. 价格数据
2. 交易量数据
3. 市场指标
请简要描述数据收集的方法和来源。""",
                
                "data_analysis": """你是一个数据分析专家。
基于收集到的股票市场数据，请说明如何进行分析：
1. 技术分析指标
2. 趋势分析
3. 市场情绪分析
请简要描述分析方法和关注点。"""
            }

            result = await self.llm.ainvoke([
                {"role": "system", "content": system_prompt[step_name]},
                {"role": "user", "content": "请描述你将如何执行这个步骤。"}
            ])
            return {
                "messages": [{"role": "assistant", "content": f"{step_name}: {result.content}"}],
                "current_step": step_name,
                "step_count": state.get("step_count", 0) + 1
            }
        except Exception as e:
            logger.error(f"步骤执行失败: {e}")
            return {
                "messages": [{"role": "system", "content": f"{step_name}: 步骤执行失败"}],
                "current_step": step_name,
                "step_count": state.get("step_count", 0) + 1
            }

    async def process_step_a(self, state: GraphState) -> Dict:
        """数据收集步骤"""
        return await self.process_step(state, "data_collection")

    async def process_step_b(self, state: GraphState) -> Dict:
        """数据分析步骤"""
        return await self.process_step(state, "data_analysis")

    def should_continue(self, state: GraphState) -> str:
        """决定工作流去向"""
        if state.get("step_count", 0) >= 3:
            return END
        return "data_analysis" if state["current_step"] == "data_collection" else "data_collection"

    def _create_workflow(self) -> StateGraph:
        """创建工作流图"""
        workflow = StateGraph(GraphState)
        
        # 使用更有意义的节点名称
        workflow.add_node("data_collection", self.process_step_a)
        workflow.add_node("data_analysis", self.process_step_b)
        
        # 添加边
        workflow.add_edge(START, "data_collection")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "data_collection",
            self.should_continue,
            {END: END, "data_analysis": "data_analysis"}
        )
        
        workflow.add_conditional_edges(
            "data_analysis",
            self.should_continue,
            {END: END, "data_collection": "data_collection"}
        )
        
        return workflow.compile()

    def visualize_graph(self, output_path: str = "workflow_graph") -> None:
        """使用 graphviz 可视化工作流图"""
        dot = graphviz.Digraph(comment='Stock Market Analysis Workflow')
        dot.attr(rankdir='LR')
        
        # 设置节点样式
        dot.attr('node', style='filled')
        dot.node('START', 'START', shape='circle', fillcolor='#ffdfba')
        dot.node('data_collection', 'Data Collection', shape='box', fillcolor='#fad7de')
        dot.node('data_analysis', 'Data Analysis', shape='box', fillcolor='#fad7de')
        dot.node('END', 'END', shape='doublecircle', fillcolor='#baffc9')
        
        # 添加边
        dot.edge('START', 'data_collection')
        dot.edge('data_collection', 'data_analysis')
        dot.edge('data_analysis', 'data_collection')
        dot.edge('data_collection', 'END')
        dot.edge('data_analysis', 'END')
        
        # 保存图形
        dot.render(output_path, view=True, format='png')

async def main():
    """主函数"""
    demo = VisualizationDemo()
    
    # 生成图表
    print("\n生成工作流图...")
    demo.visualize_graph()
    print("图表已保存为 workflow_graph.png")
    
    # 运行工作流演示
    print("\n运行工作流演示:")
    inputs = {
        "messages": [],
        "current_step": "",
        "step_count": 0
    }
    
    async for event in demo.workflow.astream(inputs):
        for k, v in event.items():
            if k != "__end__":
                print(f"\n步骤 {k}:")
                print(f"消息: {v.get('messages', [])}")
                print(f"当前步骤: {v.get('current_step', '')}")
                print(f"步骤计数: {v.get('step_count', 0)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())