#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流代码解释器实际应用示例
展示如何在真实业务场景中使用工作流模式
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from workflow_code_interpreter import WorkflowEngine, WorkflowTool, WorkflowContext


class StockDataTool(WorkflowTool):
    """股票数据获取工具（模拟）"""
    
    def __init__(self):
        super().__init__(
            name="stock_data_fetcher",
            description="获取股票数据"
        )
    
    def execute(self, context: WorkflowContext, **kwargs) -> dict:
        """模拟获取股票数据"""
        symbol = kwargs.get('symbol', 'AAPL')
        days = kwargs.get('days', 30)
        data_key = kwargs.get('data_key', 'stock_data')
        
        # 模拟股票数据
        import random
        base_price = 150.0
        stock_data = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i-1)).strftime('%Y-%m-%d')
            # 模拟价格波动
            change = random.uniform(-0.05, 0.05)
            base_price *= (1 + change)
            
            stock_data.append({
                'date': date,
                'symbol': symbol,
                'open': round(base_price * random.uniform(0.99, 1.01), 2),
                'high': round(base_price * random.uniform(1.01, 1.05), 2),
                'low': round(base_price * random.uniform(0.95, 0.99), 2),
                'close': round(base_price, 2),
                'volume': random.randint(1000000, 5000000)
            })
        
        context.add_data(data_key, stock_data, source=f"StockAPI:{symbol}")
        
        return {
            "success": True,
            "data": stock_data,
            "symbol": symbol,
            "days": days,
            "message": f"成功获取 {symbol} {days} 天的股票数据"
        }


class WeatherDataTool(WorkflowTool):
    """天气数据获取工具（模拟）"""
    
    def __init__(self):
        super().__init__(
            name="weather_data_fetcher",
            description="获取天气数据"
        )
    
    def execute(self, context: WorkflowContext, **kwargs) -> dict:
        """模拟获取天气数据"""
        city = kwargs.get('city', 'Beijing')
        days = kwargs.get('days', 7)
        data_key = kwargs.get('data_key', 'weather_data')
        
        # 模拟天气数据
        import random
        weather_conditions = ['晴', '多云', '阴', '小雨', '中雨']
        weather_data = []
        
        for i in range(days):
            date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            temp = random.randint(15, 30)
            
            weather_data.append({
                'date': date,
                'city': city,
                'temperature': temp,
                'condition': random.choice(weather_conditions),
                'humidity': random.randint(40, 80),
                'wind_speed': random.randint(5, 15)
            })
        
        context.add_data(data_key, weather_data, source=f"WeatherAPI:{city}")
        
        return {
            "success": True,
            "data": weather_data,
            "city": city,
            "days": days,
            "message": f"成功获取 {city} {days} 天的天气数据"
        }


class EmailSenderTool(WorkflowTool):
    """邮件发送工具（模拟）"""
    
    def __init__(self):
        super().__init__(
            name="email_sender",
            description="发送邮件通知"
        )
    
    def execute(self, context: WorkflowContext, **kwargs) -> dict:
        """模拟发送邮件"""
        to_email = kwargs.get('to_email', 'user@example.com')
        subject = kwargs.get('subject', '工作流执行结果')
        content = kwargs.get('content', '')
        
        # 如果没有提供内容，从上下文生成
        if not content:
            content = f"工作流执行完成\n\n"
            content += f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += f"数据项数量: {len(context.data)}\n"
            content += f"执行步骤: {len(context.history)}\n\n"
            
            # 添加数据摘要
            for key, value in context.data.items():
                metadata = context.metadata.get(key, {})
                content += f"- {key}: {type(value).__name__} (来源: {metadata.get('source', 'Unknown')})\n"
        
        # 模拟邮件发送
        print(f"📧 模拟发送邮件:")
        print(f"   收件人: {to_email}")
        print(f"   主题: {subject}")
        print(f"   内容: {content[:100]}...")
        
        return {
            "success": True,
            "to_email": to_email,
            "subject": subject,
            "message": f"邮件已发送到 {to_email}"
        }


