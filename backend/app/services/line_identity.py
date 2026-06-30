"""
Resolve LINE user to app user + role.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.roles import is_ai_assistant_role, resolve_role_from_db
from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def resolve_line_user(line_user_id: str) -> Optional[Dict[str, Any]]:
    """
    Lookup line_identities → user_id → role.
    Returns None if not linked or role not allowed.
    """
    if not line_user_id:
        return None

    supabase = get_supabase_client()
    result = (
        supabase.table("line_identities")
        .select("user_id")
        .eq("line_user_id", line_user_id)
        .limit(1)
        .execute()
    )
    row = (result.data or [None])[0]
    if not row:
        return None

    user_id = row["user_id"]
    role = resolve_role_from_db(user_id) or "staff"

    if not is_ai_assistant_role(role):
        logger.warning("LINE user %s linked but role denied: %s", line_user_id, role)
        return {"id": user_id, "role": role, "denied": True}

    return {"id": user_id, "role": role, "denied": False}


async def unlink_by_line_user_id(line_user_id: str) -> bool:
    supabase = get_supabase_client()
    supabase.table("line_identities").delete().eq("line_user_id", line_user_id).execute()
    return True
