from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import require_role
from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
admin_only = require_role(["super_admin"])


@router.get("/admin/agent-runs")
async def list_agent_runs(
    status: Optional[str] = None,
    engine: Optional[str] = None,
    fallback_used: Optional[bool] = None,
    request_type: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: dict = Depends(admin_only),
):
    """List sanitized run-level audit metadata for administrators."""
    try:
        query = (
            get_supabase_client().table("ai_agent_runs")
            .select(
                "id,request_id,trace_id,session_id,user_id,source,request_type,"
                "primary_engine,primary_status,actual_engine,model,status,"
                "fallback_used,fallback_engine,fallback_status,fallback_reason,"
                "response_source,timeout_seconds,timings,usage,input_chars,"
                "output_chars,total_tool_calls,total_skill_calls,total_model_calls,"
                "estimated_cost_usd,error_class,created_at,completed_at,last_event_at"
            )
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if status:
            query = query.eq("primary_status", status)
        if engine:
            query = query.eq("primary_engine", engine)
        if fallback_used is not None:
            query = query.eq("fallback_used", fallback_used)
        if request_type:
            query = query.eq("request_type", request_type)
        result = query.execute()
        return {"runs": result.data or [], "limit": limit, "offset": offset}
    except Exception as exc:
        logger.warning("Agent audit list unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="Agent audit storage is unavailable") from exc

@router.get("/admin/agent-runs/{run_id}")
async def get_agent_run(
    run_id: str,
    _current_user: dict = Depends(admin_only),
):
    """Return a correlated run, timeline, tool attempts, and artifacts."""
    try:
        supabase = get_supabase_client()
        run_result = (
            supabase.table("ai_agent_runs").select("*").eq("id", run_id).limit(1).execute()
        )
        if not run_result.data:
            raise HTTPException(status_code=404, detail="Agent run not found")
        events = (
            supabase.table("ai_agent_events").select("*")
            .eq("run_id", run_id).order("sequence_no").execute()
        )
        tools = (
            supabase.table("ai_tool_executions")
            .select(
                "id,run_id,request_id,tool_call_id,tool_name,risk_level,status,"
                "duration_ms,scope,http_status,failure_code,error_class,attempt,"
                "provider,created_at,started_at,completed_at,output_data"
            )
            .eq("run_id", run_id).order("created_at").execute()
        )
        artifacts = (
            supabase.table("ai_agent_artifacts").select("*")
            .eq("run_id", run_id).order("created_at").execute()
        )
        return {
            "run": run_result.data[0],
            "events": events.data or [],
            "tools": tools.data or [],
            "artifacts": artifacts.data or [],
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Agent audit detail unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="Agent audit storage is unavailable") from exc
