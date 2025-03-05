"""
这个模块实现了一个多智能体交易策略系统：
1. 高频交易信号Agent：分析分笔数据，检测大单异动和委托队列
2. 概念博弈Agent：分析涨停股和概念热度
3. 量价策略Agent：分析量价关系和多周期共振
4. 决策整合Agent：整合各Agent信号，生成最终交易策略

工作流程：
1. 接收市场数据
2. 各专业Agent并行分析数据
3. 决策整合Agent融合各Agent结果
4. 生成最终交易策略
"""

from typing import Dict, Any, TypedDict, List, Optional, Union
from typing_extensions import TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from dotenv import load_dotenv
import os
import pandas as pd
import numpy as np
from datetime import datetime

# 加载环境变量配置
load_dotenv()

class TickData(TypedDict):
    """分笔数据结构"""
    code: str  # 股票代码
    time: str  # 时间戳
    price: float  # 成交价
    volume: int  # 成交量
    amount: float  # 成交额
    bid_price: List[float]  # 买盘价格
    bid_volume: List[int]  # 买盘量
    ask_price: List[float]  # 卖盘价格
    ask_volume: List[int]  # 卖盘量

class ConceptData(TypedDict):
    """概念数据结构"""
    concept_name: str  # 概念名称
    stocks: List[str]  # 概念包含的股票
    limit_up_stocks: List[str]  # 涨停股票
    limit_up_time: Dict[str, str]  # 涨停时间
    leader_stocks: List[str]  # 龙头股
    seal_amount: Dict[str, float]  # 封单金额

class KlineData(TypedDict):
    """K线数据结构"""
    code: str  # 股票代码
    date: str  # 日期
    open: float  # 开盘价
    high: float  # 最高价
    low: float  # 最低价
    close: float  # 收盘价
    volume: int  # 成交量
    amount: float  # 成交额
    turnover: float  # 换手率

class TradingStrategyState(TypedDict):
    """
    交易策略状态定义
    
    包含了整个策略分析过程中需要的所有状态：
    - market_data: 市场数据（分笔、概念、K线）
    - hft_signal: 高频交易信号
    - concept_analysis: 概念博弈分析
    - price_volume_analysis: 量价分析
    - final_strategy: 最终策略
    - steps: 执行步骤的历史记录
    """
    market_data: Dict[str, Any]  # 包含所有输入数据
    hft_signal: Dict[str, Any]  # 高频交易信号
    concept_analysis: Dict[str, Any]  # 概念博弈分析
    price_volume_analysis: Dict[str, Any]  # 量价分析
    final_strategy: Dict[str, Any]  # 最终策略
    steps: List[Dict]  # 执行步骤记录

class TradingStrategyAgents:
    """
    交易策略智能体系统
    
    实现了一个多智能体交易策略系统，包含四个智能体：
    1. 高频交易信号Agent：分析分笔数据，检测大单异动和委托队列
    2. 概念博弈Agent：分析涨停股和概念热度
    3. 量价策略Agent：分析量价关系和多周期共振
    4. 决策整合Agent：整合各Agent信号，生成最终交易策略
    """
    
    def __init__(self):
        """
        初始化交易策略智能体系统
        
        设置：
        1. 初始化大语言模型
        2. 创建各智能体的提示模板
        3. 创建工作流图
        """
        # 初始化大语言模型
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        # 创建高频交易信号Agent提示模板
        self.hft_agent_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的高频交易信号分析师。
你的任务是分析实时分笔数据，识别大单异动和委托队列特征。

核心功能：
1. 大单异动检测：识别单笔成交超过日均值2倍以上的订单，标记为"主力资金行为"
2. 委托队列分析：监控买一/卖一档位的挂单撤单频率，计算护盘系数

请提供详细的分析结果，包括关键信号和异常点。"""),
            ("user", "请分析以下分笔数据：{tick_data}")
        ])
        
        # 创建概念博弈Agent提示模板
        self.concept_agent_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的概念博弈分析师。
你的任务是分析当日涨停股列表和概念股映射，评估概念热度和资金博弈情况。

核心功能：
1. 概念热度量化：计算涨停概念强度指数 = (概念内涨停数/全市场涨停数)×龙头股封单额
2. 梯队健康度评估：分析概念内个股涨停时间排序，检测"涨停-炸板-回封"模式

请提供详细的分析结果，包括热门概念排名和资金博弈特征。"""),
            ("user", "请分析以下概念数据：{concept_data}")
        ])
        
        # 创建量价策略Agent提示模板
        self.price_volume_agent_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的量价关系分析师。
