"""
这个简单的例子展示了 LangGraph 的基本用法，通过实现一个简单的问答系统来演示：
1. 如何定义状态类型（QAState）
2. 如何创建工作流节点（think_step 和 answer_step）
3. 如何定义工作流图（节点之间的连接关系）
4. 如何运行工作流并处理结果

工作流程：
1. 输入问题
2. 思考步骤：分析问题并提供思考过程
3. 回答步骤：根据思考过程给出最终答案
4. 结束

这个例子简单明了，适合用来理解 LangGraph 的基本概念和用法。
"""

from typing import Dict, Any, TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from dotenv import load_dotenv
import os

# 加载环境变量配置
load_dotenv()

class QAState(TypedDict):
    """
    问答状态定义
    
    这是 LangGraph 工作流的状态类型定义，包含了整个问答过程中需要的所有状态：
    - question: 用户输入的问题
    - thoughts: AI 的思考过程
    - final_answer: AI 的最终答案
    """
    question: str    # 用户问题
    thoughts: str    # 思考过程
    final_answer: str  # 最终答案，改名避免与节点名冲突

class SimpleQADemo:
    """
    简单问答演示类
    
    这个类展示了如何使用 LangGraph 构建一个简单的问答系统。
    整个系统包含两个主要步骤：
    1. 思考步骤：分析问题并提供思考过程
    2. 回答步骤：根据思考过程给出最终答案
    """
    
    def __init__(self):
        """
        初始化演示实例
        
        设置：
        1. 初始化大语言模型
        2. 创建思考和回答步骤的提示模板
        3. 创建工作流图
        """
        # 初始化大语言模型
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        # 创建思考步骤的提示模板
        self.think_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个善于思考的助手。请仔细思考如何回答用户的问题。
分析问题的关键点，并提供思考过程。"""),
            ("user", "{question}")
        ])
        
        # 创建回答步骤的提示模板
        self.answer_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个擅长回答问题的助手。
根据之前的思考过程，给出清晰、准确的答案。"""),
            ("user", "问题：{question}\n思考过程：{thoughts}")
        ])
        
        # 创建工作流图
        self.workflow = self._create_workflow()
    
    async def think_step(self, state: QAState) -> Dict:
        """
        思考步骤
        
        这是工作流的第一个节点，负责：
        1. 接收用户的问题
        2. 分析问题的关键点
        3. 生成思考过程
        """
        try:
            # 获取思考结果
            result = await self.think_prompt.ainvoke({
                "question": state["question"]
            })
            
            return {"thoughts": result.content if hasattr(result, 'content') else str(result)}
        except Exception as e:
            print(f"思考步骤出错: {str(e)}")
            return {"thoughts": "无法进行有效思考。"}
    
    async def answer_step(self, state: QAState) -> Dict:
        """
        回答步骤
        
        这是工作流的第二个节点，负责：
        1. 基于思考过程生成答案
        2. 确保答案清晰准确
        """
        try:
            # 获取回答结果
            result = await self.answer_prompt.ainvoke({
                "question": state["question"],
                "thoughts": state["thoughts"]
            })
            
            return {"final_answer": result.content if hasattr(result, 'content') else str(result)}
        except Exception as e:
            print(f"回答步骤出错: {str(e)}")
            return {"final_answer": "抱歉，我无法给出答案。"}
    
    def _create_workflow(self) -> StateGraph:
        """
        创建工作流图
        
        定义了工作流的结构：
        1. 创建状态图
        2. 添加工作流节点
        3. 定义节点之间的连接关系
        4. 编译工作流图
        """
        workflow = StateGraph(QAState)
        
        # 添加节点
        workflow.add_node("think", self.think_step)
        workflow.add_node("answer", self.answer_step)
        
        # 添加边：定义节点之间的连接关系
        workflow.add_edge(START, "think")  # 开始 -> 思考
        workflow.add_edge("think", "answer")  # 思考 -> 回答
        workflow.add_edge("answer", END)  # 回答 -> 结束
        
        return workflow.compile()
    
    async def run(self, question: str) -> Dict[str, Any]:
        """
        运行工作流
        
        执行问答过程：
        1. 创建初始状态
        2. 运行工作流
        3. 收集每个步骤的结果
        4. 返回完整的问答过程
        """
        # 创建初始状态
        inputs = QAState(
            question=question,
            thoughts="",
            final_answer=""
        )
        
        steps = []
        async for event in self.workflow.astream(inputs):
            for k, v in event.items():
                if k != "__end__":
                    steps.append({k: v})
        
        return {
            "question": question,
            "steps": steps
        }

async def main():
    """
    主函数
    
    用于演示如何使用 SimpleQADemo 类：
    1. 创建演示实例
    2. 准备测试问题
    3. 运行问答流程
    4. 展示执行结果
    """
    demo = SimpleQADemo()
    
    # 测试问题
    questions = [
        "什么是人工智能？",
        "为什么天空是蓝色的？"
    ]
    
    for question in questions:
        print(f"\n问题: {question}")
        result = await demo.run(question)
        print("\n执行步骤:")
        for step in result["steps"]:
            print(f"\n{list(step.keys())[0]}:")
            print(list(step.values())[0])
        print("-" * 50)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 