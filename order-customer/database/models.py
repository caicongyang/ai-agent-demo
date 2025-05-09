"""Database models for the order-customer service system."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum

from order_customer.config.config import DB_CONNECTION_STRING

Base = declarative_base()

class OrderStatus(enum.Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"

class Customer(Base):
    """Customer model."""
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, unique=True)
    email = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    orders = relationship("Order", back_populates="customer")
    conversations = relationship("Conversation", back_populates="customer")
    
    def __repr__(self):
        return f"<Customer(id={self.id}, name='{self.name}', phone='{self.phone}')>"

class Order(Base):
    """Order model."""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    order_number = Column(String(50), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    status = Column(String(20), default=OrderStatus.PENDING.value)
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    paid_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    expected_delivery_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    tracking_number = Column(String(100), nullable=True)
    shipping_company = Column(String(100), nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")
    
    def __repr__(self):
        return f"<Order(id={self.id}, order_number='{self.order_number}', status='{self.status}')>"
    
    @property
    def days_to_delivery(self):
        """Calculate days until expected delivery."""
        if not self.expected_delivery_at:
            return None
        
        if self.status == OrderStatus.DELIVERED.value:
            return 0
            
        days = (self.expected_delivery_at - datetime.now()).days
        return max(0, days)

class OrderItem(Base):
    """Order item model."""
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_name = Column(String(255), nullable=False)
    product_id = Column(String(50), nullable=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, product_name='{self.product_name}', quantity={self.quantity})>"

class Conversation(Base):
    """Conversation model for storing chat history."""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    session_id = Column(String(100), nullable=False)
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, customer_id={self.customer_id}, session_id='{self.session_id}')>"

class Message(Base):
    """Message model for storing individual messages in a conversation."""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    sender_type = Column(String(10), nullable=False)  # 'customer' or 'system'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, sender_type='{self.sender_type}', timestamp={self.timestamp})>"

# Initialize database connection
def init_db():
    """Initialize database connection and create tables if they don't exist."""
    engine = create_engine(DB_CONNECTION_STRING)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

# Get database session
def get_db_session():
    """Get database session."""
    engine = create_engine(DB_CONNECTION_STRING)
    Session = sessionmaker(bind=engine)
    return Session() 