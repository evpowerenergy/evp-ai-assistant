"""
Optional query rewrite for hybrid KB search.
"""
from __future__ import annotations

from app.config import settings
from app.services.llm import get_llm
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def rewrite_query_for_search(user_message: str) -> str:
    """Expand informal Thai questions into search-friendly text."""
    if not settings.KB_ENABLE_QUERY_REWRITE:
        return user_message

    prompt = f"""Rewrite this user question for document search (Thai/English keywords).
Keep it short (one line). Include key nouns and action words.
Original: {user_message}
Rewritten:"""
    try:
        llm = get_llm(temperature=0)
        response = await llm.ainvoke(prompt)
        text = (response.content if hasattr(response, "content") else str(response)).strip()
        if text and len(text) > 3:
            return text
    except Exception as e:
        logger.debug("Query rewrite skipped: %s", e)
    return user_message
