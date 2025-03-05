"""
交易策略智能体系统使用示例

这个脚本展示了如何使用 TradingStrategyAgents 类来分析市场数据并生成交易策略。
"""

import asyncio
import json
from datetime import datetime
from trading_strategy_agents import TradingStrategyAgents

async def run_example():
    """运行交易策略示例"""
    print("=== 交易策略智能体系统示例 ===")
    
    # 创建交易策略智能体系统实例
    trading_agents = TradingStrategyAgents()
    
    # 准备示例市场数据
    sample_market_data = {
        "tick_data": {
            "code": "sh603200",  # 上海机器人
            "time": "2024-03-04 09:30:00",
            "price": 25.68,
            "volume": 10000,
            "amount": 256800.0,
            "bid_price": [25.67, 25.66, 25.65, 25.64, 25.63],
            "bid_volume": [2000, 3000, 5000, 4000, 6000],
            "ask_price": [25.69, 25.70, 25.71, 25.72, 25.73],
            "ask_volume": [1500, 2500, 3500, 4500, 5500]
        },
        "concept_data": {
            "concept_name": "机器人",
            "stocks": ["sh603200", "sz300024", "sh688169"],
            "limit_up_stocks": ["sh603200", "sz300024"],
            "limit_up_time": {"sh603200": "09:45:00", "sz300024": "10:15:00"},
            "leader_stocks": ["sh603200"],
            "seal_amount": {"sh603200": 50000000.0, "sz300024": 30000000.0}
        },
        "kline_data": {
            "code": "sh603200",
            "date": "2024-03-04",
            "open": 25.10,
            "high": 26.80,
            "low": 25.05,
            "close": 26.61,
            "volume": 1500000,
            "amount": 39915000.0,
            "turnover": 2.5
        },
        "risk_preference": "中等风险"
    }
    
    # 运行策略分析流程
    print("正在分析市场数据...")
    result = await trading_agents.run(sample_market_data)
    
    # 保存结果到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trading_strategy_{sample_market_data['tick_data']['code']}_{timestamp}.md"
    
    with open(f"finance/{filename}", "w", encoding="utf-8") as f:
        f.write(f"# 交易策略分析报告 - {sample_market_data['tick_data']['code']}\n\n")
        f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 市场数据概览\n\n")
        f.write(f"- 股票代码: {sample_market_data['tick_data']['code']}\n")
        f.write(f"- 概念板块: {sample_market_data['concept_data']['concept_name']}\n")
        f.write(f"- 当前价格: {sample_market_data['tick_data']['price']}\n")
        f.write(f"- 成交量: {sample_market_data['kline_data']['volume']}\n\n")
        
        f.write("## 高频交易信号分析\n\n")
        for step in result['steps']:
            if 'hft_agent' in step:
                f.write(f"{step['hft_agent']['hft_signal']}\n\n")
                break
        
        f.write("## 概念博弈分析\n\n")
        for step in result['steps']:
            if 'concept_agent' in step:
                f.write(f"{step['concept_agent']['concept_analysis']}\n\n")
                break
        
        f.write("## 量价策略分析\n\n")
        for step in result['steps']:
            if 'price_volume_agent' in step:
                f.write(f"{step['price_volume_agent']['price_volume_analysis']}\n\n")
                break
        
        f.write("## 最终交易策略\n\n")
        f.write(f"{result['final_strategy']}\n")
    
    print(f"分析完成，结果已保存到 finance/{filename}")
    print("\n=== 最终交易策略 ===")
    print(result['final_strategy'])

if __name__ == "__main__":
    asyncio.run(run_example()) 