"""
RAG Query Node
Searches documents using vector similarity
"""
from typing import Dict, Any
from app.orchestrator.state import AIAssistantState
from app.tools.rag_tools import search_documents, format_citations
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def rag_query_node(state: AIAssistantState) -> AIAssistantState:
    """
    Node that searches documents using RAG
    """
    try:
        user_message = state.get("user_message", "")
        
        logger.info(f"RAG Query Node: processing message")
        
        # Search documents
        rag_results = await search_documents(user_message, limit=5)
        
        # Format citations
        citations = format_citations(rag_results) if rag_results else []
        
        # Update state
        state["rag_results"] = rag_results
        state["citations"] = citations
        
        logger.info(f"RAG Query Node: found {len(rag_results)} relevant documents")
        
        return state
    
    except Exception as e:
        logger.error(f"RAG Query Node error: {e}")
        state["error"] = str(e)
        return state
