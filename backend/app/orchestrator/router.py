"""
Intent Router
Determines which tool to use based on user query

NOTE: This is now a wrapper that uses LLM-based router
The actual LLM-based implementation is in llm_router.py
"""
from typing import Literal
from app.orchestrator.state import AIAssistantState
from app.utils.logger import get_logger

logger = get_logger(__name__)


def detect_intent(user_message: str) -> tuple[Literal["db_query", "rag_query", "clarify", "general"], float]:
    """
    Detect user intent from message (DEPRECATED - use LLM-based router instead)
    Returns: (intent, confidence)
    
    This function is kept for backward compatibility.
    Actual implementation should use analyze_intent_with_llm from llm_router.py
    """
    # This is a fallback - should not be used in production
    # LLM-based router should be used instead
    logger.warning("Using deprecated keyword-based intent detection. Use LLM-based router instead.")
    
    message_lower = user_message.lower()
    
    # Keywords for database queries
    db_keywords = [
        "สถานะ", "status", "ยอด", "จำนวน", "summary", "kpi",
        "ลูกค้า", "customer", "lead", "ลีด", "ทีม", "team", "sales",
        "วันนี้", "today", "สัปดาห์", "week", "เดือน", "month",
        "ข้อมูล", "data", "รายงาน", "report"
    ]
    
    # Keywords for document queries
    rag_keywords = [
        "ขั้นตอน", "procedure", "วิธี", "how", "sop", "เอกสาร",
        "document", "คู่มือ", "manual", "นโยบาย", "policy",
        "ทำอย่างไร", "how to", "guideline", "คำแนะนำ"
    ]
    
    # Check for database query intent
    db_score = sum(1 for keyword in db_keywords if keyword in message_lower)
    
    # Check for document query intent
    rag_score = sum(1 for keyword in rag_keywords if keyword in message_lower)
    
    # Determine intent
    if db_score > rag_score and db_score > 0:
        confidence = min(db_score / 3.0, 1.0)
        return ("db_query", confidence)
    
    elif rag_score > 0:
        confidence = min(rag_score / 3.0, 1.0)
        return ("rag_query", confidence)
    
    elif "?" in user_message or "อะไร" in message_lower or "what" in message_lower:
        return ("clarify", 0.5)
    
    else:
        # Default to RAG for general queries
        return ("rag_query", 0.3)
