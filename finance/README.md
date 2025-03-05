# 交易策略智能体系统

这个系统实现了一个基于多智能体协作的交易策略分析框架，利用LangGraph和大语言模型构建了一个可扩展的交易决策系统。

## 系统架构

系统包含四个专业智能体：

1. **高频交易信号Agent**：分析分笔数据，检测大单异动和委托队列特征
   - 大单异动检测：识别单笔成交超过日均值2倍以上的订单
   - 委托队列分析：监控买一/卖一档位的挂单撤单频率，计算护盘系数

2. **概念博弈Agent**：分析涨停股和概念热度
   - 概念热度量化：计算涨停概念强度指数
   - 梯队健康度评估：分析概念内个股涨停时间排序，检测资金分歧程度

3. **量价策略Agent**：分析量价关系和多周期共振
   - 量价模型构建：计算量比-价格弹性指数，检测关键位突破有效性
   - 多周期共振判断：结合多个时间周期的技术指标，判断趋势一致性

4. **决策整合Agent**：整合各Agent信号，生成最终交易策略
   - 多信号融合：使用加权投票模型整合各Agent信号，解决信号冲突
   - 动态策略生成：根据市场状态切换策略模式，生成带条件的操作指令

## 工作流程

1. 接收市场数据（分笔数据、概念数据、K线数据）
2. 三个专业Agent并行分析数据
3. 决策整合Agent融合各Agent结果
4. 生成最终交易策略

## 使用方法

### 安装依赖

确保已安装以下依赖：

```bash
pip install langchain langchain-openai langgraph pandas numpy python-dotenv
```

### 环境变量配置

在项目根目录的`.env`文件中配置：

```
LLM_API_KEY=your_api_key
LLM_BASE_URL=your_api_base_url
```

### 基本用法

```python
from finance.trading_strategy_agents import TradingStrategyAgents
import asyncio

async def main():
    # 创建交易策略智能体系统实例
    trading_agents = TradingStrategyAgents()
    
    # 准备市场数据
    market_data = {
        "tick_data": {...},  # 分笔数据
        "concept_data": {...},  # 概念数据
        "kline_data": {...},  # K线数据
        "risk_preference": "中等风险"  # 用户风险偏好
    }
    
    # 运行策略分析
    result = await trading_agents.run(market_data)
    
    # 输出最终策略
    print(result['final_strategy'])

if __name__ == "__main__":
    asyncio.run(main())
```

### 运行示例

直接运行示例脚本：

```bash
python finance/trading_strategy_example.py
```

## 数据结构

### 输入数据

- **分笔数据**：包含实时成交价、成交量、委托队列等信息
- **概念数据**：包含概念名称、概念股列表、涨停股列表等信息
- **K线数据**：包含OHLCV等基本行情数据

### 输出结果

- **高频交易信号**：大单异动、委托队列分析结果
- **概念博弈分析**：概念热度、梯队健康度评估
- **量价策略分析**：量价关系、多周期共振判断
- **最终交易策略**：标的列表、买卖点规则、仓位建议

## 扩展与定制

系统设计为可扩展架构，可以通过以下方式进行定制：

1. 修改各Agent的提示模板，调整分析逻辑
2. 添加新的专业Agent，扩展分析维度
3. 调整决策整合Agent的权重模型，优化策略生成

## 注意事项

- 本系统仅提供交易策略分析，不直接执行交易操作
- 实际应用中需要接入真实市场数据源
- 交易决策应结合个人风险偏好和市场经验 