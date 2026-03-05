"""
LangGraph State Definition
"""
from typing import TypedDict, List, Optional, Dict, Any


class AIAssistantState(TypedDict, total=False):
    """
    State for AI Assistant workflow
    Note: total=False makes all fields optional for LangGraph compatibility
    """
    # User input
    user_message: str
    user_id: str
    user_role: Optional[str]  # User role from JWT token (optional)
    session_id: Optional[str]
    
    # Chat history (NEW)
    chat_history: Optional[List[Dict[str, Any]]]  # Raw chat history from database
    history_context: Optional[str]  # Formatted history context for LLM
    
    # Intent detection
    intent: Optional[str]  # "db_query", "rag_query", "clarify", "general"
    confidence: float
    entities: Optional[Dict[str, Any]]  # Extracted entities from message
    selected_tools: List[Dict[str, Any]]  # Tools selected by LLM
    tool_parameters: Optional[Dict[str, Dict[str, Any]]]  # Parameters for each tool
    
    # Tool calls
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    
    # RAG results
    rag_results: List[Dict[str, Any]]
    citations: List[str]
    
    # Retry management (NEW)
    retry_count: int  # Number of retry attempts
    max_retries: int  # Maximum retry attempts (default: 2)
    previous_attempts: List[Dict[str, Any]]  # History of previous attempts
    
    # Data quality (NEW)
    data_quality: Optional[str]  # "sufficient", "insufficient", "empty", "error"
    quality_reason: Optional[str]  # Reason for quality assessment
    
    # Retry suggestions (NEW)
    suggested_retry_params: Optional[Dict[str, Any]]  # Suggested parameters for retry
    alternative_queries: List[str]  # Alternative queries to try
    
    # Tool selection verification (NEW)
    verification_status: Optional[str]  # "APPROVED", "REJECTED", "NEEDS_ADJUSTMENT"
    verification_reason: Optional[str]  # Reason for verification result
    verification_suggested_changes: Optional[Dict[str, Any]]  # Suggested tool/parameter changes
    verification_retry_count: int  # Number of verification retry attempts
    max_verification_retries: int  # Maximum verification retry attempts (default: 2)
    
    # Tool execution verification (NEW - Phase 2)
    execution_verification_status: Optional[str]  # "APPROVED", "WRONG_TOOL", "NEEDS_MORE_TOOLS"
    execution_verification_reason: Optional[str]  # Reason for execution verification result
    execution_verification_suggested_changes: Optional[Dict[str, Any]]  # Suggested tool/parameter changes
    execution_verification_retry_count: int  # Number of execution verification retry attempts
    max_execution_verification_retries: int  # Maximum execution verification retry attempts (default: 2)
    
    # Final response
    response: Optional[str]
    error: Optional[str]

    # Debug: pre-computed summaries (e.g. get_sales_closed category/platform/per_month) for UI
    debug_precompute: Optional[Dict[str, Any]]
