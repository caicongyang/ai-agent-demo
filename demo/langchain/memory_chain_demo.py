import os
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class MemoryChainDemo:
    """
    Memory Chain 演示类
    
    该类演示了 LangChain 中的记忆功能，包括：
    1. 对话历史记忆
    2. 对话摘要记忆
    3. 基于记忆的上下文对话
    
    Attributes:
        llm: 大语言模型实例
        buffer_memory: 对话历史记忆
        summary_memory: 对话摘要记忆
    """

    def __init__(self):
        """
        初始化 Memory Chain 演示实例
        """
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
        )
        
        # 初始化对话历史记忆
        self.buffer_memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history"
        )
        
        # 初始化对话摘要记忆
        self.summary_memory = ConversationSummaryMemory(
            llm=self.llm,
            memory_key="chat_summary"
        )

    def create_chat_chain(self, use_summary: bool = False) -> Any:
        """
        创建带记忆的对话链
        
        Args:
            use_summary: 是否使用摘要记忆
        
        Returns:
            对话链
        """
        # 选择记忆类型
        memory = self.summary_memory if use_summary else self.buffer_memory
        memory_key = "chat_summary" if use_summary else "chat_history"
        
        # 创建对话模板
        if use_summary:
            # 对于摘要记忆，使用字符串形式的提示
            chat_prompt = ChatPromptTemplate.from_messages([
                ("system", "对话历史摘要：{chat_summary}"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="context"),
            ])
        else:
            # 对于完整历史记忆，使用消息列表
            chat_prompt = ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name=memory_key),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="context"),
            ])
        
        # 创建对话链
        chain = (
            RunnablePassthrough.assign(
                context=lambda x: [],  # 可以根据需要添加额外上下文
            )
            | chat_prompt
            | self.llm
            | StrOutputParser()
        )
        
        return chain, memory

    def chat_with_memory(self, query: str, use_summary: bool = False) -> str:
        """
        使用记忆进行对话
        
        Args:
            query: 用户输入
            use_summary: 是否使用摘要记忆
        
        Returns:
            AI 回复
        """
        try:
            chain, memory = self.create_chat_chain(use_summary)
            
            # 获取记忆内容
            memory_content = memory.load_memory_variables({})
            
            # 执行对话
            response = chain.invoke({
                "input": query,
                **memory_content
            })
            
            # 更新记忆
            memory.save_context(
                {"input": query},
                {"output": response}
            )
            
            return response
        except Exception as e:
            print(f"对话过程中出现错误: {e}")
            return f"抱歉，处理您的请求时出现了错误。错误信息：{str(e)}"

    def get_memory_content(self, use_summary: bool = False) -> str:
        """
        获取记忆内容
        
        Args:
            use_summary: 是否获取摘要记忆
        
        Returns:
            记忆内容
        """
        memory = self.summary_memory if use_summary else self.buffer_memory
        memory_vars = memory.load_memory_variables({})
        return memory_vars

def main():
    """主函数，演示记忆功能的使用方法"""
    # 创建演示实例
    demo = MemoryChainDemo()
    
    # 测试对话历史记忆
    print("=== 测试对话历史记忆 ===")
    conversations = [
        "你好，我叫小明",
        "我想学习Python编程",
        "请推荐一些适合初学者的Python教程",
        "刚才说的那些教程难度如何？"
    ]
    
    for query in conversations:
        print(f"\n用户: {query}")
        response = demo.chat_with_memory(query, use_summary=False)
        print(f"AI: {response}")
    
    print("\n对话历史记忆内容:")
    print(demo.get_memory_content(use_summary=False))
    
    # 测试对话摘要记忆
    print("\n=== 测试对话摘要记忆 ===")
    conversations = [
        "我是一名大学生",
        "我对人工智能很感兴趣",
        "想了解深度学习的基础知识",
        "之前提到的内容可以总结一下吗？"
    ]
    
    for query in conversations:
        print(f"\n用户: {query}")
        response = demo.chat_with_memory(query, use_summary=True)
        print(f"AI: {response}")
    
    print("\n对话摘要记忆内容:")
    print(demo.get_memory_content(use_summary=True))

if __name__ == "__main__":
    main() 