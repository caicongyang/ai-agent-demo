#!/usr/bin/env python3
"""
智能定位器配置文件

这个文件包含了智能重定位系统的所有配置参数和策略定义。
可以根据需要调整这些参数来优化定位性能。
"""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_wait_time: float = 2.0  # 基础等待时间（秒）
    use_exponential_backoff: bool = True
    max_wait_time: float = 16.0  # 最大等待时间（秒）


@dataclass
class LLMConfig:
    """LLM配置"""
    enable_llm_analysis: bool = True
    max_page_content_length: int = 3000
    temperature: float = 0.1
    max_selectors_per_analysis: int = 5


# 预定义的元素定位策略库
ELEMENT_STRATEGIES = {
    # 搜索相关
    "search_box": {
        "name": "搜索框",
        "selectors": [
            '#twotabsearchtextbox',
            'input[name="field-keywords"]',
            '[data-testid="search-input"]',
            'input[type="text"][placeholder*="search"]',
            '.nav-search-field input',
            '#nav-search-submit-text',
            'input[aria-label*="Search"]'
        ],
        "priority": 1
    },
    
    "search_button": {
        "name": "搜索按钮",
        "selectors": [
            '#nav-search-submit-button',
            'input[type="submit"][value="Go"]',
            '[data-testid="search-submit"]',
            '.nav-search-submit input',
            'button[aria-label*="Search"]'
        ],
        "priority": 2
    },
    
    # 导航相关
    "next_page": {
        "name": "下一页按钮",
        "selectors": [
            'a[aria-label="Go to next page"]',
            '.a-pagination .a-last a',
            '[data-testid="pagination-next"]',
            'a[aria-label*="Next"]',
            'a:contains("Next")',
            '.a-pagination li:last-child a',
            'a[aria-label="Go to page 2"]'
        ],
        "priority": 1
    },
    
    "prev_page": {
        "name": "上一页按钮", 
        "selectors": [
            'a[aria-label="Go to previous page"]',
            '.a-pagination .a-first a',
            '[data-testid="pagination-prev"]',
            'a[aria-label*="Previous"]',
            'a:contains("Previous")'
        ],
        "priority": 2
    },
    
    # 位置设置相关
    "location_trigger": {
        "name": "位置设置触发器",
        "selectors": [
            '#glow-ingress-line1',
            '[data-testid="location-selector"]',
            '.nav-global-location-slot',
            '#nav-global-location-popover-link',
            '[aria-label*="location"]',
            '#nav-global-location-data-modal-action',
            '.nav-sprite.nav-logo-tagline'
        ],
        "priority": 1
    },
    
    "zip_input": {
        "name": "邮编输入框",
        "selectors": [
            'input[name="zipCode"]',
            '[data-testid="zip-input"]',
            'input[placeholder*="ZIP"]',
            'input[type="text"][maxlength="5"]',
            '#GLUXZipUpdateInput',
            'input[aria-label*="ZIP"]',
            'input[placeholder*="postal"]'
        ],
        "priority": 1
    },
    
    "apply_button": {
        "name": "确认按钮",
        "selectors": [
            'input[aria-labelledby="GLUXZipUpdate-announce"]',
            '[data-testid="apply-button"]',
            'button:contains("Apply")',
            'input[type="submit"]',
            '.a-button-primary input',
            'button[aria-label*="Apply"]',
            'input[value="Apply"]'
        ],
        "priority": 1
    },
    
    # 产品相关
    "product_container": {
        "name": "产品容器",
        "selectors": [
            '[data-component-type="s-search-result"]',
            '[data-testid="s-result-item"]',
            '[data-component-type="s-product-item"]',
            '.s-result-item',
            '[data-asin]',
            '.s-item-container'
        ],
        "priority": 1
    },
    
    "product_title": {
        "name": "产品标题",
        "selectors": [
            'h2 a span',
            '[data-cy="title-recipe-title"]',
            '.s-size-mini .s-link-style a span',
            'h2 span',
            '.a-size-medium.a-color-base',
            '[data-testid="product-title"]'
        ],
        "priority": 1
    },
    
    "product_price": {
        "name": "产品价格",
        "selectors": [
            '.a-price-whole',
            '.a-price .a-offscreen',
            '[data-testid="price-recipe-price"]',
            '.a-price-current',
            '.a-price-symbol',
            '.a-price-range'
        ],
        "priority": 1
    },
    
    # 筛选和排序
    "sort_dropdown": {
        "name": "排序下拉框",
        "selectors": [
            '#s-result-sort-select',
            '[data-testid="sort-dropdown"]',
            '.a-dropdown-container select',
            'select[name="s"]'
        ],
        "priority": 2
    },
    
    "filter_sidebar": {
        "name": "筛选侧边栏",
        "selectors": [
            '#leftNavContainer',
            '[data-testid="filter-sidebar"]',
            '.s-refinements',
            '#s-refinements'
        ],
        "priority": 2
    }
}

