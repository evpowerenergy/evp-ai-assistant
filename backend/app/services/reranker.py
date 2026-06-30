"""
LLM-based reranking for RAG retrieval candidates.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from app.config import settings
from app.services.llm import get_llm
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def rerank_chunks(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int | None = None,
) -> List[Dict[str, Any]]:
    """Score and reorder candidate chunks using a lightweight LLM call."""
    if not candidates:
        return []
    if not settings.KB_ENABLE_RERANK:
        return candidates[: top_k or settings.KB_RERANK_TOP_K]

    top_k = top_k or settings.KB_RERANK_TOP_K
    limited = candidates[: settings.KB_RETRIEVE_CANDIDATES]

    numbered = []
    for i, c in enumerate(limited, 1):
        content = (c.get("content") or "")[:800]
        title = c.get("source") or c.get("metadata", {}).get("title", "")
        numbered.append(f"[{i}] (source: {title})\n{content}")

    prompt = f"""You are a relevance scorer for a document search system.
User question: {query}

Rank these text chunks by relevance to the question (10=highly relevant, 0=irrelevant).
Return ONLY valid JSON array: [{{"id": 1, "score": 9}}, ...] for each chunk id.

Chunks:
{chr(10).join(numbered)}
"""
    try:
        llm = get_llm(temperature=0)
        response = await llm.ainvoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return limited[:top_k]
        scores = json.loads(match.group())
        score_map = {int(s["id"]): float(s.get("score", 0)) for s in scores if "id" in s}
        for i, c in enumerate(limited, 1):
            c["rerank_score"] = score_map.get(i, 0)
        ranked = sorted(limited, key=lambda x: x.get("rerank_score", 0), reverse=True)
        return ranked[:top_k]
    except Exception as e:
        logger.warning("Rerank failed, using fusion order: %s", e)
        return limited[:top_k]
