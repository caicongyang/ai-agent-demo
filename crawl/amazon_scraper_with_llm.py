"""
智能亚马逊数据抓取系统 - 基于 LLM 推理 + MCP Playwright

这个系统结合了：
1. LLM 智能任务分解和推理
2. MCP Playwright 工具进行浏览器操作
3. 自动化数据提取和导出
4. 多页面处理和邮编设置

使用示例:
    scraper = AmazonScraperWithLLM()
    await scraper.initialize()
    
    task = "在亚马逊搜索doorbell，设置邮编90210，抓取前3页数据并导出CSV"
    result = await scraper.execute_task(task)
"""

import asyncio
import json
import csv
import os
import re
from typing import Dict, Any, Optional, List
from contextlib import AsyncExitStack
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# MCP 相关导入
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 智能定位器配置
try:
    from smart_locator_config import (
        ELEMENT_STRATEGIES, 
        get_element_strategy, 
        get_llm_prompt,
        DEFAULT_CONFIG
    )
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    print("⚠️ 智能定位器配置文件未找到，使用内置配置")

# 智能滚动定位器
try:
    from smart_scroll_locator import SmartScrollLocator, ScrollStrategy, ScrollDirection
    SMART_SCROLL_AVAILABLE = True
except ImportError:
    SMART_SCROLL_AVAILABLE = False
    print("⚠️ 智能滚动定位器未找到，使用基础滚动功能")

# LLM 相关导入（支持 OpenAI 和 Azure OpenAI）
try:
    from openai import OpenAI, AzureOpenAI
    from dotenv import load_dotenv
    OPENAI_AVAILABLE = True
    # 加载环境变量
    load_dotenv()
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI 或 dotenv 未安装，将使用模拟 LLM 响应")


@dataclass
class ScrapingTask:
    """抓取任务定义"""
    website: str
    search_keyword: str
    zip_code: str = ""
    pages_to_scrape: int = 1
    export_format: str = "csv"
    additional_instructions: str = ""


@dataclass
class ProductInfo:
    """产品信息数据结构"""
    title: str = ""
    price: str = ""
    rating: str = ""
    reviews_count: str = ""
    image_url: str = ""
    product_url: str = ""
    availability: str = ""
    brand: str = ""
    page_number: int = 1
    extracted_at: str = ""


@dataclass
class TaskStep:
    """任务步骤定义"""
    step_number: int
    action: str
    description: str
    mcp_tool: str
    parameters: Dict[str, Any]
    expected_result: str
    completed: bool = False
    result: Any = None
    error: str = ""


class LLMTaskPlanner:
    """LLM 任务规划器 - 支持 OpenAI 和 Azure OpenAI"""
    
    def __init__(self, api_key: str = None, use_azure: bool = True):
        self.use_azure = use_azure
        self.api_key = api_key
        self.client = None
        
        if OPENAI_AVAILABLE:
            self._initialize_client()
    
    def _initialize_client(self):
        """初始化 OpenAI 客户端"""
        try:
            if self.use_azure:
                # 优先使用 Azure OpenAI
                azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
                azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
                azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
                
                if azure_endpoint and azure_api_key:
                    self.client = AzureOpenAI(
                        azure_endpoint=azure_endpoint,
                        api_key=azure_api_key,
                        api_version=azure_api_version
                    )
                    self.model_name = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")
                    print("✅ 使用 Azure OpenAI")
                else:
                    print("⚠️ Azure OpenAI 配置不完整，尝试使用标准 OpenAI")
                    self._init_standard_openai()
            else:
                self._init_standard_openai()
                
        except Exception as e:
            print(f"⚠️ LLM 客户端初始化失败: {e}")
            self.client = None
    
    def _init_standard_openai(self):
        """初始化标准 OpenAI 客户端"""
        openai_api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            self.client = OpenAI(api_key=openai_api_key)
            self.model_name = "gpt-3.5-turbo"
            print("✅ 使用标准 OpenAI")
        else:
            print("⚠️ 未找到 OpenAI API 密钥")
    
    async def analyze_task(self, user_input: str) -> ScrapingTask:
        """分析用户输入，提取任务参数"""
        # 使用 LLM 或规则解析用户输入
        if self.client:
            return await self._llm_analyze_task(user_input)
        else:
            return self._rule_based_analyze_task(user_input)
    
    async def _llm_analyze_task(self, user_input: str) -> ScrapingTask:
        """使用 LLM 分析任务"""
        prompt = f"""
        分析以下用户任务，提取关键信息并返回 JSON 格式：

        用户输入: {user_input}

        请提取以下信息（如果没有提到则使用默认值）：
        - website: 网站名称（默认：amazon）
        - search_keyword: 搜索关键词
        - zip_code: 邮编（如果提到）
        - pages_to_scrape: 要抓取的页数（默认：1）
        - export_format: 导出格式（默认：csv）
        - additional_instructions: 其他指令

        只返回 JSON，不要其他内容：
        {{
            "website": "amazon",
            "search_keyword": "提取的关键词",
            "zip_code": "提取的邮编或空字符串",
            "pages_to_scrape": 数字,
            "export_format": "csv",
            "additional_instructions": "其他指令"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            # 提取 JSON 部分
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                task_data = json.loads(json_match.group())
                return ScrapingTask(**task_data)
            else:
                raise ValueError("LLM 返回格式不正确")
                
        except Exception as e:
            print(f"⚠️ LLM 分析失败，使用规则解析: {e}")
            return self._rule_based_analyze_task(user_input)
    
    def _rule_based_analyze_task(self, user_input: str) -> ScrapingTask:
        """基于规则的任务分析"""
        user_lower = user_input.lower()
        
        # 提取搜索关键词
        keyword_patterns = [
            r'搜索["\']?([^"\'，。]+)["\']?',
            r'search["\']?([^"\'，。]+)["\']?',
            r'k=([^\s&]+)',
        ]
        
        search_keyword = "doorbell"  # 默认值
        for pattern in keyword_patterns:
            match = re.search(pattern, user_input)
            if match:
                search_keyword = match.group(1).strip()
                break
        
        # 提取邮编
        zip_code = ""
        zip_patterns = [r'邮编[：:]?(\d{5})', r'zip[：:]?(\d{5})', r'(\d{5})']
        for pattern in zip_patterns:
            match = re.search(pattern, user_input)
            if match:
                zip_code = match.group(1)
                break
        
        # 提取页数
        pages_to_scrape = 1
        page_patterns = [r'(\d+)页', r'前(\d+)页', r'(\d+)\s*pages?']
        for pattern in page_patterns:
            match = re.search(pattern, user_input)
            if match:
                pages_to_scrape = int(match.group(1))
                break
        
        return ScrapingTask(
            website="amazon",
            search_keyword=search_keyword,
            zip_code=zip_code,
            pages_to_scrape=pages_to_scrape,
            export_format="csv",
            additional_instructions=user_input
        )
    
    async def generate_task_steps(self, task: ScrapingTask) -> List[TaskStep]:
        """生成详细的任务步骤"""
        if self.client:
            return await self._llm_generate_steps(task)
        else:
            return self._rule_based_generate_steps(task)
    
    async def _llm_generate_steps(self, task: ScrapingTask) -> List[TaskStep]:
        """使用 LLM 生成任务步骤"""
        prompt = f"""
        为以下抓取任务生成详细的执行步骤：

        任务信息:
        - 网站: {task.website}
        - 搜索关键词: {task.search_keyword}
        - 邮编: {task.zip_code}
        - 抓取页数: {task.pages_to_scrape}
        - 导出格式: {task.export_format}

        可用的 MCP 工具:
        - browser_navigate: 导航到URL
        - browser_snapshot: 获取页面快照
        - browser_click: 点击元素
        - browser_type: 输入文本
        - browser_wait_for: 等待条件
        - browser_take_screenshot: 截图

        请生成步骤序列，返回 JSON 数组格式，每个步骤包含：
        - step_number: 步骤序号
        - action: 操作类型
        - description: 步骤描述
        - mcp_tool: 使用的 MCP 工具
        - parameters: 工具参数
        - expected_result: 预期结果

        例如：
        [
            {{
                "step_number": 1,
                "action": "navigate",
                "description": "导航到亚马逊首页",
                "mcp_tool": "browser_navigate",
                "parameters": {{"url": "https://www.amazon.com"}},
                "expected_result": "成功访问亚马逊首页"
            }}
        ]
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if json_match:
                steps_data = json.loads(json_match.group())
                return [TaskStep(**step) for step in steps_data]
            else:
                raise ValueError("LLM 返回格式不正确")
                
        except Exception as e:
            print(f"⚠️ LLM 步骤生成失败，使用预定义步骤: {e}")
            return self._rule_based_generate_steps(task)
    
    def _rule_based_generate_steps(self, task: ScrapingTask) -> List[TaskStep]:
        """基于规则生成任务步骤"""
        steps = []
        step_num = 1
        
        # 1. 导航到亚马逊
        steps.append(TaskStep(
            step_number=step_num,
            action="navigate",
            description="导航到亚马逊首页",
            mcp_tool="browser_navigate",
            parameters={"url": "https://www.amazon.com"},
            expected_result="成功访问亚马逊首页"
        ))
        step_num += 1
        
        # 2. 设置邮编（如果提供）
        if task.zip_code:
            steps.append(TaskStep(
                step_number=step_num,
                action="set_zipcode",
                description=f"设置邮编为 {task.zip_code}",
                mcp_tool="browser_click",
                parameters={"element": "邮编设置按钮", "ref": "location_selector"},
                expected_result=f"邮编设置为 {task.zip_code}"
            ))
            step_num += 1
        
        # 3. 搜索产品
        steps.append(TaskStep(
            step_number=step_num,
            action="search",
            description=f"搜索关键词: {task.search_keyword}",
            mcp_tool="browser_type",
            parameters={
                "element": "搜索框",
                "ref": "search_input",
                "text": task.search_keyword,
                "submit": True
            },
            expected_result=f"显示 {task.search_keyword} 的搜索结果"
        ))
        step_num += 1
        
        # 4. 抓取多页数据
        for page in range(1, task.pages_to_scrape + 1):
            steps.append(TaskStep(
                step_number=step_num,
                action="extract_data",
                description=f"提取第 {page} 页产品数据",
                mcp_tool="browser_snapshot",
                parameters={},
                expected_result=f"成功提取第 {page} 页产品信息"
            ))
            step_num += 1
            
            # 如果不是最后一页，添加翻页步骤
            if page < task.pages_to_scrape:
                steps.append(TaskStep(
                    step_number=step_num,
                    action="next_page",
                    description=f"翻到第 {page + 1} 页",
                    mcp_tool="browser_click",
                    parameters={"element": "下一页按钮", "ref": "next_page_button"},
                    expected_result=f"成功翻到第 {page + 1} 页"
                ))
                step_num += 1
        
        # 5. 导出数据
        steps.append(TaskStep(
            step_number=step_num,
            action="export_data",
            description=f"导出数据为 {task.export_format} 格式",
            mcp_tool="browser_take_screenshot",
            parameters={"filename": f"amazon_scraping_summary.png"},
            expected_result="数据导出完成"
        ))
        
        return steps