你的任务是分析日线级OHLCV数据和关键价位，评估量价关系和多周期共振情况。

核心功能：
1. 量价模型构建：计算量比-价格弹性指数，检测关键位突破有效性
2. 多周期共振判断：结合多个时间周期的技术指标，判断趋势一致性

请提供详细的分析结果，包括支撑压力位、趋势强度评分和量价背离预警。"""),
            ("user", "请分析以下K线数据：{kline_data}")
        ])
        
        # 创建决策整合Agent提示模板
        self.decision_agent_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的交易决策整合专家。
你的任务是整合各个专业Agent的分析结果，生成最终交易策略。

核心功能：
1. 多信号融合：使用加权投票模型整合各Agent信号，解决信号冲突
2. 动态策略生成：根据市场状态切换策略模式，生成带条件的操作指令

请提供详细的策略建议，包括标的列表、买卖点规则和仓位建议。"""),
            ("user", """请整合以下分析结果：
高频交易信号：{hft_signal}
概念博弈分析：{concept_analysis}
量价策略分析：{price_volume_analysis}
用户风险偏好：{risk_preference}""")
        ])
        
        # 创建工作流图
        self.workflow = self._create_workflow()
    
    async def hft_signal_step(self, state: TradingStrategyState) -> Dict:
        """高频交易信号分析步骤"""
        try:
            # 从状态中获取分笔数据
            tick_data = state['market_data'].get('tick_data', {})
            
            # 使用LLM分析分笔数据
            result = await self.llm.ainvoke([
                {"role": "system", "content": """你是一个专业的高频交易信号分析师。
你的任务是分析实时分笔数据，识别大单异动和委托队列特征。

核心功能：
1. 大单异动检测：识别单笔成交超过日均值2倍以上的订单，标记为"主力资金行为"
2. 委托队列分析：监控买一/卖一档位的挂单撤单频率，计算护盘系数

请提供详细的分析结果，包括关键信号和异常点。"""},
                {"role": "user", "content": f"请分析以下分笔数据：{tick_data}"}
            ])
            
            return {"hft_signal": result.content}
        except Exception as e:
            print(f"高频交易信号分析出错: {str(e)}")
            return {"hft_signal": "无法完成高频交易信号分析。"}
    
    async def concept_analysis_step(self, state: TradingStrategyState) -> Dict:
        """概念博弈分析步骤"""
        try:
            # 从状态中获取概念数据
            concept_data = state['market_data'].get('concept_data', {})
            
            # 使用LLM分析概念数据
            result = await self.llm.ainvoke([
                {"role": "system", "content": """你是一个专业的概念博弈分析师。
你的任务是分析当日涨停股列表和概念股映射，评估概念热度和资金博弈情况。

核心功能：
1. 概念热度量化：计算涨停概念强度指数 = (概念内涨停数/全市场涨停数)×龙头股封单额
2. 梯队健康度评估：分析概念内个股涨停时间排序，检测"涨停-炸板-回封"模式

请提供详细的分析结果，包括热门概念排名和资金博弈特征。"""},
                {"role": "user", "content": f"请分析以下概念数据：{concept_data}"}
            ])
            
            return {"concept_analysis": result.content}
        except Exception as e:
            print(f"概念博弈分析出错: {str(e)}")
            return {"concept_analysis": "无法完成概念博弈分析。"}
    
    async def price_volume_analysis_step(self, state: TradingStrategyState) -> Dict:
        """量价策略分析步骤"""
        try:
            # 从状态中获取K线数据
            kline_data = state['market_data'].get('kline_data', {})
            
            # 使用LLM分析K线数据
            result = await self.llm.ainvoke([
                {"role": "system", "content": """你是一个专业的量价关系分析师。
你的任务是分析日线级OHLCV数据和关键价位，评估量价关系和多周期共振情况。

核心功能：
1. 量价模型构建：计算量比-价格弹性指数，检测关键位突破有效性
2. 多周期共振判断：结合多个时间周期的技术指标，判断趋势一致性

请提供详细的分析结果，包括支撑压力位、趋势强度评分和量价背离预警。"""},
                {"role": "user", "content": f"请分析以下K线数据：{kline_data}"}
            ])
            
            return {"price_volume_analysis": result.content}
        except Exception as e:
            print(f"量价策略分析出错: {str(e)}")
            return {"price_volume_analysis": "无法完成量价策略分析。"}
    
    async def decision_integration_step(self, state: TradingStrategyState) -> Dict:
        """决策整合步骤"""
        try:
            # 获取各Agent的分析结果
            hft_signal = state.get('hft_signal', "无高频交易信号数据")
            concept_analysis = state.get('concept_analysis', "无概念博弈分析数据")
            price_volume_analysis = state.get('price_volume_analysis', "无量价策略分析数据")
            
            # 获取用户风险偏好（如果有）
            risk_preference = state['market_data'].get('risk_preference', "中等风险")
            
            # 使用LLM整合分析结果
            result = await self.llm.ainvoke([
                {"role": "system", "content": """你是一个专业的交易决策整合专家。
你的任务是整合各个专业Agent的分析结果，生成最终交易策略。

核心功能：
1. 多信号融合：使用加权投票模型整合各Agent信号，解决信号冲突
2. 动态策略生成：根据市场状态切换策略模式，生成带条件的操作指令

请提供详细的策略建议，包括标的列表、买卖点规则和仓位建议。"""},
                {"role": "user", "content": f"""请整合以下分析结果：
高频交易信号：{hft_signal}
概念博弈分析：{concept_analysis}
量价策略分析：{price_volume_analysis}
用户风险偏好：{risk_preference}"""}
            ])
            
            return {
                "final_strategy": result.content
            }
        except Exception as e:
            print(f"决策整合出错: {str(e)}")
            return {"final_strategy": "无法完成决策整合。"}
    
    def _create_workflow(self) -> StateGraph:
        """
        创建工作流图
        
        定义了交易策略分析的流程：
        1. 并行执行三个专业Agent的分析
        2. 决策整合Agent整合各分析结果
        3. 输出最终策略
        """
        workflow = StateGraph(TradingStrategyState)
        
        # 添加节点
        workflow.add_node("hft_agent", self.hft_signal_step)
        workflow.add_node("concept_agent", self.concept_analysis_step)
        workflow.add_node("price_volume_agent", self.price_volume_analysis_step)
        workflow.add_node("decision_agent", self.decision_integration_step)
        
        # 添加边 - 从开始到三个并行Agent
        workflow.add_edge(START, "hft_agent")
        workflow.add_edge(START, "concept_agent")
        workflow.add_edge(START, "price_volume_agent")
        
        # 添加边 - 三个Agent到决策整合Agent
        workflow.add_edge("hft_agent", "decision_agent")
        workflow.add_edge("concept_agent", "decision_agent")
        workflow.add_edge("price_volume_agent", "decision_agent")
        
        # 添加边 - 决策整合Agent到结束
        workflow.add_edge("decision_agent", END)
        
        return workflow.compile()
    
    async def run(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行交易策略分析
        
        执行交易策略分析流程：
        1. 初始化市场数据
        2. 执行工作流
        3. 记录过程
        4. 返回结果
        
        参数:
        - market_data: 包含分笔数据、概念数据、K线数据的字典
        
        返回:
        - 包含分析步骤和最终策略的字典
        """
        # 创建初始状态
        inputs = TradingStrategyState(
            market_data=market_data,
            hft_signal={},
            concept_analysis={},
            price_volume_analysis={},
            final_strategy={},
            steps=[]
        )
        
        steps = []
        final_strategy = "未能生成最终策略"  # 默认值
        
        async for event in self.workflow.astream(inputs):
            for k, v in event.items():
                if k != "__end__":
                    steps.append({k: v})
                    # 如果这个步骤包含了最终策略，就更新 final_strategy
                    if isinstance(v, dict) and "final_strategy" in v:
                        final_strategy = v["final_strategy"]
            inputs["steps"] = steps
        
        return {
            "market_data": market_data,
            "steps": steps,
            "final_strategy": final_strategy
        }

async def main():
    """
    主函数
    
    用于演示如何使用 TradingStrategyAgents：
    1. 创建交易策略智能体系统实例
    2. 准备示例市场数据
    3. 运行策略分析流程
    4. 展示执行结果
    """
    # 创建交易策略智能体系统实例
    trading_agents = TradingStrategyAgents()
    
    # 准备示例市场数据（实际应用中应从数据源获取）
    sample_market_data = {
        "tick_data": {
            "code": "sh603200",
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
    result = await trading_agents.run(sample_market_data)
    
    # 展示执行结果
    print("=== 交易策略分析结果 ===")
    print(f"最终策略: {result['final_strategy']}")
    print("\n=== 执行步骤 ===")
    for step in result['steps']:
        print(f"步骤: {list(step.keys())[0]}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 