def example_stock_analysis():
    """股票分析工作流示例"""
    print("📈 股票分析工作流示例")
    print("=" * 50)
    
    engine = WorkflowEngine()
    engine.register_tool(StockDataTool())
    engine.register_tool(EmailSenderTool())
    
    workflow_steps = [
        {
            "tool": "stock_data_fetcher",
            "description": "获取苹果公司股票数据",
            "symbol": "AAPL",
            "days": 30,
            "data_key": "aapl_data"
        },
        {
            "tool": "stock_data_fetcher", 
            "description": "获取谷歌公司股票数据",
            "symbol": "GOOGL",
            "days": 30,
            "data_key": "googl_data"
        },
        {
            "tool": "workflow_code_interpreter",
            "description": "分析股票数据并生成报告",
            "code": """
import statistics

# 获取股票数据
aapl_data = context_data.get('aapl_data', [])
googl_data = context_data.get('googl_data', [])

print("=== 股票分析报告 ===")
print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def analyze_stock(data, symbol):
    if not data:
        return f"{symbol}: 无数据"
    
    prices = [item['close'] for item in data]
    volumes = [item['volume'] for item in data]
    
    # 基本统计
    current_price = prices[-1]
    start_price = prices[0]
    price_change = current_price - start_price
    price_change_pct = (price_change / start_price) * 100
    
    # 技术指标
    avg_price = statistics.mean(prices)
    max_price = max(prices)
    min_price = min(prices)
    avg_volume = statistics.mean(volumes)
    
    # 波动性
    price_volatility = statistics.stdev(prices) if len(prices) > 1 else 0
    
    result = f\"\"\"
{symbol} 股票分析:
  当前价格: ${current_price:.2f}
  期间涨跌: ${price_change:+.2f} ({price_change_pct:+.2f}%)
  平均价格: ${avg_price:.2f}
  最高价格: ${max_price:.2f}
  最低价格: ${min_price:.2f}
  平均成交量: {avg_volume:,.0f}
  价格波动性: ${price_volatility:.2f}
  \"\"\"
    
    return result.strip()

# 分析两只股票
aapl_analysis = analyze_stock(aapl_data, 'AAPL')
googl_analysis = analyze_stock(googl_data, 'GOOGL')

print(aapl_analysis)
print()
print(googl_analysis)

# 比较分析
if aapl_data and googl_data:
    aapl_return = (aapl_data[-1]['close'] - aapl_data[0]['close']) / aapl_data[0]['close'] * 100
    googl_return = (googl_data[-1]['close'] - googl_data[0]['close']) / googl_data[0]['close'] * 100
    
    print("\\n=== 比较分析 ===")
    print(f"AAPL 收益率: {aapl_return:+.2f}%")
    print(f"GOOGL 收益率: {googl_return:+.2f}%")
    
    if aapl_return > googl_return:
        print("💡 AAPL 在此期间表现更好")
    elif googl_return > aapl_return:
        print("💡 GOOGL 在此期间表现更好") 
    else:
        print("💡 两只股票表现相当")

# 生成投资建议
print("\\n=== 投资建议 ===")
if aapl_data and googl_data:
    aapl_volatility = statistics.stdev([item['close'] for item in aapl_data])
    googl_volatility = statistics.stdev([item['close'] for item in googl_data])
    
    if aapl_volatility < googl_volatility:
        print("📊 AAPL 波动性较低，适合稳健投资者")
        print("📊 GOOGL 波动性较高，适合风险偏好投资者")
    else:
        print("📊 GOOGL 波动性较低，适合稳健投资者")
        print("📊 AAPL 波动性较高，适合风险偏好投资者")

print("\\n⚠️  风险提示: 以上分析仅供参考，投资有风险，入市需谨慎")
            """,
            "result_key": "stock_analysis_report"
        },
        {
            "tool": "email_sender",
            "description": "发送分析报告邮件",
            "to_email": "investor@example.com",
            "subject": "股票分析报告 - AAPL vs GOOGL",
            "content": "请查看附件中的详细股票分析报告。"
        }
    ]
    
    return engine.execute_workflow(workflow_steps)


