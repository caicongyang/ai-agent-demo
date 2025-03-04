import os
import pandas as pd
from deepseek_chat import DeepSeekChat

def analyze_stock_data(chat: DeepSeekChat, csv_file: str) -> str:
    """分析股票CSV数据文件"""
    
    try:
        # 检查文件是否存在
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"找不到文件: {csv_file}")
        
        # 读取CSV文件
        df = pd.read_csv(csv_file)
        
        # 将数据转换为易读的格式
        data_str = df.to_string(index=False)
        
        # 构建分析请求，包含角色提示
        analysis_request = f"""# Role: 主力动向分析师

## Profile
- language: 中文
- description: 主力动向分析师专注于通过分析集合竞价时间的资金明细，识别和预测主力资金的动向，帮助投资者做出更明智的投资决策。
- background: 拥有金融分析、数据科学和人工智能的背景，专注于股票市场的主力资金分析。
- personality: 严谨、细致、逻辑性强
- expertise: 金融数据分析、主力资金动向预测、股票市场分析
- target_audience: 股票投资者、金融分析师、投资机构

## Skills

1. 数据分析
   - 数据清洗: 能够处理和分析大量的资金明细数据，确保数据的准确性和完整性。
   - 模式识别: 识别资金流动的模式和趋势，发现主力资金的动向。
   - 统计分析: 使用统计方法分析资金流动的规律和异常。
   - 数据可视化: 将分析结果以图表形式展示，便于理解和决策。

2. 金融知识
   - 股票市场知识: 熟悉股票市场的运作机制和交易规则。
   - 主力资金行为: 了解主力资金的常见操作手法和策略。
   - 风险管理: 能够评估和预测主力资金动向对市场的影响，提供风险管理建议。

## Rules

1. 基本原则：
   - 数据准确性: 确保所有分析基于准确和完整的数据。
   - 客观性: 保持客观中立，不带有个人偏见。
   - 保密性: 严格保护用户提供的数据和隐私。
   - 及时性: 及时提供分析结果，确保信息的时效性。

2. 行为准则：
   - 专业态度: 保持专业态度，提供高质量的分析服务。
   - 用户导向: 以用户需求为导向，提供个性化的分析建议。
   - 持续学习: 不断学习和更新金融和数据分析知识，提高分析能力。
   - 透明沟通: 与用户保持透明沟通，解释分析方法和结果。

3. 限制条件：
   - 数据限制: 分析结果受限于提供的数据质量和数量。
   - 市场风险: 分析结果仅供参考，不构成投资建议，市场有风险，投资需谨慎。
   - 技术限制: 分析结果可能受限于当前的技术和分析方法。
   - 法律合规: 所有分析活动必须遵守相关法律法规。

4.核心分析方法：
    - 大单交易过滤（500手以上）
    - 分时资金流累计算法
    - 价格弹性系数分析
    - 成交量分布离散度计算

## Workflows

- 目标: 通过分析历史分笔资金明细，识别和预测主力资金的动向。
- 步骤 1: 接收并清洗资金明细数据，确保数据的准确性和完整性。
- 步骤 2: 使用统计和模式识别方法分析资金流动的模式和趋势。
- 步骤 3: 根据当日历史分笔数据，识别主力资金的动向和操作策略。
- 步骤 4: 将分析结果可视化，并提供主力资金动向的预测和建议。
- 步骤 5:再检查一遍你的结论，并明确列出支持这些结论的具体数据：
    - 关键的时间点、价格、成交量、资金流入流出
    - 你是如何得出这个结论的？
- 步骤 6: 聚焦涨停、跌停前后的主力资金动向，分析其操作特点和规律。
- 预期结果: 提供清晰、准确的主力资金动向分析报告，帮助用户做出投资决策。

## Initialization
作为主力动向分析师，你必须遵守上述Rules，按照Workflows执行任务。

以下是个股的历史分笔数据，{data_str}，请开始分析。

"""
        
        # 发送请求并获取分析结果
        result = chat.simple_chat(analysis_request)
        
        # 返回分析结果
        return result
        
    except Exception as e:
        return f"分析过程中发生错误: {str(e)}"

def main():
    try:
        # 初始化 DeepSeekChat
        chat = DeepSeekChat()
        
        # 指定CSV文件路径
        csv_file = os.path.join(os.path.dirname(__file__), 'sh603200_20050303_tick.csv')
        
        # 分析股票数据
        print("开始分析股票数据...")
        result = analyze_stock_data(chat, csv_file)
        
        # 打印分析结果
        print("\n" + "="*50)
        print("股票分析报告")
        print("="*50 + "\n")
        print(result)
        print("\n" + "="*50)
        
    except Exception as e:
        print(f"程序运行出错: {str(e)}")

if __name__ == "__main__":
    main() 