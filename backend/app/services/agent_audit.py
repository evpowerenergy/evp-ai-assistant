from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger
from app.utils.pii_masker import redact_pii

logger = get_logger(__name__)
_sequence_lock = asyncio.Lock()
_sequences: Dict[str, int] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _next_sequence(run_id: str) -> int:
    async with _sequence_lock:
        value = _sequences.get(run_id, 0) + 1
        _sequences[run_id] = value
        return value


async def emit_agent_event(
    *, run_id: Optional[str], request_id: str, event_type: str,
    event_name: str, status: str, actor_type: Optional[str] = None,
    actor_id: Optional[str] = None, parent_actor_id: Optional[str] = None,
    duration_ms: Optional[int] = None, model: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Best-effort append-only event; never fail the user request."""
    if not run_id:
        return
    try:
        occurred_at = _now()
        get_supabase_client().table("ai_agent_events").insert({
            "run_id": run_id,
            "request_id": request_id,
            "sequence_no": await _next_sequence(run_id),
            "event_type": event_type,
            "event_name": event_name,
            "status": status,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "parent_actor_id": parent_actor_id,
            "duration_ms": duration_ms,
            "model": model,
            "metadata": redact_pii(metadata or {}),
            "occurred_at": occurred_at,
        }).execute()
        get_supabase_client().table("ai_agent_runs").update({
            "last_event_at": occurred_at,
        }).eq("id", run_id).execute()
    except Exception as exc:
        logger.debug("Agent event audit unavailable: %s", exc)


async def start_agent_run(
    *, request_id: str, trace_id: str, session_id: str, user_id: str,
    source: str, primary_engine: str, request_type: str, input_chars: int,
    timeout_seconds: int,
) -> Optional[str]:
    try:
        result = get_supabase_client().table("ai_agent_runs").insert({
            "request_id": request_id,
            "trace_id": trace_id,
            "session_id": session_id,
            "user_id": user_id,
            "source": source if source in {"web", "line", "system", "test"} else "system",
            "primary_engine": primary_engine,
            "status": "started",
            "primary_status": "running",
            "request_type": request_type,
            "input_chars": input_chars,
            "timeout_seconds": timeout_seconds,
            "last_event_at": _now(),
        }).execute()
        run_id = result.data[0].get("id") if result.data else None
        await emit_agent_event(
            run_id=run_id, request_id=request_id, event_type="run",
            event_name="run.started", status="started",
            actor_type="gateway", actor_id="fastapi",
            metadata={"source": source, "request_type": request_type},
        )
        return run_id
    except Exception as exc:
        # Deploying code before the migration is intentionally safe.
        logger.debug("Agent run start audit unavailable: %s", exc)
        return None


async def complete_agent_run(
    run_id: Optional[str], *, engine: str, model: Optional[str], fallback_used: bool,
    usage: Dict[str, Any], runtime: float, request_id: str,
    output_chars: int, fallback_reason: Optional[str] = None,
    runtime_logs: Optional[list] = None,
) -> None:
    if not run_id:
        return
    try:
        get_supabase_client().table("ai_agent_runs").update({
            "actual_engine": engine,
            "model": model,
            "status": "completed",
            "fallback_used": fallback_used,
            "fallback_engine": engine if fallback_used else None,
            "fallback_status": "completed" if fallback_used else None,
            "fallback_reason": fallback_reason,
            "primary_status": "timed_out" if fallback_used and "Timeout" in (fallback_reason or "") else "completed",
            "response_source": engine,
            "output_chars": output_chars,
            "total_tool_calls": sum(1 for event in (runtime_logs or []) if event.get("type") == "tool"),
            "total_skill_calls": sum(1 for event in (runtime_logs or []) if event.get("type") == "skill"),
            "total_model_calls": sum(
                int(str(event.get("api_calls") or "0/0").split("/", 1)[0])
                for event in (runtime_logs or [])
                if event.get("type") == "summary"
            ),
            "usage": usage,
            "timings": {"total_seconds": runtime},
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_id).execute()
        await emit_agent_event(
            run_id=run_id, request_id=request_id, event_type="run",
            event_name="run.completed", status="completed",
            actor_type="engine", actor_id=engine, model=model,
            duration_ms=int(runtime * 1000),
            metadata={"fallback_used": fallback_used},
        )
    except Exception as exc:
        logger.debug("Agent run completion audit unavailable: %s", exc)


async def fail_agent_run(
    run_id: Optional[str], *, request_id: str, error: Exception, runtime: float
) -> None:
    if not run_id:
        return
    try:
        get_supabase_client().table("ai_agent_runs").update({
            "status": "failed",
            "primary_status": "failed",
            "error_class": type(error).__name__,
            "timings": {"total_seconds": runtime},
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_id).execute()
        await emit_agent_event(
            run_id=run_id, request_id=request_id, event_type="run",
            event_name="run.failed", status="failed",
            duration_ms=int(runtime * 1000),
            metadata={"error_class": type(error).__name__},
        )
    except Exception as exc:
        logger.debug("Agent run failure audit unavailable: %s", exc)


async def log_internal_tool_execution(
    *, request_id: str, tool_call_id: str, tool_name: str, risk: str,
    arguments: Dict[str, Any], output: Any, duration_ms: int,
    status: str = "completed", error_class: Optional[str] = None,
    failure_code: Optional[str] = None, scope: Optional[str] = None,
) -> None:
    """Best-effort MCP audit; never store full business result payloads."""
    try:
        supabase = get_supabase_client()
        run = (
            supabase.table("ai_agent_runs")
            .select("id")
            .eq("request_id", request_id)
            .limit(1)
            .execute()
        )
        run_id = run.data[0].get("id") if run.data else None
        summary = {
            "type": type(output).__name__,
            "success": output.get("success") if isinstance(output, dict) else status == "completed",
        }
        supabase.table("ai_tool_executions").upsert({
            "run_id": run_id,
            "request_id": request_id,
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "risk_level": risk,
            "status": status,
            "scope": scope,
            "input_data": redact_pii(arguments),
            "output_data": summary,
            "duration_ms": duration_ms,
            "failure_code": failure_code,
            "error_class": error_class,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="request_id,tool_call_id").execute()
        await emit_agent_event(
            run_id=run_id, request_id=request_id, event_type="mcp",
            event_name=f"mcp.{tool_name}",
            status="completed" if status == "completed" else "failed",
            actor_type="gateway", actor_id="evp-mcp",
            duration_ms=duration_ms,
            metadata={"risk": risk, "scope": scope, "failure_code": failure_code},
        )
    except Exception as exc:
        logger.debug("Internal tool audit unavailable: %s", exc)
