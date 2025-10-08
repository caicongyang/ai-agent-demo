#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码解释器演示
使用 LangChain 的 PythonREPLTool 和 PythonAstREPLTool 实现一个小型代码解释器

Features:
1. 使用 PythonREPLTool 执行 Python 代码
2. 使用 PythonAstREPLTool 进行安全的代码执行
3. 交互式代码解释器界面
4. 代码执行历史记录
5. 错误处理和安全性控制
"""

import os
import sys
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_experimental.tools import PythonREPLTool, PythonAstREPLTool
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage


class CodeInterpreter:
    """代码解释器类"""
    
    def __init__(self, use_ast_repl: bool = True, openai_api_key: str = None):
        """
        初始化代码解释器
        
        Args:
            use_ast_repl: 是否使用 PythonAstREPLTool (更安全)
            openai_api_key: OpenAI API 密钥
        """
        self.use_ast_repl = use_ast_repl
        self.execution_history = []
        
        # 初始化工具
        if use_ast_repl:
            self.python_tool = PythonAstREPLTool()
            print("✅ 使用 PythonAstREPLTool (安全模式)")
        else:
            self.python_tool = PythonREPLTool()
            print("⚠️  使用 PythonREPLTool (完整功能模式)")
        
        # 初始化 LLM (如果提供了 API 密钥)
        self.llm = None
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
            self.llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
            
            # 创建内存
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            
            # 创建智能代理
            self.agent = initialize_agent(
                tools=[self.python_tool],
                llm=self.llm,
                agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                memory=self.memory,
                verbose=True
            )
    
    def execute_code(self, code: str) -> Dict[str, Any]:
        """
        执行 Python 代码
        
        Args:
            code: 要执行的 Python 代码
            
        Returns:
            包含执行结果的字典
        """
        execution_record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "code": code,
            "success": False,
            "result": None,
            "error": None
        }
        
        try:
            # 使用工具执行代码
            result = self.python_tool.run(code)
            execution_record["success"] = True
            execution_record["result"] = result
            
            print(f"✅ 执行成功:")
            print(f"代码: {code}")
            print(f"结果: {result}")
            
        except Exception as e:
            execution_record["error"] = str(e)
            print(f"❌ 执行失败:")
            print(f"代码: {code}")
            print(f"错误: {e}")
            
        # 添加到历史记录
        self.execution_history.append(execution_record)
        return execution_record
    
    def execute_with_ai(self, query: str) -> str:
        """
        使用 AI 代理执行查询
        
        Args:
            query: 用户查询
            
        Returns:
            AI 代理的响应
        """
        if not self.llm:
            return "❌ 未配置 OpenAI API 密钥，无法使用 AI 功能"
        
        try:
            response = self.agent.run(query)
            return response
        except Exception as e:
            return f"❌ AI 执行失败: {e}"
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """获取执行历史记录"""
        return self.execution_history
    
    def clear_history(self):
        """清除执行历史记录"""
        self.execution_history.clear()
        if hasattr(self, 'memory'):
            self.memory.clear()
        print("📝 历史记录已清除")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
🔧 代码解释器帮助
==================

基本命令:
- 直接输入 Python 代码进行执行
- /help - 显示帮助信息
- /history - 显示执行历史
- /clear - 清除历史记录
- /quit 或 /exit - 退出程序

示例代码:
- print("Hello, World!")
- import math; math.sqrt(16)
- x = [1, 2, 3, 4, 5]; sum(x)
- import matplotlib.pyplot as plt; plt.plot([1,2,3,4])

AI 查询 (需要 OpenAI API 密钥):
- 以 "ai:" 开头的查询会使用 AI 代理处理
- 例如: ai: 计算斐波那契数列的前10项

安全性:
- PythonAstREPLTool: 限制危险操作 (推荐)
- PythonREPLTool: 完整 Python 功能 (需谨慎使用)
        """
        print(help_text)


def demo_basic_usage():
    """基本使用演示"""
    print("\n" + "="*50)
    print("🚀 基本使用演示")
    print("="*50)
    
    # 创建代码解释器 (使用 AST 模式)
    interpreter = CodeInterpreter(use_ast_repl=True)
    
    # 示例代码列表
    demo_codes = [
        "print('Hello, Code Interpreter!')",
        "import math\nresult = math.sqrt(16)\nprint(f'sqrt(16) = {result}')",
        "numbers = [1, 2, 3, 4, 5]\ntotal = sum(numbers)\nprint(f'Sum: {total}')",
        "# 创建简单的数据分析\nimport statistics\ndata = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]\nmean = statistics.mean(data)\nprint(f'平均值: {mean}')",
    ]
    
    # 执行演示代码
    for i, code in enumerate(demo_codes, 1):
        print(f"\n📝 示例 {i}:")
        print(f"代码:\n{code}")
        print("-" * 30)
        interpreter.execute_code(code)
        print()


