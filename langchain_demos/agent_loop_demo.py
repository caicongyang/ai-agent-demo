from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticToolsParser
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os
import time

# 加载环境变量
load_dotenv()

# 定义工具模式
class SearchWeb(BaseModel):
    """搜索互联网信息的工具"""
    query: str = Field(..., description="搜索关键词")

class CalculateMath(BaseModel):
    """执行数学计算的工具"""
    expression: str = Field(..., description="数学表达式")

class WriteFile(BaseModel):
    """写入文件的工具"""
    filename: str = Field(..., description="文件名")
    content: str = Field(..., description="文件内容")

class ReadFile(BaseModel):
    """读取文件的工具"""
    filename: str = Field(..., description="文件名")

class SendEmail(BaseModel):
    """发送邮件的工具"""
    to: str = Field(..., description="收件人")
    subject: str = Field(..., description="邮件主题")
    body: str = Field(..., description="邮件内容")

class ProcessListItem(BaseModel):
    """处理列表中的单个项目"""
    item_id: str = Field(..., description="项目ID")
    action: str = Field(..., description="对该项目执行的操作")
    data: str = Field(..., description="项目数据")

class GetApiData(BaseModel):
    """获取API数据的工具"""
    endpoint: str = Field(..., description="API端点")
    filters: str = Field(default="", description="查询过滤条件")

def search_web(query: str) -> str:
    """模拟搜索网络"""
    return f"搜索结果：关于'{query}'的相关信息已找到"

def calculate_math(expression: str) -> str:
    """执行数学计算"""
    try:
        result = eval(expression)
        return f"计算结果：{expression} = {result}"
    except Exception as e:
        return f"计算错误：{str(e)}"

def write_file(filename: str, content: str) -> str:
    """模拟写入文件"""
    return f"文件 {filename} 已写入内容：{content[:50]}..."

def read_file(filename: str) -> str:
    """模拟读取文件"""
    return f"文件 {filename} 的内容已读取"

def send_email(to: str, subject: str, body: str) -> str:
    """模拟发送邮件"""
    return f"邮件已发送至 {to}，主题：{subject}"

def process_list_item(item_id: str, action: str, data: str) -> str:
    """处理列表中的单个项目"""
    return f"处理项目 {item_id}: 执行操作 '{action}' 对数据 '{data}'"

def get_api_data(endpoint: str, filters: str = "") -> List[Dict[str, Any]]:
    """模拟获取API数据，返回10个项目的列表"""
    base_data = [
        {"id": f"item_{i+1}", "name": f"产品{i+1}", "price": 100 + i*10, "category": "电子产品" if i % 2 == 0 else "服装"}
        for i in range(10)
    ]
    return base_data

