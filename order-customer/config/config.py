"""Configuration settings for the order-customer service system."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'username': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'root'),
    'database': os.getenv('DB_NAME', 'root'),
}

# Database connection string
DB_CONNECTION_STRING = f"mysql+pymysql://{DB_CONFIG['username']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# LLM configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL_NAME = os.getenv('OPENAI_MODEL_NAME', 'gpt-3.5-turbo')

# Application settings
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Customer service settings
DEFAULT_GREETING = "欢迎联系客服，我是您的订单助手。请问有什么可以帮助您？"
DEFAULT_WAITING_MESSAGE = "感谢您的耐心等待，我正在查询相关信息..."
DEFAULT_FAREWELL = "感谢您的咨询，祝您生活愉快！如有其他问题，随时联系我们。" 