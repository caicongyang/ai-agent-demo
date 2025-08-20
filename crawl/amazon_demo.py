"""
智能亚马逊抓取器使用示例

这个文件展示了如何使用 AmazonScraperWithLLM 进行各种抓取任务
"""

import asyncio
import os
from dotenv import load_dotenv
from amazon_scraper_with_llm import AmazonScraperWithLLM

# 加载环境变量
load_dotenv()


async def demo_basic_scraping():
    """演示基础抓取功能"""
    print("🚀 演示 1: 基础商品抓取")
    print("-" * 40)
    
    scraper = AmazonScraperWithLLM()
    
    try:
        await scraper.initialize()
        
        # 简单的搜索任务
        task = "在亚马逊搜索doorbell"
        result = await scraper.execute_task(task)
        
        print(f"任务完成! 找到 {result.get('products_found', 0)} 个产品")
        
    finally:
        await scraper.cleanup()


async def demo_multi_page_scraping():
    """演示多页抓取"""
    print("\n🚀 演示 2: 多页数据抓取")
    print("-" * 40)
    
    scraper = AmazonScraperWithLLM()
    
    try:
        await scraper.initialize()
        
        # 多页抓取任务
        task = "搜索smart doorbell，抓取3页数据，导出到CSV"
        result = await scraper.execute_task(task)
        
        print(f"多页抓取完成! 总共找到 {result.get('products_found', 0)} 个产品")
        
    finally:
        await scraper.cleanup()


async def demo_with_zipcode():
    """演示带邮编的抓取"""
    print("\n🚀 演示 3: 带邮编设置的抓取")
    print("-" * 40)
    
    scraper = AmazonScraperWithLLM()
    
    try:
        await scraper.initialize()
        
        # 带邮编的任务
        task = "搜索wireless doorbell，设置邮编90210，抓取前2页数据"
        result = await scraper.execute_task(task)
        
        print(f"带邮编抓取完成! 邮编: 90210, 产品数: {result.get('products_found', 0)}")
        
    finally:
        await scraper.cleanup()


async def demo_with_llm():
    """演示使用 LLM 增强功能"""
    print("\n🚀 演示 4: LLM 增强抓取 (Azure OpenAI)")
    print("-" * 40)
    
    # 检查 Azure OpenAI 或标准 OpenAI 配置
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if azure_endpoint and azure_api_key:
        print("✅ 使用 Azure OpenAI 配置")
        scraper = AmazonScraperWithLLM(use_azure=True)
    elif openai_api_key:
        print("✅ 使用标准 OpenAI 配置")
        scraper = AmazonScraperWithLLM(openai_api_key=openai_api_key, use_azure=False)
    else:
        print("⚠️ 未设置 LLM API 配置，将使用规则解析")
        scraper = AmazonScraperWithLLM(use_azure=False)
    
    try:
        await scraper.initialize()
        
        # 复杂的自然语言任务
        task = """
        我想在亚马逊上找些门铃产品，具体要求是：
        1. 搜索关键词用 'video doorbell'
        2. 我住在洛杉矶，邮编是90210
        3. 帮我抓取前3页的产品信息
        4. 最后导出成CSV文件方便我分析
        """
        
        result = await scraper.execute_task(task)
        
        if azure_endpoint and azure_api_key:
            print("✅ Azure OpenAI 成功解析了复杂的自然语言任务!")
        elif openai_api_key:
            print("✅ OpenAI 成功解析了复杂的自然语言任务!")
        else:
            print("📝 使用规则解析了任务（建议配置 Azure OpenAI 或 OpenAI 获得更好效果）")
        
        print(f"任务执行结果: {result.get('products_found', 0)} 个产品")
        
    finally:
        await scraper.cleanup()


async def demo_different_products():
    """演示不同产品的抓取"""
    print("\n🚀 演示 5: 不同产品类型抓取")
    print("-" * 40)
    
    scraper = AmazonScraperWithLLM()
    
    try:
        await scraper.initialize()
        
        # 测试不同类型的产品
        products = [
            "bluetooth speakers",
            "wireless headphones", 
            "smart watch"
        ]
        
        for product in products:
            print(f"\n🔍 正在抓取: {product}")
            task = f"搜索{product}，抓取1页数据"
            
            result = await scraper.execute_task(task)
            print(f"✅ {product}: 找到 {result.get('products_found', 0)} 个产品")
            
            # 清空之前的数据
            scraper.scraped_products = []
            
            # 短暂等待
            await asyncio.sleep(2)
        
    finally:
        await scraper.cleanup()


