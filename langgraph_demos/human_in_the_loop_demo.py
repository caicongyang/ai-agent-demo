"""
LangGraph 人机交互演示
基于官方教程：https://langchain-ai.github.io/langgraph/tutorials/get-started/4-human-in-the-loop/

这个演示展示了如何在 LangGraph 中实现人机交互功能，允许 AI 代理在需要时请求人工协助。
"""

import os
from typing import Annotated, Dict, Any, List
from typing_extensions import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class HumanInLoopState(TypedDict):
    """
    人机交互状态定义
    
    包含了整个人机交互过程中需要的所有状态：
    - task: 用户任务
    - ai_response: AI的回复
    - human_input_needed: 是否需要人工输入
    - human_feedback: 人工反馈
    - final_output: 最终输出
    - steps: 执行步骤的历史记录
    """
    task: str
    ai_response: str
    human_input_needed: bool
    human_feedback: str
    final_output: str
    steps: List[Dict]


class HumanInLoopDemo:
    """
    人机交互演示类
    
    这个类展示了如何使用 LangGraph 构建一个具有人机交互功能的系统。
    系统可以在需要时暂停执行，等待人工输入，然后继续处理。
    """
    
    def __init__(self):
        """
        初始化演示实例
        
        设置：
        1. 初始化大语言模型
        2. 创建各种提示模板
        3. 创建工作流图
        """
        logger.info("初始化 HumanInLoopDemo...")
        
        # 初始化大语言模型
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        # 创建AI分析提示模板
        self.ai_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能助手，负责分析用户的请求。
当用户请求专家建议或需要人工协助时，你应该识别出这种需求。
如果用户明确要求专家建议或人工协助，请在回复中包含"需要人工协助"这个短语。
否则，直接回答用户的问题。"""),
            ("user", "{task}")
        ])
        
        # 创建最终回复提示模板
        self.final_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能助手，现在需要基于人工专家的反馈给用户最终回复。
请整合专家的建议，给出完整、有用的回答。"""),
            ("user", "用户任务：{task}\n\n专家反馈：{human_feedback}")
        ])
        
        # 创建工作流图
        self.workflow = self._create_workflow()
        logger.info("工作流创建完成")
    
    async def ai_analysis_step(self, state: HumanInLoopState) -> Dict:
        """
        AI分析步骤
        
        分析用户请求，判断是否需要人工协助
        """
        try:
            logger.info("执行AI分析步骤...")
            
            # 创建分析链：prompt + LLM
            analysis_chain = self.ai_prompt | self.llm
            # 获取分析结果
            result = await analysis_chain.ainvoke({
                "task": state["task"]
            })
            
            ai_response = result.content if hasattr(result, 'content') else str(result)
            
            # 检查是否需要人工协助
            need_human = "需要人工协助" in ai_response or "专家建议" in state["task"] or "协助" in state["task"]
            
            return {
                "ai_response": ai_response,
                "human_input_needed": need_human,
                "steps": [{"ai_analysis": ai_response}]
            }
        except Exception as e:
            logger.error(f"AI分析步骤出错: {str(e)}")
            return {
                "ai_response": "分析过程中出现错误。",
                "human_input_needed": False,
                "steps": [{"ai_analysis": f"错误: {str(e)}"}]
            }
    
    def human_input_step(self, state: HumanInLoopState) -> Dict:
        """
        人工输入步骤
        
        模拟等待人工输入的过程
        """
        logger.info("等待人工输入...")
        
        print(f"\n🤖 AI分析结果: {state['ai_response']}")
        print("="*50)
        print("🤖 系统提示: AI代理请求人工协助")
        print(f"📝 用户任务: {state['task']}")
        
        # 在实际应用中，这里会暂停等待真实的人工输入
        # 这里我们模拟人工专家的回复
        if "AI代理" in state["task"] or "agent" in state["task"].lower():
            human_feedback = """专家建议：
1. 使用 LangGraph 构建AI代理是个很好的选择，它提供了：
   - 状态管理功能
   - 人机交互支持  
   - 工作流控制
   - 检查点和恢复机制

2. 推荐的开发步骤：
   - 定义状态结构
   - 创建工作流节点
   - 设置节点间的连接
   - 添加条件分支逻辑

3. 最佳实践：
   - 保持状态简洁
   - 合理设计节点粒度
   - 添加错误处理
   - 使用日志记录执行过程"""
        else:
            human_feedback = f"专家建议：关于 '{state['task']}'，建议您提供更具体的需求描述，这样我们可以给出更精准的建议。"
        
        print(f"👨‍💼 专家反馈: {human_feedback}")
        
        return {
            "human_feedback": human_feedback,
            "steps": [{"human_input": human_feedback}]
        }
    
    async def final_response_step(self, state: HumanInLoopState) -> Dict:
        """
        最终回复步骤
        
        基于人工反馈生成最终回复
        """
        try:
            logger.info("生成最终回复...")
            
            # 创建最终回复链：prompt + LLM
            final_chain = self.final_prompt | self.llm
            # 获取最终回复
            result = await final_chain.ainvoke({
                "task": state["task"],
                "human_feedback": state["human_feedback"]
            })
            
            final_output = result.content if hasattr(result, 'content') else str(result)
            
            return {
                "final_output": final_output,
                "steps": [{"final_response": final_output}]
            }
        except Exception as e:
            logger.error(f"最终回复步骤出错: {str(e)}")
            return {
                "final_output": f"生成最终回复时出现错误: {str(e)}",
                "steps": [{"final_response": f"错误: {str(e)}"}]
            }
    
    def decide_next_step(self, state: HumanInLoopState) -> str:
        """
        决定下一步操作
        
        基于当前状态决定是否需要人工输入
        """
        if state.get("human_input_needed", False) and not state.get("human_feedback"):
            return "human_input"
        else:
            return "final_response"
    
    def _create_workflow(self) -> StateGraph:
        """
        创建工作流图
        
        定义了工作流的结构：
        1. 创建状态图
        2. 添加工作流节点
        3. 定义节点之间的连接关系
        4. 编译工作流图
        """
        workflow = StateGraph(HumanInLoopState)
        
        # 添加节点
        workflow.add_node("ai_analysis", self.ai_analysis_step)
        workflow.add_node("human_input", self.human_input_step)
        workflow.add_node("final_response", self.final_response_step)
        
        # 添加边：定义节点之间的连接关系
        workflow.add_edge(START, "ai_analysis")
        
        # 添加条件边：根据是否需要人工输入决定下一步
        workflow.add_conditional_edges(
            "ai_analysis",
            self.decide_next_step,
            {
                "human_input": "human_input",
                "final_response": "final_response"
            }
        )
        
        workflow.add_edge("human_input", "final_response")
        workflow.add_edge("final_response", END)
        
        return workflow.compile()
    
    async def run(self, task: str) -> Dict[str, Any]:
        """
        运行工作流
        
        执行人机交互过程：
        1. 创建初始状态
        2. 运行工作流
        3. 收集每个步骤的结果
        4. 返回完整的执行过程
        """
        # 创建初始状态
        inputs = HumanInLoopState(
            task=task,
            ai_response="",
            human_input_needed=False,
            human_feedback="",
            final_output="",
            steps=[]
        )
        
        all_steps = []
        async for event in self.workflow.astream(inputs):
            for k, v in event.items():
                if k != "__end__":
                    all_steps.append({k: v})
        
        return {
            "task": task,
            "steps": all_steps
        }


