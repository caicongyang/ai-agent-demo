"""Command-line interface for testing the customer service system."""

import os
import argparse
import json
from dotenv import load_dotenv
from order_customer.database.models import init_db
from order_customer.models.customer_service import CustomerServiceAgent

# Load environment variables
load_dotenv()

def create_sample_data():
    """Create sample data for testing."""
    from datetime import datetime, timedelta
    from order_customer.database.models import get_db_session, Customer, Order, OrderItem, OrderStatus
    
    session = get_db_session()
    try:
        # Check if data already exists
        customers = session.query(Customer).all()
        if customers:
            print("Sample data already exists. Skipping creation.")
            return
        
        # Create sample customer
        customer = Customer(
            name="张三",
            phone="13800138000",
            email="zhangsan@example.com",
            address="北京市朝阳区某小区1号楼2单元303"
        )
        session.add(customer)
        session.flush()  # Get ID without committing
        
        # Create sample orders
        orders = [
            # Delivered order
            Order(
                order_number="ORD12345678",
                customer_id=customer.id,
                status=OrderStatus.DELIVERED.value,
                total_amount=299.99,
                created_at=datetime.now() - timedelta(days=30),
                paid_at=datetime.now() - timedelta(days=30),
                shipped_at=datetime.now() - timedelta(days=28),
                expected_delivery_at=datetime.now() - timedelta(days=25),
                delivered_at=datetime.now() - timedelta(days=24),
                tracking_number="SF1234567890",
                shipping_company="顺丰快递"
            ),
            # Shipped order
            Order(
                order_number="ORD87654321",
                customer_id=customer.id,
                status=OrderStatus.SHIPPED.value,
                total_amount=599.99,
                created_at=datetime.now() - timedelta(days=3),
                paid_at=datetime.now() - timedelta(days=3),
                shipped_at=datetime.now() - timedelta(days=1),
                expected_delivery_at=datetime.now() + timedelta(days=2),
                tracking_number="YT9876543210",
                shipping_company="圆通快递"
            ),
            # Pending order
            Order(
                order_number="ORD11223344",
                customer_id=customer.id,
                status=OrderStatus.PENDING.value,
                total_amount=1299.99,
                created_at=datetime.now() - timedelta(hours=2)
            )
        ]
        
        for order in orders:
            session.add(order)
        
        session.flush()  # Get IDs without committing
        
        # Create sample order items
        order_items = [
            # Items for first order
            OrderItem(
                order_id=orders[0].id,
                product_name="蓝牙耳机",
                product_id="SKU001",
                quantity=1,
                price=299.99
            ),
            # Items for second order
            OrderItem(
                order_id=orders[1].id,
                product_name="智能手表",
                product_id="SKU002",
                quantity=1,
                price=399.99
            ),
            OrderItem(
                order_id=orders[1].id,
                product_name="保护套",
                product_id="SKU003",
                quantity=1,
                price=99.99
            ),
            OrderItem(
                order_id=orders[1].id,
                product_name="充电器",
                product_id="SKU004",
                quantity=1,
                price=100.01
            ),
            # Items for third order
            OrderItem(
                order_id=orders[2].id,
                product_name="智能手机",
                product_id="SKU005",
                quantity=1,
                price=1299.99
            )
        ]
        
        for item in order_items:
            session.add(item)
        
        session.commit()
        print("Sample data created successfully.")
        
    except Exception as e:
        session.rollback()
        print(f"Error creating sample data: {str(e)}")
    finally:
        session.close()

def main():
    """Run the customer service CLI."""
    parser = argparse.ArgumentParser(description='Customer Service CLI')
    parser.add_argument('--init-data', action='store_true', help='Initialize sample data')
    parser.add_argument('--phone', type=str, default='13800138000', help='Customer phone number')
    parser.add_argument('--name', type=str, default='张三', help='Customer name')
    
    args = parser.parse_args()
    
    # Initialize database
    try:
        init_db()
        print("Database initialized.")
        
        if args.init_data:
            create_sample_data()
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        return
    
    # Initialize customer service agent
    agent = CustomerServiceAgent()
    
    # Start conversation
    conversation = agent.start_conversation(args.phone, args.name)
    session_id = conversation['session_id']
    
    print("\n" + "=" * 60)
    print("Customer Service CLI")
    print("=" * 60)
    print(f"Session ID: {session_id}")
    print(f"Customer: {args.name} ({args.phone})")
    print("=" * 60)
    print(f"System: {conversation['greeting']}")
    print("=" * 60)
    print("Type 'exit' or 'quit' to end the conversation.")
    print("=" * 60 + "\n")
    
    # Main conversation loop
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            farewell = agent.end_conversation(session_id)
            print(f"System: {farewell}")
            break
        
        # Process message
        response = agent.process_message(session_id, user_input)
        print(f"System: {response}")
        print()

if __name__ == "__main__":
    main()