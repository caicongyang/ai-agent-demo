"""Order database service for handling order-related operations."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union

from order_customer.database.models import get_db_session, Order, OrderItem, Customer, OrderStatus

class OrderService:
    """Service for order-related database operations."""
    
    @staticmethod
    def get_order_by_number(order_number: str) -> Optional[Dict[str, Any]]:
        """Get order details by order number."""
        session = get_db_session()
        try:
            order = session.query(Order).filter(Order.order_number == order_number).first()
            if not order:
                return None
                
            # Get customer and items
            customer = order.customer
            items = order.order_items
            
            # Format order details
            order_details = {
                'order_id': order.id,
                'order_number': order.order_number,
                'customer_name': customer.name,
                'customer_phone': customer.phone,
                'status': order.status,
                'total_amount': order.total_amount,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'items': [
                    {
                        'name': item.product_name,
                        'quantity': item.quantity,
                        'price': item.price
                    } for item in items
                ]
            }
            
            # Add shipping details if available
            if order.shipped_at:
                order_details['shipped_at'] = order.shipped_at.strftime('%Y-%m-%d %H:%M:%S')
            if order.expected_delivery_at:
                order_details['expected_delivery_at'] = order.expected_delivery_at.strftime('%Y-%m-%d %H:%M:%S')
                order_details['days_to_delivery'] = order.days_to_delivery
            if order.tracking_number:
                order_details['tracking_number'] = order.tracking_number
            if order.shipping_company:
                order_details['shipping_company'] = order.shipping_company
                
            return order_details
            
        finally:
            session.close()
    
    @staticmethod
    def get_orders_by_customer_phone(phone: str) -> List[Dict[str, Any]]:
        """Get all orders for a customer by phone number."""
        session = get_db_session()
        try:
            customer = session.query(Customer).filter(Customer.phone == phone).first()
            if not customer:
                return []
                
            orders = session.query(Order).filter(Order.customer_id == customer.id).all()
            
            result = []
            for order in orders:
                order_details = {
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'status': order.status,
                    'total_amount': order.total_amount,
                    'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Add shipping details if available
                if order.shipped_at:
                    order_details['shipped_at'] = order.shipped_at.strftime('%Y-%m-%d %H:%M:%S')
                if order.expected_delivery_at:
                    order_details['expected_delivery_at'] = order.expected_delivery_at.strftime('%Y-%m-%d %H:%M:%S')
                    order_details['days_to_delivery'] = order.days_to_delivery
                    
                result.append(order_details)
                
            return result
            
        finally:
            session.close()
    
    @staticmethod
    def get_tracking_info(order_number: str) -> Optional[Dict[str, Any]]:
        """Get tracking information for an order."""
        session = get_db_session()
        try:
            order = session.query(Order).filter(Order.order_number == order_number).first()
            if not order or not order.tracking_number:
                return None
                
            tracking_info = {
                'order_number': order.order_number,
                'tracking_number': order.tracking_number,
                'shipping_company': order.shipping_company,
                'status': order.status,
                'shipped_at': order.shipped_at.strftime('%Y-%m-%d %H:%M:%S') if order.shipped_at else None,
                'expected_delivery_at': order.expected_delivery_at.strftime('%Y-%m-%d %H:%M:%S') if order.expected_delivery_at else None,
                'days_to_delivery': order.days_to_delivery
            }
            
            return tracking_info
            
        finally:
            session.close()
    
    @staticmethod
    def update_order_status(order_number: str, status: str) -> bool:
        """Update order status."""
        session = get_db_session()
        try:
            order = session.query(Order).filter(Order.order_number == order_number).first()
            if not order:
                return False
                
            order.status = status
            
            # Update status-related timestamps
            if status == OrderStatus.SHIPPED.value and not order.shipped_at:
                order.shipped_at = datetime.now()
            elif status == OrderStatus.DELIVERED.value and not order.delivered_at:
                order.delivered_at = datetime.now()
                
            session.commit()
            return True
            
        except Exception:
            session.rollback()
            return False
            
        finally:
            session.close()

    @staticmethod
    def search_orders(query: str) -> List[Dict[str, Any]]:
        """Search orders by order number, customer name, or phone."""
        session = get_db_session()
        try:
            # Search by order number
            orders = session.query(Order).filter(Order.order_number.like(f'%{query}%')).all()
            
            # Search by customer name or phone
            customers = session.query(Customer).filter(
                (Customer.name.like(f'%{query}%')) | (Customer.phone.like(f'%{query}%'))
            ).all()
            
            customer_ids = [c.id for c in customers]
            if customer_ids:
                customer_orders = session.query(Order).filter(Order.customer_id.in_(customer_ids)).all()
                # Combine results, removing duplicates
                orders = list(set(orders + customer_orders))
            
            result = []
            for order in orders:
                order_details = {
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'customer_name': order.customer.name,
                    'customer_phone': order.customer.phone,
                    'status': order.status,
                    'total_amount': order.total_amount,
                    'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                result.append(order_details)
                
            return result
            
        finally:
            session.close() 