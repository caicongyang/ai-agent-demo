"""Customer service system using LangChain for order inquiries."""

from typing import Dict, List, Any, Optional
import re
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from order_customer.models.base_model import get_llm
from order_customer.database.order_service import OrderService
from order_customer.database.conversation_service import ConversationService
from order_customer.config.config import DEFAULT_GREETING, DEFAULT_WAITING_MESSAGE, DEFAULT_FAREWELL

# Define the system prompt template
SYSTEM_PROMPT = """你是一个专业的电商客服助手，负责回答关于订单的各种问题，包括：
1. 订单状态查询：发货状态、预计到货时间
2. 物流跟踪：物流公司、快递单号、物流进度
3. 基本话术：问候、告别、常见问题回复

按照以下规范回复用户：
- 保持专业、礼貌和友好的态度
- 首次交流时主动问候用户
- 询问订单号时，说明订单号的格式要求
- 回复中使用恰当的敬语
- 表达歉意时要诚恳
- 回答要简洁明了，不要太冗长
- 对于无法解决的问题，引导用户提供更多信息或转人工客服

不要编造不存在的订单信息，如果订单数据库中没有相关信息，直接告知用户未找到该订单。

您可以访问以下信息：
1. 用户过去的对话历史（如果有）
2. 数据库中的订单信息（如果用户提供了订单号或手机号）

若用户询问订单信息，但数据库中不存在相关订单，请礼貌地告知用户未找到订单，并询问订单号是否正确。
"""

