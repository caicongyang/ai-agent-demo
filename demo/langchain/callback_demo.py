from typing import Any, Dict, List
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
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

class StockAnalysisCallbackHandler(BaseCallbackHandler):
    """股票分析回调处理器"""
    
    def __init__(self):
        """初始化回调处理器"""
        self.steps = []
        
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """当 LLM 开始处理时触发"""
        self.steps.append({
            "event": "llm_start",
            "message": "开始生成分析结果..."
        })
        
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """当 LLM 完成处理时触发"""
        self.steps.append({
            "event": "llm_end",
            "message": "分析生成完成"
        })
    
    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """当 LLM 发生错误时触发"""
        self.steps.append({
            "event": "llm_error",
            "message": f"分析过程出错: {str(error)}"
        })
    
    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """当链开始处理时触发"""
        self.steps.append({
            "event": "chain_start",
            "message": "开始处理分析链",
            "inputs": inputs.get("query", "")
        })
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """当链完成处理时触发"""
        self.steps.append({
            "event": "chain_end",
            "message": "分析链处理完成",
            "outputs": outputs
        })
    
    def on_chain_error(self, error: Exception, **kwargs: Any) -> None:
        """当链发生错误时触发"""
        self.steps.append({
            "event": "chain_error",
            "message": f"处理链出错: {str(error)}"
        })
    
    def on_parser_start(self, serialized: Dict[str, Any], **kwargs: Any) -> None:
        """当解析器开始处理时触发"""
        self.steps.append({
            "event": "parser_start",
            "message": "开始解析结果..."
        })
    
    def on_parser_end(self, parsed_output: Dict[str, Any], **kwargs: Any) -> None:
        """当解析器完成处理时触发"""
        self.steps.append({
            "event": "parser_end",
            "message": "解析完成",
            "parsed_output": parsed_output
        })
    
    def get_steps(self) -> List[Dict[str, Any]]:
        """获取所有处理步骤"""
        return self.steps

class CallbackDemo:
    """回调演示类"""
    
    def __init__(self):
        """初始化回调演示实例"""
        # 创建回调处理器
        self.callback_handler = StockAnalysisCallbackHandler()
        
        # 初始化 LLM
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            callbacks=[self.callback_handler]
        )
        
        # 创建 Pydantic 解析器
        self.parser = PydanticOutputParser(pydantic_object=StockAnalysis)
        
        # 创建提示模板
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的股票分析师。请根据用户的查询提供股票分析结果。
用户的查询中会包含股票代码，格式为 {{股票代码}}，如：平安银行{{000001}}。

{format_instructions}

请确保：
1. 准确提取查询中的股票代码
2. 输出为有效的 JSON 格式
3. 包含所有必需字段
4. risk_level 只能是 "低"、"中"、"高" 之一
            """),
            ("human", "{query}")
        ])
    
    def analyze_stock(self, query: str) -> Dict[str, Any]:
        """分析股票并返回结果"""
        try:
            # 创建处理链
            chain = self.prompt | self.llm | self.parser
            
            # 执行分析
            result = chain.invoke({
                "query": query,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            return {
                "success": True,
                "result": result.dict(),
                "steps": self.callback_handler.get_steps()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "steps": self.callback_handler.get_steps()
            }

def main():
    """主函数"""
    demo = CallbackDemo()
    
    # 测试查询
    query = "分析平安银行{000001}的投资价值"
    print(f"查询: {query}\n")
    
    # 执行分析
    result = demo.analyze_stock(query)
    
    # 打印处理步骤
    print("处理步骤:")
    for step in result["steps"]:
        print(f"\n事件: {step['event']}")
        print(f"消息: {step['message']}")
        if "inputs" in step:
            print(f"输入: {step['inputs']}")
        if "outputs" in step:
            print(f"输出: {json.dumps(step['outputs'], ensure_ascii=False, indent=2)}")
    
    # 打印最终结果
    print("\n最终结果:")
    if result["success"]:
        print(json.dumps(result["result"], ensure_ascii=False, indent=2))
    else:
        print(f"分析失败: {result['error']}")

if __name__ == "__main__":
    main() 