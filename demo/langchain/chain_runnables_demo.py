import os
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableParallel, RunnableLambda

class ChainRunnablesDemo:
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        初始化 Chain Runnables 演示
        
        :param api_key: API 密钥
        :param base_url: 基础 URL
        """
        # 设置 API 密钥
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # 初始化大模型
        self.llm = ChatOpenAI(
            model="deepseek-chat", 
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url if base_url else None,
        )
    
    def create_joke_chain(self) -> Any:
        """
        创建一个生成笑话的链
        
        :return: 笑话生成链
        """
        # 创建笑话提示模板
        joke_prompt = ChatPromptTemplate.from_template(
            "请用{style}风格讲一个关于{topic}的笑话"
        )
        
        # 构建链：提示模板 -> 大模型 -> 输出解析
        joke_chain = joke_prompt | self.llm | StrOutputParser()
        
        return joke_chain
    
    def create_joke_analysis_chain(self) -> Any:
        """
        创建一个分析笑话的链
        
        :return: 笑话分析链
        """
        # 创建分析提示模板
        analysis_prompt = ChatPromptTemplate.from_template(
            "请分析这个笑话的幽默程度和创意性:\n{joke}"
        )
        
        # 构建分析链：提示模板 -> 大模型 -> 输出解析
        analysis_chain = analysis_prompt | self.llm | StrOutputParser()
        
        return analysis_chain
    
    def create_composed_joke_chain(self) -> Any:
        """
        创建一个组合的笑话链
        
        :return: 组合笑话链
        """
        # 获取笑话和分析链
        joke_chain = self.create_joke_chain()
        analysis_chain = self.create_joke_analysis_chain()
        
        # 使用 RunnableParallel 并行执行
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
    # 创建演示实例
    demo = ChainRunnablesDemo(
        api_key="sk-00acc077d0d34f43a21910049163d796",
        base_url="https://api.deepseek.com/v1"
    )
    
    # 测试不同的链
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
        
        # 调用链
        result = composed_chain.invoke(case)
        
        print("生成的笑话:")
        print(result['joke'])
        print("\n笑话分析:")
        print(result['analysis'])
        print("-" * 50)

if __name__ == "__main__":
    main() 