# LLM分析提示模板
LLM_ANALYSIS_PROMPTS = {
    "general": """
分析以下网页内容，找到用于"{element_type}"的最佳CSS选择器或XPath。

目标操作: {action}
元素类型: {element_type}
{text_info}

页面内容摘要:
{page_content}

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
5. 选择器应该具有良好的特异性和稳定性
""",
    
    "search_box": """
分析页面内容，找到亚马逊搜索框的最佳选择器。

页面内容:
{page_content}

搜索框通常具有以下特征：
- 输入类型为text
- 包含placeholder如"Search Amazon"
- 位于页面顶部导航区域
- 可能有name="field-keywords"属性
- 可能有特定的id如"twotabsearchtextbox"

返回JSON格式：
{{
    "selectors": ["选择器1", "选择器2", "选择器3"],
    "confidence": 0.9,
    "reasoning": "基于亚马逊搜索框的典型特征选择"
}}
""",
    
    "next_page": """
分析页面内容，找到"下一页"按钮的最佳选择器。

页面内容:
{page_content}

下一页按钮通常具有以下特征：
- 文本内容包含"Next"或">"
- aria-label包含"next page"
- 位于页面底部分页区域
- 可能在.a-pagination容器内
- 通常是<a>标签

返回JSON格式：
{{
    "selectors": ["选择器1", "选择器2", "选择器3"],
    "confidence": 0.8,
    "reasoning": "基于分页导航的典型模式选择"
}}
"""
}

# 性能优化配置
PERFORMANCE_CONFIG = {
    "enable_selector_caching": True,
    "cache_duration_minutes": 30,
    "max_cache_size": 100,
    "enable_success_rate_tracking": True,
    "min_attempts_for_rate_calculation": 3
}

# 调试配置
DEBUG_CONFIG = {
    "enable_debug_logging": True,
    "log_failed_selectors": True,
    "log_llm_prompts": False,
    "log_page_content": False,
    "save_failed_snapshots": False
}

# 默认配置组合
DEFAULT_CONFIG = {
    "retry": RetryConfig(),
    "llm": LLMConfig(),
    "performance": PERFORMANCE_CONFIG,
    "debug": DEBUG_CONFIG
}


def get_element_strategy(element_type: str) -> Dict:
    """获取元素定位策略"""
    return ELEMENT_STRATEGIES.get(element_type, {
        "name": element_type,
        "selectors": [],
        "priority": 3
    })


def get_llm_prompt(element_type: str, **kwargs) -> str:
    """获取LLM分析提示"""
    template = LLM_ANALYSIS_PROMPTS.get(element_type, LLM_ANALYSIS_PROMPTS["general"])
    return template.format(element_type=element_type, **kwargs)


def update_element_strategy(element_type: str, new_selectors: List[str], success_rate: float = 0.0):
    """更新元素定位策略"""
    if element_type not in ELEMENT_STRATEGIES:
        ELEMENT_STRATEGIES[element_type] = {
            "name": element_type,
            "selectors": [],
            "priority": 2
        }
    
    strategy = ELEMENT_STRATEGIES[element_type]
    
    # 添加新选择器（避免重复）
    for selector in new_selectors:
        if selector not in strategy["selectors"]:
            # 根据成功率决定插入位置
            if success_rate > 0.8:
                strategy["selectors"].insert(0, selector)  # 高成功率放前面
            else:
                strategy["selectors"].append(selector)  # 低成功率放后面


if __name__ == "__main__":
    # 配置文件测试
    print("🔧 智能定位器配置测试")
    print("=" * 40)
    
    # 显示所有策略
    print(f"已配置 {len(ELEMENT_STRATEGIES)} 种元素类型:")
    for element_type, strategy in ELEMENT_STRATEGIES.items():
        print(f"  - {element_type}: {len(strategy['selectors'])} 个选择器")
    
    # 测试获取策略
    search_strategy = get_element_strategy("search_box")
    print(f"\n搜索框策略: {search_strategy['name']}")
    print(f"选择器数量: {len(search_strategy['selectors'])}")
    
    # 测试LLM提示
    prompt = get_llm_prompt("search_box", 
                           action="type", 
                           page_content="<html>...</html>",
                           text_info="输入文本: doorbell")
    print(f"\nLLM提示长度: {len(prompt)} 字符")
    
    print("\n✅ 配置文件测试完成")