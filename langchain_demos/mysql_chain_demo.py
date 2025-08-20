import os
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv
import pymysql
from sqlalchemy import create_engine, text

# 加载环境变量
load_dotenv()

class MySQLChainDemo:
    """MySQL Chain 演示类"""

    def __init__(self, database: str = None):
        """
        初始化 MySQL Chain 演示实例
        
        Args:
            database: 数据库名称，如果不指定则使用环境变量中的配置
        """
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        
        # 使用传入的数据库名或环境变量中的配置
        self.database = database or os.getenv("MYSQL_DATABASE", "stock")
        
        # 创建数据库连接
        db_url = (f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
                 f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{self.database}")
        
        self.engine = create_engine(db_url)
        self.db = SQLDatabase(engine=self.engine)

    def get_tables_info(self) -> str:
        """获取所有表的信息"""
        try:
            with self.engine.connect() as conn:
                # 获取所有表名
                tables = conn.execute(text("SHOW TABLES")).fetchall()
                tables = [table[0] for table in tables]
                
                tables_info = [f"当前数据库: {self.database}"]
                for table in tables:
                    # 获取表结构
                    columns = conn.execute(text(f"DESCRIBE `{table}`")).fetchall()
                    columns_info = [f"{col[0]} ({col[1]})" for col in columns]
                    
                    tables_info.append(f"\n表名: {table}")
                    tables_info.append("列: " + ", ".join(columns_info))
                
                return "\n".join(tables_info)
        except Exception as e:
            return f"获取表信息失败: {str(e)}"

    def execute_query(self, question: str) -> str:
        """执行自然语言查询"""
        try:
            # 创建提示模板
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个MySQL专家，请将用户的自然语言问题转换为可执行的MySQL查询语句。

当前数据库环境：
数据库名称: {database}

数据库表结构如下：
{tables_info}

规则：
1. 只返回一个MySQL查询语句
2. 不要包含任何注释或额外说明
3. 不要使用markdown格式
4. 使用反引号(`)包裹表名和列名
5. 确保SQL语法正确
6. 查询information_schema时使用当前数据库名称

示例：
问题：数据库中有哪些表？
返回：SELECT TABLE_NAME as table_name FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{database}';

问题：查询用户表有多少条记录？
返回：SELECT COUNT(*) as total FROM `users`;
"""),
                ("human", "{question}")
            ])
            
            # 获取表信息
            tables_info = self.get_tables_info()
            
            # 生成SQL
            chain = prompt | self.llm | StrOutputParser()
            sql = chain.invoke({
                "question": question,
                "tables_info": tables_info,
                "database": self.database
            }).strip()
            
            # 执行SQL
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = result.fetchall()
                
                if not rows:
                    return f"SQL查询: {sql}\n\n查询结果: 无数据"
                
                # 格式化结果
                columns = result.keys()
                results = []
                for row in rows:
                    result_dict = dict(zip(columns, row))
                    results.append(str(result_dict))
                
                return f"SQL查询: {sql}\n\n查询结果:\n" + "\n".join(results)
                
        except Exception as e:
            return f"查询执行失败: {str(e)}\nSQL: {sql if 'sql' in locals() else '未生成'}"

def main():
    """主函数"""
    # 可以指定数据库名称，或使用默认值
    demo = MySQLChainDemo()  # 使用默认的 stock 数据库
    # demo = MySQLChainDemo(database="other_db")  # 使用指定的数据库
    
    # 测试查询
    test_queries = [
        "数据库中有哪些表？",
        "查询t_stock_min_trade表中最新的交易时间",
        "查询t_stock_min_trade表中股票代码为000001的最近3条记录",
        "统计t_stock_min_trade表中有多少个不同的股票代码"
    ]
    
    for query in test_queries:
        print(f"\n问题: {query}")
        result = demo.execute_query(query)
        print(result)
        print("-" * 50)

if __name__ == "__main__":
    main() 