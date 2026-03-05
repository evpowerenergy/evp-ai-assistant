"""
LLM Service (OpenAI)
"""
from langchain_openai import ChatOpenAI
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global LLM instance
_llm: ChatOpenAI = None


def get_llm(temperature: float = 1.0, model: str = None) -> ChatOpenAI:
    """
    Get or create OpenAI LLM instance
    Uses model from settings if not provided
    Note: Some models (like gpt-4o-mini, gpt-5-mini) only support temperature=1.0 (default)
    """
    # Use default from settings if not provided
    if model is None:
        model = settings.OPENAI_MODEL
    
    # For mini models, force temperature=1.0 (they only support default)
    mini_models = ["gpt-4o-mini", "gpt-5-mini"]
    if model in mini_models and temperature != 1.0:
        logger.warning(f"{model} only supports temperature=1.0, using 1.0 instead of {temperature}")
        temperature = 1.0
    
    # Create new instance with specified temperature
    # (Don't cache globally since temperature may vary)
    try:
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=settings.OPENAI_API_KEY
        )
        logger.debug(f"LLM instance created: {model} (temperature={temperature})")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        raise
