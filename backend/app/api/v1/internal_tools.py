from __future__ import annotations

from typing import Any, Dict
import hashlib
import json
import time

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.execution_auth import require_execution_scope, verify_execution_token
from app.tools.registry import TOOL_REGISTRY
from app.services.agent_audit import log_internal_tool_execution

router = APIRouter()


class ToolExecutionRequest(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict)


@router.post("/internal/tools/{tool_name}:execute", include_in_schema=False)
async def execute_internal_tool(
    tool_name: str,
    body: ToolExecutionRequest,
    x_evp_execution_token: str = Header(default=""),
):
    actor = verify_execution_token(x_evp_execution_token)
    spec = TOOL_REGISTRY.get(tool_name)
    if not spec:
        raise HTTPException(status_code=404, detail="Unknown tool")
    require_execution_scope(actor, spec.scope)
    started = time.monotonic()
    argument_hash = hashlib.sha256(
        json.dumps(body.arguments, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    tool_call_id = f"{tool_name}:{argument_hash}"
    try:
        output = await spec.handler(dict(body.arguments), actor)
    except Exception as exc:
        await log_internal_tool_execution(
            request_id=actor["request_id"],
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            risk=spec.risk,
            scope=spec.scope,
            arguments=body.arguments,
            output=None,
            duration_ms=int((time.monotonic() - started) * 1000),
            status="failed",
            error_class=type(exc).__name__,
            failure_code="tool_exception",
        )
        raise
    await log_internal_tool_execution(
        request_id=actor["request_id"],
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        risk=spec.risk,
        scope=spec.scope,
        arguments=body.arguments,
        output=output,
        duration_ms=int((time.monotonic() - started) * 1000),
    )
    return {
        "success": True,
        "tool": spec.name,
        "risk": spec.risk,
        "request_id": actor["request_id"],
        "output": output,
    }
