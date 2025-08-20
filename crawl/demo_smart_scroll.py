#!/usr/bin/env python3
"""
智能滚动定位功能演示

展示如何通过滚动查找页面上的特定元素
"""

import asyncio
from amazon_scraper_with_llm import AmazonScraperWithLLM
from smart_scroll_locator import SmartScrollLocator, ScrollStrategy, ScrollDirection


async def demo_smart_scroll():
    """智能滚动定位演示"""
    print("🎯 智能滚动定位功能演示")
    print("=" * 50)
    print("这个演示将展示如何通过滚动找到页面上的特定元素")
    print()
    
    scraper = AmazonScraperWithLLM(use_azure=True)
    
    try:
        # 初始化
        print("🔧 正在初始化...")
        if not await scraper.initialize():
            print("❌ 初始化失败")
            return
        
        print("✅ 初始化成功")
        
        # 创建智能滚动定位器
        scroll_locator = SmartScrollLocator(scraper.session)
        
        # 导航到测试页面
        print("\n🌐 导航到Amazon搜索页面...")
        await scraper.session.call_tool("browser_navigate", {"url": "https://www.amazon.com/s?k=wireless+mouse"})
        await scraper._wait(3)
        print("✅ 页面加载完成")
        
        # 演示1: 查找翻页按钮
        print("\n🎯 演示1: 使用渐进式滚动查找翻页按钮")
        print("-" * 40)
        
        result = await scroll_locator.find_element_by_scrolling(
            target_selector='a[aria-label="Go to next page"]',
            strategy=ScrollStrategy.GRADUAL,
            max_scrolls=6,
            scroll_step=500,
            direction=ScrollDirection.DOWN
        )
        
        print(f"📊 查找结果:")
        print(f"  成功: {'✅' if result.success else '❌'}")
        print(f"  找到元素: {'✅' if result.element_found else '❌'}")
        print(f"  元素可见: {'✅' if result.element_visible else '❌'}")
        print(f"  滚动次数: {result.total_scrolls}")
        print(f"  最终位置: Y={result.scroll_position.get('y', 0):.1f}px")
        
        if result.success and result.final_element_info:
            info = result.final_element_info
            print(f"  元素文本: '{info.text}'")
            print(f"  元素位置: top={info.position.get('top', 0):.1f}px")
            print(f"  在视口内: {'✅' if info.in_viewport else '❌'}")
        
        # 演示2: 查找页面底部元素
        print("\n🎯 演示2: 使用视口扫描查找页面底部")
        print("-" * 40)
        
        # 先滚动回顶部
        await scroll_locator._scroll_to_position(0, 0)
        await asyncio.sleep(1)
        
        footer_result = await scroll_locator.find_element_by_scrolling(
            target_selector='footer',
            strategy=ScrollStrategy.VIEWPORT_SCAN,
            max_scrolls=8,
            scroll_step=600
        )
        
        print(f"📊 页脚查找结果:")
        print(f"  成功: {'✅' if footer_result.success else '❌'}")
        print(f"  找到元素: {'✅' if footer_result.element_found else '❌'}")
        print(f"  滚动次数: {footer_result.total_scrolls}")
        
        if footer_result.success:
            print("✅ 成功找到页面底部!")
        
        # 演示3: 性能对比
        print("\n🎯 演示3: 不同策略性能对比")
        print("-" * 40)
        
        test_selector = '.a-pagination'
        strategies = [
            (ScrollStrategy.GRADUAL, "渐进式滚动"),
            (ScrollStrategy.BINARY_SEARCH, "二分查找")
        ]
        
        for strategy, name in strategies:
            # 滚动回顶部
            await scroll_locator._scroll_to_position(0, 0)
            await asyncio.sleep(0.5)
            
            print(f"🧪 测试 {name}...")
            
            import time
            start_time = time.time()
            
            test_result = await scroll_locator.find_element_by_scrolling(
                target_selector=test_selector,
                strategy=strategy,
                max_scrolls=6
            )
            
            duration = time.time() - start_time
            
            status = "✅ 成功" if test_result.success else "❌ 失败"
            print(f"  结果: {status} | {test_result.total_scrolls}次滚动 | {duration:.2f}秒")
        
        print("\n🎊 演示完成!")
        print("\n📋 总结:")
        print("✅ 智能滚动定位可以自动找到页面上的任何元素")
        print("✅ 支持多种滚动策略，适应不同场景")
        print("✅ 提供详细的元素位置和可见性信息")
        print("✅ 自动处理页面边界和错误情况")
        
    except Exception as e:
        print(f"❌ 演示过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await scraper.cleanup()
        print("\n👋 演示结束")


async def interactive_demo():
    """交互式演示"""
    print("🎮 交互式智能滚动定位演示")
    print("=" * 50)
    
    scraper = AmazonScraperWithLLM(use_azure=True)
    
    try:
        if not await scraper.initialize():
            print("❌ 初始化失败")
            return
        
        scroll_locator = SmartScrollLocator(scraper.session)
        
        # 导航到页面
        await scraper.session.call_tool("browser_navigate", {"url": "https://www.amazon.com/s?k=laptop"})
        await scraper._wait(3)
        
        print("✅ 已导航到Amazon笔记本搜索页面")
        print("\n请选择要查找的元素:")
        print("1. 翻页按钮")
        print("2. 第10个产品")
        print("3. 页面底部")
        print("4. 自定义选择器")
        
        choice = input("\n请输入选择 (1-4): ").strip()
        
        if choice == "1":
            selector = 'a[aria-label="Go to next page"]'
            strategy = ScrollStrategy.GRADUAL
            print(f"🔍 查找翻页按钮: {selector}")
        elif choice == "2":
            selector = '[data-component-type="s-search-result"]:nth-child(10)'
            strategy = ScrollStrategy.BINARY_SEARCH
            print(f"🔍 查找第10个产品: {selector}")
        elif choice == "3":
            selector = 'footer'
            strategy = ScrollStrategy.VIEWPORT_SCAN
            print(f"🔍 查找页面底部: {selector}")
        elif choice == "4":
            selector = input("请输入CSS选择器: ").strip()
            strategy = ScrollStrategy.GRADUAL
            print(f"🔍 查找自定义元素: {selector}")
        else:
            selector = 'a[aria-label="Go to next page"]'
            strategy = ScrollStrategy.GRADUAL
            print("🔍 默认查找翻页按钮")
        
        print(f"\n📜 使用 {strategy.value} 策略搜索...")
        
        result = await scroll_locator.find_element_by_scrolling(
            target_selector=selector,
            strategy=strategy,
            max_scrolls=8,
            scroll_step=400
        )
        
        print(f"\n📊 搜索结果:")
        print(f"成功: {'✅' if result.success else '❌'}")
        print(f"找到元素: {'✅' if result.element_found else '❌'}")
        print(f"元素可见: {'✅' if result.element_visible else '❌'}")
        print(f"滚动次数: {result.total_scrolls}")
        print(f"最终滚动位置: Y={result.scroll_position.get('y', 0):.1f}px")
        
        if result.success and result.final_element_info:
            info = result.final_element_info
            print(f"元素文本: '{info.text[:50]}{'...' if len(info.text) > 50 else ''}'")
            print(f"元素位置: {info.position}")
            print(f"在视口内: {'✅' if info.in_viewport else '❌'}")
        
        if result.error_message:
            print(f"错误信息: {result.error_message}")
        
    except Exception as e:
        print(f"❌ 交互演示失败: {e}")
    
    finally:
        await scraper.cleanup()


async def main():
    """主函数"""
    print("🚀 智能滚动定位功能演示系统")
    print("通过滚动自动查找页面上的任何元素")
    print("=" * 60)
    
    print("请选择演示模式:")
    print("1. 自动演示 (推荐)")
    print("2. 交互式演示")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        await demo_smart_scroll()
    elif choice == "2":
        await interactive_demo()
    else:
        print("默认运行自动演示...")
        await demo_smart_scroll()


if __name__ == "__main__":
    asyncio.run(main())