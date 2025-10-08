#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流代码解释器测试脚本
用于验证工作流功能是否正常
"""

import json
import tempfile
from workflow_code_interpreter import WorkflowEngine


def test_basic_workflow():
    """测试基本工作流功能"""
    print("🧪 测试基本工作流功能")
    print("=" * 40)
    
    engine = WorkflowEngine()
    
    # 创建测试数据
    test_data = {
        "users": [
            {"id": 1, "name": "张三", "age": 25, "city": "北京"},
            {"id": 2, "name": "李四", "age": 30, "city": "上海"},
            {"id": 3, "name": "王五", "age": 28, "city": "北京"},
        ]
    }
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f, ensure_ascii=False)
        temp_file = f.name
    
    try:
        # 定义测试工作流
        workflow_steps = [
            {
                "tool": "file_reader",
                "description": "读取测试数据",
                "file_path": temp_file,
                "data_key": "test_users"
            },
            {
                "tool": "workflow_code_interpreter",
                "description": "分析用户数据",
                "code": """
# 分析用户数据
users_data = context_data.get('test_users', {})
users = users_data.get('users', [])

print(f"用户数量: {len(users)}")

if users:
    # 年龄分析
    ages = [user['age'] for user in users]
    avg_age = sum(ages) / len(ages)
    print(f"平均年龄: {avg_age:.1f}")
    
    # 城市分布
    cities = {}
    for user in users:
        city = user['city']
        cities[city] = cities.get(city, 0) + 1
    
    print("城市分布:")
    for city, count in cities.items():
        print(f"  {city}: {count} 人")
                """,
                "result_key": "user_analysis"
            }
        ]
        
        # 执行工作流
        result = engine.execute_workflow(workflow_steps)
        
        if result['success']:
            print("✅ 基本工作流测试通过")
            return True
        else:
            print("❌ 基本工作流测试失败")
            return False
            
    finally:
        # 清理临时文件
        import os
        try:
            os.unlink(temp_file)
        except:
            pass


def test_multi_step_workflow():
    """测试多步骤工作流"""
    print("\n🔄 测试多步骤工作流")
    print("=" * 40)
    
    engine = WorkflowEngine()
    
    workflow_steps = [
        {
            "tool": "database_query",
            "description": "获取销售数据",
            "query": "SELECT * FROM sales",
            "data_key": "sales_data"
        },
        {
            "tool": "database_query", 
            "description": "获取用户数据",
            "query": "SELECT * FROM users",
            "data_key": "users_data"
        },
        {
            "tool": "workflow_code_interpreter",
            "description": "关联分析",
            "code": """
# 关联分析
sales = context_data.get('sales_data', [])
users = context_data.get('users_data', [])

print("=== 数据关联分析 ===")
print(f"销售记录: {len(sales)} 条")
print(f"用户记录: {len(users)} 条")

if sales and users:
    # 创建用户映射
    user_map = {user['id']: user for user in users}
    
    # 分析销售数据
    total_sales = sum(item['amount'] for item in sales)
    print(f"总销售额: {total_sales}")
    
    # 用户购买分析
    user_purchases = {}
    for sale in sales:
        # 这里简化处理，假设有user_id字段
        user_id = 1  # 模拟用户ID
        if user_id not in user_purchases:
            user_purchases[user_id] = 0
        user_purchases[user_id] += sale['amount']
    
    print(f"活跃购买用户: {len(user_purchases)} 人")

print("✅ 多步骤分析完成")
            """,
            "result_key": "correlation_analysis"
        }
    ]
    
    result = engine.execute_workflow(workflow_steps)
    
    if result['success']:
        print("✅ 多步骤工作流测试通过")
        return True
    else:
        print("❌ 多步骤工作流测试失败")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n⚠️  测试错误处理")
    print("=" * 40)
    
    engine = WorkflowEngine()
    
    workflow_steps = [
        {
            "tool": "file_reader",
            "description": "读取不存在的文件",
            "file_path": "/nonexistent/file.json",
            "data_key": "nonexistent_data"
        },
        {
            "tool": "workflow_code_interpreter",
            "description": "处理错误情况",
            "code": """
# 检查数据是否存在
data = context_data.get('nonexistent_data')
if data is None:
    print("⚠️  数据不存在，使用默认处理")
    default_data = {"message": "使用默认数据"}
    print(f"默认数据: {default_data}")
else:
    print("✅ 数据存在，正常处理")
            """,
            "result_key": "error_handling_result"
        }
    ]
    
    result = engine.execute_workflow(workflow_steps)
    
    # 即使某个步骤失败，工作流应该能继续执行
    if len(result['results']) == 2:  # 两个步骤都执行了
        print("✅ 错误处理测试通过")
        return True
    else:
        print("❌ 错误处理测试失败")
        return False


def test_context_data_passing():
    """测试上下文数据传递"""
    print("\n📊 测试上下文数据传递")
    print("=" * 40)
    
    engine = WorkflowEngine()
    
    workflow_steps = [
        {
            "tool": "workflow_code_interpreter",
            "description": "生成初始数据",
            "code": """
# 生成一些测试数据
import random

data = {
    'numbers': [random.randint(1, 100) for _ in range(10)],
    'timestamp': '2024-01-01 12:00:00',
    'source': 'test_generator'
}

# 将数据保存到上下文
context_data['generated_data'] = data
print(f"生成数据: {len(data['numbers'])} 个数字")
            """,
            "result_key": "data_generation"
        },
        {
            "tool": "workflow_code_interpreter",
            "description": "处理生成的数据",
            "code": """
# 获取之前生成的数据
generated = context_data.get('generated_data', {})
numbers = generated.get('numbers', [])

if numbers:
    # 统计分析
    total = sum(numbers)
    average = total / len(numbers)
    maximum = max(numbers)
    minimum = min(numbers)
    
    print("=== 数据分析结果 ===")
    print(f"数量: {len(numbers)}")
    print(f"总和: {total}")
    print(f"平均值: {average:.2f}")
    print(f"最大值: {maximum}")
    print(f"最小值: {minimum}")
    
    # 保存分析结果
    analysis_result = {
        'count': len(numbers),
        'sum': total,
        'average': average,
        'max': maximum,
        'min': minimum
    }
    context_data['analysis_result'] = analysis_result
else:
    print("❌ 没有找到生成的数据")
            """,
            "result_key": "data_analysis"
        },
        {
            "tool": "workflow_code_interpreter", 
            "description": "生成最终报告",
            "code": """
# 生成最终报告
generated = context_data.get('generated_data', {})
analysis = context_data.get('analysis_result', {})

print("=== 最终报告 ===")
print(f"数据源: {generated.get('source', 'Unknown')}")
print(f"生成时间: {generated.get('timestamp', 'Unknown')}")
print(f"数据分析:")

if analysis:
    for key, value in analysis.items():
        print(f"  {key}: {value}")
    
    print("✅ 报告生成完成")
else:
    print("❌ 缺少分析数据")
            """,
            "result_key": "final_report"
        }
    ]
    
    result = engine.execute_workflow(workflow_steps)
    
    if result['success']:
        print("✅ 上下文数据传递测试通过")
        return True
    else:
        print("❌ 上下文数据传递测试失败")
        return False


def main():
    """运行所有测试"""
    print("🧪 工作流代码解释器测试套件")
    print("=" * 60)
    
    tests = [
        ("基本工作流", test_basic_workflow),
        ("多步骤工作流", test_multi_step_workflow), 
        ("错误处理", test_error_handling),
        ("上下文数据传递", test_context_data_passing),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请检查相关功能")


if __name__ == "__main__":
    main()