def example_weather_business_analysis():
    """天气数据对业务影响分析"""
    print("\n🌤️ 天气数据业务影响分析")
    print("=" * 50)
    
    engine = WorkflowEngine()
    engine.register_tool(WeatherDataTool())
    
    workflow_steps = [
        {
            "tool": "weather_data_fetcher",
            "description": "获取北京天气数据",
            "city": "Beijing",
            "days": 7,
            "data_key": "beijing_weather"
        },
        {
            "tool": "database_query",
            "description": "获取历史销售数据",
            "query": "SELECT * FROM sales",
            "data_key": "sales_data"
        },
        {
            "tool": "workflow_code_interpreter",
            "description": "分析天气对销售的影响",
            "code": """
# 天气与业务关联分析
weather_data = context_data.get('beijing_weather', [])
sales_data = context_data.get('sales_data', [])

print("=== 天气业务影响分析 ===")

if weather_data:
    print("\\n📊 天气预报概览:")
    for day in weather_data:
        print(f"  {day['date']}: {day['condition']}, {day['temperature']}°C, 湿度{day['humidity']}%")
    
    # 天气统计
    sunny_days = len([d for d in weather_data if d['condition'] == '晴'])
    rainy_days = len([d for d in weather_data if '雨' in d['condition']])
    avg_temp = sum(d['temperature'] for d in weather_data) / len(weather_data)
    
    print(f"\\n🌞 晴天: {sunny_days} 天")
    print(f"🌧️  雨天: {rainy_days} 天") 
    print(f"🌡️  平均温度: {avg_temp:.1f}°C")
    
    # 业务预测
    print("\\n=== 业务影响预测 ===")
    
    # 根据天气条件预测销售影响
    weather_impact = {
        '晴': 1.2,    # 晴天销售增加20%
        '多云': 1.0,  # 多云正常
        '阴': 0.9,    # 阴天略微下降
        '小雨': 0.8,  # 小雨下降20%
        '中雨': 0.6   # 中雨下降40%
    }
    
    if sales_data:
        base_daily_sales = sum(item['amount'] for item in sales_data) / len(sales_data)
        print(f"历史日均销售额: {base_daily_sales:.2f}")
        
        total_predicted_sales = 0
        print("\\n📈 未来7天销售预测:")
        
        for day in weather_data:
            condition = day['condition']
            impact_factor = weather_impact.get(condition, 1.0)
            predicted_sales = base_daily_sales * impact_factor
            total_predicted_sales += predicted_sales
            
            print(f"  {day['date']} ({condition}): {predicted_sales:.2f} (影响系数: {impact_factor})")
        
        print(f"\\n📊 预测周销售总额: {total_predicted_sales:.2f}")
        weekly_change = (total_predicted_sales - base_daily_sales * 7) / (base_daily_sales * 7) * 100
        print(f"📊 相比平均水平: {weekly_change:+.1f}%")
    
    # 运营建议
    print("\\n=== 运营建议 ===")
    if rainy_days >= 3:
        print("☔ 雨天较多，建议:")
        print("   - 增加室内活动相关产品库存")
        print("   - 推出雨天优惠活动")
        print("   - 加强外卖配送服务")
    
    if sunny_days >= 5:
        print("☀️ 晴天较多，建议:")
        print("   - 增加户外用品库存")
        print("   - 推出户外活动促销")
        print("   - 延长营业时间")
    
    if avg_temp > 25:
        print("🔥 温度较高，建议:")
        print("   - 增加清凉饮品供应")
        print("   - 推广防暑用品")
        print("   - 调整店内空调温度")
    elif avg_temp < 15:
        print("🧥 温度较低，建议:")
        print("   - 增加热饮供应")
        print("   - 推广保暖用品")
        print("   - 提供温暖的购物环境")

print("\\n💡 以上分析基于历史数据和天气预报，实际情况可能有所不同")
            """,
            "result_key": "weather_business_analysis"
        }
    ]
    
    return engine.execute_workflow(workflow_steps)


