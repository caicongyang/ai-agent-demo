from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticToolsParser
from langchain_core.tools import tool
from dotenv import load_dotenv
import os
import json
from datetime import datetime

# 加载环境变量
load_dotenv()

# 定义复杂的工具模式，带有详细参数说明
class DatabaseQuery(BaseModel):
    """
    数据库查询工具 - 执行复杂的数据库查询操作
    
    这个工具可以执行各种数据库操作，包括查询、过滤、排序等。
    支持多种数据库类型和复杂的查询条件。
    """
    table_name: str = Field(
        ..., 
        description="要查询的表名，例如：'users', 'orders', 'products'",
        examples=["users", "orders", "products"]
    )
    columns: List[str] = Field(
        default=["*"], 
        description="要查询的列名列表，默认为所有列。例如：['name', 'email', 'age']",
        examples=[["name", "email"], ["*"], ["id", "created_at"]]
    )
    where_conditions: Optional[Dict[str, Any]] = Field(
        default=None,
        description="WHERE条件字典，键为列名，值为条件值。例如：{'age': '>25', 'status': 'active'}",
        examples=[{"age": ">25"}, {"status": "active", "created_at": ">2023-01-01"}]
    )
    order_by: Optional[str] = Field(
        default=None,
        description="排序字段，可以包含ASC或DESC。例如：'created_at DESC', 'name ASC'",
        examples=["created_at DESC", "name ASC", "age DESC"]
    )
    limit: Optional[int] = Field(
        default=None,
        description="限制返回的记录数量，必须为正整数",
        ge=1,
        le=1000,
        examples=[10, 50, 100]
    )
    database_type: Literal["mysql", "postgresql", "sqlite", "mongodb"] = Field(
        default="mysql",
        description="数据库类型，支持mysql、postgresql、sqlite、mongodb"
    )

class FileProcessor(BaseModel):
    """
    文件处理工具 - 处理各种文件操作
    
    支持文件的读取、写入、转换等操作。
    可以处理多种文件格式，包括文本、JSON、CSV等。
    """
    file_path: str = Field(
        ...,
        description="文件路径，支持相对路径和绝对路径。例如：'./data/file.txt', '/home/user/document.json'",
        examples=["./data/users.csv", "/tmp/output.json", "documents/report.txt"]
    )
    operation: Literal["read", "write", "append", "delete", "convert"] = Field(
        ...,
        description="要执行的文件操作类型"
    )
    content: Optional[str] = Field(
        default=None,
        description="文件内容（当操作为write或append时需要）",
        examples=["Hello World", '{"name": "John", "age": 30}', "Name,Age,City\nJohn,30,NYC"]
    )
    encoding: str = Field(
        default="utf-8",
        description="文件编码格式",
        examples=["utf-8", "gbk", "ascii"]
    )
    convert_to: Optional[str] = Field(
        default=None,
        description="转换目标格式（当操作为convert时需要）。例如：'json', 'csv', 'xml'",
        examples=["json", "csv", "xml", "yaml"]
    )

class APIRequest(BaseModel):
    """
    API请求工具 - 发送HTTP请求到外部API
    
    支持GET、POST、PUT、DELETE等HTTP方法。
    可以设置请求头、参数、认证信息等。
    """
    url: str = Field(
        ...,
        description="API端点URL，必须是完整的HTTP/HTTPS地址",
        examples=["https://api.github.com/users", "https://jsonplaceholder.typicode.com/posts"]
    )
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(
        default="GET",
        description="HTTP请求方法"
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="请求头字典，键值对形式。例如：{'Content-Type': 'application/json', 'Authorization': 'Bearer token'}",
        examples=[{"Content-Type": "application/json"}, {"Authorization": "Bearer abc123"}]
    )
    params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="URL查询参数字典。例如：{'page': 1, 'limit': 10, 'search': 'python'}",
        examples=[{"page": 1, "limit": 10}, {"q": "python", "sort": "stars"}]
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="POST/PUT请求的数据体，将转换为JSON格式发送",
        examples=[{"name": "John", "email": "john@example.com"}, {"title": "New Post", "content": "Hello World"}]
    )
    timeout: int = Field(
        default=30,
        description="请求超时时间（秒）",
        ge=1,
        le=300,
        examples=[10, 30, 60]
    )

