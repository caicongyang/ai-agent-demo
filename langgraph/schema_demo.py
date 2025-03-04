"""
这个示例展示了如何在 LangGraph 中定义和使用不同的输入输出模式：
1. 如何定义输入模式（InputState）
2. 如何定义输出模式（OutputState）
3. 如何定义内部状态模式（OverallState）
4. 如何在工作流中使用这些模式

工作流程：
1. 接收输入文本和目标语言
2. 进行翻译
3. 返回翻译结果和置信度
"""

from typing import Dict, Any, List
from typing_extensions import TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from dotenv import load_dotenv
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 定义输入状态
class InputState(TypedDict):
    """输入状态定义"""
    text: str  # 要翻译的文本
    target_lang: str  # 目标语言

# 定义输出状态
class OutputState(TypedDict):
    """输出状态定义"""
    translated_text: str  # 翻译后的文本
    confidence: float  # 翻译置信度

# 定义整体状态
class OverallState(InputState, OutputState):
    """整体状态定义，包含中间状态"""
    detected_lang: str  # 检测到的源语言
    translation_steps: List[Dict]  # 翻译步骤记录

class TranslationDemo:
    """翻译演示类"""
    
    def __init__(self):
        """初始化翻译演示实例"""
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        # 创建工作流图
        self.workflow = self._create_workflow()
        logger.info("翻译演示实例初始化完成")

    async def detect_language(self, state: InputState) -> Dict:
        """检测语言步骤"""
        logger.info(f"开始检测语言: {state['text'][:50]}...")
        try:
            result = await self.llm.ainvoke([
                {"role": "system", "content": "你是一个语言检测专家。请检测给定文本的语言，只返回语言名称。"},
                {"role": "user", "content": f"检测这段文本的语言：{state['text']}"}
            ])
            detected_lang = result.content
            logger.info(f"检测到的语言: {detected_lang}")
            return {"detected_lang": detected_lang}
        except Exception as e:
            logger.error(f"语言检测失败: {e}")
            return {"detected_lang": "unknown"}

    async def translate_text(self, state: OverallState) -> Dict:
        """翻译步骤"""
        logger.info(f"开始翻译，目标语言: {state['target_lang']}")
        try:
            result = await self.llm.ainvoke([
                {"role": "system", "content": f"""你是一个专业翻译。
请将文本从{state['detected_lang']}翻译成{state['target_lang']}。
只返回翻译结果，不要添加任何解释。"""},
                {"role": "user", "content": state['text']}
            ])
            translated_text = result.content
            logger.info("翻译完成")
            return {
                "translated_text": translated_text,
                "confidence": 0.95  # 简化示例，使用固定置信度
            }
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            return {
                "translated_text": "Translation failed",
                "confidence": 0.0
            }

    def _create_workflow(self) -> StateGraph:
        """创建工作流图"""
        # 使用 OverallState 作为内部状态
        workflow = StateGraph(OverallState, input=InputState, output=OutputState)
        
        # 添加节点
        workflow.add_node("detect", self.detect_language)
        workflow.add_node("translate", self.translate_text)
        
        # 添加边
        workflow.add_edge(START, "detect")
        workflow.add_edge("detect", "translate")
        workflow.add_edge("translate", END)
        
        return workflow.compile()

    async def translate(self, text: str, target_lang: str) -> Dict[str, Any]:
        """执行翻译"""
        logger.info(f"开始处理翻译请求: {text[:50]}... -> {target_lang}")
        
        # 创建输入状态
        inputs = {
            "text": text,
            "target_lang": target_lang,
            "translation_steps": []
        }
        
        try:
            # 执行工作流
            result = await self.workflow.ainvoke(inputs)
            logger.info("翻译请求处理完成")
            return result
        except Exception as e:
            logger.error(f"翻译请求处理失败: {e}")
            return {
                "translated_text": "Translation failed",
                "confidence": 0.0
            }

async def main():
    """主函数"""
    demo = TranslationDemo()
    
    # 测试用例
    test_cases = [
        ("Hello, how are you?", "中文"),
        ("今天天气真好", "English"),
        ("Bonjour, comment allez-vous?", "日本語")
    ]
    
    for text, target_lang in test_cases:
        print(f"\n原文: {text}")
        print(f"目标语言: {target_lang}")
        
        result = await demo.translate(text, target_lang)
        
        print(f"翻译结果: {result['translated_text']}")
        print(f"置信度: {result['confidence']}")
        print("-" * 50)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 