async def demo_error_handling():
    """演示错误处理"""
    print("\n🚀 演示 6: 错误处理和恢复")
    print("-" * 40)
    
    scraper = AmazonScraperWithLLM()
    
    try:
        await scraper.initialize()
        
        # 故意使用一个可能导致问题的任务
        task = "搜索非常特殊的产品abcdef12345xyz，抓取10页数据"
        
        result = await scraper.execute_task(task)
        
        print("错误处理演示完成:")
        print(f"- 执行的步骤: {result.get('steps_completed', 0)}/{result.get('steps_executed', 0)}")
        print(f"- 是否有错误: {'是' if not result.get('success', True) else '否'}")
        
    finally:
        await scraper.cleanup()


async def interactive_demo():
    """交互式演示"""
    print("\n🚀 演示 7: 交互式使用")
    print("-" * 40)
    print("请输入你的抓取任务，或输入 'quit' 退出")
    
    scraper = AmazonScraperWithLLM()
    
    try:
        await scraper.initialize()
        
        while True:
            user_input = input("\n💬 请输入任务: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                print("👋 再见!")
                break
            
            if not user_input:
                continue
            
            try:
                print(f"\n🚀 执行任务: {user_input}")
                result = await scraper.execute_task(user_input)
                
                print("\n📊 任务结果:")
                print(f"- 产品数量: {result.get('products_found', 0)}")
                print(f"- 执行步骤: {result.get('steps_completed', 0)}/{result.get('steps_executed', 0)}")
                
                if result.get('export_result', {}).get('success'):
                    export_info = result['export_result']
                    print(f"- 导出文件: {export_info.get('csv_file', 'N/A')}")
                
                # 清空数据准备下次使用
                scraper.scraped_products = []
                
            except Exception as e:
                print(f"❌ 执行错误: {e}")
        
    finally:
        await scraper.cleanup()


async def main():
    """主演示函数"""
    print("🤖 智能亚马逊抓取器 - 使用演示")
    print("=" * 60)
    print("这个演示展示了如何使用 LLM + MCP Playwright 进行智能网页抓取")
    print("=" * 60)
    
    demos = [
        ("基础商品抓取", demo_basic_scraping),
        ("多页数据抓取", demo_multi_page_scraping), 
        ("带邮编设置的抓取", demo_with_zipcode),
        ("LLM 增强抓取", demo_with_llm),
        ("不同产品类型抓取", demo_different_products),
        ("错误处理演示", demo_error_handling),
        ("交互式使用", interactive_demo),
    ]
    
    print("\n选择要运行的演示:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  0. 运行所有演示")
    print("  q. 退出")
    
    while True:
        choice = input("\n请输入选择 (0-7 或 q): ").strip().lower()
        
        if choice == 'q':
            print("👋 再见!")
            break
        elif choice == '0':
            print("🚀 运行所有演示...")
            for name, demo_func in demos:
                try:
                    print(f"\n{'='*20} {name} {'='*20}")
                    await demo_func()
                except KeyboardInterrupt:
                    print("\n⚠️ 用户中断，跳过当前演示")
                    continue
                except Exception as e:
                    print(f"❌ 演示 '{name}' 执行失败: {e}")
                    continue
            break
        elif choice.isdigit() and 1 <= int(choice) <= len(demos):
            demo_index = int(choice) - 1
            name, demo_func = demos[demo_index]
            try:
                print(f"\n{'='*20} {name} {'='*20}")
                await demo_func()
            except KeyboardInterrupt:
                print("\n⚠️ 用户中断")
            except Exception as e:
                print(f"❌ 演示失败: {e}")
            break
        else:
            print("❌ 无效选择，请重新输入")


if __name__ == "__main__":
    print("📋 使用前请确保:")
    print("  1. npm install -g @playwright/mcp")
    print("  2. pip install mcp openai")
    print("  3. playwright install")
    print("  4. export OPENAI_API_KEY='your-key' (可选)")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断，再见!")
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")