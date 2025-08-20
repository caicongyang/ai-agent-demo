#!/usr/bin/env python3
"""
智能滚动定位集成示例

展示如何在现有的Amazon抓取器中集成智能滚动定位功能
"""

import asyncio
from amazon_scraper_with_llm import AmazonScraperWithLLM
from smart_scroll_locator import SmartScrollLocator, ScrollStrategy, ScrollDirection


class EnhancedAmazonScraper(AmazonScraperWithLLM):
    """增强的Amazon抓取器，集成智能滚动定位功能"""
    
    def __init__(self, use_azure: bool = True):
        super().__init__(use_azure)
        self.scroll_locator = None
    
    async def initialize(self):
        """初始化，包括滚动定位器"""
        success = await super().initialize()
        if success:
            self.scroll_locator = SmartScrollLocator(self.session)
            print("✅ 智能滚动定位器已初始化")
        return success
    
    async def find_element_with_scroll(
        self, 
        selectors: list, 
        strategy: ScrollStrategy = ScrollStrategy.GRADUAL,
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
            print("❌ 滚动定位器未初始化")
            return None
        
        for selector in selectors:
            print(f"🔍 尝试滚动查找元素: {selector}")
            
            result = await self.scroll_locator.find_element_by_scrolling(
                target_selector=selector,
                strategy=strategy,
                max_scrolls=max_scrolls,
                scroll_step=scroll_step,
                direction=ScrollDirection.DOWN
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
        
        print("⚠️ 所有选择器都未找到对应元素")
        return None
    
    async def smart_next_page(self):
        """智能翻页功能"""
        print("📄 开始智能翻页...")
        
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
        
        # 使用渐进式滚动策略查找翻页按钮
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
                    return True
                else:
                    print("❌ 翻页按钮点击失败")
                    return False
                    
            except Exception as e:
                print(f"❌ 点击翻页按钮时出错: {e}")
                return False
        else:
            print("❌ 未找到翻页按钮")
            return False
    
    async def smart_find_products(self, min_products: int = 10):
        """智能查找产品，确保找到足够数量的产品"""
        print(f"🛍️ 智能查找产品 (最少 {min_products} 个)...")
        
        # 产品容器选择器
        product_selectors = [
            '[data-component-type="s-search-result"]',
            '.s-result-item',
            '.s-widget-container .s-card-container',
            '[data-index]'
        ]
        
        all_products = []
        
        # 使用视口扫描策略查找所有产品
        for selector in product_selectors:
            print(f"🔍 扫描产品容器: {selector}")
            
            # 滚动回顶部开始扫描
            await self.scroll_locator._scroll_to_position(0, 0)
            await asyncio.sleep(1)
            
            result = await self.scroll_locator.find_element_by_scrolling(
                target_selector=selector,
                strategy=ScrollStrategy.VIEWPORT_SCAN,
                max_scrolls=15,
                scroll_step=400
            )
            
            if result.success:
                print(f"✅ 找到产品容器: {selector}")
                
                # 提取所有产品信息
                products = await self._extract_products_from_page()
                if products and len(products) >= min_products:
                    print(f"✅ 找到 {len(products)} 个产品，满足要求")
                    return products
                else:
                    print(f"⚠️ 只找到 {len(products) if products else 0} 个产品，继续尝试其他选择器")
        
        print("❌ 未找到足够数量的产品")
        return []
    
    async def smart_search_with_scroll(self, search_term: str, pages: int = 3):
        """
        智能搜索，结合滚动定位功能
        
        Args:
            search_term: 搜索关键词
            pages: 要抓取的页数
        """
        print(f"🔍 开始智能搜索: {search_term}")
        print(f"📄 计划抓取 {pages} 页")
        
        all_products = []
        
        try:
            # 1. 导航到搜索页面
            search_url = f"https://www.amazon.com/s?k={search_term.replace(' ', '+')}"
            await self.session.call_tool("browser_navigate", {"url": search_url})
            await self._wait(3)
            
            # 2. 逐页抓取
            for page_num in range(1, pages + 1):
                print(f"\n📄 处理第 {page_num} 页...")
                
                # 查找并提取当前页产品
                products = await self.smart_find_products(min_products=5)
                if products:
                    print(f"✅ 第 {page_num} 页找到 {len(products)} 个产品")
                    all_products.extend(products)
                else:
                    print(f"⚠️ 第 {page_num} 页未找到足够产品")
                
                # 如果不是最后一页，尝试翻页
                if page_num < pages:
                    success = await self.smart_next_page()
                    if not success:
                        print(f"❌ 无法翻到第 {page_num + 1} 页，停止抓取")
                        break
            
            print(f"\n🎊 智能搜索完成!")
            print(f"📊 总计找到 {len(all_products)} 个产品")
            
            return all_products
            
        except Exception as e:
            print(f"❌ 智能搜索过程中出错: {e}")
            return all_products


async def demo_scroll_integration():
    """演示滚动集成功能"""
    print("🚀 智能滚动定位集成演示")
    print("=" * 60)
    
    scraper = EnhancedAmazonScraper(use_azure=True)
    
    try:
        # 初始化
        if not await scraper.initialize():
            print("❌ 初始化失败")
            return
        
        # 演示1: 智能搜索
        print("\n🎯 演示1: 智能搜索功能")
        print("-" * 40)
        
        products = await scraper.smart_search_with_scroll(
            search_term="bluetooth headphones",
            pages=2
        )
        
        if products:
            print(f"✅ 搜索成功，找到 {len(products)} 个产品")
            for i, product in enumerate(products[:3], 1):
                print(f"  产品 {i}: {product.get('name', 'Unknown')[:50]}...")
        
        # 演示2: 智能元素查找
        print("\n🎯 演示2: 智能元素查找功能")
        print("-" * 40)
        
        # 查找页面底部的相关搜索
        related_search_selectors = [
            '#s-related-search-suggestions',
            '.s-suggestion-container',
            '[data-cel-widget="related_search_suggestions"]'
        ]
        
        related_element = await scraper.find_element_with_scroll(
            selectors=related_search_selectors,
            strategy=ScrollStrategy.BINARY_SEARCH,
            max_scrolls=6
        )
        
        if related_element:
            print("✅ 找到相关搜索区域")
            print(f"  文本内容: {related_element.text[:100]}...")
        else:
            print("❌ 未找到相关搜索区域")
        
        # 演示3: 不同滚动策略对比
        print("\n🎯 演示3: 滚动策略对比")
        print("-" * 40)
        
        test_selector = 'footer'
        strategies = [
            (ScrollStrategy.GRADUAL, "渐进式"),
            (ScrollStrategy.BINARY_SEARCH, "二分查找"),
            (ScrollStrategy.VIEWPORT_SCAN, "视口扫描")
        ]
        
        for strategy, name in strategies:
            # 滚动回顶部
            await scraper.scroll_locator._scroll_to_position(0, 0)
            await asyncio.sleep(0.5)
            
            print(f"🧪 测试 {name} 策略...")
            
            import time
            start_time = time.time()
            
            result = await scraper.scroll_locator.find_element_by_scrolling(
                target_selector=test_selector,
                strategy=strategy,
                max_scrolls=8
            )
            
            duration = time.time() - start_time
            
            if result.success:
                print(f"  ✅ 成功 | {result.total_scrolls}次滚动 | {duration:.2f}秒")
            else:
                print(f"  ❌ 失败 | {result.total_scrolls}次滚动 | {duration:.2f}秒")
        
        print("\n🎊 集成演示完成!")
        
    except Exception as e:
        print(f"❌ 演示过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await scraper.cleanup()


async def quick_test():
    """快速测试特定功能"""
    print("⚡ 快速测试智能滚动定位")
    
    scraper = EnhancedAmazonScraper(use_azure=True)
    
    try:
        if not await scraper.initialize():
            print("❌ 初始化失败")
            return
        
        # 导航到页面
        await scraper.session.call_tool("browser_navigate", {"url": "https://www.amazon.com/s?k=doorbell"})
        await scraper._wait(3)
        
        # 快速查找翻页按钮
        pagination_found = await scraper.find_element_with_scroll(
            selectors=['a[aria-label="Go to next page"]', '.a-pagination .a-last a'],
            strategy=ScrollStrategy.GRADUAL,
            max_scrolls=5,
            scroll_step=500
        )
        
        if pagination_found:
            print("✅ 快速测试成功 - 找到翻页按钮")
            print(f"  位置: {pagination_found.position}")
            print(f"  文本: '{pagination_found.text}'")
        else:
            print("❌ 快速测试失败 - 未找到翻页按钮")
        
    except Exception as e:
        print(f"❌ 快速测试失败: {e}")
    
    finally:
        await scraper.cleanup()


async def main():
    """主函数"""
    print("🚀 智能滚动定位集成系统")
    print("=" * 50)
    
    print("请选择运行模式:")
    print("1. 完整演示 (推荐)")
    print("2. 快速测试")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        await demo_scroll_integration()
    elif choice == "2":
        await quick_test()
    else:
        print("默认运行完整演示...")
        await demo_scroll_integration()


if __name__ == "__main__":
    asyncio.run(main())