def example_data_pipeline():
    """数据管道处理示例"""
    print("\n🔄 数据管道处理示例")
    print("=" * 50)
    
    engine = WorkflowEngine()
    
    # 创建示例数据文件
    raw_data = {
        "transactions": [
            {"id": 1, "user_id": 101, "amount": 299.99, "date": "2024-01-01", "status": "completed"},
            {"id": 2, "user_id": 102, "amount": 199.50, "date": "2024-01-02", "status": "pending"},
            {"id": 3, "user_id": 101, "amount": 599.00, "date": "2024-01-03", "status": "completed"},
            {"id": 4, "user_id": 103, "amount": 99.99, "date": "2024-01-04", "status": "failed"},
            {"id": 5, "user_id": 102, "amount": 399.00, "date": "2024-01-05", "status": "completed"},
        ]
    }
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(raw_data, f)
        temp_file = f.name
    
    workflow_steps = [
        {
            "tool": "file_reader",
            "description": "读取原始交易数据",
            "file_path": temp_file,
            "data_key": "raw_transactions"
        },
        {
            "tool": "workflow_code_interpreter",
            "description": "数据清洗和预处理",
            "code": """
# 数据清洗和预处理
raw_data = context_data.get('raw_transactions', {})
transactions = raw_data.get('transactions', [])

print("=== 数据清洗和预处理 ===")
print(f"原始数据量: {len(transactions)} 条交易记录")

# 数据质量检查
valid_transactions = []
invalid_transactions = []

for trans in transactions:
    # 检查必要字段
    if all(key in trans for key in ['id', 'user_id', 'amount', 'date', 'status']):
        # 检查数据类型和范围
        if (isinstance(trans['amount'], (int, float)) and trans['amount'] > 0 and
            trans['status'] in ['completed', 'pending', 'failed']):
            valid_transactions.append(trans)
        else:
            invalid_transactions.append(trans)
    else:
        invalid_transactions.append(trans)

print(f"有效记录: {len(valid_transactions)} 条")
print(f"无效记录: {len(invalid_transactions)} 条")

# 数据转换
processed_transactions = []
for trans in valid_transactions:
    processed_trans = trans.copy()
    
    # 添加计算字段
    processed_trans['amount_category'] = (
        'high' if trans['amount'] > 400 else
        'medium' if trans['amount'] > 200 else
        'low'
    )
    
    # 日期处理
    from datetime import datetime
    processed_trans['date_obj'] = datetime.strptime(trans['date'], '%Y-%m-%d')
    processed_trans['day_of_week'] = processed_trans['date_obj'].strftime('%A')
    
    processed_transactions.append(processed_trans)

print(f"处理后记录: {len(processed_transactions)} 条")

# 保存清洗后的数据到上下文
import json
context_data['cleaned_transactions'] = processed_transactions
print("✅ 数据清洗完成")
            """,
            "result_key": "data_cleaning_result"
        },
        {
            "tool": "workflow_code_interpreter",
            "description": "数据分析和统计",
            "code": """
# 数据分析和统计
cleaned_data = context_data.get('cleaned_transactions', [])

print("\\n=== 数据分析报告 ===")

if not cleaned_data:
    print("❌ 无有效数据进行分析")
else:
    # 基础统计
    total_transactions = len(cleaned_data)
    completed_transactions = [t for t in cleaned_data if t['status'] == 'completed']
    total_revenue = sum(t['amount'] for t in completed_transactions)
    avg_transaction_value = total_revenue / len(completed_transactions) if completed_transactions else 0
    
    print(f"📊 基础统计:")
    print(f"   总交易数: {total_transactions}")
    print(f"   已完成交易: {len(completed_transactions)}")
    print(f"   总收入: ${total_revenue:.2f}")
    print(f"   平均交易价值: ${avg_transaction_value:.2f}")
    
    # 状态分析
    status_count = {}
    for trans in cleaned_data:
        status = trans['status']
        status_count[status] = status_count.get(status, 0) + 1
    
    print(f"\\n📈 交易状态分布:")
    for status, count in status_count.items():
        percentage = count / total_transactions * 100
        print(f"   {status}: {count} ({percentage:.1f}%)")
    
    # 金额分类分析
    amount_categories = {}
    for trans in cleaned_data:
        category = trans['amount_category']
        amount_categories[category] = amount_categories.get(category, 0) + 1
    
    print(f"\\n💰 交易金额分布:")
    for category, count in amount_categories.items():
        percentage = count / total_transactions * 100
        print(f"   {category}: {count} ({percentage:.1f}%)")
    
    # 用户分析
    user_stats = {}
    for trans in cleaned_data:
        user_id = trans['user_id']
        if user_id not in user_stats:
            user_stats[user_id] = {'count': 0, 'total_amount': 0}
        user_stats[user_id]['count'] += 1
        if trans['status'] == 'completed':
            user_stats[user_id]['total_amount'] += trans['amount']
    
    print(f"\\n👥 用户分析:")
    print(f"   活跃用户数: {len(user_stats)}")
    
    # 找出最有价值的用户
    if user_stats:
        top_user = max(user_stats.items(), key=lambda x: x[1]['total_amount'])
        print(f"   最有价值用户: ID {top_user[0]} (消费 ${top_user[1]['total_amount']:.2f})")
    
    # 星期几分析
    weekday_stats = {}
    for trans in cleaned_data:
        weekday = trans['day_of_week']
        weekday_stats[weekday] = weekday_stats.get(weekday, 0) + 1
    
    print(f"\\n📅 星期分布:")
    for weekday, count in weekday_stats.items():
        print(f"   {weekday}: {count} 笔交易")
    
    # 业务洞察
    print(f"\\n💡 业务洞察:")
    success_rate = len(completed_transactions) / total_transactions * 100
    print(f"   交易成功率: {success_rate:.1f}%")
    
    if success_rate < 80:
        print("   ⚠️  交易成功率较低，需要优化支付流程")
    
    high_value_ratio = amount_categories.get('high', 0) / total_transactions * 100
    if high_value_ratio > 30:
        print("   📈 高价值交易占比较高，用户质量良好")
    
    # 生成数据质量报告
    print(f"\\n📋 数据质量报告:")
    print(f"   数据完整性: 100% (所有记录都有必要字段)")
    print(f"   数据准确性: 通过基本验证")
    print(f"   数据一致性: 状态字段标准化")
            """,
            "result_key": "data_analysis_result"
        }
    ]
    
    result = engine.execute_workflow(workflow_steps)
    
    # 清理临时文件
    try:
        import os
        os.unlink(temp_file)
    except:
        pass
    
    return result


def main():
    """主函数"""
    print("🔄 工作流代码解释器实际应用示例")
    print("=" * 60)
    
    while True:
        print("\n请选择示例:")
        print("1. 股票数据分析工作流")
        print("2. 天气数据业务影响分析")
        print("3. 数据管道处理示例")
        print("0. 退出")
        
        choice = input("\n请输入选择 (0-3): ").strip()
        
        if choice == "1":
            example_stock_analysis()
        elif choice == "2":
            example_weather_business_analysis()
        elif choice == "3":
            example_data_pipeline()
        elif choice == "0":
            print("👋 再见!")
            break
        else:
            print("❌ 无效选择，请重新输入")


if __name__ == "__main__":
    main()
