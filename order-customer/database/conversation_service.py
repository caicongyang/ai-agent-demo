"""Conversation service for handling chat history operations."""

from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

from order_customer.database.models import get_db_session, Conversation, Message, Customer

class ConversationService:
    """Service for conversation-related database operations."""
    
    @staticmethod
    def create_conversation(customer_id: int) -> str:
        """Create a new conversation and return the session ID."""
        session = get_db_session()
        try:
            # Generate a unique session ID
            session_id = str(uuid.uuid4())
            
            # Create a new conversation
            conversation = Conversation(
                customer_id=customer_id,
                session_id=session_id,
                start_time=datetime.now()
            )
            
            session.add(conversation)
            session.commit()
            
            return session_id
        
        except Exception:
            session.rollback()
            raise
        
        finally:
            session.close()
    
    @staticmethod
    def get_or_create_customer(phone: str, name: Optional[str] = None) -> int:
        """Get or create a customer by phone number and return the customer ID."""
        session = get_db_session()
        try:
            # Check if customer exists
            customer = session.query(Customer).filter(Customer.phone == phone).first()
            
            if customer:
                # Update name if provided
                if name and customer.name != name:
                    customer.name = name
                    session.commit()
                return customer.id
            
            # Create a new customer
            customer = Customer(
                phone=phone,
                name=name or f"Customer_{phone[-4:]}"  # Use last 4 digits if name not provided
            )
            
            session.add(customer)
            session.commit()
            
            return customer.id
        
        except Exception:
            session.rollback()
            raise
        
        finally:
            session.close()
    
    @staticmethod
    def add_message(session_id: str, content: str, sender_type: str) -> bool:
        """Add a message to a conversation."""
        session = get_db_session()
        try:
            # Get the conversation
            conversation = session.query(Conversation).filter(Conversation.session_id == session_id).first()
            
            if not conversation:
                return False
            
            # Create a new message
            message = Message(
                conversation_id=conversation.id,
                sender_type=sender_type,  # 'customer' or 'system'
                content=content,
                timestamp=datetime.now()
            )
            
            session.add(message)
            session.commit()
            
            return True
        
        except Exception:
            session.rollback()
            return False
        
        finally:
            session.close()
    
    @staticmethod
    def get_conversation_history(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        session = get_db_session()
        try:
            conversation = session.query(Conversation).filter(Conversation.session_id == session_id).first()
            
            if not conversation:
                return []
            
            # Get messages, ordered by timestamp
            messages = session.query(Message).filter(
                Message.conversation_id == conversation.id
            ).order_by(Message.timestamp.desc()).limit(limit).all()
            
            # Format messages
            result = []
            for message in reversed(messages):  # Reverse to get chronological order
                result.append({
                    'sender': message.sender_type,
                    'content': message.content,
                    'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            return result
        
        finally:
            session.close()
    
    @staticmethod
    def close_conversation(session_id: str) -> bool:
        """Close a conversation by setting the end time."""
        session = get_db_session()
        try:
            conversation = session.query(Conversation).filter(Conversation.session_id == session_id).first()
            
            if not conversation:
                return False
            
            conversation.end_time = datetime.now()
            session.commit()
            
            return True
        
        except Exception:
            session.rollback()
            return False
        
        finally:
            session.close()
    
    @staticmethod
    def get_recent_conversations(customer_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversations for a customer."""
        session = get_db_session()
        try:
            conversations = session.query(Conversation).filter(
                Conversation.customer_id == customer_id
            ).order_by(Conversation.start_time.desc()).limit(limit).all()
            
            result = []
            for conversation in conversations:
                # Get the first and last message
                first_message = session.query(Message).filter(
                    Message.conversation_id == conversation.id
                ).order_by(Message.timestamp.asc()).first()
                
                last_message = session.query(Message).filter(
                    Message.conversation_id == conversation.id
                ).order_by(Message.timestamp.desc()).first()
                
                result.append({
                    'session_id': conversation.session_id,
                    'start_time': conversation.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': conversation.end_time.strftime('%Y-%m-%d %H:%M:%S') if conversation.end_time else None,
                    'first_message': first_message.content if first_message else None,
                    'last_message': last_message.content if last_message else None,
                    'message_count': session.query(Message).filter(Message.conversation_id == conversation.id).count()
                })
            
            return result
        
        finally:
            session.close() 