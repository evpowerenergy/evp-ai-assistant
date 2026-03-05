"""
RAG Tools for Document Search
"""
from typing import List, Dict, Any
from app.services.vector_store import search_similar
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def search_documents(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search documents using RAG
    Returns relevant document chunks with citations
    """
    try:
        results = await search_similar(query, limit=limit)
        
        # Format results with citations
        formatted_results = []
        for result in results:
            formatted_results.append({
                "content": result.get("content", ""),
                "source": result.get("source", ""),
                "document_id": result.get("document_id", ""),
                "chunk_index": result.get("chunk_index", 0),
                "similarity": result.get("similarity", 0.0)
            })
        
        logger.info(f"RAG search: query={query[:50]}..., results={len(formatted_results)}")
        return formatted_results
    
    except Exception as e:
        logger.error(f"RAG search error: {e}")
        return []


def format_citations(results: List[Dict[str, Any]]) -> List[str]:
    """
    Format search results as citations
    """
    citations = []
    for i, result in enumerate(results, 1):
        source = result.get("source", "Unknown")
        citations.append(f"[{i}] {source}")
    
    return citations
