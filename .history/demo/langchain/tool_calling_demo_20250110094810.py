from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticToolsParser
from openai import OpenAI

# 使用 Pydantic 类定义工具模式
class Add(BaseModel):
    """
    将两个整数相加的工具
    
    Args:
        a: 第一个整数
        b: 第二个整数
    
    Returns:
        两个整数的和
    """
    a: int = Field(..., description="第一个整数")
    b: int = Field(..., description="第二个整数")

class Multiply(BaseModel):
    """
    将两个整数相乘的工具
    
    Args:
        a: 第一个整数
        b: 第二个整数
    
    Returns:
        两个整数的乘积
    """
    a: int = Field(..., description="第一个整数")
    b: int = Field(..., description="第二个整数")

def add(a: int, b: int) -> int:
    """实际执行加法的函数"""
    return a + b

def multiply(a: int, b: int) -> int:
    """实际执行乘法的函数"""
    return a * b

class ToolCallingDemo:
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        初始化工具调用演示
        
        :param api_key: API 密钥，如果未提供则从环境变量读取
        :param base_url: 基础 URL
        """
        import os
        
        # 设置 API 密钥和基础 URL
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # 初始化 OpenAI 客户端
        client_params = {
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
        
        # 如果提供了 base_url，则添加
        if base_url:
            client_params["base_url"] = base_url
        
        # 初始化 OpenAI 客户端
        openai_client = OpenAI(**client_params)
        
        # 初始化 LLM 并绑定工具
        self.llm = ChatOpenAI(
            model="gpt-4o-mini", 
            openai_api_key=client_params["api_key"],
            base_url=base_url if base_url else None,
            client=openai_client
        )
        
        self.tools = [Add, Multiply]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
    
    def call_tools(self, query: str) -> List[dict]:
        """
        调用工具并返回工具调用结果
        
        :param query: 用户查询
        :return: 工具调用结果列表
        """
        response = self.llm_with_tools.invoke(query)
        return response.tool_calls
    
    def parse_tools(self, query: str) -> List[BaseModel]:
        """
        解析工具调用并返回 Pydantic 对象
        
        :param query: 用户查询
        :return: Pydantic 工具对象列表
        """
        chain = self.llm_with_tools | PydanticToolsParser(tools=self.tools)
        return chain.invoke(query)
    
    def execute_tools(self, query: str) -> List[int]:
        """
        执行工具并返回结果
        
        :param query: 用户查询
        :return: 工具执行结果列表
        """
        tool_calls = self.parse_tools(query)
        results = []
        
        for tool_call in tool_calls:
            if isinstance(tool_call, Add):
                results.append(add(tool_call.a, tool_call.b))
            elif isinstance(tool_call, Multiply):
                results.append(multiply(tool_call.a, tool_call.b))
        
        return results

def main():
    # 创建工具调用演示实例
    demo = ToolCallingDemo(
        api_key="sk-00acc077d0d34f43a21910049163d796",
        base_url="https://api.deepseek.com/v1"
    )
    
    # 测试查询
    queries = [
        "What is 3 * 12?",
        "What is 11 + 49?",
        "Calculate 5 * 7 and then add 3"
    ]
    
    for query in queries:
        print(f"\n查询: {query}")
        
        # 打印工具调用
        print("工具调用:")
        tool_calls = demo.call_tools(query)
        for call in tool_calls:
            print(f"- 工具: {call['name']}, 参数: {call['args']}")
        
        # 打印解析后的工具
        print("\n解析后的工具:")
        parsed_tools = demo.parse_tools(query)
        for tool in parsed_tools:
            print(f"- {tool}")
        
        # 执行工具并打印结果
        print("\n工具执行结果:")
        results = demo.execute_tools(query)
        for result in results:
            print(f"- 结果: {result}")

if __name__ == "__main__":
    main() 