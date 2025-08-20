#!/usr/bin/env python3
"""
智能滚动定位器

通过渐进式滚动来查找和定位页面上的特定元素
支持多种滚动策略和元素检测方法
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class ScrollDirection(Enum):
    """滚动方向"""
    DOWN = "down"
    UP = "up"
    LEFT = "left"
    RIGHT = "right"


class ScrollStrategy(Enum):
    """滚动策略"""
    GRADUAL = "gradual"      # 渐进式滚动
    BINARY_SEARCH = "binary" # 二分查找式滚动
    VIEWPORT_SCAN = "scan"   # 视口扫描式滚动


@dataclass
class ScrollStep:
    """滚动步骤"""
    direction: ScrollDirection
    distance: int
    duration: float = 0.5


@dataclass
class ElementInfo:
    """元素信息"""
    selector: str
    found: bool
    visible: bool
    in_viewport: bool
    position: Dict[str, float]
    text: str = ""
    attributes: Dict[str, str] = None


@dataclass
class ScrollResult:
    """滚动结果"""
    success: bool
    element_found: bool
    element_visible: bool
    scroll_position: Dict[str, float]
    total_scrolls: int
    final_element_info: Optional[ElementInfo] = None
    error_message: str = ""


class SmartScrollLocator:
    """智能滚动定位器"""
    
    def __init__(self, session):
        self.session = session
        self.current_scroll_position = {"x": 0, "y": 0}
        self.page_dimensions = {"width": 0, "height": 0, "scrollWidth": 0, "scrollHeight": 0}
        self.viewport_size = {"width": 0, "height": 0}
        
    async def initialize(self):
        """初始化页面信息"""
        try:
            result = await self.session.call_tool("browser_evaluate", {
                "function": """
                () => {
                    return {
                        scroll: {
                            x: window.pageXOffset,
                            y: window.pageYOffset
                        },
                        page: {
                            width: document.documentElement.scrollWidth,
                            height: document.documentElement.scrollHeight
                        },
                        viewport: {
                            width: window.innerWidth,
                            height: window.innerHeight
                        }
                    };
                }
                """
            })
            
            if result.content and result.content[0].text:
                data = json.loads(result.content[0].text)
                self.current_scroll_position = data["scroll"]
                self.page_dimensions = data["page"]
                self.viewport_size = data["viewport"]
                
            print(f"📏 页面初始化完成:")
            print(f"  当前滚动位置: {self.current_scroll_position}")
            print(f"  页面尺寸: {self.page_dimensions}")
            print(f"  视口尺寸: {self.viewport_size}")
            
        except Exception as e:
            print(f"⚠️ 页面初始化失败: {e}")
    
    async def find_element_by_scrolling(
        self, 
        target_selector: str,
        strategy: ScrollStrategy = ScrollStrategy.GRADUAL,
        max_scrolls: int = 10,
        scroll_step: int = 500,
        direction: ScrollDirection = ScrollDirection.DOWN
    ) -> ScrollResult:
        """
        通过滚动查找元素
        
        Args:
            target_selector: 目标元素的CSS选择器
            strategy: 滚动策略
            max_scrolls: 最大滚动次数
            scroll_step: 每次滚动距离(px)
            direction: 滚动方向
            
        Returns:
            ScrollResult: 滚动和查找结果
        """
        print(f"🔍 开始智能滚动定位元素: {target_selector}")
        print(f"📋 滚动策略: {strategy.value}, 最大滚动次数: {max_scrolls}, 步长: {scroll_step}px")
        
        scroll_count = 0
        element_found = False
        element_visible = False
        final_element_info = None
        
        try:
            # 初始化页面信息
            await self.initialize()
            
            # 先检查元素是否已经在当前视口中
            print("🔍 检查元素是否已在当前视口...")
            initial_check = await self._check_element_visibility(target_selector)
            if initial_check.found and initial_check.visible and initial_check.in_viewport:
                print("✅ 元素已在当前视口中，无需滚动")
                return ScrollResult(
                    success=True,
                    element_found=True,
                    element_visible=True,
                    scroll_position=self.current_scroll_position,
                    total_scrolls=0,
                    final_element_info=initial_check
                )
            
            # 根据策略执行滚动搜索
            if strategy == ScrollStrategy.GRADUAL:
                result = await self._gradual_scroll_search(
                    target_selector, max_scrolls, scroll_step, direction
                )
            elif strategy == ScrollStrategy.BINARY_SEARCH:
                result = await self._binary_search_scroll(
                    target_selector, max_scrolls
                )
            elif strategy == ScrollStrategy.VIEWPORT_SCAN:
                result = await self._viewport_scan_search(
                    target_selector, max_scrolls, scroll_step
                )
            else:
                raise ValueError(f"不支持的滚动策略: {strategy}")
                
            return result
            
        except Exception as e:
            print(f"❌ 滚动定位过程中出错: {e}")
            return ScrollResult(
                success=False,
                element_found=False,
                element_visible=False,
                scroll_position=self.current_scroll_position,
                total_scrolls=scroll_count,
                error_message=str(e)
            )
    
    async def _gradual_scroll_search(
        self,
        target_selector: str,
        max_scrolls: int,
        scroll_step: int,
        direction: ScrollDirection
    ) -> ScrollResult:
        """渐进式滚动搜索"""
        print("📜 使用渐进式滚动策略")
        
        scroll_count = 0
        previous_position = self.current_scroll_position.copy()
        
        for i in range(max_scrolls):
            scroll_count += 1
            
            # 执行滚动
            print(f"📜 第 {scroll_count} 次滚动 ({direction.value} {scroll_step}px)")
            await self._scroll_by_distance(direction, scroll_step)
            
            # 等待页面稳定
            await asyncio.sleep(0.5)
            
            # 检查元素
            element_info = await self._check_element_visibility(target_selector)
            
            if element_info.found:
                print(f"🎯 找到元素: {element_info.selector}")
                print(f"  可见性: {element_info.visible}")
                print(f"  在视口内: {element_info.in_viewport}")
                print(f"  位置: {element_info.position}")
                
                if element_info.visible and element_info.in_viewport:
                    print("✅ 元素已在视口中且可见")
                    return ScrollResult(
                        success=True,
                        element_found=True,
                        element_visible=True,
                        scroll_position=self.current_scroll_position,
                        total_scrolls=scroll_count,
                        final_element_info=element_info
                    )
                elif element_info.visible:
                    # 元素可见但不完全在视口内，尝试滚动到元素位置
                    print("🎯 元素可见但不在视口内，滚动到元素位置...")
                    await self._scroll_to_element(target_selector)
                    await asyncio.sleep(0.5)
                    
                    # 重新检查
                    final_check = await self._check_element_visibility(target_selector)
                    return ScrollResult(
                        success=True,
                        element_found=True,
                        element_visible=final_check.visible,
                        scroll_position=self.current_scroll_position,
                        total_scrolls=scroll_count,
                        final_element_info=final_check
                    )
            
            # 检查是否已到页面边界
            current_position = await self._get_current_scroll_position()
            if self._is_at_boundary(previous_position, current_position, direction):
                print(f"🛑 已到达页面边界，停止滚动")
                break
                
            previous_position = current_position
        
        # 搜索完成但未找到元素
        print(f"❌ 经过 {scroll_count} 次滚动未找到元素")
        return ScrollResult(
            success=False,
            element_found=False,
            element_visible=False,
            scroll_position=self.current_scroll_position,
            total_scrolls=scroll_count,
            error_message=f"经过 {scroll_count} 次滚动未找到元素"
        )
    
    async def _binary_search_scroll(self, target_selector: str, max_scrolls: int) -> ScrollResult:
        """二分查找式滚动"""
        print("🔍 使用二分查找滚动策略")
        
        # 先滚动到页面顶部
        await self._scroll_to_position(0, 0)
        
        low = 0
        high = self.page_dimensions["height"]
        scroll_count = 0
        
        while low <= high and scroll_count < max_scrolls:
            scroll_count += 1
            mid = (low + high) // 2
            
            print(f"🔍 二分查找第 {scroll_count} 次: 滚动到 Y={mid}")
            await self._scroll_to_position(0, mid)
            await asyncio.sleep(0.5)
            
            element_info = await self._check_element_visibility(target_selector)
            
            if element_info.found and element_info.in_viewport:
                print("✅ 二分查找成功找到元素")
                return ScrollResult(
                    success=True,
                    element_found=True,
                    element_visible=element_info.visible,
                    scroll_position=self.current_scroll_position,
                    total_scrolls=scroll_count,
                    final_element_info=element_info
                )
            elif element_info.found:
                # 元素存在但不在视口中，调整搜索范围
                element_y = element_info.position.get("top", 0)
                current_y = self.current_scroll_position["y"]
                
                if element_y < current_y:
                    high = mid - 1
                else:
                    low = mid + 1
            else:
                # 元素不存在，继续搜索下半部分
                low = mid + 1
        
        print(f"❌ 二分查找经过 {scroll_count} 次未找到元素")
        return ScrollResult(
            success=False,
            element_found=False,
            element_visible=False,
            scroll_position=self.current_scroll_position,
            total_scrolls=scroll_count,
            error_message="二分查找未找到元素"
        )
    
    async def _viewport_scan_search(
        self, 
        target_selector: str, 
        max_scrolls: int, 
        scroll_step: int
    ) -> ScrollResult:
        """视口扫描式搜索"""
        print("👀 使用视口扫描搜索策略")
        
        scroll_count = 0
        viewport_height = self.viewport_size["height"]
        
        # 从页面顶部开始扫描
        await self._scroll_to_position(0, 0)
        
        while scroll_count < max_scrolls:
            scroll_count += 1
            
            print(f"👀 视口扫描第 {scroll_count} 次")
            
            # 检查当前视口中的元素
            element_info = await self._check_element_visibility(target_selector)
            
            if element_info.found and element_info.in_viewport:
                print("✅ 视口扫描找到元素")
                return ScrollResult(
                    success=True,
                    element_found=True,
                    element_visible=element_info.visible,
                    scroll_position=self.current_scroll_position,
                    total_scrolls=scroll_count,
                    final_element_info=element_info
                )
            
            # 滚动一个视口高度
            await self._scroll_by_distance(ScrollDirection.DOWN, viewport_height - 50)
            await asyncio.sleep(0.5)
            
            # 检查是否到达页面底部
            current_position = await self._get_current_scroll_position()
            if current_position["y"] + viewport_height >= self.page_dimensions["height"]:
                print("🛑 视口扫描已到达页面底部")
                break
        
        print(f"❌ 视口扫描经过 {scroll_count} 次未找到元素")
        return ScrollResult(
            success=False,
            element_found=False,
            element_visible=False,
            scroll_position=self.current_scroll_position,
            total_scrolls=scroll_count,
            error_message="视口扫描未找到元素"
        )
    
    async def _check_element_visibility(self, selector: str) -> ElementInfo:
        """检查元素可见性和位置信息"""
        try:
            result = await self.session.call_tool("browser_evaluate", {
                "function": f"""
                () => {{
                    const element = document.querySelector('{selector.replace("'", "\\'")}');
                    
                    if (!element) {{
                        return {{
                            found: false,
                            visible: false,
                            inViewport: false,
                            position: {{}},
                            text: "",
                            attributes: {{}}
                        }};
                    }}
                    
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    
                    // 检查元素是否在视口内
                    const inViewport = rect.top >= 0 && 
                                     rect.left >= 0 && 
                                     rect.bottom <= window.innerHeight && 
                                     rect.right <= window.innerWidth;
                    
                    // 检查元素是否可见
                    const visible = style.display !== 'none' && 
                                  style.visibility !== 'hidden' && 
                                  style.opacity !== '0' &&
                                  rect.width > 0 && 
                                  rect.height > 0;
                    
                    // 获取元素属性
                    const attributes = {{}};
                    for (let attr of element.attributes) {{
                        attributes[attr.name] = attr.value;
                    }}
                    
                    return {{
                        found: true,
                        visible: visible,
                        inViewport: inViewport,
                        position: {{
                            top: rect.top,
                            left: rect.left,
                            bottom: rect.bottom,
                            right: rect.right,
                            width: rect.width,
                            height: rect.height,
                            absoluteTop: rect.top + window.pageYOffset,
                            absoluteLeft: rect.left + window.pageXOffset
                        }},
                        text: element.textContent.trim(),
                        attributes: attributes
                    }};
                }}
                """
            })
            
            if result.content and result.content[0].text:
                data = json.loads(result.content[0].text)
                return ElementInfo(
                    selector=selector,
                    found=data["found"],
                    visible=data["visible"],
                    in_viewport=data["inViewport"],
                    position=data["position"],
                    text=data["text"],
                    attributes=data["attributes"]
                )
                
        except Exception as e:
            print(f"⚠️ 检查元素可见性失败: {e}")
            
        return ElementInfo(
            selector=selector,
            found=False,
            visible=False,
            in_viewport=False,
            position={}
        )
    
    async def _scroll_by_distance(self, direction: ScrollDirection, distance: int):
        """按指定方向和距离滚动"""
        scroll_script = ""
        
        if direction == ScrollDirection.DOWN:
            scroll_script = f"window.scrollBy(0, {distance})"
        elif direction == ScrollDirection.UP:
            scroll_script = f"window.scrollBy(0, -{distance})"
        elif direction == ScrollDirection.LEFT:
            scroll_script = f"window.scrollBy(-{distance}, 0)"
        elif direction == ScrollDirection.RIGHT:
            scroll_script = f"window.scrollBy({distance}, 0)"
        
        await self.session.call_tool("browser_evaluate", {
            "function": f"() => {{ {scroll_script}; return {{success: true}}; }}"
        })
        
        # 更新当前滚动位置
        self.current_scroll_position = await self._get_current_scroll_position()
    
    async def _scroll_to_position(self, x: int, y: int):
        """滚动到指定位置"""
        await self.session.call_tool("browser_evaluate", {
            "function": f"""
            () => {{
                window.scrollTo({x}, {y});
                return {{success: true}};
            }}
            """
        })
        
        # 更新当前滚动位置
        self.current_scroll_position = await self._get_current_scroll_position()
    
    async def _scroll_to_element(self, selector: str):
        """滚动到指定元素"""
        await self.session.call_tool("browser_evaluate", {
            "function": f"""
            () => {{
                const element = document.querySelector('{selector.replace("'", "\\'")}');
                if (element) {{
                    element.scrollIntoView({{
                        behavior: 'smooth',
                        block: 'center',
                        inline: 'center'
                    }});
                    return {{success: true}};
                }}
                return {{success: false}};
            }}
            """
        })
        
        await asyncio.sleep(1)  # 等待滚动完成
        self.current_scroll_position = await self._get_current_scroll_position()
    
    async def _get_current_scroll_position(self) -> Dict[str, float]:
        """获取当前滚动位置"""
        try:
            result = await self.session.call_tool("browser_evaluate", {
                "function": "() => ({ x: window.pageXOffset, y: window.pageYOffset })"
            })
            
            if result.content and result.content[0].text:
                return json.loads(result.content[0].text)
                
        except Exception as e:
            print(f"⚠️ 获取滚动位置失败: {e}")
            
        return {"x": 0, "y": 0}
    
    def _is_at_boundary(
        self, 
        previous_pos: Dict[str, float], 
        current_pos: Dict[str, float], 
        direction: ScrollDirection
    ) -> bool:
        """检查是否到达页面边界"""
        if direction == ScrollDirection.DOWN:
            return (current_pos["y"] == previous_pos["y"] and 
                   current_pos["y"] + self.viewport_size["height"] >= self.page_dimensions["height"])
        elif direction == ScrollDirection.UP:
            return current_pos["y"] == previous_pos["y"] and current_pos["y"] <= 0
        elif direction == ScrollDirection.LEFT:
            return current_pos["x"] == previous_pos["x"] and current_pos["x"] <= 0
        elif direction == ScrollDirection.RIGHT:
            return (current_pos["x"] == previous_pos["x"] and 
                   current_pos["x"] + self.viewport_size["width"] >= self.page_dimensions["width"])
        
        return False


# 使用示例
async def demo_smart_scroll():
    """智能滚动定位演示"""
    print("🚀 智能滚动定位演示")
    
    # 这里需要实际的session对象
    # locator = SmartScrollLocator(session)
    
    # 示例1: 渐进式滚动查找翻页按钮
    # result = await locator.find_element_by_scrolling(
    #     target_selector='a[aria-label="Go to next page"]',
    #     strategy=ScrollStrategy.GRADUAL,
    #     max_scrolls=10,
    #     scroll_step=500,
    #     direction=ScrollDirection.DOWN
    # )
    
    # 示例2: 二分查找特定产品
    # result = await locator.find_element_by_scrolling(
    #     target_selector='[data-component-type="s-search-result"]:nth-child(20)',
    #     strategy=ScrollStrategy.BINARY_SEARCH,
    #     max_scrolls=8
    # )
    
    # 示例3: 视口扫描查找评论区
    # result = await locator.find_element_by_scrolling(
    #     target_selector='#reviews-section',
    #     strategy=ScrollStrategy.VIEWPORT_SCAN,
    #     max_scrolls=15
    # )
    
    print("演示完成")


if __name__ == "__main__":
    asyncio.run(demo_smart_scroll())