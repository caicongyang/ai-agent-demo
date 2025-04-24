import os
import pandas as pd
import akshare as ak
from deepseek_chat import DeepSeekChat
from datetime import datetime


def analyze_stock_data(chat: DeepSeekChat, stock_data: pd.DataFrame) -> str:
    """分析股票数据"""

    try:
        # 构建分析请求，包含角色提示
        analysis_request = f"""
# Role: 主力动向分析师

## Profile
- language: 中文
- description: 主力动向分析师专注于通过分析集合竞价时间的资金明细，识别和预测主力资金的动向，帮助投资者做出更明智的投资决策。
- background: 拥有金融分析、数据科学和人工智能的背景，专注于股票市场的主力资金分析。
- personality: 严谨、细致、逻辑性强
- expertise: 金融数据分析、主力资金动向预测、股票市场分析
- target_audience: 股票投资者、金融分析师、投资机构

## Skills
1. 数据分析
   - 数据清洗: 能够处理和分析大量的历史分笔数据，确保数据的准确性和完整性。
   - 模式识别: 能够识别主力资金的典型操作模式，如大单买入或卖出。
   - 趋势预测: 基于历史数据，预测股票的未来走势。
   - 异常检测: 能够检测数据中的异常点，如异常的大单交易。

2. 金融知识
   - 股票市场分析: 深入理解股票市场的运作机制和影响因素。
   - 主力资金行为分析: 熟悉主力资金的常见操作手法和策略。
   - 投资策略建议: 能够根据分析结果，提供具体的投资策略建议。

## Rules
1. 基本原则：
   - 数据驱动: 所有分析和结论必须基于提供的数据，禁止编造或假设数据。
   - 客观公正: 分析过程中保持客观，不受个人情感或外部因素影响。
   - 透明性: 分析方法和过程必须透明，便于验证和复现。
   - 及时性: 分析结果应及时提供，确保信息的时效性。

2. 行为准则：
   - 保密性: 严格保护用户提供的数据，不泄露任何敏感信息。
   - 专业性: 保持专业态度，提供高质量的分析服务。
   - 用户导向: 以用户需求为中心，提供有针对性的分析建议。
   - 持续学习: 不断更新知识和技能，适应市场变化。

3. 限制条件：
   - 数据限制: 分析结果受限于提供的数据质量和数量。
   - 市场风险: 股票市场存在不确定性，分析结果仅供参考。
   - 时间限制: 分析过程可能需要一定时间，用户需耐心等待。
   - 技术限制: 分析工具和方法可能存在技术限制，影响分析结果。

## Workflows
- 目标: 分析个股的历史分笔数据，识别主力资金的动向，预测未来走势。
- 步骤 1: 数据清洗和预处理，确保数据的准确性和完整性。
- 步骤 2: 分析数据中的大单交易，识别主力资金的典型操作模式。
- 步骤 3: 基于识别出的模式，预测股票的未来走势。
- 预期结果: 提供详细的分析报告，包括主力资金的操作手法和未来走势预测。

## Initialization
作为主力动向分析师，你必须遵守上述Rules，按照Workflows执行任务。

---

以下是个股的历史分笔数据，这是三天的数据{fenbi_data1},{fenbi_data2},{fenbi_data3}，
你帮我分析一下这只股票是否存在主力操盘的行为，如果是，那么主力是如何操作的，以及接下来的走势如何？
必须根据投喂你的数据进行分析，禁止自己编造假数据。描述当天的股价走势，自证没有虚构数据。你的观点需要数据支撑。
"""

        # 发送请求并获取分析结果
        result = chat.simple_chat(analysis_request)

        # 返回分析结果
        return result

    except Exception as e:
        return f"分析过程中发生错误: {str(e)}"


def save_to_markdown(content: str, stock_code: str) -> str:
    """将分析结果保存为Markdown文件"""
    try:
        # 创建文件名，包含股票代码和当前日期时间
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{stock_code}_analysis_{now}.md"

        # 写入文件
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        return filename
    except Exception as e:
        print(f"保存Markdown文件时出错: {e}")
        return None


def main():
    try:
        # 初始化 DeepSeekChat
        chat = DeepSeekChat()

        # 设置要分析的股票代码
        stock_code = "sh601177"  # 例如：sh603200 是上海洗霸

        print(f"正在获取股票 {stock_code} 的分笔数据...")

        # 使用 akshare 直接从接口获取股票分笔数据
        try:
            # 获取最新交易日的分笔数据
            df = ak.stock_zh_a_tick_tx_js(symbol=stock_code)

            # 打印数据基本信息
            print(f"获取到 {len(df)} 条分笔数据")
            print(f"数据列: {df.columns.tolist()}")
            print(f"数据样例:\n{df.head()}")

            # 分析股票数据
            print("开始分析股票数据...")
            result = analyze_stock_data(chat, df)

            # 保存分析结果到Markdown文件
            md_file = save_to_markdown(result, stock_code)
            if md_file:
                print(f"分析报告已保存到: {md_file}")

            # 打印分析结果
            print("\n" + "=" * 50)
            print(f"股票 {stock_code} 分析报告")
            print("=" * 50 + "\n")
            print(result)
            print("\n" + "=" * 50)

        except Exception as e:
            print(f"获取股票数据失败: {e}")
            print("尝试使用备用方法...")

            # 如果接口获取失败，尝试从本地文件读取
            csv_file = os.path.join(os.path.dirname(__file__), 'sh603200_20050303_tick.csv')
            if os.path.exists(csv_file):
                print(f"从本地文件 {csv_file} 读取数据")
                df = pd.read_csv(csv_file)

                # 分析股票数据
                print("开始分析股票数据...")
                result = analyze_stock_data(chat, df)

                # 保存分析结果到Markdown文件
                md_file = save_to_markdown(result, stock_code)
                if md_file:
                    print(f"分析报告已保存到: {md_file}")

                # 打印分析结果
                print("\n" + "=" * 50)
                print("股票分析报告 (从本地文件)")
                print("=" * 50 + "\n")
                print(result)
                print("\n" + "=" * 50)
            else:
                print(f"本地文件 {csv_file} 不存在")
                raise

    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()
