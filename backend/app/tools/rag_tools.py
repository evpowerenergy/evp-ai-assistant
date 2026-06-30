"""
RAG Tools for Document Search
"""
from typing import Any, Dict, List, Tuple

from app.services.vector_store import search_similar
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def search_documents(
    query: str,
    limit: int = 5,
    category_filter: str | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Search documents using hybrid retrieval + rerank.
    Returns (formatted_results, retrieval_meta).
    """
    try:
        results, meta = await search_similar(
            query,
            limit=limit,
            category_filter=category_filter,
        )

        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "content": result.get("content", ""),
                    "source": result.get("source", ""),
                    "document_id": result.get("document_id", ""),
                    "chunk_index": result.get("chunk_index", 0),
                    "similarity": result.get("similarity", 0.0),
                    "rerank_score": result.get("rerank_score"),
                    "metadata": result.get("metadata", {}),
                }
            )

        logger.info("RAG search: query=%s..., results=%s", query[:50], len(formatted_results))
        return formatted_results, meta

    except Exception as e:
        logger.error("RAG search error: %s", e)
        return [], {"error": str(e)}


def format_citations(results: List[Dict[str, Any]]) -> List[str]:
    """Format search results as citations."""
    citations = []
    for i, result in enumerate(results, 1):
        source = result.get("source", "Unknown")
        meta = result.get("metadata") or {}
        page = meta.get("page_number")
        suffix = f" หน้า {page}" if page else ""
        citations.append(f"[{i}] {source}{suffix}")
    return citations