class CustomerServiceAgent:
    """Customer service agent for handling order inquiries."""
    
    def __init__(self):
        """Initialize the customer service agent."""
        self.llm = get_llm(temperature=0.7)
        self.output_parser = StrOutputParser()
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Build the chain
        self.chain = (
            {
                "input": RunnablePassthrough(),
                "history": RunnablePassthrough(),
                "agent_scratchpad": RunnablePassthrough()
            }
            | self.prompt
            | self.llm
            | self.output_parser
        )
    
    def _extract_order_number(self, text: str) -> Optional[str]:
        """Extract order number from text.
        
        Common order number formats:
        - ORDxxxxxxxx
        - Order-xxxxxxxx
        - #xxxxxxxx
        """
        patterns = [
            r'ORD[0-9]{8,}',  # ORDxxxxxxxx
            r'Order-[0-9]{8,}',  # Order-xxxxxxxx
            r'#[0-9]{8,}',  # #xxxxxxxx
            r'订单[号碼][:：\s]*([A-Za-z0-9-]{8,})',  # Chinese: 订单号/订单号：xxxxxxxx
            r'订单[:：\s]*([A-Za-z0-9-]{8,})'  # Chinese: 订单/订单：xxxxxxxx
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_phone_number(self, text: str) -> Optional[str]:
        """Extract phone number from text."""
        patterns = [
            r'1[3-9][0-9]{9}',  # Chinese mobile number
            r'[0-9]{3}[-\.\s][0-9]{3}[-\.\s][0-9]{4}',  # xxx-xxx-xxxx
            r'[0-9]{10,11}'  # 10-11 digit number
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None
    
    def _get_order_info(self, text: str) -> Dict[str, Any]:
        """Extract order info from text and fetch from database."""
        order_info = {"found": False, "data": None, "type": None}
        
        # Try to extract order number
        order_number = self._extract_order_number(text)
        if order_number:
            order_data = OrderService.get_order_by_number(order_number)
            if order_data:
                order_info["found"] = True
                order_info["data"] = order_data
                order_info["type"] = "order_number"
                return order_info
        
        # Try to extract phone number if no order found
        phone_number = self._extract_phone_number(text)
        if phone_number:
            orders = OrderService.get_orders_by_customer_phone(phone_number)
            if orders:
                order_info["found"] = True
                order_info["data"] = orders
                order_info["type"] = "phone_number"
                return order_info
        
        return order_info
    
    def _get_tracking_info(self, text: str) -> Dict[str, Any]:
        """Get tracking info for an order."""
        tracking_info = {"found": False, "data": None}
        
        # Extract order number
        order_number = self._extract_order_number(text)
        if order_number:
            data = OrderService.get_tracking_info(order_number)
            if data:
                tracking_info["found"] = True
                tracking_info["data"] = data
        
        return tracking_info
    
    def _format_messages(self, conversation_history: List[Dict[str, Any]]) -> List[Any]:
        """Format conversation history as messages for the LLM."""
        formatted_messages = []
        
        for message in conversation_history:
            if message["sender"] == "customer":
                formatted_messages.append(HumanMessage(content=message["content"]))
            else:
                formatted_messages.append(AIMessage(content=message["content"]))
        
        return formatted_messages
    
    def _check_order_inquiry(self, text: str) -> bool:
        """Check if the user is inquiring about an order."""
        order_keywords = [
            "订单", "物流", "快递", "发货", "到货", "送达", "何时", "什么时候",
            "order", "tracking", "delivery", "shipped", "package", "when"
        ]
        
        for keyword in order_keywords:
            if keyword in text.lower():
                return True
        
        return False
    
    def _format_agent_scratchpad(self, information: Dict[str, Any]) -> str:
        """Format information as agent scratchpad."""
        scratchpad = []
        
        if "order_info" in information and information["order_info"]["found"]:
            order_info = information["order_info"]
            scratchpad.append("订单信息查询结果：")
            
            if order_info["type"] == "order_number":
                order_data = order_info["data"]
                scratchpad.append(f"- 订单号: {order_data['order_number']}")
                scratchpad.append(f"- 客户名称: {order_data['customer_name']}")
                scratchpad.append(f"- 订单状态: {order_data['status']}")
                scratchpad.append(f"- 下单时间: {order_data['created_at']}")
                
                if "shipped_at" in order_data:
                    scratchpad.append(f"- 发货时间: {order_data['shipped_at']}")
                if "expected_delivery_at" in order_data:
                    scratchpad.append(f"- 预计送达时间: {order_data['expected_delivery_at']}")
                if "tracking_number" in order_data:
                    scratchpad.append(f"- 快递单号: {order_data['tracking_number']}")
                if "shipping_company" in order_data:
                    scratchpad.append(f"- 物流公司: {order_data['shipping_company']}")
            
            elif order_info["type"] == "phone_number":
                orders = order_info["data"]
                scratchpad.append(f"找到 {len(orders)} 个订单:")
                
                for i, order in enumerate(orders, 1):
                    scratchpad.append(f"\n订单 {i}:")
                    scratchpad.append(f"- 订单号: {order['order_number']}")
                    scratchpad.append(f"- 订单状态: {order['status']}")
                    scratchpad.append(f"- 下单时间: {order['created_at']}")
                    
                    if "shipped_at" in order:
                        scratchpad.append(f"- 发货时间: {order['shipped_at']}")
                    if "expected_delivery_at" in order:
                        scratchpad.append(f"- 预计送达时间: {order['expected_delivery_at']}")
        
        if "tracking_info" in information and information["tracking_info"]["found"]:
            tracking_info = information["tracking_info"]["data"]
            scratchpad.append("\n物流信息查询结果：")
            scratchpad.append(f"- 订单号: {tracking_info['order_number']}")
            scratchpad.append(f"- 快递单号: {tracking_info['tracking_number']}")
            scratchpad.append(f"- 物流公司: {tracking_info['shipping_company']}")
            scratchpad.append(f"- 发货时间: {tracking_info['shipped_at'] or '未发货'}")
            scratchpad.append(f"- 预计送达时间: {tracking_info['expected_delivery_at'] or '未知'}")
            
            if tracking_info['days_to_delivery'] is not None:
                scratchpad.append(f"- 预计还需 {tracking_info['days_to_delivery']} 天送达")
        
        return "\n".join(scratchpad)
    
    def process_message(self, session_id: str, message: str) -> str:
        """Process a customer message and generate a response."""
        # Save customer message to conversation history
        ConversationService.add_message(session_id, message, "customer")
        
        # Get conversation history
        conversation_history = ConversationService.get_conversation_history(session_id)
        formatted_history = self._format_messages(conversation_history)
        
        # Prepare information for the agent
        information = {}
        agent_scratchpad = ""
        
        # Check if the user is inquiring about an order
        if self._check_order_inquiry(message):
            # Get order info
            information["order_info"] = self._get_order_info(message)
            
            # Get tracking info if applicable
            if "tracking" in message.lower() or "物流" in message or "快递" in message:
                information["tracking_info"] = self._get_tracking_info(message)
            
            # Format agent scratchpad
            agent_scratchpad = self._format_agent_scratchpad(information)
        
        # Generate response
        response = self.chain.invoke({
            "input": message,
            "history": formatted_history,
            "agent_scratchpad": agent_scratchpad
        })
        
        # Save system response to conversation history
        ConversationService.add_message(session_id, response, "system")
        
        return response
    
    def start_conversation(self, phone: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Start a new conversation and return session details."""
        # Get or create customer
        customer_id = ConversationService.get_or_create_customer(phone, name)
        
        # Create a new conversation
        session_id = ConversationService.create_conversation(customer_id)
        
        # Add greeting message
        ConversationService.add_message(session_id, DEFAULT_GREETING, "system")
        
        return {
            "session_id": session_id,
            "customer_id": customer_id,
            "greeting": DEFAULT_GREETING
        }
    
    def end_conversation(self, session_id: str) -> str:
        """End a conversation with a farewell message."""
        # Add farewell message
        ConversationService.add_message(session_id, DEFAULT_FAREWELL, "system")
        
        # Close the conversation
        ConversationService.close_conversation(session_id)
        
        return DEFAULT_FAREWELL 