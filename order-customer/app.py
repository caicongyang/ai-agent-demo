"""Flask API for the order customer service system."""

from flask import Flask, request, jsonify
import os
import logging
from datetime import datetime

from order_customer.models.customer_service import CustomerServiceAgent
from order_customer.database.models import init_db
from order_customer.config.config import DEBUG, LOG_LEVEL

# Set up logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the app
app = Flask(__name__)
app.debug = DEBUG

# Initialize the database
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Error initializing database: {e}")

# Initialize the customer service agent
customer_service_agent = CustomerServiceAgent()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/conversation/start', methods=['POST'])
def start_conversation():
    """Start a new conversation."""
    try:
        data = request.json
        phone = data.get('phone')
        name = data.get('name')
        
        if not phone:
            return jsonify({
                "success": False,
                "error": "Phone number is required"
            }), 400
        
        result = customer_service_agent.start_conversation(phone, name)
        return jsonify({
            "success": True,
            "data": result
        })
    
    except Exception as e:
        logger.error(f"Error starting conversation: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@app.route('/api/conversation/message', methods=['POST'])
def process_message():
    """Process a customer message."""
    try:
        data = request.json
        session_id = data.get('session_id')
        message = data.get('message')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "Session ID is required"
            }), 400
            
        if not message:
            return jsonify({
                "success": False,
                "error": "Message is required"
            }), 400
        
        response = customer_service_agent.process_message(session_id, message)
        return jsonify({
            "success": True,
            "data": {
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@app.route('/api/conversation/end', methods=['POST'])
def end_conversation():
    """End a conversation."""
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "Session ID is required"
            }), 400
        
        farewell = customer_service_agent.end_conversation(session_id)
        return jsonify({
            "success": True,
            "data": {
                "farewell": farewell,
                "timestamp": datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f"Error ending conversation: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@app.route('/api/conversation/history', methods=['GET'])
def get_conversation_history():
    """Get conversation history."""
    try:
        session_id = request.args.get('session_id')
        limit = request.args.get('limit', default=10, type=int)
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "Session ID is required"
            }), 400
        
        from order_customer.database.conversation_service import ConversationService
        history = ConversationService.get_conversation_history(session_id, limit)
        
        return jsonify({
            "success": True,
            "data": {
                "history": history,
                "count": len(history)
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)