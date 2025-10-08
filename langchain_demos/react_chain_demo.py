import os
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import Tool
from langchain_community.utilities import SerpAPIWrapper
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class ReActChainDemo:
    """
    ReAct Chain 演示类
    
    该类演示了 LangChain 中的 ReAct (Reasoning + Acting) 模式，包括：
    1. 思维推理
    2. 工具使用
    3. 行动执行
    
    Attributes:
        llm: 大语言模型实例
        tools: 可用工具列表
    """

    def __init__(self):
        """
        初始化 ReAct Chain 演示实例
        """
        # 设置环境变量
        os.environ["SERPAPI_API_KEY"] = os.getenv("SERPAPI_API_KEY")
        
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
        )
        
        # 初始化搜索工具
        search = SerpAPIWrapper()
        
        # 初始化工具
        self.tools = [
            Tool(
                name="search",
                description="搜索引擎，用于查找网络上的信息。输入应该是搜索查询字符串。",
                func=search.run
            ),
            Tool(
                name="calculator",
                description="计算器，用于进行数学计算。输入应该是数学表达式字符串。",

                func=self._calculator
            )
        ]
    
    def _calculator(self, expression: str) -> str:
        """简单计算器实现"""
        try:
            return str(eval(expression))
        except Exception as e:
            return f"计算错误: {str(e)}"
    
    def create_react_chain(self) -> Any:
        """
        创建 ReAct 链
        
        Returns:
            ReAct 处理链
        """
        # ReAct 提示模板
        react_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个可以思考和行动的助手。解决问题时请遵循以下步骤：

1. 思考 (Thought): 分析问题，确定需要采取的行动
2. 行动 (Action): 使用可用工具执行行动，格式为 tool_name("input")
3. 观察 (Observation): 观察行动结果
4. 继续思考或得出结论

可用工具:
{tools}

示例格式:
问题: 谁是当前的联合国秘书长？
思考: 我需要搜索最新的联合国秘书长信息
行动: search("current UN Secretary-General")
观察: 根据搜索结果，现任联合国秘书长是安东尼奥·古特雷斯
结论: 联合国现任秘书长是安东尼奥·古特雷斯

请按照以上格式，清晰地展示每个步骤，解答用户的问题。
"""),
            ("human", "{input}")
        ])
        
        # 创建处理链
        chain = react_prompt | self.llm | StrOutputParser()
        
        return chain
    
    def process_query(self, query: str) -> str:
        """
        处理用户查询
        
        Args:
            query: 用户输入的问题
        
        Returns:
            处理结果
        """
        try:
            chain = self.create_react_chain()
            
            # 准备工具描述
            tools_desc = "\n".join([
                f"- {tool.name}: {tool.description}"
                for tool in self.tools
            ])
            
            # 执行处理链
            response = chain.invoke({
                "input": query,
                "tools": tools_desc
            })
            
            return response
        except Exception as e:
            print(f"处理查询时出现错误: {e}")
            return f"抱歉，处理您的请求时出现了错误。错误信息：{str(e)}"

def main():
    """主函数，演示 ReAct 功能的使用方法"""
    # 创建演示实例
    demo = ReActChainDemo()
    
    # 测试用例
    test_queries = [
        "2023年诺贝尔物理学奖获得者是谁？",
        "计算 123 * 456 的结果",
        "OpenAI 的 CEO 是谁？",
        "中国最高的山峰是什么？它有多高？"
    ]
    
    # 执行测试
    for query in test_queries:
        print(f"\n问题: {query}")
        response = demo.process_query(query)
        print("\n回答:")
        print(response)
        print("-" * 50)

if __name__ == "__main__":
    main() 