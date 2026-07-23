"""
Shared chat turn processing (web + LINE).
"""
from __future__ import annotations

import time
from uuid import uuid4
from typing import Any, Dict, Optional

from app.core.audit import log_chat_request, log_tool_call
from app.engines.service import get_agent_service
from app.engines.base import ActorContext, AgentRequest
from app.services.active_session import assert_session_owner, touch_session
from app.services.agent_audit import (
    complete_agent_run, emit_agent_event, fail_agent_run, start_agent_run,
)
from app.config import settings
from app.services.chat_mode import get_chat_mode, normalize_chat_mode
from app.services.chat_history import (
    format_history_for_llm,
    load_chat_history,
    save_message,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def classify_request_type(message: str, chat_mode: str) -> str:
    normalized = (message or "").lower()
    research_terms = ("google map", "google maps", "รีวิว", "ค้นเว็บ", "เว็บไซต์", "คู่แข่ง")
    if any(term in normalized for term in research_terms):
        return "web_research"
    return "knowledge" if chat_mode == "kb" else "crm"


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
    await assert_session_owner(user_id, session_id)
    chat_history = await load_chat_history(session_id, limit=20, exclude_current=False)
    history_context = (
        format_history_for_llm(chat_history, max_tokens=2000) if chat_history else ""
    )

    start_time = time.time()
    resolved_mode = (
        normalize_chat_mode(chat_mode) if chat_mode else await get_chat_mode(user_id)
    )
    request_id = str(uuid4())
    trace_id = str(uuid4())
    request_type = classify_request_type(message, resolved_mode)
    run_id = await start_agent_run(
        request_id=request_id,
        trace_id=trace_id,
        session_id=session_id,
        user_id=user_id,
        source=source,
        primary_engine=settings.AI_PRIMARY_ENGINE,
        request_type=request_type,
        input_chars=len(message),
        timeout_seconds=int(settings.HERMES_TURN_TIMEOUT_SECONDS),
    )
    try:
        result = await get_agent_service().run(
            AgentRequest(
                message=message,
                history=chat_history,
                history_context=history_context,
                chat_mode=resolved_mode,
                request_type=request_type,
            ),
            ActorContext(
                user_id=user_id,
                user_role=user_role,
                session_id=session_id,
                source=source,
                request_id=request_id,
                run_id=run_id,
                trace_id=trace_id,
                line_user_id=line_user_id,
            ),
        )
    except Exception as exc:
        await fail_agent_run(
            run_id, request_id=request_id, error=exc,
            runtime=time.time() - start_time,
        )
        raise
    runtime = time.time() - start_time
    runtime_logs = result.metadata.get("runtime_logs", [])
    for event in runtime_logs:
        event_type = event.get("type") if event.get("type") in {"tool", "skill", "model", "subagent"} else "engine"
        await emit_agent_event(
            run_id=run_id,
            request_id=request_id,
            event_type=event_type,
            event_name=str(event.get("name") or "runtime.event"),
            status="failed" if event.get("status") == "error" else "completed",
            actor_type="engine",
            actor_id="hermes",
            duration_ms=int(float(event.get("duration") or 0) * 1000),
            model=event.get("model"),
            metadata={
                "api_calls": event.get("api_calls"),
                "tool_turns": event.get("tool_turns"),
            },
        )
    await complete_agent_run(
        run_id,
        engine=result.engine,
        model=result.model,
        fallback_used=result.fallback_used,
        usage=result.usage,
        runtime=runtime,
        request_id=request_id,
        output_chars=len(result.response),
        fallback_reason=result.metadata.get("fallback_reason"),
        runtime_logs=runtime_logs,
    )

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
        content=result.response,
        metadata={
            "source": source,
            "chat_mode": resolved_mode,
            "request_id": request_id,
            "engine": result.engine,
            "model": result.model,
            "fallback_used": result.fallback_used,
            "intent": result.intent,
            "citations": result.citations,
            "tool_calls": result.tool_calls,
            "rag": result.metadata.get("rag_retrieval_meta"),
        },
    )
    await emit_agent_event(
        run_id=run_id,
        request_id=request_id,
        event_type="response",
        event_name="response.delivered",
        status="completed",
        actor_type="gateway",
        actor_id="fastapi",
        model=result.model,
        metadata={"response_source": result.engine},
    )
    await touch_session(session_id)

    for tool_call in result.tool_calls:
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
        response=result.response,
        tool_calls=result.tool_calls,
    )

    return {
        "response": result.response,
        "session_id": session_id,
        "citations": result.citations,
        "tool_calls": result.tool_calls,
        "tool_results": result.tool_results,
        "intent": result.intent,
        "chat_mode": result.metadata.get("chat_mode", resolved_mode),
        "engine": result.engine,
        "model": result.model,
        "fallback_used": result.fallback_used,
        "usage": result.usage,
        "request_id": request_id,
        "runtime": runtime,
        "debug_precompute": result.metadata.get("debug_precompute"),
        "runtime_logs": result.metadata.get("runtime_logs", []),
    }