class EmailSender(BaseModel):
    """
    邮件发送工具 - 发送电子邮件
    
    支持发送文本和HTML格式的邮件。
    可以添加附件、设置优先级、抄送等。
    """
    to_addresses: List[str] = Field(
        ...,
        description="收件人邮箱地址列表，至少需要一个有效邮箱",
        min_items=1,
        examples=[["user@example.com"], ["user1@example.com", "user2@example.com"]]
    )
    subject: str = Field(
        ...,
        description="邮件主题，不能为空",
        min_length=1,
        max_length=200,
        examples=["重要通知", "会议邀请", "项目进度更新"]
    )
    body: str = Field(
        ...,
        description="邮件正文内容",
        examples=["您好，这是一封测试邮件。", "<h1>HTML邮件</h1><p>这是HTML格式的邮件内容。</p>"]
    )
    cc_addresses: Optional[List[str]] = Field(
        default=None,
        description="抄送邮箱地址列表",
        examples=[["cc1@example.com"], ["cc1@example.com", "cc2@example.com"]]
    )
    bcc_addresses: Optional[List[str]] = Field(
        default=None,
        description="密送邮箱地址列表",
        examples=[["bcc@example.com"]]
    )
    is_html: bool = Field(
        default=False,
        description="邮件内容是否为HTML格式"
    )
    priority: Literal["low", "normal", "high"] = Field(
        default="normal",
        description="邮件优先级"
    )
    attachments: Optional[List[str]] = Field(
        default=None,
        description="附件文件路径列表",
        examples=[["./document.pdf"], ["./image.jpg", "./report.xlsx"]]
    )

class DataAnalyzer(BaseModel):
    """
    数据分析工具 - 执行数据分析和统计计算
    
    支持各种统计分析、数据可视化、机器学习等操作。
    可以处理CSV、JSON等格式的数据。
    """
    data_source: str = Field(
        ...,
        description="数据源路径或数据库连接字符串",
        examples=["./data/sales.csv", "postgresql://user:pass@localhost/db", "https://api.example.com/data"]
    )
    analysis_type: Literal["descriptive", "correlation", "regression", "clustering", "classification", "visualization"] = Field(
        ...,
        description="分析类型"
    )
    target_columns: List[str] = Field(
        ...,
        description="要分析的目标列名列表",
        min_items=1,
        examples=[["sales", "profit"], ["age", "income", "score"]]
    )
    group_by: Optional[List[str]] = Field(
        default=None,
        description="分组字段列表，用于分组分析",
        examples=[["category"], ["region", "product_type"]]
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="数据过滤条件",
        examples=[{"date": ">=2023-01-01"}, {"category": "electronics", "price": ">100"}]
    )
    output_format: Literal["json", "csv", "chart", "report"] = Field(
        default="json",
        description="输出格式"
    )
    chart_type: Optional[Literal["bar", "line", "scatter", "pie", "histogram", "heatmap"]] = Field(
        default=None,
        description="图表类型（当output_format为chart时需要）"
    )

# 实际执行函数
def execute_database_query(query_params: DatabaseQuery) -> Dict[str, Any]:
    """执行数据库查询"""
    return {
        "status": "success",
        "query": f"SELECT {','.join(query_params.columns)} FROM {query_params.table_name}",
        "conditions": query_params.where_conditions,
        "order": query_params.order_by,
        "limit": query_params.limit,
        "database": query_params.database_type,
        "result": f"模拟查询结果：从{query_params.table_name}表中查询到数据"
    }

def execute_file_operation(file_params: FileProcessor) -> Dict[str, Any]:
    """执行文件操作"""
    return {
        "status": "success",
        "operation": file_params.operation,
        "file_path": file_params.file_path,
        "encoding": file_params.encoding,
        "result": f"模拟{file_params.operation}操作：处理文件{file_params.file_path}"
    }

def execute_api_request(api_params: APIRequest) -> Dict[str, Any]:
    """执行API请求"""
    return {
        "status": "success",
        "method": api_params.method,
        "url": api_params.url,
        "headers": api_params.headers,
        "params": api_params.params,
        "timeout": api_params.timeout,
        "result": f"模拟API请求：{api_params.method} {api_params.url}"
    }

def execute_email_send(email_params: EmailSender) -> Dict[str, Any]:
    """执行邮件发送"""
    return {
        "status": "success",
        "to": email_params.to_addresses,
        "subject": email_params.subject,
        "cc": email_params.cc_addresses,
        "bcc": email_params.bcc_addresses,
        "priority": email_params.priority,
        "is_html": email_params.is_html,
        "attachments": email_params.attachments,
        "result": f"模拟发送邮件：主题'{email_params.subject}'发送给{len(email_params.to_addresses)}个收件人"
    }

