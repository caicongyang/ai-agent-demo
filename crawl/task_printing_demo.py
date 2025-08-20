#!/usr/bin/env python3
"""
任务打印演示脚本

展示智能抓取器如何详细打印每个任务步骤的信息
"""

import asyncio
from amazon_scraper_with_llm import AmazonScraperWithLLM


async def demo_task_printing():
    """演示任务打印功能"""
    print("🖨️  任务打印功能演示")
    print("=" * 80)
    
    # 创建抓取器实例
    scraper = AmazonScraperWithLLM(use_azure=True)
    
    try:
        # 初始化
        print("🔄 正在初始化抓取器...")
        if not await scraper.initialize():
            print("❌ 初始化失败")
            return
        
        print("✅ 抓取器初始化成功")
        
        # 演示任务 - 生成步骤但不执行
        print("\n" + "="*60 + " 任务分析演示 " + "="*60)
        task_description = "搜索wireless earbuds，设置邮编10001，抓取前2页数据并导出CSV和JSON"
        
        print(f"📝 用户任务: {task_description}")
        
        # 1. LLM 分析任务
        print(f"\n🧠 正在分析任务...")
        current_task = await scraper.task_planner.analyze_task(task_description)
        
        print(f"📋 任务解析结果:")
        print(f"  🔍 搜索关键词: {current_task.search_keyword}")
        print(f"  📮 邮编设置: {current_task.zip_code or '未设置'}")
        print(f"  📄 抓取页数: {current_task.pages_to_scrape}")
        print(f"  💾 导出格式: {current_task.export_format}")
        print(f"  📝 附加指令: {current_task.additional_instructions[:50]}...")
        
        # 2. LLM 生成执行步骤
        print(f"\n🔧 正在生成执行步骤...")
        task_steps = await scraper.task_planner.generate_task_steps(current_task)
        scraper.task_steps = task_steps  # 设置到抓取器中
        scraper.current_task = current_task
        
        print(f"📝 生成了 {len(task_steps)} 个执行步骤")
        
        # 3. 使用新的打印函数展示任务
        print(f"\n" + "="*60 + " 任务步骤总览 " + "="*60)
        scraper.print_task_steps_summary()
        
        # 4. 展示每个步骤的详细信息
        print(f"\n" + "="*60 + " 详细步骤信息 " + "="*60)
        for i, step in enumerate(task_steps, 1):
            scraper.print_task_step_detail(step)
            if i < len(task_steps):
                input("\n⏳ 按 Enter 键查看下一个步骤...")
        
        # 5. 模拟一些步骤的执行状态
        print(f"\n" + "="*60 + " 模拟执行状态 " + "="*60)
        
        # 模拟第1步成功
        task_steps[0].completed = True
        task_steps[0].result = {"message": "成功导航到亚马逊首页", "url": "https://www.amazon.com"}
        
        # 模拟第2步失败
        if len(task_steps) > 1:
            task_steps[1].error = "无法找到位置设置按钮，页面结构可能发生变化"
        
        # 模拟第3步成功
        if len(task_steps) > 2:
            task_steps[2].completed = True
            task_steps[2].result = {"message": "搜索成功", "keyword": "wireless earbuds"}
        
        # 重新显示更新后的状态
        print("🔄 更新后的任务状态:")
        scraper.print_task_steps_summary()
        
        # 显示执行统计
        completed_steps = sum(1 for step in task_steps if step.completed)
        failed_steps = sum(1 for step in task_steps if step.error)
        pending_steps = len(task_steps) - completed_steps - failed_steps
        
        print(f"\n📊 执行统计:")
        print(f"  ✅ 已完成: {completed_steps} 步")
        print(f"  ❌ 失败: {failed_steps} 步")
        print(f"  ⏳ 待执行: {pending_steps} 步")
        print(f"  📈 成功率: {completed_steps/len(task_steps)*100:.1f}%")
        
        print(f"\n🎉 任务打印演示完成!")
        
    except Exception as e:
        print(f"❌ 演示过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await scraper.cleanup()


async def demo_step_types():
    """演示不同类型的任务步骤"""
    print("\n" + "="*80)
    print("🎭 不同类型任务步骤演示")
    print("=" * 80)
    
    from amazon_scraper_with_llm import TaskStep
    
    # 创建不同类型的示例步骤
    sample_steps = [
        TaskStep(
            step_number=1,
            action="navigate",
            description="导航到亚马逊首页",
            mcp_tool="browser_navigate",
            parameters={"url": "https://www.amazon.com"},
            expected_result="成功访问亚马逊首页",
            completed=True
        ),
        TaskStep(
            step_number=2,
            action="set_zipcode",
            description="设置配送地址邮编为 10001",
            mcp_tool="browser_click",
            parameters={"element": "位置设置", "ref": "#glow-ingress-line1"},
            expected_result="邮编设置为 10001",
            error="定位元素失败：页面结构发生变化"
        ),
        TaskStep(
            step_number=3,
            action="search",
            description="搜索关键词 'wireless earbuds'",
            mcp_tool="browser_type",
            parameters={
                "element": "搜索框",
                "ref": "#twotabsearchtextbox",
                "text": "wireless earbuds",
                "submit": True
            },
            expected_result="显示 wireless earbuds 的搜索结果",
            completed=True
        ),
        TaskStep(
            step_number=4,
            action="extract_data",
            description="提取第 1 页产品数据",
            mcp_tool="browser_snapshot",
            parameters={},
            expected_result="成功提取第 1 页产品信息"
        ),
        TaskStep(
            step_number=5,
            action="next_page",
            description="翻到第 2 页",
            mcp_tool="browser_click",
            parameters={"element": "下一页按钮", "ref": ".a-pagination .a-last a"},
            expected_result="成功翻到第 2 页"
        )
    ]
    
    # 创建临时抓取器实例来使用打印函数
    scraper = AmazonScraperWithLLM(use_azure=True)
    scraper.task_steps = sample_steps
    
    # 显示步骤摘要
    scraper.print_task_steps_summary()
    
    # 显示每个步骤的详细信息
    print(f"\n📋 各步骤详细信息:")
    for step in sample_steps:
        scraper.print_task_step_detail(step)
    
    print(f"\n✨ 步骤类型演示完成!")


async def main():
    """主函数"""
    print("🖨️  智能抓取器任务打印系统")
    print("展示如何详细打印和跟踪每个任务步骤")
    print("=" * 80)
    
    # 演示1：完整的任务打印流程
    await demo_task_printing()
    
    # 演示2：不同类型的步骤
    await demo_step_types()
    
    print("\n🎊 所有演示完成!")


if __name__ == "__main__":
    print("🚀 启动任务打印演示...")
    print("💡 这个演示将展示智能抓取器如何详细打印每个任务步骤")
    print()
    
    asyncio.run(main())