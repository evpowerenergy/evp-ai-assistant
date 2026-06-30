"""
Shared role resolution utilities (web JWT + LINE identity).
"""
from typing import Optional

from app.config import settings
from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


def resolve_role_from_db(auth_user_id: str) -> Optional[str]:
    """Resolve role from users or employees table (service role, no RLS)."""
    try:
        supabase = get_supabase_client()
        for table in ("users", "employees"):
            r = (
                supabase.table(table)
                .select("role")
                .eq("auth_user_id", auth_user_id)
                .limit(1)
                .execute()
            )
            row = (r.data or [])[0] if r.data else None
            if row and row.get("role"):
                role = str(row.get("role", "")).strip()
                if role:
                    return role
    except Exception as e:
        logger.debug("resolve role from db: %s", e)
    return None


def is_ai_assistant_role(role: Optional[str]) -> bool:
    """True if role may use AI Assistant (web or LINE)."""
    allowed = {r.lower() for r in settings.ai_assistant_allowed_roles_list}
    return (role or "").strip().lower() in allowed
