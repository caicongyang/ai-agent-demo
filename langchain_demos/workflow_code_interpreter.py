#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流代码解释器
支持多工具协作的代码执行环境

场景：
1. 先调用 API 获取数据
2. 将数据传递给代码解释器进行分析
3. 支持复杂的数据处理工作流
4. 可以链式调用多个工具
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, List

import requests
from langchain.tools.base import BaseTool
from langchain_experimental.tools import PythonAstREPLTool

# 尝试导入我们的沙箱解释器
try:
    from sandboxed_code_interpreter import SandboxedCodeInterpreter, SandboxConfig
    SANDBOX_AVAILABLE = True
except ImportError:
    SANDBOX_AVAILABLE = False


@dataclass
class WorkflowContext:
    """工作流上下文，用于在工具间传递数据"""
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    history: List[Dict[str, Any]]
    
    def add_data(self, key: str, value: Any, source: str = "unknown"):
        """添加数据到上下文"""
        self.data[key] = value
        self.metadata[key] = {
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "type": type(value).__name__
        }
        
        # 记录历史
        self.history.append({
            "action": "add_data",
            "key": key,
            "source": source,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_data(self, key: str) -> Any:
        """从上下文获取数据"""
        return self.data.get(key)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class WorkflowTool(ABC):
    """工作流工具基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """执行工具逻辑"""
        pass


class APIDataTool(WorkflowTool):
    """API 数据获取工具"""
    
    def __init__(self):
        super().__init__(
            name="api_data_fetcher",
            description="从 API 获取数据"
        )
    
    def execute(self, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """获取 API 数据"""
        url = kwargs.get('url')
        method = kwargs.get('method', 'GET')
        headers = kwargs.get('headers', {})
        params = kwargs.get('params', {})
        data_key = kwargs.get('data_key', 'api_data')
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=params, timeout=10)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")
            
            response.raise_for_status()
            api_data = response.json()
            
            # 将数据添加到上下文
            context.add_data(data_key, api_data, source=f"API:{url}")
            
            return {
                "success": True,
                "data": api_data,
                "status_code": response.status_code,
                "message": f"成功从 {url} 获取数据"
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API 请求失败: {str(e)}"
            return {
                "success": False,
                "error": error_msg,
                "message": error_msg
            }
        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析失败: {str(e)}"
            return {
                "success": False,
                "error": error_msg,
                "message": error_msg
            }


class DatabaseTool(WorkflowTool):
    """数据库查询工具（模拟）"""
    
    def __init__(self):
        super().__init__(
            name="database_query",
            description="从数据库查询数据"
        )
    
    def execute(self, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """模拟数据库查询"""
        query = kwargs.get('query', '')
        data_key = kwargs.get('data_key', 'db_data')
        
        # 模拟数据库数据
        mock_data = {
            "users": [
                {"id": 1, "name": "张三", "age": 25, "city": "北京"},
                {"id": 2, "name": "李四", "age": 30, "city": "上海"},
                {"id": 3, "name": "王五", "age": 28, "city": "广州"},
            ],
            "sales": [
                {"date": "2024-01-01", "amount": 1000, "product": "产品A"},
                {"date": "2024-01-02", "amount": 1500, "product": "产品B"},
                {"date": "2024-01-03", "amount": 800, "product": "产品C"},
            ],
            "orders": [
                {"id": 101, "user_id": 1, "total": 299.99, "status": "completed"},
                {"id": 102, "user_id": 2, "total": 199.50, "status": "pending"},
                {"id": 103, "user_id": 3, "total": 599.00, "status": "completed"},
            ]
        }
        
        try:
            # 简单的查询解析
            if "users" in query.lower():
                result_data = mock_data["users"]
            elif "sales" in query.lower():
                result_data = mock_data["sales"]
            elif "orders" in query.lower():
                result_data = mock_data["orders"]
            else:
                result_data = {"message": "未找到匹配的数据"}
            
            context.add_data(data_key, result_data, source=f"Database:{query}")
            
            return {
                "success": True,
                "data": result_data,
                "query": query,
                "message": f"成功执行查询: {query}"
            }
            
        except Exception as e:
            error_msg = f"数据库查询失败: {str(e)}"
            return {
                "success": False,
                "error": error_msg,
                "message": error_msg
            }


class FileDataTool(WorkflowTool):
    """文件数据读取工具"""
    
    def __init__(self):
        super().__init__(
            name="file_reader",
            description="从文件读取数据"
        )
    
    def execute(self, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """读取文件数据"""
        file_path = kwargs.get('file_path', '')
        data_key = kwargs.get('data_key', 'file_data')
        file_type = kwargs.get('file_type', 'auto')
        
        try:
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"文件不存在: {file_path}",
                    "message": f"文件不存在: {file_path}"
                }
            
            # 根据文件类型读取
            if file_type == 'auto':
                if file_path.endswith('.json'):
                    file_type = 'json'
                elif file_path.endswith('.csv'):
                    file_type = 'csv'
                else:
                    file_type = 'text'
            
            if file_type == 'json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            elif file_type == 'csv':
                import pandas as pd
                data = pd.read_csv(file_path).to_dict('records')
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = f.read()
            
            context.add_data(data_key, data, source=f"File:{file_path}")
            
            return {
                "success": True,
                "data": data,
                "file_path": file_path,
                "file_type": file_type,
                "message": f"成功读取文件: {file_path}"
            }
            
        except Exception as e:
            error_msg = f"文件读取失败: {str(e)}"
            return {
                "success": False,
                "error": error_msg,
                "message": error_msg
            }


class WorkflowCodeInterpreter(WorkflowTool):
    """工作流代码解释器"""
    
    def __init__(self, use_sandbox: bool = True):
        super().__init__(
            name="workflow_code_interpreter",
            description="在工作流中执行代码，可以访问上下文数据"
        )
        
        self.use_sandbox = use_sandbox and SANDBOX_AVAILABLE
        
        if self.use_sandbox:
            config = SandboxConfig(
                use_docker=False,  # 为了演示方便
                use_restricted_python=True,
                allowed_modules=["math", "json", "statistics", "datetime", "pandas", "numpy"]
            )
            self.interpreter = SandboxedCodeInterpreter(config)
        else:
            self.interpreter = PythonAstREPLTool()
    
    def execute(self, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """执行代码，可以访问上下文数据"""
        code = kwargs.get('code', '')
        result_key = kwargs.get('result_key', 'code_result')
        
        if not code:
            return {
                "success": False,
                "error": "未提供代码",
                "message": "未提供代码"
            }
        
        try:
            # 准备上下文数据，将其注入到代码环境中
            context_data = context.data
            
            # 构建包含上下文数据的代码
            setup_code = "# 工作流上下文数据\n"
            setup_code += f"context_data = {json.dumps(context_data, ensure_ascii=False, default=str)}\n"
            setup_code += "import json\n"
            setup_code += "# 将 JSON 字符串转换回 Python 对象\n"
            setup_code += "for key, value in context_data.items():\n"
            setup_code += "    if isinstance(value, str):\n"
            setup_code += "        try:\n"
            setup_code += "            context_data[key] = json.loads(value)\n"
            setup_code += "        except:\n"
            setup_code += "            pass\n"
            setup_code += "\n# 用户代码:\n"
            
            full_code = setup_code + code
            
            if self.use_sandbox:
                result = self.interpreter.execute_code(full_code)
                success = result.get('success', False)
                output = result.get('output', '')
                error = result.get('error', '')
            else:
                try:
                    output = self.interpreter.run(full_code)
                    success = True
                    error = None
                except Exception as e:
                    output = ""
                    success = False
                    error = str(e)
            
            if success:
                # 将结果添加到上下文
                context.add_data(result_key, output, source="CodeInterpreter")
                
                return {
                    "success": True,
                    "output": output,
                    "message": "代码执行成功"
                }
            else:
                return {
                    "success": False,
                    "error": error,
                    "output": output,
                    "message": f"代码执行失败: {error}"
                }
                
        except Exception as e:
            error_msg = f"代码执行异常: {str(e)}"
            return {
                "success": False,
                "error": error_msg,
                "message": error_msg
            }


class WorkflowEngine:
    """工作流执行引擎"""
    
    def __init__(self):
        self.tools = {}
        self.context = WorkflowContext(data={}, metadata={}, history=[])
        
        # 注册默认工具
        self.register_tool(APIDataTool())
        self.register_tool(DatabaseTool())
        self.register_tool(FileDataTool())
        self.register_tool(WorkflowCodeInterpreter())
    
    def register_tool(self, tool: WorkflowTool):
        """注册工具"""
        self.tools[tool.name] = tool
        print(f"✅ 注册工具: {tool.name}")
    
    def execute_step(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行单个工作流步骤"""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"工具不存在: {tool_name}",
                "message": f"工具不存在: {tool_name}"
            }
        
        tool = self.tools[tool_name]
        print(f"🔧 执行工具: {tool_name}")
        
        try:
            result = tool.execute(self.context, **kwargs)
            
            # 记录执行历史
            self.context.history.append({
                "tool": tool_name,
                "kwargs": kwargs,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            print(f"{'✅' if result.get('success') else '❌'} {result.get('message', '')}")
            return result
            
        except Exception as e:
            error_msg = f"工具执行异常: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "message": error_msg
            }
    
    def execute_workflow(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行完整工作流"""
        print("🚀 开始执行工作流")
        print("=" * 50)
        
        results = []
        
        for i, step in enumerate(steps, 1):
            print(f"\n📝 步骤 {i}: {step.get('description', step.get('tool', 'Unknown'))}")
            
            tool_name = step.get('tool')
            if not tool_name:
                error_msg = f"步骤 {i} 缺少工具名称"
                print(f"❌ {error_msg}")
                results.append({
                    "step": i,
                    "success": False,
                    "error": error_msg
                })
                continue
            
            # 提取参数
            kwargs = {k: v for k, v in step.items() if k not in ['tool', 'description']}
            
            # 执行步骤
            result = self.execute_step(tool_name, **kwargs)
            results.append({
                "step": i,
                "tool": tool_name,
                **result
            })
            
            # 如果步骤失败且需要停止
            if not result.get('success') and step.get('stop_on_error', False):
                print(f"❌ 步骤 {i} 失败，停止工作流执行")
                break
        
        print("\n🏁 工作流执行完成")
        return {
            "success": all(r.get('success', False) for r in results),
            "results": results,
            "context": self.context.to_dict()
        }
    
    def get_context_summary(self) -> str:
        """获取上下文摘要"""
        summary = "📊 工作流上下文摘要:\n"
        summary += f"   数据项数量: {len(self.context.data)}\n"
        summary += f"   执行步骤数量: {len(self.context.history)}\n"
        summary += "   数据项:\n"
        
        for key, value in self.context.data.items():
            metadata = self.context.metadata.get(key, {})
            summary += f"     - {key}: {type(value).__name__} (来源: {metadata.get('source', 'Unknown')})\n"
        
        return summary
    
    def clear_context(self):
        """清除上下文"""
        self.context = WorkflowContext(data={}, metadata={}, history=[])
        print("🗑️ 上下文已清除")


# LangChain 工具包装器
class WorkflowCodeInterpreterTool(BaseTool):
    """LangChain 工具包装器"""
    
    name: str = "workflow_code_interpreter"
    description: str = "执行工作流代码解释器，可以先获取数据再进行分析"
    
    def __init__(self):
        super().__init__()
        self.engine = WorkflowEngine()
    
    def _run(self, workflow_steps: str) -> str:
        """执行工作流"""
        try:
            # 解析工作流步骤（假设是 JSON 格式）
            steps = json.loads(workflow_steps)
            result = self.engine.execute_workflow(steps)
            
            if result['success']:
                return f"工作流执行成功\n{self.engine.get_context_summary()}"
            else:
                return f"工作流执行失败: {result}"
                
        except json.JSONDecodeError:
            return "工作流步骤格式错误，请提供有效的 JSON 格式"
        except Exception as e:
            return f"工作流执行异常: {str(e)}"
    
    async def _arun(self, workflow_steps: str) -> str:
        """异步执行"""
        return self._run(workflow_steps)


def demo_api_to_code():
    """演示：API 数据 -> 代码分析"""
    print("🌐 演示：API 数据获取 + 代码分析")
    print("=" * 50)
    
    engine = WorkflowEngine()
    
    # 定义工作流步骤
    workflow_steps = [
        {
            "tool": "api_data_fetcher",
            "description": "获取随机用户数据",
            "url": "https://jsonplaceholder.typicode.com/users",
            "method": "GET",
            "data_key": "users_data"
        },
        {
            "tool": "workflow_code_interpreter",
            "description": "分析用户数据",
            "code": """
# 分析用户数据
users = context_data.get('users_data', [])
print(f"获取到 {len(users)} 个用户数据")

# 统计分析
if users:
    # 提取城市信息
    cities = [user.get('address', {}).get('city', 'Unknown') for user in users]
    city_count = {}
    for city in cities:
        city_count[city] = city_count.get(city, 0) + 1
    
    print("\\n城市分布:")
    for city, count in city_count.items():
        print(f"  {city}: {count} 人")
    
    # 分析用户名长度
    name_lengths = [len(user.get('name', '')) for user in users]
    avg_name_length = sum(name_lengths) / len(name_lengths)
    print(f"\\n平均用户名长度: {avg_name_length:.2f}")
    
    # 找出最长的用户名
    longest_name_user = max(users, key=lambda u: len(u.get('name', '')))
    print(f"最长用户名: {longest_name_user.get('name', 'N/A')}")
else:
    print("没有用户数据可分析")
            """,
            "result_key": "analysis_result"
        }
    ]
    
    # 执行工作流
    result = engine.execute_workflow(workflow_steps)
    
    print("\n" + engine.get_context_summary())
    return result


def demo_database_to_code():
    """演示：数据库查询 -> 代码分析"""
    print("\n💾 演示：数据库查询 + 代码分析")
    print("=" * 50)
    
    engine = WorkflowEngine()
    
    workflow_steps = [
        {
            "tool": "database_query",
            "description": "查询销售数据",
            "query": "SELECT * FROM sales",
            "data_key": "sales_data"
        },
        {
            "tool": "database_query",
            "description": "查询用户数据",
            "query": "SELECT * FROM users",
            "data_key": "users_data"
        },
        {
            "tool": "workflow_code_interpreter",
            "description": "综合分析销售和用户数据",
            "code": """
# 综合数据分析
sales_data = context_data.get('sales_data', [])
users_data = context_data.get('users_data', [])

print("=== 数据概览 ===")
print(f"销售记录数: {len(sales_data)}")
print(f"用户记录数: {len(users_data)}")

if sales_data:
    print("\\n=== 销售分析 ===")
    total_sales = sum(item['amount'] for item in sales_data)
    avg_sales = total_sales / len(sales_data)
    print(f"总销售额: {total_sales}")
    print(f"平均销售额: {avg_sales:.2f}")
    
    # 产品销售分析
    product_sales = {}
    for item in sales_data:
        product = item['product']
        amount = item['amount']
        product_sales[product] = product_sales.get(product, 0) + amount
    
    print("\\n产品销售排名:")
    for product, amount in sorted(product_sales.items(), key=lambda x: x[1], reverse=True):
        print(f"  {product}: {amount}")

if users_data:
    print("\\n=== 用户分析 ===")
    # 年龄分析
    ages = [user['age'] for user in users_data]
    avg_age = sum(ages) / len(ages)
    print(f"用户平均年龄: {avg_age:.1f}")
    
    # 城市分布
    city_count = {}
    for user in users_data:
        city = user['city']
        city_count[city] = city_count.get(city, 0) + 1
    
    print("\\n用户城市分布:")
    for city, count in city_count.items():
        print(f"  {city}: {count} 人")
            """,
            "result_key": "comprehensive_analysis"
        }
    ]
    
    result = engine.execute_workflow(workflow_steps)
    print("\n" + engine.get_context_summary())
    return result


def demo_multi_source_analysis():
    """演示：多数据源综合分析"""
    print("\n🔄 演示：多数据源综合分析")
    print("=" * 50)
    
    engine = WorkflowEngine()
    
    # 创建临时 JSON 文件用于演示
    temp_data = {
        "products": [
            {"id": 1, "name": "产品A", "price": 299.99, "category": "电子"},
            {"id": 2, "name": "产品B", "price": 199.50, "category": "服装"},
            {"id": 3, "name": "产品C", "price": 599.00, "category": "电子"}
        ]
    }
    
    temp_file = "/tmp/products.json"
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(temp_data, f, ensure_ascii=False)
    
    workflow_steps = [
        {
            "tool": "file_reader",
            "description": "读取产品数据文件",
            "file_path": temp_file,
            "data_key": "products_data"
        },
        {
            "tool": "database_query",
            "description": "查询订单数据",
            "query": "SELECT * FROM orders",
            "data_key": "orders_data"
        },
        {
            "tool": "workflow_code_interpreter",
            "description": "产品和订单关联分析",
            "code": """
# 多数据源关联分析
products = context_data.get('products_data', {}).get('products', [])
orders = context_data.get('orders_data', [])

print("=== 多数据源分析报告 ===")
print(f"产品数量: {len(products)}")
print(f"订单数量: {len(orders)}")

if products:
    print("\\n=== 产品信息 ===")
    total_product_value = sum(p['price'] for p in products)
    print(f"产品总价值: {total_product_value:.2f}")
    
    # 按类别分组
    categories = {}
    for product in products:
        cat = product['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(product)
    
    print("\\n产品类别分布:")
    for cat, prods in categories.items():
        avg_price = sum(p['price'] for p in prods) / len(prods)
        print(f"  {cat}: {len(prods)} 个产品, 平均价格: {avg_price:.2f}")

if orders:
    print("\\n=== 订单分析 ===")
    total_revenue = sum(order['total'] for order in orders)
    completed_orders = [o for o in orders if o['status'] == 'completed']
    completion_rate = len(completed_orders) / len(orders) * 100
    
    print(f"总收入: {total_revenue:.2f}")
    print(f"订单完成率: {completion_rate:.1f}%")
    
    # 用户订单分析
    user_orders = {}
    for order in orders:
        user_id = order['user_id']
        if user_id not in user_orders:
            user_orders[user_id] = []
        user_orders[user_id].append(order)
    
    print(f"\\n活跃用户数: {len(user_orders)}")
    avg_orders_per_user = len(orders) / len(user_orders)
    print(f"每用户平均订单数: {avg_orders_per_user:.1f}")

# 综合洞察
print("\\n=== 业务洞察 ===")
if products and orders:
    avg_product_price = sum(p['price'] for p in products) / len(products)
    avg_order_value = sum(o['total'] for o in orders) / len(orders)
    print(f"平均产品价格: {avg_product_price:.2f}")
    print(f"平均订单价值: {avg_order_value:.2f}")
    
    if avg_order_value < avg_product_price:
        print("💡 洞察: 订单价值低于产品平均价格，可能存在折扣或多产品订单较少")
    else:
        print("💡 洞察: 订单价值高于产品平均价格，客户倾向于购买多个产品")
            """,
            "result_key": "business_insights"
        }
    ]
    
    result = engine.execute_workflow(workflow_steps)
    print("\n" + engine.get_context_summary())
    
    # 清理临时文件
    try:
        os.unlink(temp_file)
    except:
        pass
    
    return result


def demo_interactive_workflow():
    """交互式工作流演示"""
    print("\n🎮 交互式工作流模式")
    print("=" * 50)
    
    engine = WorkflowEngine()
    
    print("💡 可用工具:")
    for name, tool in engine.tools.items():
        print(f"   - {name}: {tool.description}")
    
    print("\n📖 命令格式:")
    print("   tool_name key1=value1 key2=value2")
    print("   例如: api_data_fetcher url=https://api.example.com data_key=my_data")
    print("   输入 'summary' 查看上下文摘要")
    print("   输入 'quit' 退出")
    
    while True:
        try:
            user_input = input("\n🔧 workflow>>> ").strip()
            
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'summary':
                print(engine.get_context_summary())
                continue
            elif user_input.lower() == 'clear':
                engine.clear_context()
                continue
            elif user_input == '':
                continue
            
            # 解析命令
            parts = user_input.split()
            if not parts:
                continue
            
            tool_name = parts[0]
            kwargs = {}
            
            for part in parts[1:]:
                if '=' in part:
                    key, value = part.split('=', 1)
                    # 尝试解析 JSON 值
                    try:
                        kwargs[key] = json.loads(value)
                    except:
                        kwargs[key] = value
            
            # 执行工具
            result = engine.execute_step(tool_name, **kwargs)
            
            if result.get('success'):
                print(f"✅ 执行成功: {result.get('message', '')}")
                if 'output' in result:
                    print(f"输出: {result['output']}")
            else:
                print(f"❌ 执行失败: {result.get('error', '')}")
            
        except KeyboardInterrupt:
            print("\n👋 再见!")
            break
        except EOFError:
            print("\n👋 再见!")
            break
        except Exception as e:
            print(f"❌ 命令解析错误: {e}")


def main():
    """主函数"""
    print("🔄 工作流代码解释器演示")
    print("=" * 60)
    
    while True:
        print("\n请选择演示模式:")
        print("1. API 数据获取 + 代码分析")
        print("2. 数据库查询 + 代码分析") 
        print("3. 多数据源综合分析")
        print("4. 交互式工作流模式")
        print("0. 退出")
        
        choice = input("\n请输入选择 (0-4): ").strip()
        
        if choice == "1":
            demo_api_to_code()
        elif choice == "2":
            demo_database_to_code()
        elif choice == "3":
            demo_multi_source_analysis()
        elif choice == "4":
            demo_interactive_workflow()
        elif choice == "0":
            print("👋 再见!")
            break
        else:
            print("❌ 无效选择，请重新输入")


if __name__ == "__main__":
    main()