def demo_comparison():
    """PythonREPLTool vs PythonAstREPLTool 对比演示"""
    print("\n" + "="*50)
    print("⚖️  工具对比演示")
    print("="*50)
    
    # 测试代码 - 一些可能有安全风险的操作
    test_codes = [
        "import os\nos.getcwd()",  # 获取当前目录
        "open('test.txt', 'w').write('test')",  # 文件操作
        "import subprocess\n# subprocess.run(['ls'])",  # 系统命令 (注释掉)
    ]
    
    print("🔒 使用 PythonAstREPLTool (安全模式):")
    ast_interpreter = CodeInterpreter(use_ast_repl=True)
    
    for code in test_codes:
        print(f"\n测试代码: {code}")
        ast_interpreter.execute_code(code)
    
    print("\n" + "-"*50)
    print("🔓 使用 PythonREPLTool (完整模式):")
    repl_interpreter = CodeInterpreter(use_ast_repl=False)
    
    for code in test_codes:
        print(f"\n测试代码: {code}")
        repl_interpreter.execute_code(code)


def interactive_mode():
    """交互式模式"""
    print("\n" + "="*50)
    print("🎮 交互式代码解释器")
    print("="*50)
    
    # 检查是否有 OpenAI API 密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("💡 提示: 设置 OPENAI_API_KEY 环境变量以启用 AI 功能")
    
    # 创建解释器
    interpreter = CodeInterpreter(use_ast_repl=True, openai_api_key=api_key)
    interpreter.show_help()
    
    print("\n🎯 交互式模式已启动! 输入 Python 代码或命令:")
    
    while True:
        try:
            # 获取用户输入
            user_input = input("\n>>> ").strip()
            
            # 处理特殊命令
            if user_input in ["/quit", "/exit"]:
                print("👋 再见!")
                break
            elif user_input == "/help":
                interpreter.show_help()
                continue
            elif user_input == "/history":
                history = interpreter.get_execution_history()
                if not history:
                    print("📝 暂无执行历史")
                else:
                    print(f"📝 执行历史 ({len(history)} 条记录):")
                    for i, record in enumerate(history, 1):
                        status = "✅" if record["success"] else "❌"
                        print(f"{i}. {status} [{record['timestamp']}]")
                        print(f"   代码: {record['code'][:50]}...")
                        if record["success"]:
                            print(f"   结果: {str(record['result'])[:100]}...")
                        else:
                            print(f"   错误: {record['error']}")
                continue
            elif user_input == "/clear":
                interpreter.clear_history()
                continue
            elif user_input == "":
                continue
            
            # 处理 AI 查询
            if user_input.startswith("ai:"):
                query = user_input[3:].strip()
                print("🤖 AI 处理中...")
                result = interpreter.execute_with_ai(query)
                print(f"🤖 AI 响应: {result}")
                continue
            
            # 执行 Python 代码
            interpreter.execute_code(user_input)
            
        except KeyboardInterrupt:
            print("\n\n👋 程序被中断，再见!")
            break
        except EOFError:
            print("\n\n👋 再见!")
            break
        except Exception as e:
            print(f"❌ 意外错误: {e}")


def demo_advanced_features():
    """高级功能演示"""
    print("\n" + "="*50)
    print("🎯 高级功能演示")
    print("="*50)
    
    interpreter = CodeInterpreter(use_ast_repl=True)
    
    # 数据科学相关代码
    advanced_codes = [
        """
# 数据分析示例
import json
data = {'name': 'Alice', 'age': 30, 'city': 'Beijing'}
json_str = json.dumps(data, ensure_ascii=False)
print(f'JSON: {json_str}')
        """,
        """
# 数学计算
import math
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# 计算前8项斐波那契数列
fib_sequence = [fibonacci(i) for i in range(8)]
print(f'斐波那契数列: {fib_sequence}')
        """,
        """
# 字符串处理
text = "Hello, 代码解释器!"
processed = text.upper().replace("HELLO", "你好")
print(f'处理后的文本: {processed}')

# 统计字符
char_count = len(text)
print(f'字符数: {char_count}')
        """,
    ]
    
    for i, code in enumerate(advanced_codes, 1):
        print(f"\n🔥 高级示例 {i}:")
        print("-" * 30)
        interpreter.execute_code(code.strip())
        print()


def main():
    """主函数"""
    print("🐍 LangChain 代码解释器演示")
    print("=" * 60)
    
    while True:
        print("\n请选择演示模式:")
        print("1. 基本使用演示")
        print("2. 工具对比演示")
        print("3. 高级功能演示")
        print("4. 交互式模式")
        print("0. 退出")
        
        choice = input("\n请输入选择 (0-4): ").strip()
        
        if choice == "1":
            demo_basic_usage()
        elif choice == "2":
            demo_comparison()
        elif choice == "3":
            demo_advanced_features()
        elif choice == "4":
            interactive_mode()
        elif choice == "0":
            print("👋 再见!")
            break
        else:
            print("❌ 无效选择，请重新输入")


if __name__ == "__main__":
    main()
