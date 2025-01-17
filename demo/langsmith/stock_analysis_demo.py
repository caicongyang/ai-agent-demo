"""
这个示例展示了如何使用 LangSmith 进行追踪和评估：
1. 如何追踪 LLM 调用
2. 如何创建评估数据集
3. 如何运行评估实验
"""

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langsmith import Client, traceable
from dotenv import load_dotenv
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class StockAnalysisDemo:
    """股票分析演示类"""
    
    def __init__(self):
        """初始化演示实例"""
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        self.client = Client()
        logger.info("股票分析演示实例初始化完成")

    @traceable(name="stock_analysis")
    async def analyze_stock(self, stock_code: str) -> Dict[str, Any]:
        """分析股票"""
        logger.info(f"开始分析股票: {stock_code}")
        try:
            result = await self.llm.ainvoke([
                {"role": "system", "content": """你是一个专业的股票分析师。
请对给定的股票进行分析，包括：
1. 基本面分析
2. 技术面分析
3. 投资建议"""},
                {"role": "user", "content": f"请分析股票 {stock_code} 的投资价值。"}
            ])
            return {
                "stock_code": stock_code,
                "analysis": result.content,
                "confidence": 0.85
            }
        except Exception as e:
            logger.error(f"分析失败: {e}")
            return {
                "stock_code": stock_code,
                "analysis": "分析失败",
                "confidence": 0.0
            }

    async def create_evaluation_dataset(self):
        """创建评估数据集"""
        logger.info("创建评估数据集")
        try:
            # 添加时间戳创建唯一数据集名称
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dataset_name = f"Stock_Analysis_Dataset_{timestamp}"
            
            # 创建数据集
            dataset = self.client.create_dataset(
                dataset_name,
                description="用于评估股票分析性能的数据集"
            )

            # 添加测试用例
            self.client.create_examples(
                inputs=[
                    {"stock_code": "000001"},
                    {"stock_code": "600519"},
                    {"stock_code": "300059"}
                ],
                outputs=[
                    {"analysis": "平安银行是...", "confidence": 0.9},
                    {"analysis": "贵州茅台是...", "confidence": 0.95},
                    {"analysis": "东方财富是...", "confidence": 0.85}
                ],
                dataset_id=dataset.id
            )
            
            logger.info(f"成功创建数据集: {dataset_name}")
            return dataset
        except Exception as e:
            logger.error(f"创建数据集失败: {e}")
            return None

    def evaluate_exact_match(self, outputs: Dict, reference_outputs: Dict) -> Dict:
        """评估函数：检查置信度是否达标"""
        confidence_threshold = 0.8
        is_confident = outputs.get("confidence", 0) >= confidence_threshold
        return {
            "score": 1.0 if is_confident else 0.0,
            "reasoning": f"置信度{'达标' if is_confident else '未达标'}"
        }

    async def run_evaluation(self):
        """运行评估"""
        logger.info("开始运行评估")
        try:
            # 创建数据集
            dataset = await self.create_evaluation_dataset()
            if not dataset:
                return
            
            # 运行评估 - 使用 aevaluate 替代 evaluate
            from langsmith import aevaluate
            
            experiment_results = await aevaluate(
                self.analyze_stock,
                data=dataset,
                evaluators=[self.evaluate_exact_match],
                experiment_prefix="stock-analysis",
                metadata={
                    "version": "1.0.0",
                    "model": "deepseek-chat"
                },
                max_concurrency=4
            )
            
            return experiment_results
        except Exception as e:
            logger.error(f"评估失败: {e}")
            return None

async def main():
    """主函数"""
    demo = StockAnalysisDemo()
    
    # 测试单个分析
    print("\n测试股票分析:")
    result = await demo.analyze_stock("000001")
    print(f"分析结果: {result}")
    
    # 运行评估
    print("\n运行评估实验:")
    eval_results = await demo.run_evaluation()
    if eval_results:
        print("评估完成，请在 LangSmith 界面查看详细结果")
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 