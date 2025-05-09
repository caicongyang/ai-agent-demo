"""Base language model configuration for the customer service system."""

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from typing import Optional

from order_customer.config.config import OPENAI_API_KEY, OPENAI_MODEL_NAME

def get_llm(model_name: Optional[str] = None, temperature: float = 0.7) -> BaseChatModel:
    """Get a language model instance."""
    
    # Use the configured model name if none provided
    model_name = model_name or OPENAI_MODEL_NAME
    
    # Initialize the ChatOpenAI model
    llm = ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model_name=model_name,
        temperature=temperature
    )
    
    return llm 