class AgentLoopDemo:
    """
    Agent循环演示类

    该类演示了如何使用单次LLM调用生成多个工具调用，
    然后在for循环中执行这些工具调用
    """

    def __init__(self):
        """初始化Agent演示"""
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )

        # 定义可用的工具
        self.tools = [SearchWeb, CalculateMath, WriteFile, ReadFile, SendEmail, ProcessListItem, GetApiData]
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # 工具执行映射
        self.tool_executors = {
            'SearchWeb': search_web,
            'CalculateMath': calculate_math,
            'WriteFile': write_file,
            'ReadFile': read_file,
            'SendEmail': send_email,
            'ProcessListItem': process_list_item,
            'GetApiData': get_api_data
        }

    def create_agent_prompt(self) -> ChatPromptTemplate:
        """创建Agent提示模板"""
        return ChatPromptTemplate.from_messages([
            ("system", """你是一个智能助手，能够使用多种工具来完成复杂任务。

可用工具：
1. SearchWeb - 搜索互联网信息
2. CalculateMath - 执行数学计算
3. WriteFile - 写入文件
4. ReadFile - 读取文件
5. SendEmail - 发送邮件
6. ProcessListItem - 处理列表中的单个项目
7. GetApiData - 获取API数据

根据用户的请求，请规划并生成所需的工具调用序列。
你可以同时调用多个工具来完成复合任务。

**重要：当需要批量处理数据时，请为每个数据项生成单独的工具调用。**
例如：如果有10个项目需要处理，请生成10个ProcessListItem工具调用，每个调用处理一个项目。

请根据任务需要，生成相应的工具调用。"""),
            ("human", "{input}")
        ])

    def generate_tool_calls(self, query: str) -> List[BaseModel]:
        """
        生成工具调用列表

        Args:
            query: 用户查询

        Returns:
            工具调用对象列表
        """
        prompt = self.create_agent_prompt()
        chain = prompt | self.llm_with_tools | PydanticToolsParser(tools=self.tools)

        print(f"🤖 处理查询: {query}")
        print("🧠 正在分析任务并生成工具调用...")

        tool_calls = chain.invoke({"input": query})

        print(f"📋 生成了 {len(tool_calls)} 个工具调用")
        return tool_calls

    def execute_tool_calls(self, tool_calls: List[BaseModel]) -> List[str]:
        """
        在for循环中执行工具调用

        Args:
            tool_calls: 工具调用对象列表

        Returns:
            执行结果列表
        """
        results = []

        print("\n🔄 开始执行工具调用...")

        for i, tool_call in enumerate(tool_calls, 1):
            tool_name = tool_call.__class__.__name__
            print(f"\n📍 步骤 {i}: 执行 {tool_name}")
            print(f"   参数: {tool_call.model_dump()}")

            # 模拟执行时间
            time.sleep(0.5)

            # 执行工具
            if tool_name in self.tool_executors:
                if tool_name == 'SearchWeb':
                    result = self.tool_executors[tool_name](tool_call.query)
                elif tool_name == 'CalculateMath':
                    result = self.tool_executors[tool_name](tool_call.expression)
                elif tool_name == 'WriteFile':
                    result = self.tool_executors[tool_name](tool_call.filename, tool_call.content)
                elif tool_name == 'ReadFile':
                    result = self.tool_executors[tool_name](tool_call.filename)
                elif tool_name == 'SendEmail':
                    result = self.tool_executors[tool_name](tool_call.to, tool_call.subject, tool_call.body)
                elif tool_name == 'ProcessListItem':
                    result = self.tool_executors[tool_name](tool_call.item_id, tool_call.action, tool_call.data)
                elif tool_name == 'GetApiData':
                    result = self.tool_executors[tool_name](tool_call.endpoint, tool_call.filters)
                else:
                    result = f"未知工具: {tool_name}"
            else:
                result = f"工具 {tool_name} 未找到执行器"

            print(f"   结果: {result}")
            results.append(result)

        return results

    def run_agent_loop(self, query: str) -> Dict[str, Any]:
        """
        运行完整的Agent循环

        Args:
            query: 用户查询

        Returns:
            包含工具调用和执行结果的字典
        """
        start_time = time.time()

        # 单次LLM调用生成所有工具调用
        tool_calls = self.generate_tool_calls(query)

        # for循环执行工具调用
        results = self.execute_tool_calls(tool_calls)

        end_time = time.time()

        return {
            "query": query,
            "tool_calls": [
                {
                    "tool": tool_call.__class__.__name__,
                    "params": tool_call.model_dump()
                }
                for tool_call in tool_calls
            ],
            "results": results,
            "execution_time": end_time - start_time,
            "total_tools": len(tool_calls)
        }

    def run_batch_processing_demo(self, query: str) -> Dict[str, Any]:
        """
        演示批量处理功能，LLM自动生成多个工具调用

        Args:
            query: 用户查询

        Returns:
            包含批量处理结果的字典
        """
        print(f"\n🔥 批量处理演示: {query}")
        print("=" * 60)

        # 首先获取API数据（模拟获取10个项目）
        api_data = get_api_data("/api/products", "category=electronics")
        print(f"📊 获取到 {len(api_data)} 个数据项:")
        for item in api_data[:3]:  # 只显示前3个
            print(f"   - {item}")
        print("   ...")

        # 构建包含数据的查询
        enhanced_query = f"{query}\n\n数据列表: {api_data}"

        # 让LLM生成批量工具调用
        start_time = time.time()
        tool_calls = self.generate_tool_calls(enhanced_query)
        results = self.execute_tool_calls(tool_calls)
        end_time = time.time()

        return {
            "original_query": query,
            "data_items": len(api_data),
            "generated_tool_calls": len(tool_calls),
            "results": results,
            "execution_time": end_time - start_time
        }

def main():
    """主函数，演示Agent循环功能"""
    demo = AgentLoopDemo()

    # 测试场景
    test_scenarios = [
        "帮我搜索Python编程教程，然后计算25*4的结果，最后写入到results.txt文件中",
        "计算圆周率乘以10的结果，搜索关于AI的最新新闻，然后发送邮件给admin@example.com总结今天的工作",
        "读取config.txt文件，计算100除以5的结果，搜索机器学习相关资料",
        "写入一个包含'Hello World'的test.txt文件，然后计算2的10次方"
    ]

    # 批量处理测试场景
    batch_scenarios = [
        "为每个产品项目执行价格计算和分类处理",
        "对每个产品项目进行数据清洗和验证操作",
        "为每个产品生成摘要报告并保存到文件"
    ]

    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*60}")
        print(f"测试场景 {i}")
        print(f"{'='*60}")

        result = demo.run_agent_loop(scenario)

        print(f"\n📊 执行总结:")
        print(f"   - 查询: {result['query']}")
        print(f"   - 工具调用数量: {result['total_tools']}")
        print(f"   - 执行时间: {result['execution_time']:.2f}秒")
        print(f"   - 所有结果:")
        for j, res in enumerate(result['results'], 1):
            print(f"     {j}. {res}")

        print(f"\n⏱️  等待下一个测试...")
        time.sleep(2)

    # 演示批量处理功能
    print(f"\n{'='*80}")
    print("🔥 批量处理演示 - LLM自动生成多个工具调用")
    print(f"{'='*80}")

    for i, batch_scenario in enumerate(batch_scenarios, 1):
        print(f"\n{'='*60}")
        print(f"批量处理场景 {i}")
        print(f"{'='*60}")

        result = demo.run_batch_processing_demo(batch_scenario)

        print(f"\n📊 批量处理总结:")
        print(f"   - 原始查询: {result['original_query']}")
        print(f"   - 数据项数量: {result['data_items']}")
        print(f"   - 生成工具调用数量: {result['generated_tool_calls']}")
        print(f"   - 执行时间: {result['execution_time']:.2f}秒")
        print(f"   - 处理结果:")
        for j, res in enumerate(result['results'], 1):
            print(f"     {j}. {res}")

        if i < len(batch_scenarios):
            print(f"\n⏱️  等待下一个批量处理测试...")
            time.sleep(3)

if __name__ == "__main__":
    main()