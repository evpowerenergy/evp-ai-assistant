"""
Audit Logging
"""
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
from app.utils.logger import get_logger
from app.utils.pii_masker import redact_pii
from app.services.supabase import get_supabase_client

logger = get_logger(__name__)


async def log_audit(
    user_id: str,
    action: str,
    resource: str,
    request_data: Optional[Dict[str, Any]] = None,
    response_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log audit event to database
    All PII is redacted before logging
    """
    try:
        supabase = get_supabase_client()
        
        # Redact PII from request and response
        redacted_request = redact_pii(request_data) if request_data else None
        redacted_response = redact_pii(response_data) if response_data else None
        
        audit_log = {
            "id": str(uuid4()),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "request_data": redacted_request,
            "response_data": redacted_response,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Insert into audit_logs table
        try:
            result = supabase.table("audit_logs").insert(audit_log).execute()
            logger.debug(f"Audit logged: {action} on {resource} by {user_id}")
        except Exception as db_error:
            # Log to console if DB insert fails
            logger.warning(f"Failed to insert audit log to DB: {db_error}")
            logger.info(f"Audit: {action} on {resource} by {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")


async def log_chat_request(
    user_id: str,
    session_id: str,
    message: str,
    response: Optional[str] = None,
    tool_calls: Optional[list] = None
) -> None:
    """Log chat request/response"""
    await log_audit(
        user_id=user_id,
        action="chat_request",
        resource="chat",
        request_data={"session_id": session_id, "message": message},
        response_data={"response": response, "tool_calls": tool_calls} if response else None
    )


async def log_tool_call(
    user_id: str,
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_output: Optional[Dict[str, Any]] = None
) -> None:
    """Log AI tool call"""
    await log_audit(
        user_id=user_id,
        action="tool_call",
        resource=tool_name,
        request_data=tool_input,
        response_data=tool_output
    )
