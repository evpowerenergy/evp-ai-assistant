"""
RAG Query Node — hybrid search with observability metadata.
"""
from typing import Dict, Any
from app.orchestrator.state import AIAssistantState
from app.tools.rag_tools import search_documents, format_citations
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def rag_query_node(state: AIAssistantState) -> AIAssistantState:
    """Search documents using production RAG pipeline."""
    try:
        user_message = state.get("user_message", "")

        logger.info("RAG Query Node: processing message")

        rag_results, retrieval_meta = await search_documents(user_message, limit=5)
        citations = format_citations(rag_results) if rag_results else []

        state["rag_results"] = rag_results
        state["citations"] = citations
        state["rag_retrieval_meta"] = retrieval_meta

        logger.info(
            "RAG Query Node: found %s relevant documents (ms=%s)",
            len(rag_results),
            retrieval_meta.get("retrieval_ms"),
        )

        return state

    except Exception as e:
        logger.error(f"RAG Query Node error: {e}")
        state["error"] = str(e)
        state["rag_retrieval_meta"] = {"error": str(e)}
        return state
