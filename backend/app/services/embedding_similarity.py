"""
Embedding Similarity Service
Uses OpenAI text-embedding-3-small for semantic similarity
"""
from openai import AsyncOpenAI
from app.config import settings
from app.utils.logger import get_logger
import math

logger = get_logger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def get_embedding(text: str) -> list[float]:
    """Get embedding for text using OpenAI API"""
    if not text or not text.strip():
        return []
    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text.strip()
        )
        return resp.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return []


async def compute_similarity(text_a: str, text_b: str) -> float:
    """
    Compute semantic similarity between two texts (0.0 - 1.0).
    Returns 0.0 on error or empty input.
    """
    if not text_a or not text_b:
        return 0.0
    emb_a = await get_embedding(text_a)
    emb_b = await get_embedding(text_b)
    if not emb_a or not emb_b:
        return 0.0
    sim = cosine_similarity(emb_a, emb_b)
    return round(max(0.0, min(1.0, sim)), 4)