async def demo_human_in_loop():
    """演示人机交互功能"""
    print("🚀 LangGraph 人机交互演示")
    print("="*50)
    
    demo = HumanInLoopDemo()
    
    # 测试任务列表
    test_tasks = [
        "我需要一些关于构建AI代理的专家建议。你能为我请求协助吗？",
        "如何优化Python代码性能？",
        "请帮我分析一下机器学习项目的架构设计，需要专家建议。"
    ]
    
    for i, task in enumerate(test_tasks, 1):
        print(f"\n📝 测试任务 {i}: {task}")
        print("-" * 60)
        
        try:
            result = await demo.run(task)
            
            print(f"\n✅ 任务完成！执行步骤:")
            for j, step in enumerate(result["steps"], 1):
                step_name = list(step.keys())[0]
                step_data = list(step.values())[0]
                
                print(f"\n第{j}步 - {step_name}:")
                if isinstance(step_data, dict):
                    for key, value in step_data.items():
                        if key == "steps" and isinstance(value, list):
                            continue  # 跳过嵌套的steps
                        print(f"  {key}: {value}")
                else:
                    print(f"  结果: {step_data}")
            
            print("=" * 60)
            
        except Exception as e:
            logger.error(f"执行任务时出错: {str(e)}")
            print(f"❌ 任务执行失败: {e}")


async def interactive_demo():
    """交互式演示"""
    print("🎯 交互式人机交互演示")
    print("输入 'quit' 退出")
    print("="*50)
    
    demo = HumanInLoopDemo()
    
    while True:
        try:
            user_input = input("\n👤 请输入您的任务: ")
            if user_input.lower() in ['quit', 'exit', '退出']:
                break
            
            print("\n🔄 处理中...")
            result = await demo.run(user_input)
            
            print(f"\n✅ 处理完成！")
            print(f"📝 任务: {result['task']}")
            
            # 显示最终结果
            final_step = None
            for step in result["steps"]:
                if "final_response" in step:
                    final_step = step["final_response"]
                    break
            
            if final_step and isinstance(final_step, dict) and "final_output" in final_step:
                print(f"\n🎯 最终回复: {final_step['final_output']}")
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            logger.error(f"交互演示出错: {str(e)}")
            print(f"❌ 错误: {e}")


async def main():
    """主函数"""
    print("选择演示模式:")
    print("1. 自动演示")
    print("2. 交互式演示")
    
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "1":
        await demo_human_in_loop()
    elif choice == "2":
        await interactive_demo()
    else:
        print("无效选择，运行自动演示...")
        await demo_human_in_loop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
