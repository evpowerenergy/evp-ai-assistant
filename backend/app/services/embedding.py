"""
Text Embedding Service (OpenAI)
"""
from langchain_openai import OpenAIEmbeddings
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global embeddings instance
_embeddings = None


def get_embeddings() -> OpenAIEmbeddings:
    """
    Get or create OpenAI embeddings instance
    """
    global _embeddings
    
    if _embeddings is None:
        try:
            _embeddings = OpenAIEmbeddings(
                openai_api_key=settings.OPENAI_API_KEY,
                model="text-embedding-3-small"
            )
            logger.info("Embeddings service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise
    
    return _embeddings
