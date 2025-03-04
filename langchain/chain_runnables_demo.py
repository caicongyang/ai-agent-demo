from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableParallel, RunnableLambda
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

class ChainRunnablesDemo:
    """
    Chain Runnables 演示类
    
    该类演示了 LangChain 中链式调用和并行执行的功能，包括：
    1. 创建笑话生成链
    2. 创建笑话分析链
    3. 组合多个链并行执行
    
    Attributes:
        llm: 大语言模型实例，用于生成和分析文本
    """

    def __init__(self):
        """
        初始化 Chain Runnables 演示
        """
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
    
    def create_joke_chain(self) -> Any:
        """
        创建笑话生成链
        
        创建一个可以根据给定主题和风格生成笑话的处理链。
        
        Returns:
            Any: 笑话生成链，接受 style 和 topic 参数
        
        Example:
            >>> chain = demo.create_joke_chain()
            >>> result = chain.invoke({"style": "幽默", "topic": "编程"})
        """
        joke_prompt = ChatPromptTemplate.from_template(
            "请用{style}风格讲一个关于{topic}的笑话"
        )
        
        joke_chain = joke_prompt | self.llm | StrOutputParser()
        
        return joke_chain
    
    def create_joke_analysis_chain(self) -> Any:
        """
        创建笑话分析链
        
        创建一个可以分析笑话幽默程度和创意性的处理链。
        
        Returns:
            Any: 笑话分析链，接受 joke 参数
        
        Example:
            >>> chain = demo.create_joke_analysis_chain()
            >>> result = chain.invoke({"joke": "一个程序员笑话..."})
        """
        analysis_prompt = ChatPromptTemplate.from_template(
            "请分析这个笑话的幽默程度和创意性:\n{joke}"
        )
        
        analysis_chain = analysis_prompt | self.llm | StrOutputParser()
        
        return analysis_chain
    
    def create_composed_joke_chain(self) -> Any:
        """
        创建组合笑话链
        
        将笑话生成链和分析链组合成一个并行执行的复合链。
        该链可以同时生成笑话并分析其质量。
        
        Returns:
            Any: 组合笑话链，接受 style 和 topic 参数，返回笑话和分析结果
        
        Example:
            >>> chain = demo.create_composed_joke_chain()
            >>> result = chain.invoke({
            ...     "style": "技术幽默",
            ...     "topic": "Python"
            ... })
            >>> print(result["joke"])
            >>> print(result["analysis"])
        """
        joke_chain = self.create_joke_chain()
        analysis_chain = self.create_joke_analysis_chain()
        
        composed_chain = RunnableParallel({
            "joke": joke_chain,
            "style": RunnableLambda(lambda x: x["style"]),
            "topic": RunnableLambda(lambda x: x["topic"])
        }) | RunnableLambda(lambda x: {
            "joke": x["joke"],
            "analysis": analysis_chain.invoke({"joke": x["joke"]})
        })
        
        return composed_chain

def main():
    """
    主函数，演示链式调用的使用方法
    
    包括：
    1. 创建演示实例
    2. 定义测试用例
    3. 创建组合链
    4. 执行链并打印结果
    """
    # 创建演示实例
    demo = ChainRunnablesDemo()
    
    # 测试用例
    test_cases = [
        {"topic": "程序员", "style": "技术幽默"},
        {"topic": "人工智能", "style": "讽刺"},
        {"topic": "数学", "style": "学术笑话"}
    ]
    
    # 创建组合链
    composed_chain = demo.create_composed_joke_chain()
    
    # 执行并打印结果
    for case in test_cases:
        print(f"\n主题: {case['topic']}, 风格: {case['style']}")
        
        result = composed_chain.invoke(case)
        
        print("生成的笑话:")
        print(result['joke'])
        print("\n笑话分析:")
        print(result['analysis'])
        print("-" * 50)

if __name__ == "__main__":
    main() 