@dataclass
class LocatorStrategy:
    """定位策略定义"""
    name: str
    selectors: List[str]
    success_count: int = 0
    failure_count: int = 0
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


class SmartElementLocator:
    """智能元素定位器 - 支持多策略重试和LLM分析"""
    
    def __init__(self, session: ClientSession, llm_planner: LLMTaskPlanner):
        self.session = session
        self.llm_planner = llm_planner
        self.config = DEFAULT_CONFIG if CONFIG_AVAILABLE else {}
        
        # 从配置文件加载定位策略库
        self.locator_strategies = {}
        if CONFIG_AVAILABLE:
            # 使用配置文件中的策略
            for element_type, strategy_config in ELEMENT_STRATEGIES.items():
                self.locator_strategies[element_type] = LocatorStrategy(
                    name=strategy_config["name"],
                    selectors=strategy_config["selectors"].copy()
                )
        else:
            # 使用内置的基础策略
            self.locator_strategies = {
                "search_box": LocatorStrategy(
                    name="搜索框",
                    selectors=[
                        '#twotabsearchtextbox',
                        'input[name="field-keywords"]',
                        '[data-testid="search-input"]',
                        'input[type="text"][placeholder*="search"]',
                        '.nav-search-field input'
                    ]
                ),
                "next_page": LocatorStrategy(
                    name="下一页按钮",
                    selectors=[
                        'a[aria-label="Go to next page"]',
                        '.a-pagination .a-last a',
                        '[data-testid="pagination-next"]',
                        'a[aria-label*="Next"]',
                        'a:contains("Next")'
                    ]
                ),
                "location_trigger": LocatorStrategy(
                    name="位置设置触发器",
                    selectors=[
                        '#glow-ingress-line1',
                        '[data-testid="location-selector"]',
                        '.nav-global-location-slot',
                        '#nav-global-location-popover-link',
                        '[aria-label*="location"]'
                    ]
                ),
                "zip_input": LocatorStrategy(
                    name="邮编输入框",
                    selectors=[
                        'input[name="zipCode"]',
                        '[data-testid="zip-input"]',
                        'input[placeholder*="ZIP"]',
                        'input[type="text"][maxlength="5"]',
                        '#GLUXZipUpdateInput'
                    ]
                ),
                "apply_button": LocatorStrategy(
                    name="确认按钮",
                    selectors=[
                        'input[aria-labelledby="GLUXZipUpdate-announce"]',
                        '[data-testid="apply-button"]',
                        'button:contains("Apply")',
                        'input[type="submit"]',
                        '.a-button-primary input'
                    ]
                )
            }
    
    async def locate_and_interact(self, element_type: str, action: str, 
                                 text: str = None, max_retries: int = 3) -> Dict[str, Any]:
        """智能定位并交互元素"""
        print(f"🎯 开始智能定位: {element_type} (动作: {action})")
        
        for attempt in range(max_retries):
            print(f"🔄 第 {attempt + 1} 次尝试定位 {element_type}")
            
            try:
                # 1. 获取页面快照
                snapshot = await self.session.call_tool("browser_snapshot", {})
                
                # 2. 尝试预定义策略
                success = await self._try_predefined_strategies(element_type, action, text, snapshot)
                if success:
                    return success
                
                # 3. 使用LLM分析页面
                if self.llm_planner.client and attempt < max_retries - 1:
                    llm_result = await self._llm_analyze_and_locate(element_type, action, snapshot, text)
                    if llm_result:
                        return llm_result
                
                # 4. 等待后重试
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    print(f"⏳ 等待 {wait_time} 秒后重试...")
                    await self._wait(wait_time)
                
            except Exception as e:
                print(f"⚠️ 第 {attempt + 1} 次尝试失败: {e}")
        
        print(f"❌ 所有定位策略都失败了: {element_type}")
        return {"success": False, "error": f"无法定位元素: {element_type}"}
    
    async def _try_predefined_strategies(self, element_type: str, action: str, 
                                       text: str, snapshot: Any) -> Optional[Dict[str, Any]]:
        """尝试预定义的定位策略"""
        if element_type not in self.locator_strategies:
            return None
        
        strategy = self.locator_strategies[element_type]
        
        # 按成功率排序选择器
        sorted_selectors = sorted(strategy.selectors, 
                                key=lambda x: strategy.success_rate, reverse=True)
        
        for selector in sorted_selectors:
            try:
                print(f"🔍 尝试选择器: {selector}")
                
                # 根据动作类型执行相应操作
                if action == "click":
                    print(f"🖱️ 执行点击操作: {strategy.name}")
                    
                    # 对于翻页按钮，先尝试滚动到元素位置
                    if element_type == "next_page":
                        print("📜 翻页按钮：先滚动到元素位置...")
                        try:
                            # 使用session的方法来滚动到元素
                            scroll_script = f"""
                            () => {{
                                const element = document.querySelector('{selector.replace("'", "\\'")}');
                                if (element) {{
                                    element.scrollIntoView({{
                                        behavior: 'smooth',
                                        block: 'center'
                                    }});
                                    return {{success: true, found: true}};
                                }}
                                return {{success: false, found: false}};
                            }}
                            """
                            
                            scroll_result = await self.session.call_tool("browser_evaluate", {
                                "function": scroll_script
                            })
                            
                            await self._wait(1)
                            print("✅ 已尝试滚动到翻页按钮位置")
                        except Exception as e:
                            print(f"⚠️ 滚动到元素失败: {e}，尝试滚动到页面底部...")
                            try:
                                # 简单滚动到底部
                                await self.session.call_tool("browser_evaluate", {
                                    "function": "() => window.scrollTo(0, document.body.scrollHeight)"
                                })
                                await self._wait(1)
                                print("✅ 已滚动到页面底部")
                            except Exception as e2:
                                print(f"⚠️ 滚动到底部也失败: {e2}")
                    
                    result = await self.session.call_tool("browser_click", {
                        "element": strategy.name,
                        "ref": selector
                    })
                    print(f"✅ 点击命令已发送: {result}")
                    
                    # 对于翻页等重要操作，添加额外的等待时间
                    if element_type == "next_page":
                        print("⏳ 翻页操作后等待页面响应...")
                        await self._wait(2)
                elif action == "type" and text:
                    result = await self.session.call_tool("browser_type", {
                        "element": strategy.name,
                        "ref": selector,
                        "text": text,
                        "submit": False
                    })
                elif action == "submit" and text:
                    result = await self.session.call_tool("browser_type", {
                        "element": strategy.name,
                        "ref": selector,
                        "text": text,
                        "submit": True
                    })
                else:
                    continue
                
                # 记录成功
                strategy.success_count += 1
                print(f"✅ 选择器成功: {selector}")
                return {"success": True, "selector": selector, "result": result}
                
            except Exception as e:
                # 记录失败
                strategy.failure_count += 1
                print(f"❌ 选择器失败: {selector} - {e}")
                continue
        
        return None
    
    async def _llm_analyze_and_locate(self, element_type: str, action: str, 
                                    snapshot: Any, text: str = None) -> Optional[Dict[str, Any]]:
        """使用LLM分析页面并生成新的定位策略"""
        print(f"🧠 使用LLM分析页面来定位: {element_type}")
        
        try:
            # 提取页面内容
            page_content = self._extract_page_content(snapshot)
            
            # 使用配置文件中的提示模板
            if CONFIG_AVAILABLE:
                try:
                    llm_config = self.config.get("llm", {}) if hasattr(self.config, 'get') else {}
                    max_content_length = llm_config.get("max_page_content_length", 3000) if hasattr(llm_config, 'get') else 3000
                    prompt = get_llm_prompt(
                        element_type,
                        action=action,
                        page_content=page_content[:max_content_length],
                        text_info=f"输入文本: {text}" if text else ""
                    )
                except Exception as e:
                    print(f"⚠️ 配置文件使用失败: {e}，使用内置模板")
                    prompt = f"""
                    分析以下网页内容，找到用于"{element_type}"的最佳CSS选择器。

                    目标操作: {action}
                    元素类型: {element_type}
                    {'输入文本: ' + text if text else ''}

                    页面内容摘要:
                    {page_content[:3000]}

                    请返回JSON格式的结果：
                    {{
                        "selectors": ["选择器1", "选择器2", "选择器3"],
                        "confidence": 0.8,
                        "reasoning": "选择这些选择器的原因"
                    }}

                    要求：
                    1. 提供3-5个备选选择器
                    2. 优先使用稳定的属性（id, data-testid, aria-label等）
                    3. 避免使用易变的class名称
                    4. 考虑元素的上下文和语义
                    """
            else:
                # 使用内置提示模板
                prompt = f"""
                分析以下网页内容，找到用于"{element_type}"的最佳CSS选择器或XPath。

                目标操作: {action}
                元素类型: {element_type}
                {'输入文本: ' + text if text else ''}

                页面内容摘要:
                {page_content[:3000]}

                请返回JSON格式的结果：
                {{
                    "selectors": ["选择器1", "选择器2", "选择器3"],
                    "confidence": 0.8,
                    "reasoning": "选择这些选择器的原因"
                }}

                要求：
                1. 提供3-5个备选选择器
                2. 优先使用稳定的属性（id, data-testid, aria-label等）
                3. 避免使用易变的class名称
                4. 考虑元素的上下文和语义
                """
            
            response = self.llm_planner.client.chat.completions.create(
                model=self.llm_planner.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            
            if json_match:
                llm_result = json.loads(json_match.group())
                selectors = llm_result.get("selectors", [])
                
                print(f"🎯 LLM推荐的选择器: {selectors}")
                
                # 尝试LLM推荐的选择器
                for selector in selectors:
                    try:
                        if action == "click":
                            result = await self.session.call_tool("browser_click", {
                                "element": element_type,
                                "ref": selector
                            })
                        elif action == "type" and text:
                            result = await self.session.call_tool("browser_type", {
                                "element": element_type,
                                "ref": selector,
                                "text": text,
                                "submit": False
                            })
                        elif action == "submit" and text:
                            result = await self.session.call_tool("browser_type", {
                                "element": element_type,
                                "ref": selector,
                                "text": text,
                                "submit": True
                            })
                        else:
                            continue
                        
                        print(f"✅ LLM推荐的选择器成功: {selector}")
                        
                        # 将成功的选择器添加到策略库
                        self._update_strategy_with_new_selector(element_type, selector)
                        
                        return {"success": True, "selector": selector, "result": result, "source": "llm"}
                        
                    except Exception as e:
                        print(f"❌ LLM选择器失败: {selector} - {e}")
                        continue
            
        except Exception as e:
            print(f"⚠️ LLM分析失败: {e}")
        
        return None
    
    def _extract_page_content(self, snapshot: Any) -> str:
        """从快照中提取页面内容"""
        try:
            if hasattr(snapshot, 'content') and snapshot.content:
                content = ""
                for item in snapshot.content:
                    if hasattr(item, 'text'):
                        content += item.text + "\n"
                return content
            else:
                return str(snapshot)
        except:
            return str(snapshot)
    
    def _update_strategy_with_new_selector(self, element_type: str, selector: str):
        """将新的成功选择器添加到策略库"""
        if element_type in self.locator_strategies:
            strategy = self.locator_strategies[element_type]
            if selector not in strategy.selectors:
                strategy.selectors.insert(0, selector)  # 添加到最前面
                print(f"📚 新选择器已添加到策略库: {selector}")
    
    async def _wait(self, seconds: float):
        """等待指定时间"""
        await self.session.call_tool("browser_wait_for", {"time": seconds})


class AmazonScraperWithLLM:
    """智能亚马逊抓取器"""
    
    def __init__(self, openai_api_key: str = None, use_azure: bool = True):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.is_connected = False
        
        # LLM 任务规划器
        self.task_planner = LLMTaskPlanner(openai_api_key, use_azure)
        
        # 智能元素定位器
        self.smart_locator: Optional[SmartElementLocator] = None
        
        # 智能滚动定位器
        self.scroll_locator: Optional[SmartScrollLocator] = None
        
        # 数据存储
        self.scraped_products: List[ProductInfo] = []
        self.current_task: Optional[ScrapingTask] = None
        self.task_steps: List[TaskStep] = []
    
    async def initialize(self) -> bool:
        """初始化 MCP 连接"""
        try:
            print("🔄 正在初始化智能亚马逊抓取器...")
            
            # 配置 Playwright MCP 服务器
            server_params = StdioServerParameters(
                command="npx",
                args=["@playwright/mcp"],
                env=None
            )
            
            # 建立连接
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            
            # 创建会话
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
            
            # 初始化
            await self.session.initialize()
            self.is_connected = True
            
            # 创建智能元素定位器
            self.smart_locator = SmartElementLocator(self.session, self.task_planner)
            
            # 创建智能滚动定位器
            if SMART_SCROLL_AVAILABLE:
                self.scroll_locator = SmartScrollLocator(self.session)
                print("✅ 智能滚动定位器已初始化")
            else:
                print("⚠️ 智能滚动定位器不可用，使用基础功能")
            
            print("✅ 智能抓取器初始化成功")
            return True
            
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            return False
    
    async def execute_task(self, user_input: str) -> Dict[str, Any]:
        """执行用户任务"""
        try:
            print(f"\n🧠 分析任务: {user_input}")
            
            # 1. LLM 分析任务
            self.current_task = await self.task_planner.analyze_task(user_input)
            print(f"📋 任务解析结果:")
            print(f"  - 搜索关键词: {self.current_task.search_keyword}")
            print(f"  - 邮编: {self.current_task.zip_code or '未设置'}")
            print(f"  - 抓取页数: {self.current_task.pages_to_scrape}")
            
            # 2. LLM 生成执行步骤
            print(f"\n🔧 生成执行步骤...")
            self.task_steps = await self.task_planner.generate_task_steps(self.current_task)
            print(f"📝 生成了 {len(self.task_steps)} 个执行步骤")
            
            # 3. 执行步骤序列
            print(f"\n🚀 开始执行任务...")
            execution_results = []
            
            for step in self.task_steps:
                print(f"\n步骤 {step.step_number}: {step.description}")
                
                try:
                    # 执行具体步骤
                    step_result = await self._execute_step(step)
                    step.completed = True
                    step.result = step_result
                    
                    execution_results.append({
                        "step": step.step_number,
                        "success": True,
                        "result": step_result
                    })
                    print(f"✅ 步骤 {step.step_number} 完成")
                    
                    # 步骤间等待
                    await self._wait(2)
                    
                except Exception as e:
                    step.error = str(e)
                    execution_results.append({
                        "step": step.step_number,
                        "success": False,
                        "error": str(e)
                    })
                    print(f"❌ 步骤 {step.step_number} 失败: {e}")
            
            # 4. 导出数据
            export_result = await self._export_data()
            
            # 5. 生成报告
            report = {
                "task": asdict(self.current_task),
                "steps_executed": len(self.task_steps),
                "steps_completed": sum(1 for step in self.task_steps if step.completed),
                "products_found": len(self.scraped_products),
                "export_result": export_result,
                "execution_results": execution_results,
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"\n📊 任务执行完成!")
            print(f"  - 执行步骤: {report['steps_completed']}/{report['steps_executed']}")
            print(f"  - 找到产品: {report['products_found']} 个")
            print(f"  - 导出结果: {export_result.get('message', '未导出')}")
            
            return report
            
        except Exception as e:
            error_msg = f"任务执行失败: {str(e)}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
    
    async def _execute_step(self, step: TaskStep) -> Any:
        """执行单个步骤"""
        if not self.is_connected or not self.session:
            raise RuntimeError("MCP 连接未初始化")
        
        # 映射 LLM 生成的动作类型到处理函数
        if step.action == "navigate":
            return await self._handle_navigate(step)
        elif step.action == "set_zipcode":
            return await self._handle_set_zipcode(step)
        elif step.action == "search":
            return await self._handle_search(step)
        elif step.action == "extract_data":
            return await self._handle_extract_data(step)
        elif step.action == "next_page":
            return await self._handle_next_page(step)
        elif step.action == "export_data" or step.action == "export":
            # 直接调用数据导出，不依赖步骤参数
            return await self._export_data()
        # 处理 LLM 生成的其他动作类型
        elif step.action == "type":
            return await self._handle_type_input(step)
        elif step.action == "click":
            return await self._handle_click(step) 
        elif step.action == "wait_for":
            return await self._handle_wait(step)
        elif step.action == "snapshot":
            return await self._handle_snapshot_and_extract(step)
        elif step.action == "take_screenshot":
            return await self._handle_screenshot(step)
        else:
            # 通用 MCP 工具调用
            print(f"🔧 执行通用 MCP 工具: {step.mcp_tool}")
            return await self.session.call_tool(step.mcp_tool, step.parameters)
    
    async def _handle_navigate(self, step: TaskStep) -> Any:
        """处理导航步骤"""
        result = await self.session.call_tool("browser_navigate", step.parameters)
        await self._wait(3)  # 等待页面加载
        return result
    
    async def _handle_set_zipcode(self, step: TaskStep) -> Any:
        """处理设置邮编步骤 - 使用智能定位系统"""
        print(f"🏠 设置邮编为: {self.current_task.zip_code}")
        
        if not self.smart_locator:
            return {"message": "智能定位器未初始化", "success": False}
        
        try:
            # 1. 点击位置设置入口
            print("🖱️ 智能定位并点击位置设置入口...")
            trigger_result = await self.smart_locator.locate_and_interact(
                "location_trigger", "click"
            )
            
            if not trigger_result.get("success"):
                print("⚠️ 无法找到位置设置入口，尝试跳过")
                return {"message": "无法找到位置设置入口", "success": False}
            
            await self._wait(2)
            
            # 2. 输入邮编
            print(f"⌨️ 智能定位并输入邮编: {self.current_task.zip_code}")
            zip_result = await self.smart_locator.locate_and_interact(
                "zip_input", "type", self.current_task.zip_code
            )
            
            if not zip_result.get("success"):
                print("⚠️ 无法找到邮编输入框")
                return {"message": "无法找到邮编输入框", "success": False}
            
            await self._wait(1)
            
            # 3. 确认设置
            print("✅ 智能定位并点击确认按钮...")
            apply_result = await self.smart_locator.locate_and_interact(
                "apply_button", "click"
            )
            
            if not apply_result.get("success"):
                print("⚠️ 无法找到确认按钮，但邮编可能已设置")
                return {"message": "邮编可能已设置，但无法确认", "success": True}
            
            await self._wait(3)
            
            print(f"✅ 邮编设置完成: {self.current_task.zip_code}")
            return {"message": f"邮编设置为 {self.current_task.zip_code}", "success": True}
            
        except Exception as e:
            print(f"⚠️ 邮编设置过程中出错: {e}")
            return {"message": f"邮编设置失败: {e}", "success": False}
    
    async def _handle_search(self, step: TaskStep) -> Any:
        """处理搜索步骤 - 使用智能定位系统"""
        print(f"🔍 搜索关键词: {self.current_task.search_keyword}")
        
        if not self.smart_locator:
            # 备用方案：直接导航到搜索URL
            search_url = f"https://www.amazon.com/s?k={self.current_task.search_keyword}"
            result = await self.session.call_tool("browser_navigate", {"url": search_url})
            await self._wait(3)
            return result
        
        try:
            # 1. 尝试智能定位搜索框并输入
            print("🔍 智能定位搜索框并输入关键词...")
            search_result = await self.smart_locator.locate_and_interact(
                "search_box", "submit", self.current_task.search_keyword
            )
            
            if search_result.get("success"):
                await self._wait(3)
                print("✅ 搜索成功")
                return search_result
            else:
                # 备用方案：直接导航到搜索URL
                print("⚠️ 搜索框定位失败，使用备用方案...")
                search_url = f"https://www.amazon.com/s?k={self.current_task.search_keyword}"
                result = await self.session.call_tool("browser_navigate", {"url": search_url})
                await self._wait(3)
                return result
                
        except Exception as e:
            print(f"⚠️ 搜索过程中出错: {e}")
            # 备用方案
            search_url = f"https://www.amazon.com/s?k={self.current_task.search_keyword}"
            result = await self.session.call_tool("browser_navigate", {"url": search_url})
            await self._wait(3)
            return result
    
    async def _handle_extract_data(self, step: TaskStep) -> Any:
        """处理数据提取步骤 - 真实数据提取"""
        print("📸 获取页面快照并提取真实产品数据...")
        
        # 1. 获取页面快照
        snapshot_result = await self.session.call_tool("browser_snapshot", {})
        
        # 2. 解析快照数据，提取真实产品信息
        extracted_products = await self._extract_products_from_snapshot(snapshot_result)
        
        # 3. 计算当前页码
        page_number = self._calculate_current_page()
        
        # 4. 为产品添加页码和时间戳
        for product in extracted_products:
            product.page_number = page_number
            product.extracted_at = datetime.now().isoformat()
        
        self.scraped_products.extend(extracted_products)
        
        print(f"📦 从第 {page_number} 页提取了 {len(extracted_products)} 个真实产品")
        return {"extracted_count": len(extracted_products), "page": page_number}
    
    async def _handle_next_page(self, step: TaskStep) -> Any:
        """处理翻页步骤 - 优先使用智能滚动定位系统"""
        print("📄 开始智能翻页...")
        
        # 1. 优先尝试智能滚动翻页
        if self.scroll_locator and SMART_SCROLL_AVAILABLE:
            print("🎯 使用智能滚动定位翻页...")
            scroll_result = await self.smart_next_page_with_scroll()
            if scroll_result.get("success"):
                return scroll_result
            else:
                print("⚠️ 智能滚动翻页失败，尝试传统方法...")
        
        # 2. 回退到传统智能定位方法
        if not self.smart_locator:
            print("⚠️ 智能定位器未初始化，使用备用方法")
            return await self._fallback_next_page()
        
        try:
            # 记录当前页面状态（用于验证翻页是否成功）
            print("📸 记录当前页面状态...")
            current_snapshot = await self.session.call_tool("browser_snapshot", {})
            current_url = await self._get_current_url()
            
            # 滚动到页面底部以显示翻页按钮
            print("📜 滚动到页面底部以显示翻页按钮...")
            try:
                # 直接使用JavaScript滚动到底部
                await self.session.call_tool("browser_evaluate", {
                    "function": """
                    () => {
                        window.scrollTo({
                            top: document.body.scrollHeight,
                            behavior: 'smooth'
                        });
                        return {
                            scrollTop: window.pageYOffset,
                            scrollHeight: document.body.scrollHeight
                        };
                    }
                    """
                })
                print("✅ 滚动到页面底部完成")
                await self._wait(3)  # 等待页面稳定和滚动完成
            except Exception as e:
                print(f"⚠️ 滚动失败: {e}")
                await self._wait(2)
            
            # 使用传统智能定位系统寻找并点击下一页按钮
            print("🎯 使用传统方法定位下一页按钮...")
            next_result = await self.smart_locator.locate_and_interact(
                "next_page", "click"
            )
            
            if next_result.get("success"):
                print("🖱️ 下一页按钮点击成功，验证页面是否发生变化...")
                
                # 等待页面加载并验证变化
                success = await self._verify_page_change(current_url, current_snapshot)
                
                if success:
                    print("✅ 翻页成功，页面已发生变化")
                    return {"message": "翻页成功", "success": True, "result": next_result, "verified": True}
                else:
                    print("⚠️ 点击了下一页按钮但页面未发生变化，可能已到最后一页")
                    return {"message": "页面未发生变化", "success": False, "clicked": True}
            else:
                print("⚠️ 未找到下一页按钮，可能已到最后一页")
                return {"message": "未找到下一页按钮", "success": False}
                
        except Exception as e:
            print(f"⚠️ 翻页过程中出错: {e}")
            return {"message": f"翻页失败: {e}", "success": False}
    
    async def _get_current_url(self) -> str:
        """获取当前页面URL"""
        try:
            # 使用JavaScript获取当前URL
            js_result = await self.session.call_tool("browser_evaluate", {
                "function": "() => window.location.href"
            })
            
            if hasattr(js_result, 'content') and js_result.content:
                content_item = js_result.content[0] if js_result.content else None
                if content_item and hasattr(content_item, 'text'):
                    return content_item.text.strip('"')
            
            return "unknown"
        except Exception as e:
            print(f"⚠️ 获取URL失败: {e}")
            return "unknown"
    
    async def _verify_page_change(self, original_url: str, original_snapshot: Any, max_wait: int = 10) -> bool:
        """验证页面是否发生了变化"""
        print("🔍 验证页面变化...")
        
        for attempt in range(max_wait):
            try:
                # 等待1秒
                await self._wait(1)
                
                # 获取新的URL和快照
                new_url = await self._get_current_url()
                new_snapshot = await self.session.call_tool("browser_snapshot", {})
                
                # 检查URL是否变化
                if new_url != original_url and new_url != "unknown":
                    print(f"✅ URL已变化: {original_url} → {new_url}")
                    return True
                
                # 检查页面内容是否变化
                if self._has_content_changed(original_snapshot, new_snapshot):
                    print("✅ 页面内容已发生变化")
                    return True
                
                print(f"⏳ 第 {attempt + 1} 次检查，页面尚未变化...")
                
            except Exception as e:
                print(f"⚠️ 验证页面变化时出错: {e}")
        
        print("❌ 页面在等待时间内未发生变化")
        return False
    
    def _has_content_changed(self, original_snapshot: Any, new_snapshot: Any) -> bool:
        """检查页面内容是否发生变化"""
        try:
            # 简单的内容比较
            original_content = str(original_snapshot)
            new_content = str(new_snapshot)
            
            # 如果内容长度差异超过10%，认为发生了变化
            if abs(len(original_content) - len(new_content)) > len(original_content) * 0.1:
                return True
            
            # 检查是否包含页码相关的变化
            if "page=2" in new_content and "page=2" not in original_content:
                return True
            if "page=3" in new_content and "page=3" not in original_content:
                return True
            
            return False
        except:
            return False
    
    async def _fallback_next_page(self) -> Dict[str, Any]:
        """备用翻页方法"""
        try:
            # 1. 先滚动到页面底部
            print("📜 备用方法：滚动到页面底部...")
            await self._scroll_to_bottom()
            await self._wait(2)
            
            # 2. 获取页面快照
            snapshot_result = await self.session.call_tool("browser_snapshot", {})
            
            # 3. 寻找下一页按钮
            next_button_ref = await self._find_next_page_button(snapshot_result)
            
            if next_button_ref:
                # 4. 点击下一页按钮
                print(f"🖱️ 点击下一页按钮: {next_button_ref}")
                click_result = await self.session.call_tool("browser_click", {
                    "element": "下一页按钮",
                    "ref": next_button_ref
                })
                
                # 5. 等待页面加载
                await self._wait(3)
                
                print("✅ 成功翻到下一页")
                return {"message": "翻页成功", "button_ref": next_button_ref, "result": click_result}
            else:
                print("⚠️ 未找到下一页按钮，可能已到最后一页")
                return {"message": "未找到下一页按钮", "success": False}
        except Exception as e:
            return {"message": f"备用翻页方法失败: {e}", "success": False}
    
    async def _handle_export_data(self, step: TaskStep) -> Any:
        """处理数据导出步骤"""
        return await self._export_data()
    
    async def _export_data(self) -> Dict[str, Any]:
        """导出抓取的数据"""
        if not self.scraped_products:
            return {"success": False, "message": "没有数据可导出"}
        
        try:
            # 创建输出目录
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"amazon_{self.current_task.search_keyword}_{timestamp}.csv"
            filepath = output_dir / filename
            
            # 导出为 CSV
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                # 修复：直接获取字段名列表
                fieldnames = list(ProductInfo.__dataclass_fields__.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for product in self.scraped_products:
                    writer.writerow(asdict(product))
            
            # 同时导出为 JSON
            json_filename = filename.replace('.csv', '.json')
            json_filepath = output_dir / json_filename
            
            with open(json_filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump([asdict(product) for product in self.scraped_products], 
                         jsonfile, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "csv_file": str(filepath),
                "json_file": str(json_filepath),
                "products_count": len(self.scraped_products),
                "message": f"成功导出 {len(self.scraped_products)} 个产品数据"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _wait(self, seconds: float):
        """等待指定时间"""
        if self.session:
            await self.session.call_tool("browser_wait_for", {"time": seconds})
    
    async def _scroll_to_bottom(self):
        """滚动到页面底部"""
        try:
            print("📜 执行滚动到页面底部...")
            
            # 使用JavaScript滚动到页面底部
            scroll_script = """
            () => {
                // 平滑滚动到页面底部
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
                
                // 返回滚动信息
                return {
                    scrollTop: window.pageYOffset,
                    scrollHeight: document.body.scrollHeight,
                    clientHeight: window.innerHeight
                };
            }
            """
            
            result = await self.session.call_tool("browser_evaluate", {
                "function": scroll_script
            })
            
            print("✅ 页面滚动完成")
            
            # 额外等待，确保动态内容加载
            await self._wait(1)
            
            return result
            
        except Exception as e:
            print(f"⚠️ 滚动到底部失败: {e}")
            # 备用方案：使用按键滚动
            try:
                print("🔄 尝试备用滚动方案...")
                # 模拟按End键滚动到底部
                await self.session.call_tool("browser_key", {"key": "End"})
                await self._wait(1)
                print("✅ 备用滚动方案完成")
            except Exception as e2:
                print(f"⚠️ 备用滚动方案也失败: {e2}")
    
    async def _scroll_to_element(self, selector: str):
        """滚动到特定元素"""
        try:
            print(f"📜 滚动到元素: {selector}")
            
            scroll_script = f"""
            () => {{
                const element = document.querySelector('{selector}');
                if (element) {{
                    element.scrollIntoView({{
                        behavior: 'smooth',
                        block: 'center'
                    }});
                    return {{success: true, found: true}};
                }}
                return {{success: false, found: false}};
            }}
            """
            
            result = await self.session.call_tool("browser_evaluate", {
                "function": scroll_script
            })
            
            await self._wait(1)
            return result
            
        except Exception as e:
            print(f"⚠️ 滚动到元素失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _scroll_to_element_by_selector(self, selector: str):
        """根据选择器滚动到特定元素"""
        try:
            print(f"📜 滚动到选择器元素: {selector}")
            
            # 转义选择器中的特殊字符
            escaped_selector = selector.replace("'", "\\'").replace('"', '\\"')
            
            scroll_script = f"""
            () => {{
                const element = document.querySelector('{escaped_selector}');
                if (element) {{
                    // 检查元素是否在视口中
                    const rect = element.getBoundingClientRect();
                    const isVisible = rect.top >= 0 && rect.bottom <= window.innerHeight;
                    
                    if (!isVisible) {{
                        element.scrollIntoView({{
                            behavior: 'smooth',
                            block: 'center'
                        }});
                    }}
                    
                    return {{
                        success: true, 
                        found: true, 
                        wasVisible: isVisible,
                        rect: {{top: rect.top, bottom: rect.bottom, left: rect.left, right: rect.right}}
                    }};
                }}
                return {{success: false, found: false}};
            }}
            """
            
            result = await self.session.call_tool("browser_evaluate", {
                "function": scroll_script
            })
            
            if hasattr(result, 'content') and result.content:
                content_item = result.content[0] if result.content else None
                if content_item and hasattr(content_item, 'text'):
                    try:
                        result_data = json.loads(content_item.text)
                        if result_data.get("found"):
                            await self._wait(1)  # 等待滚动完成
                        return result_data
                    except:
                        pass
            
            return {"success": False, "found": False}
            
        except Exception as e:
            print(f"⚠️ 滚动到选择器元素失败: {e}")
            return {"success": False, "found": False, "error": str(e)}
    
    async def _scroll_to_bottom_simple(self):
        """简单的滚动到底部方法"""
        try:
            print("📜 简单滚动到页面底部...")
            
            scroll_script = """
            () => {
                window.scrollTo(0, document.body.scrollHeight);
                return {success: true, scrollTop: window.pageYOffset};
            }
            """
            
            await self.session.call_tool("browser_evaluate", {
                "function": scroll_script
            })
            
            await self._wait(1)
            print("✅ 简单滚动完成")
            
        except Exception as e:
            print(f"⚠️ 简单滚动失败: {e}")
    
    async def _handle_type_input(self, step: TaskStep) -> Any:
        """处理文本输入步骤"""
        print(f"⌨️ 输入文本: {step.description}")
        
        # 如果是搜索相关，直接导航到搜索URL
        if "搜索" in step.description or "search" in step.description.lower():
            search_url = f"https://www.amazon.com/s?k={self.current_task.search_keyword}"
            result = await self.session.call_tool("browser_navigate", {"url": search_url})
            await self._wait(3)
            return result
        else:
            # 其他输入情况
            return await self.session.call_tool("browser_type", step.parameters)
    
    async def _handle_click(self, step: TaskStep) -> Any:
        """处理点击步骤"""
        print(f"🖱️ 点击操作: {step.description}")
        
        # 如果是翻页相关的点击（扩展匹配条件）
        pagination_keywords = [
            "下一页", "next", "第二页", "第三页", "第四页", "第五页",
            "page", "翻页", "页面", "链接"
        ]
        
        is_pagination = any(keyword in step.description.lower() for keyword in pagination_keywords)
        
        # 检查是否包含页码数字
        import re
        page_number_pattern = r'第\s*(\d+)\s*页|page\s*(\d+)|(\d+)\s*页'
        has_page_number = re.search(page_number_pattern, step.description.lower())
        
        if is_pagination or has_page_number:
            print(f"🔄 检测到翻页操作，使用智能翻页处理: {step.description}")
            return await self._handle_next_page(step)
        else:
            print(f"🖱️ 普通点击操作")
            return await self.session.call_tool("browser_click", step.parameters)
    
    async def _handle_wait(self, step: TaskStep) -> Any:
        """处理等待步骤"""
        print(f"⏳ 等待: {step.description}")
        await self._wait(3)
        return {"message": f"等待完成: {step.description}"}
    
    async def _handle_snapshot_and_extract(self, step: TaskStep) -> Any:
        """处理快照并提取数据 - 真实数据提取"""
        print(f"📸 获取快照并提取真实数据: {step.description}")
        
        # 1. 获取页面快照
        snapshot_result = await self.session.call_tool("browser_snapshot", {})
        
        # 2. 如果描述中包含页面相关信息，进行真实数据提取
        if any(keyword in step.description for keyword in ["页面", "结果", "产品", "搜索"]):
            # 3. 提取真实产品数据
            extracted_products = await self._extract_products_from_snapshot(snapshot_result)
            
            # 4. 计算当前页码
            page_number = self._calculate_current_page()
            
            # 5. 为产品添加元数据
            for product in extracted_products:
                product.page_number = page_number
                product.extracted_at = datetime.now().isoformat()
            
            self.scraped_products.extend(extracted_products)
            print(f"📦 从第 {page_number} 页提取了 {len(extracted_products)} 个真实产品")
            
            return {
                "snapshot": snapshot_result,
                "extracted_count": len(extracted_products),
                "page": page_number
            }
        
        return {"snapshot": snapshot_result}
    
    async def _handle_screenshot(self, step: TaskStep) -> Any:
        """处理截图步骤"""
        print(f"📷 截图: {step.description}")
        filename = step.parameters.get("filename", f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        return await self.session.call_tool("browser_take_screenshot", {"filename": filename})
    
    def _calculate_current_page(self) -> int:
        """计算当前页码"""
        page_number = 1
        
        # 扩展的翻页关键词匹配
        pagination_keywords = [
            "下一页", "next", "第二页", "第三页", "第四页", "第五页",
            "page", "翻页", "页面", "链接"
        ]
        
        for step in self.task_steps:
            if step.completed:
                # 检查是否是翻页操作
                is_pagination = any(keyword in step.description.lower() for keyword in pagination_keywords)
                
                # 检查是否包含页码数字
                import re
                page_number_match = re.search(r'第\s*(\d+)\s*页|page\s*(\d+)|(\d+)\s*页', step.description.lower())
                
                if is_pagination or page_number_match:
                    page_number += 1
                    print(f"📄 检测到已完成的翻页步骤: {step.description}，当前页码: {page_number}")
        
        print(f"📊 计算得出当前页码: {page_number}")
        return page_number
    
    async def _extract_products_from_snapshot(self, snapshot_result: Any) -> List[ProductInfo]:
        """从页面快照中提取真实产品数据"""
        products = []
        
        try:
            print("🔍 使用 JavaScript 提取页面产品信息...")
            
            # 使用 browser_evaluate 执行 JavaScript 来提取产品数据
            js_script = """
            () => {
                const products = [];
                
                // 亚马逊产品容器的常见选择器
                const productSelectors = [
                    '[data-component-type="s-search-result"]',
                    '[data-testid="s-result-item"]',
                    '[data-component-type="s-product-item"]',
                    '.s-result-item'
                ];
                
                let productElements = [];
                for (const selector of productSelectors) {
                    productElements = document.querySelectorAll(selector);
                    if (productElements.length > 0) break;
                }
                
                console.log(`找到 ${productElements.length} 个产品元素`);
                
                productElements.forEach((element, index) => {
                    try {
                        // 提取产品标题
                        const titleSelectors = [
                            'h2 a span',
                            '[data-cy="title-recipe-title"]',
                            '.s-size-mini .s-link-style a span',
                            'h2 span'
                        ];
                        let title = '';
                        for (const selector of titleSelectors) {
                            const titleEl = element.querySelector(selector);
                            if (titleEl && titleEl.textContent.trim()) {
                                title = titleEl.textContent.trim();
                                break;
                            }
                        }
                        
                        // 提取价格
                        const priceSelectors = [
                            '.a-price-whole',
                            '.a-price .a-offscreen',
                            '[data-testid="price-recipe-price"]',
                            '.a-price-current'
                        ];
                        let price = '';
                        for (const selector of priceSelectors) {
                            const priceEl = element.querySelector(selector);
                            if (priceEl && priceEl.textContent.trim()) {
                                price = priceEl.textContent.trim();
                                break;
                            }
                        }
                        
                        // 提取评分
                        const ratingSelectors = [
                            '[aria-label*="stars"]',
                            '.a-icon-alt',
                            '[data-testid="reviews-recipe-rating"]'
                        ];
                        let rating = '';
                        for (const selector of ratingSelectors) {
                            const ratingEl = element.querySelector(selector);
                            if (ratingEl) {
                                const ariaLabel = ratingEl.getAttribute('aria-label') || ratingEl.textContent;
                                if (ariaLabel && ariaLabel.includes('star')) {
                                    rating = ariaLabel;
                                    break;
                                }
                            }
                        }
                        
                        // 提取评论数
                        const reviewSelectors = [
                            'a[href*="#customerReviews"] span',
                            '[data-testid="reviews-recipe-count"]',
                            '.a-size-base'
                        ];
                        let reviewCount = '';
                        for (const selector of reviewSelectors) {
                            const reviewEl = element.querySelector(selector);
                            if (reviewEl && reviewEl.textContent.match(/\\d+/)) {
                                reviewCount = reviewEl.textContent.trim();
                                break;
                            }
                        }
                        
                        // 提取图片链接
                        const imgEl = element.querySelector('img');
                        const imageUrl = imgEl ? imgEl.src : '';
                        
                        // 提取产品链接
                        const linkEl = element.querySelector('h2 a, .s-link-style a');
                        const productUrl = linkEl ? 'https://www.amazon.com' + linkEl.getAttribute('href') : '';
                        
                        // 只添加有标题的产品
                        if (title) {
                            products.push({
                                title: title,
                                price: price || 'N/A',
                                rating: rating || 'N/A',
                                reviews_count: reviewCount || 'N/A',
                                image_url: imageUrl,
                                product_url: productUrl,
                                availability: 'In Stock',
                                brand: 'N/A'
                            });
                        }
                    } catch (error) {
                        console.log(`提取第 ${index} 个产品时出错:`, error);
                    }
                });
                
                console.log(`成功提取 ${products.length} 个产品`);
                return products;
            }
            """
            
            # 执行 JavaScript
            js_result = await self.session.call_tool("browser_evaluate", {
                "function": js_script
            })
            
            # 解析 JavaScript 返回的结果
            if hasattr(js_result, 'content') and js_result.content:
                # 获取第一个内容项
                content_item = js_result.content[0] if js_result.content else None
                if content_item and hasattr(content_item, 'text'):
                    try:
                        products_data = json.loads(content_item.text)
                        
                        for item in products_data:
                            product = ProductInfo(
                                title=item.get('title', ''),
                                price=item.get('price', ''),
                                rating=item.get('rating', ''),
                                reviews_count=item.get('reviews_count', ''),
                                image_url=item.get('image_url', ''),
                                product_url=item.get('product_url', ''),
                                availability=item.get('availability', ''),
                                brand=item.get('brand', '')
                            )
                            products.append(product)
                        
                        print(f"🎯 JavaScript 成功提取了 {len(products)} 个真实产品")
                        
                    except json.JSONDecodeError as e:
                        print(f"⚠️ 解析 JavaScript 结果失败: {e}")
                        print(f"原始结果: {content_item.text[:200]}...")
                        
            if not products:
                print("⚠️ JavaScript 提取未找到产品，尝试其他方法...")
                # 备用方案：从快照中提取
                products = await self._fallback_extract_from_snapshot(snapshot_result)
                
        except Exception as e:
            print(f"⚠️ JavaScript 数据提取过程中出错: {e}")
            # 备用方案
            products = await self._fallback_extract_from_snapshot(snapshot_result)
        
        return products
    
    async def _llm_extract_products(self, page_content: str) -> List[ProductInfo]:
        """使用 LLM 提取产品信息"""
        prompt = f"""
        从以下亚马逊搜索结果页面内容中提取产品信息，返回 JSON 数组格式：

        页面内容摘要: {page_content[:2000]}...

        请提取所有产品的以下信息：
        - title: 产品标题
        - price: 价格
        - rating: 评分
        - reviews_count: 评论数量
        - image_url: 图片链接
        - product_url: 产品链接
        - availability: 库存状态
        - brand: 品牌

        只返回 JSON 数组，格式如下：
        [
            {{
                "title": "产品名称",
                "price": "$价格",
                "rating": "评分",
                "reviews_count": "评论数",
                "image_url": "图片链接",
                "product_url": "产品链接",
                "availability": "库存状态",
                "brand": "品牌"
            }}
        ]
        """
        
        try:
            response = self.task_planner.client.chat.completions.create(
                model=self.task_planner.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            
            if json_match:
                products_data = json.loads(json_match.group())
                products = []
                
                for item in products_data:
                    product = ProductInfo(
                        title=item.get('title', ''),
                        price=item.get('price', ''),
                        rating=item.get('rating', ''),
                        reviews_count=item.get('reviews_count', ''),
                        image_url=item.get('image_url', ''),
                        product_url=item.get('product_url', ''),
                        availability=item.get('availability', ''),
                        brand=item.get('brand', '')
                    )
                    products.append(product)
                
                print(f"🤖 LLM 成功提取了 {len(products)} 个产品")
                return products
            else:
                print("⚠️ LLM 返回格式不正确，使用正则表达式提取")
                return await self._regex_extract_products(page_content)
                
        except Exception as e:
            print(f"⚠️ LLM 提取失败: {e}，使用正则表达式提取")
            return await self._regex_extract_products(page_content)
    
    async def _fallback_extract_from_snapshot(self, snapshot_result: Any) -> List[ProductInfo]:
        """备用方案：从快照中提取产品信息"""
        products = []
        
        try:
            # 解析快照数据结构
            if hasattr(snapshot_result, 'content') and snapshot_result.content:
                content_items = snapshot_result.content
                content = ""
                for item in content_items:
                    if hasattr(item, 'text'):
                        content += item.text + "\n"
            else:
                content = str(snapshot_result)
            
            print("📋 使用快照内容分析...")
            
            # 如果内容很少，可能不是页面内容
            if len(content) < 1000:
                print(f"⚠️ 快照内容太少 ({len(content)} 字符)，可能不是页面内容")
                return []
            
            # 使用 LLM 分析页面内容并提取产品信息
            if self.task_planner.client:
                products = await self._llm_extract_products(content)
            else:
                products = await self._regex_extract_products(content)
                
        except Exception as e:
            print(f"⚠️ 备用提取方法失败: {e}")
            products = []
        
        return products
    
    async def _regex_extract_products(self, page_content: str) -> List[ProductInfo]:
        """使用正则表达式提取产品信息"""
        products = []
        
        # 简化的正则提取（实际项目中需要根据页面结构调整）
        print("📋 使用正则表达式分析页面内容...")
        
        # 这里添加一些基本的模式匹配
        title_pattern = r'data-testid="product-title"[^>]*>([^<]+)'
        price_pattern = r'\$(\d+\.?\d*)'
        
        titles = re.findall(title_pattern, page_content)
        prices = re.findall(price_pattern, page_content)
        
        # 组合提取到的信息
        for i, title in enumerate(titles[:10]):  # 限制最多10个产品
            price = f"${prices[i]}" if i < len(prices) else "Price not available"
            
            product = ProductInfo(
                title=title.strip(),
                price=price,
                rating="N/A",
                reviews_count="N/A", 
                image_url="",
                product_url="",
                availability="In Stock",
                brand="N/A"
            )
            products.append(product)
        
        print(f"📊 正则表达式提取了 {len(products)} 个产品")
        return products
    
    async def _find_next_page_button(self, snapshot_result: Any) -> Optional[str]:
        """寻找下一页按钮的引用"""
        try:
            # 解析快照寻找下一页按钮
            if isinstance(snapshot_result, dict):
                content = str(snapshot_result)
            else:
                content = str(snapshot_result)
            
            # 常见的下一页按钮特征
            next_patterns = [
                r'aria-label="[^"]*next[^"]*"[^>]*data-testid="([^"]+)"',
                r'data-testid="([^"]*next[^"]*)"',
                r'class="[^"]*next[^"]*"[^>]*data-testid="([^"]+)"',
                r'>Next<[^>]*data-testid="([^"]+)"'
            ]
            
            for pattern in next_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    ref = match.group(1)
                    print(f"🔍 找到下一页按钮引用: {ref}")
                    return ref
            
            print("⚠️ 未找到下一页按钮引用")
            return None
            
        except Exception as e:
            print(f"⚠️ 寻找下一页按钮时出错: {e}")
            return None
    
    async def _find_location_elements(self, snapshot_result: Any) -> Dict[str, str]:
        """寻找位置设置相关元素"""
        location_elements = {}
        
        try:
            content = str(snapshot_result)
            
            # 位置设置触发器
            trigger_patterns = [
                r'data-testid="([^"]*location[^"]*)"',
                r'aria-label="[^"]*location[^"]*"[^>]*data-testid="([^"]+)"',
                r'data-testid="([^"]*deliver[^"]*)"'
            ]
            
            for pattern in trigger_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    location_elements["trigger"] = match.group(1)
                    break
            
            # 邮编输入框
            input_patterns = [
                r'data-testid="([^"]*zip[^"]*)"',
                r'data-testid="([^"]*postal[^"]*)"',
                r'type="text"[^>]*data-testid="([^"]+)"[^>]*placeholder="[^"]*zip[^"]*"'
            ]
            
            for pattern in input_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    location_elements["input"] = match.group(1)
                    break
            
            # 确认按钮
            submit_patterns = [
                r'data-testid="([^"]*apply[^"]*)"',
                r'data-testid="([^"]*submit[^"]*)"',
                r'>Apply<[^>]*data-testid="([^"]+)"'
            ]
            
            for pattern in submit_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    location_elements["submit"] = match.group(1)
                    break
            
            print(f"🔍 找到位置元素: {list(location_elements.keys())}")
            return location_elements
            
        except Exception as e:
            print(f"⚠️ 寻找位置元素时出错: {e}")
            return {}

    async def find_element_with_scroll(
        self, 
        selectors: list, 
        strategy: 'ScrollStrategy' = None,
        max_scrolls: int = 8,
        scroll_step: int = 400
    ):
        """
        使用智能滚动查找元素
        
        Args:
            selectors: 元素选择器列表
            strategy: 滚动策略
            max_scrolls: 最大滚动次数
            scroll_step: 滚动步长
            
        Returns:
            找到的元素信息或None
        """
        if not self.scroll_locator:
            print("❌ 智能滚动定位器未初始化，使用传统方法")
            return None
        
        # 默认使用渐进式滚动策略
        if strategy is None and SMART_SCROLL_AVAILABLE:
            strategy = ScrollStrategy.GRADUAL
        
        for selector in selectors:
            print(f"🔍 尝试滚动查找元素: {selector}")
            
            try:
                result = await self.scroll_locator.find_element_by_scrolling(
                    target_selector=selector,
                    strategy=strategy,
                    max_scrolls=max_scrolls,
                    scroll_step=scroll_step,
                    direction=ScrollDirection.DOWN if SMART_SCROLL_AVAILABLE else None
                )
                
                if result.success and result.element_found and result.element_visible:
                    print(f"✅ 成功找到元素: {selector}")
                    print(f"  滚动次数: {result.total_scrolls}")
                    print(f"  元素位置: {result.final_element_info.position}")
                    return result.final_element_info
                else:
                    print(f"❌ 未找到元素: {selector}")
                    if result.error_message:
                        print(f"  错误: {result.error_message}")
            except Exception as e:
                print(f"⚠️ 滚动查找过程中出错: {e}")
                continue
        
        print("⚠️ 所有选择器都未找到对应元素")
        return None
    
    async def smart_next_page_with_scroll(self):
        """智能翻页功能 - 使用滚动定位"""
        print("📄 开始智能滚动翻页...")
        
        # 翻页按钮选择器优先级列表
        next_page_selectors = [
            'a[aria-label="Go to next page"]',
            '.a-pagination .a-last a',
            'a[href*="page=2"]',
            'button[aria-label="转到下一页"]',
            '.a-pagination li:last-child a',
            'a:contains("Next")',
            'button:contains("下一页")'
        ]
        
        # 使用智能滚动定位器查找翻页按钮
        if self.scroll_locator and SMART_SCROLL_AVAILABLE:
            element_info = await self.find_element_with_scroll(
                selectors=next_page_selectors,
                strategy=ScrollStrategy.GRADUAL,
                max_scrolls=10,
                scroll_step=300
            )
            
            if element_info:
                print("🖱️ 尝试点击翻页按钮...")
                try:
                    # 点击找到的翻页按钮
                    click_result = await self.session.call_tool("browser_click", {
                        "element": "下一页按钮",
                        "ref": element_info.selector
                    })
                    
                    if click_result:
                        print("✅ 翻页按钮点击成功")
                        await self._wait(3)  # 等待页面加载
                        return {"message": "智能滚动翻页成功", "success": True, "result": click_result}
                    else:
                        print("❌ 翻页按钮点击失败")
                        return {"message": "翻页按钮点击失败", "success": False}
                        
                except Exception as e:
                    print(f"❌ 点击翻页按钮时出错: {e}")
                    return {"message": f"点击翻页按钮失败: {e}", "success": False}
            else:
                print("❌ 未找到翻页按钮")
                return {"message": "未找到翻页按钮", "success": False}
        else:
            # 回退到原有的翻页方法
            print("⚠️ 智能滚动定位器不可用，使用传统翻页方法")
            return await self._handle_next_page(None)

    async def cleanup(self):
        """清理资源"""
        if self.exit_stack:
            await self.exit_stack.aclose()
            self.is_connected = False
            print("✅ 智能抓取器已关闭")


async def main():
    """主函数 - 演示智能亚马逊抓取"""
    print("🤖 智能亚马逊数据抓取系统")
    print("=" * 60)
    print("结合 LLM 推理和 MCP Playwright 的智能网页抓取")
    print("=" * 60)
    
    # 创建抓取器实例（默认使用 Azure OpenAI）
    scraper = AmazonScraperWithLLM(use_azure=True)
    
    try:
        # 初始化
        if not await scraper.initialize():
            print("❌ 初始化失败")
            return
        
        # 示例任务 1
        print("\n" + "="*50 + " 任务 1 " + "="*50)
        task1 = "https://www.amazon.com/s?k=doorbell 到亚马逊首页，输入关键词doorbell，然后数据提取+导出。更进一步是：翻页，把1-3页的数据导出json"
        result1 = await scraper.execute_task(task1)
        
        # 演示智能滚动功能
        print("\n" + "="*50 + " 智能滚动演示 " + "="*50)
        if scraper.scroll_locator and SMART_SCROLL_AVAILABLE:
            print("🎯 演示智能滚动查找功能...")
            
            # 导航到搜索页面
            await scraper.session.call_tool("browser_navigate", {"url": "https://www.amazon.com/s?k=wireless+mouse"})
            await scraper._wait(3)
            
            # 演示1: 查找翻页按钮
            print("\n📄 演示1: 智能滚动查找翻页按钮")
            pagination_selectors = [
                'a[aria-label="Go to next page"]',
                '.a-pagination .a-last a'
            ]
            
            pagination_element = await scraper.find_element_with_scroll(
                selectors=pagination_selectors,
                strategy=ScrollStrategy.GRADUAL,
                max_scrolls=6,
                scroll_step=400
            )
            
            if pagination_element:
                print(f"✅ 找到翻页按钮: {pagination_element.text}")
                print(f"📍 位置: {pagination_element.position}")
            else:
                print("❌ 未找到翻页按钮")
            
            # 演示2: 查找页面底部元素
            print("\n🔍 演示2: 智能滚动查找页面底部")
            footer_element = await scraper.find_element_with_scroll(
                selectors=['footer', '.navFooterLine'],
                strategy=ScrollStrategy.VIEWPORT_SCAN,
                max_scrolls=8
            )
            
            if footer_element:
                print("✅ 找到页面底部元素")
            else:
                print("❌ 未找到页面底部元素")
                
            print("🎊 智能滚动演示完成!")
        else:
            print("⚠️ 智能滚动功能不可用，跳过演示")
        
        # # 重置产品数据为下一个任务
        # scraper.scraped_products = []
        
        # # 示例任务 2  
        # print("\n" + "="*50 + " 任务 2 " + "="*50)
        # task2 = "搜索smart watch，抓取2页数据，邮编10001"
        # result2 = await scraper.execute_task(task2)
        
        print("\n🎉 所有任务执行完成!")
        
    except Exception as e:
        print(f"❌ 运行过程中出错: {e}")
    
    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    print("📋 使用前请确保已安装:")
    print("  1. npm install -g @playwright/mcp")
    print("  2. pip install mcp")
    print("  3. playwright install")
    print("  4. pip install openai (可选，用于 LLM 推理)")
    print()
    print("💡 设置环境变量:")
    print("  export OPENAI_API_KEY='your-api-key'  # 可选")
    print()
    
    asyncio.run(main())