"""
Shared chat turn processing (web + LINE).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.core.audit import log_chat_request, log_tool_call
from app.orchestrator.graph import process_message
from app.orchestrator.state import AIAssistantState
from app.services.active_session import touch_session
from app.services.chat_mode import get_chat_mode, normalize_chat_mode
from app.services.chat_history import (
    format_history_for_llm,
    load_chat_history,
    save_message,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_chat_turn(
    user_id: str,
    user_role: str,
    message: str,
    session_id: str,
    source: str = "web",
    line_user_id: Optional[str] = None,
    chat_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run one AI chat turn: load history, process_message, save messages, audit.
    """
    chat_history = await load_chat_history(session_id, limit=20, exclude_current=False)
    history_context = (
        format_history_for_llm(chat_history, max_tokens=2000) if chat_history else ""
    )

    start_time = time.time()
    resolved_mode = (
        normalize_chat_mode(chat_mode) if chat_mode else await get_chat_mode(user_id)
    )
    initial_state: AIAssistantState = {
        "user_message": message,
        "user_id": user_id,
        "user_role": user_role,
        "session_id": session_id,
        "chat_mode": resolved_mode,
        "chat_history": chat_history,
        "history_context": history_context,
        "intent": None,
        "confidence": 0.0,
        "tool_calls": [],
        "tool_results": [],
        "rag_results": [],
        "citations": [],
        "rag_retrieval_meta": None,
        "retry_count": 0,
        "max_retries": 0,
        "previous_attempts": [],
        "data_quality": None,
        "quality_reason": None,
        "suggested_retry_params": None,
        "alternative_queries": [],
        "response": None,
        "error": None,
    }

    result_state = await process_message(initial_state)
    runtime = time.time() - start_time

    user_meta: Dict[str, Any] = {"source": source, "chat_mode": resolved_mode}
    if line_user_id:
        user_meta["line_user_id"] = line_user_id

    await save_message(
        session_id=session_id,
        role="user",
        content=message,
        metadata=user_meta,
    )
    await save_message(
        session_id=session_id,
        role="assistant",
        content=result_state.get("response", ""),
        metadata={
            "source": source,
            "chat_mode": resolved_mode,
            "intent": result_state.get("intent"),
            "citations": result_state.get("citations", []),
            "tool_calls": result_state.get("tool_calls", []),
            "rag": result_state.get("rag_retrieval_meta"),
        },
    )
    await touch_session(session_id)

    for tool_call in result_state.get("tool_calls", []):
        await log_tool_call(
            user_id=user_id,
            tool_name=tool_call.get("tool", "unknown"),
            tool_input=tool_call.get("input", {}),
            tool_output=tool_call.get("output", {}),
        )

    await log_chat_request(
        user_id=user_id,
        session_id=session_id,
        message=message,
        response=result_state.get("response"),
        tool_calls=result_state.get("tool_calls"),
    )

    return {
        "response": result_state.get("response", "ขออภัยครับ ไม่สามารถสร้างคำตอบได้"),
        "session_id": session_id,
        "citations": result_state.get("citations"),
        "tool_calls": result_state.get("tool_calls"),
        "tool_results": result_state.get("tool_results", []),
        "intent": result_state.get("intent"),
        "chat_mode": resolved_mode,
        "runtime": runtime,
        "debug_precompute": result_state.get("debug_precompute"),
    }
