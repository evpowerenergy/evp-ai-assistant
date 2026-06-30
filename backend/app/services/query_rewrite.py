"""
Optional query rewrite for hybrid KB search.
"""
from __future__ import annotations

import re

from app.config import settings
from app.services.llm import get_llm
from app.utils.logger import get_logger

logger = get_logger(__name__)

_KB_COMPANY_VAGUE_MARKERS = (
    "บริษัทเรา",
    "บริษัททำ",
    "ทำอะไรบ้าง",
    "ทำธุรกิจอะไร",
    "เกี่ยวกับบริษัท",
    "บริษัทคือ",
    "ธุรกิจอะไร",
    "บริษัทเป็น",
    "เราทำอะไร",
    "ทำอะไร",
)


def expand_kb_company_query(user_message: str) -> str | None:
    """Rule-based expansion for vague company-profile questions."""
    text = (user_message or "").strip()
    if not text:
        return None
    lower = text.lower()
    if not any(marker in lower for marker in _KB_COMPANY_VAGUE_MARKERS):
        return None
    # Avoid expanding CRM-style live-data questions
    if re.search(r"(ลีด|ยอดขาย|นัด|kpi|qt\d|marketing|แอด)", lower):
        return None
    return (
        f"{text} EV POWER ENERGY ประเภทธุรกิจ พลังงานสะอาด "
        "Solar สถานีชาร์จ Super EV HUB Solvana ภาพรวมบริษัท วิสัยทัศน์ พันธกิจ"
    )


async def rewrite_query_for_search(user_message: str) -> str:
    """Expand informal Thai questions into search-friendly text."""
    expanded = expand_kb_company_query(user_message)
    if expanded:
        return expanded

    if not settings.KB_ENABLE_QUERY_REWRITE:
        return user_message

    prompt = f"""Rewrite this user question for document search (Thai/English keywords).
Keep it short (one line). Include key nouns and action words. Thai/English only.
Original: {user_message}
Rewritten:"""
    try:
        llm = get_llm(temperature=0)
        response = await llm.ainvoke(prompt)
        text = (response.content if hasattr(response, "content") else str(response)).strip()
        if text and len(text) > 3 and len(text) < 300:
            return text
    except Exception as e:
        logger.debug("Query rewrite skipped: %s", e)
    return user_message
