from typing import List, Dict
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import json
import os

# 加载环境变量
load_dotenv()

class StockAnalysis(BaseModel):
    """股票分析结果模型"""
    stock_code: str = Field(description="股票代码")
    stock_name: str = Field(description="股票名称")
    analysis: str = Field(description="分析结论")
    recommendation: str = Field(description="投资建议")
    risk_level: str = Field(description="风险等级：低/中/高")

class JsonParserDemo:
    def __init__(self):
        """初始化 JSON 解析器演示实例"""
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        # 创建 Pydantic 解析器
        self.parser = PydanticOutputParser(pydantic_object=StockAnalysis)
        
        # 创建提示模板，使用双大括号转义所有变量
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的股票分析师。请根据用户的查询提供股票分析结果。
用户的查询中会包含股票代码，格式为 {{股票代码}}，如：平安银行{{000001}}。

{format_instructions}

请确保：
1. 准确提取查询中的股票代码
2. 输出为有效的 JSON 格式
3. 包含所有必需字段
4. risk_level 只能是 "低"、"中"、"高" 之一

示例查询：
分析平安银行{{000001}}的投资价值

示例输出：
{{
    "stock_code": "000001",
    "stock_name": "平安银行",
    "analysis": "平安银行作为国内领先的股份制商业银行...",
    "recommendation": "建议长期持有",
    "risk_level": "中"
}}
            """),
            ("human", "{query}")
        ])

    def analyze_stock(self, query: str) -> str:
        """分析股票并返回 JSON 字符串"""
        try:
            # 创建处理链
            chain = self.prompt | self.llm | self.parser
            
            # 执行分析
            result = chain.invoke({
                "query": query,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # 转换为 JSON 字符串
            return json.dumps(result.dict(), ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"分析过程出现错误: {str(e)}")
            # 返回错误信息的 JSON
            error_result = {
                "error": True,
                "message": str(e),
                "fallback_data": {
                    "stock_code": "未知",
                    "stock_name": "未知",
                    "analysis": "分析失败",
                    "recommendation": "无法提供建议",
                    "risk_level": "高"
                }
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)

    def stream_analysis(self, query: str):
        """流式输出分析结果"""
        try:
            chain = self.prompt | self.llm | self.parser
            
            # 收集所有块
            chunks = []
            for chunk in chain.stream({
                "query": query,
                "format_instructions": self.parser.get_format_instructions()
            }):
                chunks.append(chunk)
            
            # 合并并转换为 JSON
            result = chunks[-1] if chunks else None
            if result:
                return json.dumps(result.dict(), ensure_ascii=False, indent=2)
            else:
                return json.dumps({"error": "No result"}, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({
                "error": True,
                "message": f"流式分析出错: {str(e)}"
            }, ensure_ascii=False, indent=2)

def main():
    """主函数"""
    demo = JsonParserDemo()
    
    # 测试查询
    test_queries = [
        "分析平安银行{000001}的投资价值",
        "评估贵州茅台{600519}的投资风险",
        "分析腾讯控股{00700.HK}的未来发展"
    ]
    
    # 测试普通分析
    print("=== 测试普通分析 ===")
    for query in test_queries:
        print(f"\n查询: {query}")
        result_json = demo.analyze_stock(query)
        print("分析结果:")
        print(result_json)
        print("-" * 50)
    
    # 测试流式输出
    print("\n=== 测试流式输出 ===")
    query = "分析阿里巴巴{9988.HK}的投资价值"
    print(f"\n查询: {query}")
    print("流式分析结果:")
    result_json = demo.stream_analysis(query)
    print(result_json)

if __name__ == "__main__":
    main() 