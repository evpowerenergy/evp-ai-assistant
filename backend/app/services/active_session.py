"""
Shared active chat session (web + LINE).
"""
from __future__ import annotations

from typing import Optional
from uuid import uuid4

from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _title_from_message(message: str) -> str:
    t = (message or "").strip()[:50]
    return t + ("..." if len((message or "").strip()) > 50 else "") if t else "New Chat"


async def touch_session(session_id: str) -> None:
    try:
        supabase = get_supabase_client()
        supabase.table("chat_sessions").update({"updated_at": "now()"}).eq(
            "id", session_id
        ).execute()
    except Exception as e:
        logger.debug("touch_session: %s", e)


async def set_active_session(user_id: str, session_id: str) -> None:
    supabase = get_supabase_client()
    existing = (
        supabase.table("user_chat_preferences")
        .select("user_id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        supabase.table("user_chat_preferences").update(
            {"active_session_id": session_id, "updated_at": "now()"}
        ).eq("user_id", user_id).execute()
    else:
        supabase.table("user_chat_preferences").insert(
            {"user_id": user_id, "active_session_id": session_id}
        ).execute()


async def get_active_session_id(user_id: str) -> Optional[str]:
    supabase = get_supabase_client()
    prefs = (
        supabase.table("user_chat_preferences")
        .select("active_session_id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if prefs.data and prefs.data[0].get("active_session_id"):
        sid = prefs.data[0]["active_session_id"]
        check = (
            supabase.table("chat_sessions")
            .select("id")
            .eq("id", sid)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if check.data:
            return sid

    latest = (
        supabase.table("chat_sessions")
        .select("id")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    if latest.data:
        sid = latest.data[0]["id"]
        await set_active_session(user_id, sid)
        return sid
    return None


async def create_session(user_id: str, title: str) -> str:
    supabase = get_supabase_client()
    session_id = str(uuid4())
    supabase.table("chat_sessions").insert(
        {
            "id": session_id,
            "user_id": user_id,
            "title": title,
        }
    ).execute()
    return session_id


async def get_active_session(user_id: str, first_message: Optional[str] = None) -> str:
    """
    Return active session id; create new session if none exists.
  """
    sid = await get_active_session_id(user_id)
    if sid:
        return sid

    title = _title_from_message(first_message or "")
    sid = await create_session(user_id, title)
    await set_active_session(user_id, sid)
    return sid
