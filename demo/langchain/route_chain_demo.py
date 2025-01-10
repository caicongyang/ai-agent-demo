import os
from typing import Dict, Any, List
from enum import Enum
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough, RunnableBranch

class QueryType(Enum):
    """查询类型枚举"""
    TRANSLATION = "translation"
    CODE = "code"
    MATH = "math"
    GENERAL = "general"

class RouteChainDemo:
    """
    Route Chain 演示类
    
    该类演示了 LangChain 中路由链的功能，包括：
    1. 查询分类路由
    2. 特定领域处理链
    3. 条件分支执行
    
    Attributes:
        llm: 大语言模型实例，用于处理各类查询
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        """
        初始化 Route Chain 演示实例
        
        Args:
            api_key (str, optional): API 密钥. Defaults to None.
            base_url (str, optional): API 基础 URL. Defaults to None.
        """
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        self.llm = ChatOpenAI(
            model="deepseek-chat", 
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url if base_url else None,
        )
    
    def create_classifier_chain(self) -> Any:
        """
        创建查询分类链
        
        用于判断用户输入属于哪种类型的查询。
        
        Returns:
            Any: 分类链，返回查询类型
        """
        classifier_prompt = ChatPromptTemplate.from_template(
            """判断以下查询属于哪种类型，仅返回类型名称：
            - translation: 需要翻译的内容
            - code: 编程相关问题
            - math: 数学计算问题
            - general: 其他一般性问题
            
            查询: {query}
            """
        )
        
        classifier_chain = classifier_prompt | self.llm | StrOutputParser()
        return classifier_chain
    
    def create_translation_chain(self) -> Any:
        """创建翻译处理链"""
        translation_prompt = ChatPromptTemplate.from_template(
            """请将以下内容翻译成英文：
            {query}
            """
        )
        return translation_prompt | self.llm | StrOutputParser()
    
    def create_code_chain(self) -> Any:
        """创建代码处理链"""
        code_prompt = ChatPromptTemplate.from_template(
            """请解答这个编程问题，并提供代码示例：
            {query}
            """
        )
        return code_prompt | self.llm | StrOutputParser()
    
    def create_math_chain(self) -> Any:
        """创建数学处理链"""
        math_prompt = ChatPromptTemplate.from_template(
            """请解答这个数学问题，并展示计算过程：
            {query}
            """
        )
        return math_prompt | self.llm | StrOutputParser()
    
    def create_general_chain(self) -> Any:
        """创建通用处理链"""
        general_prompt = ChatPromptTemplate.from_template(
            """请回答这个问题：
            {query}
            """
        )
        return general_prompt | self.llm | StrOutputParser()
    
    def create_route_chain(self) -> Any:
        """
        创建路由链
        
        根据查询类型将请求路由到相应的处理链。
        
        Returns:
            Any: 路由链，根据查询类型选择不同的处理方式
        
        Example:
            >>> chain = demo.create_route_chain()
            >>> result = chain.invoke("把'你好'翻译成英文")
        """
        classifier_chain = self.create_classifier_chain()
        
        # 创建各种处理链
        translation_chain = self.create_translation_chain()
        code_chain = self.create_code_chain()
        math_chain = self.create_math_chain()
        general_chain = self.create_general_chain()
        
        # 创建分支链
        branch_chain = RunnableBranch(
            (lambda x: x["category"] == QueryType.TRANSLATION.value, translation_chain),
            (lambda x: x["category"] == QueryType.CODE.value, code_chain),
            (lambda x: x["category"] == QueryType.MATH.value, math_chain),
            general_chain  # 默认分支
        )
        
        # 组合分类和处理
        route_chain = (
            {
                "category": classifier_chain,
                "query": RunnablePassthrough()
            }
            | branch_chain
        )
        
        return route_chain

def main():
    """
    主函数，演示路由链的使用方法
    """
    # 创建演示实例
    demo = RouteChainDemo(
        api_key="sk-00acc077d0d34f43a21910049163d796",
        base_url="https://api.deepseek.com/v1"
    )
    
    # 创建路由链
    route_chain = demo.create_route_chain()
    
    # 测试用例
    test_queries = [
        "把'你好世界'翻译成英文",
        "如何用Python实现快速排序？",
        "计算 (23 + 45) * 6 的结果",
        "今天天气怎么样？"
    ]
    
    # 执行测试
    for query in test_queries:
        print(f"\n查询: {query}")
        try:
            result = route_chain.invoke(query)
            print("回答:")
            print(result)
            print("-" * 50)
        except Exception as e:
            print(f"处理出错: {e}")

if __name__ == "__main__":
    main() 