def execute_data_analysis(analysis_params: DataAnalyzer) -> Dict[str, Any]:
    """执行数据分析"""
    return {
        "status": "success",
        "data_source": analysis_params.data_source,
        "analysis_type": analysis_params.analysis_type,
        "target_columns": analysis_params.target_columns,
        "group_by": analysis_params.group_by,
        "filters": analysis_params.filters,
        "output_format": analysis_params.output_format,
        "chart_type": analysis_params.chart_type,
        "result": f"模拟{analysis_params.analysis_type}分析：分析{len(analysis_params.target_columns)}个目标列"
    }

class AdvancedToolParamsDemo:
    def __init__(self):
        """初始化高级工具参数演示"""
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0.1
        )
        
        self.tools = [DatabaseQuery, FileProcessor, APIRequest, EmailSender, DataAnalyzer]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # 工具执行映射
        self.tool_executors = {
            "DatabaseQuery": execute_database_query,
            "FileProcessor": execute_file_operation,
            "APIRequest": execute_api_request,
            "EmailSender": execute_email_send,
            "DataAnalyzer": execute_data_analysis
        }
    
    def show_tool_schemas(self):
        """显示所有工具的详细参数说明"""
        print("=" * 80)
        print("🛠️  可用工具及其参数说明")
        print("=" * 80)
        
        for tool in self.tools:
            print(f"\n📋 工具名称: {tool.__name__}")
            print(f"📝 工具描述: {tool.__doc__.strip() if tool.__doc__ else '无描述'}")
            print("\n参数列表:")
            
            for field_name, field_info in tool.model_fields.items():
                print(f"  • {field_name}:")
                print(f"    - 类型: {field_info.annotation}")
                print(f"    - 描述: {field_info.description}")
                if hasattr(field_info, 'examples') and field_info.examples:
                    print(f"    - 示例: {field_info.examples}")
                if field_info.default is not None:
                    print(f"    - 默认值: {field_info.default}")
                print()
    
    def parse_and_execute_tools(self, query: str) -> List[Dict[str, Any]]:
        """解析并执行工具调用"""
        print(f"\n🔍 处理查询: {query}")
        print("-" * 60)
        
        # 解析工具调用
        chain = self.llm_with_tools | PydanticToolsParser(tools=self.tools)
        parsed_tools = chain.invoke(query)
        
        results = []
        
        for i, tool_call in enumerate(parsed_tools, 1):
            tool_name = tool_call.__class__.__name__
            print(f"\n🔧 工具调用 #{i}: {tool_name}")
            
            # 显示解析出的参数
            print("📋 解析出的参数:")
            tool_dict = tool_call.model_dump()
            for key, value in tool_dict.items():
                if value is not None:
                    print(f"  • {key}: {value}")
            
            # 执行工具
            if tool_name in self.tool_executors:
                print("\n⚡ 执行结果:")
                result = self.tool_executors[tool_name](tool_call)
                print(json.dumps(result, indent=2, ensure_ascii=False))
                results.append(result)
            else:
                print(f"❌ 未找到工具执行器: {tool_name}")
        
        return results
    
    def interactive_demo(self):
        """交互式演示"""
        print("🚀 高级工具参数演示 - 交互模式")
        print("输入 'help' 查看可用工具，输入 'quit' 退出")
        print("=" * 80)
        
        while True:
            try:
                query = input("\n💬 请输入您的请求: ").strip()
                
                if query.lower() == 'quit':
                    print("👋 再见！")
                    break
                elif query.lower() == 'help':
                    self.show_tool_schemas()
                elif query:
                    self.parse_and_execute_tools(query)
                else:
                    print("❌ 请输入有效的查询")
                    
            except KeyboardInterrupt:
                print("\n👋 再见！")
                break
            except Exception as e:
                print(f"❌ 发生错误: {e}")

def main():
    """主函数"""
    demo = AdvancedToolParamsDemo()
    
    # 显示工具说明
    demo.show_tool_schemas()
    
    # 预定义测试查询
    test_queries = [
        "查询用户表中所有活跃用户的姓名和邮箱，按创建时间降序排列，限制10条记录",
        "读取./data/sales.csv文件的内容",
        "向https://api.github.com/users/octocat发送GET请求获取用户信息",
        "发送一封主题为'项目进度更新'的邮件给team@company.com，抄送给manager@company.com",
        "对sales.csv文件进行描述性统计分析，分析销售额和利润列，按地区分组"
    ]
    
    print("\n🧪 运行预定义测试查询:")
    print("=" * 80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 测试查询 #{i}:")
        demo.parse_and_execute_tools(query)
        print("\n" + "="*80)
    
    # 启动交互模式
    print("\n🎮 启动交互模式...")
    demo.interactive_demo()

if __name__ == "__main__":
    main()
