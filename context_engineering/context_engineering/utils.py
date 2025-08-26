"""
Utility functions for context engineering notebooks.

上下文工程笔记本的实用函数。
"""

from rich.console import Console
from rich.panel import Panel
import json

console = Console()


def format_message_content(message):
    """Convert message content to displayable string
    
    将消息内容转换为可显示的字符串"""
    if isinstance(message.content, str):
        return message.content
    elif isinstance(message.content, list):
        # Handle complex content like tool calls
        # 处理复杂内容，如工具调用
        parts = []
        for item in message.content:
            if item.get('type') == 'text':
                parts.append(item['text'])
            elif item.get('type') == 'tool_use':
                parts.append(f"\n🔧 Tool Call: {item['name']}") # 工具调用
                parts.append(f"   Args: {json.dumps(item['input'], indent=2)}") # 参数
        return "\n".join(parts)
    else:
        return str(message.content)


def format_messages(messages):
    """Format and display a list of messages with Rich formatting
    
    使用Rich格式化格式化并显示消息列表"""
    for m in messages:
        msg_type = m.__class__.__name__.replace('Message', '')
        content = format_message_content(m)

        if msg_type == 'Human':
            console.print(Panel(content, title="🧑 Human", border_style="blue")) # 人类
        elif msg_type == 'Ai':
            console.print(Panel(content, title="🤖 Assistant", border_style="green")) # 助手
        elif msg_type == 'Tool':
            console.print(Panel(content, title="🔧 Tool Output", border_style="yellow")) # 工具输出
        else:
            console.print(Panel(content, title=f"📝 {msg_type}", border_style="white"))


def format_message(messages):
    """Alias for format_messages for backward compatibility
    
    format_messages的别名，用于向后兼容"""
    return format_messages(messages)