"""
LINE account linking — verification codes.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

CODE_TTL_MINUTES = 10
LINK_CODE_PATTERN = "LINK"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _generate_six_digit_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def generate_link_code(user_id: str) -> Dict[str, Any]:
    """Create a new 6-digit link code (invalidates previous unused codes for user)."""
    supabase = get_supabase_client()
    now = _now_utc()
    expires_at = now + timedelta(minutes=CODE_TTL_MINUTES)

    try:
        supabase.table("line_link_codes").delete().eq("user_id", user_id).is_(
            "used_at", "null"
        ).execute()
    except Exception as e:
        logger.debug("Could not clear old link codes: %s", e)

    code = _generate_six_digit_code()
    for _ in range(5):
        existing = (
            supabase.table("line_link_codes")
            .select("id")
            .eq("code", code)
            .is_("used_at", "null")
            .gt("expires_at", now.isoformat())
            .limit(1)
            .execute()
        )
        if not existing.data:
            break
        code = _generate_six_digit_code()

    row = {
        "id": str(uuid4()),
        "user_id": user_id,
        "code": code,
        "expires_at": expires_at.isoformat(),
    }
    result = supabase.table("line_link_codes").insert(row).execute()
    if not result.data:
        raise RuntimeError("Failed to create link code")

    return {
        "code": code,
        "expires_at": expires_at.isoformat(),
        "instruction": f"พิมพ์ {LINK_CODE_PATTERN} {code} ในแชท LINE Official Account",
    }


async def get_line_link_status(user_id: str) -> Dict[str, Any]:
    """Return whether user has a linked LINE identity."""
    supabase = get_supabase_client()
    result = (
        supabase.table("line_identities")
        .select("id, line_user_id, linked_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    row = (result.data or [None])[0]
    if row:
        return {
            "linked": True,
            "line_user_id": row.get("line_user_id"),
            "linked_at": row.get("linked_at"),
        }
    return {"linked": False}


async def unlink_line_account(user_id: str) -> bool:
    """Remove LINE identity for user."""
    supabase = get_supabase_client()
    supabase.table("line_identities").delete().eq("user_id", user_id).execute()
    return True


async def consume_link_code(code: str, line_user_id: str) -> Dict[str, Any]:
    """
    Validate code and link line_user_id to app user.
    Returns {success, message, user_id?}.
    """
    supabase = get_supabase_client()
    now = _now_utc().isoformat()
    normalized = (code or "").strip()

    row_result = (
        supabase.table("line_link_codes")
        .select("*")
        .eq("code", normalized)
        .is_("used_at", "null")
        .gt("expires_at", now)
        .limit(1)
        .execute()
    )
    row = (row_result.data or [None])[0]
    if not row:
        return {"success": False, "message": "รหัสไม่ถูกต้องหรือหมดอายุ กรุณาสร้างรหัสใหม่ที่เว็บ"}

    user_id = row["user_id"]

    existing_line = (
        supabase.table("line_identities")
        .select("user_id")
        .eq("line_user_id", line_user_id)
        .limit(1)
        .execute()
    )
    if existing_line.data:
        other = existing_line.data[0].get("user_id")
        if other != user_id:
            return {
                "success": False,
                "message": "บัญชี LINE นี้เชื่อมต่อกับผู้ใช้อื่นแล้ว",
            }

    supabase.table("line_identities").delete().eq("user_id", user_id).execute()
    supabase.table("line_identities").delete().eq("line_user_id", line_user_id).execute()

    supabase.table("line_identities").insert(
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "line_user_id": line_user_id,
        }
    ).execute()

    supabase.table("line_link_codes").update({"used_at": now}).eq("id", row["id"]).execute()

    return {
        "success": True,
        "message": "เชื่อมต่อสำเร็จ! ถามคำถามได้เลย",
        "user_id": user_id,
    }


def parse_link_command(text: str) -> Optional[str]:
    """Parse 'LINK 123456' or 'LINK123456' → code or None."""
    t = (text or "").strip().upper()
    if not t.startswith(LINK_CODE_PATTERN):
        return None
    rest = t[len(LINK_CODE_PATTERN) :].strip()
    if rest.isdigit() and len(rest) == 6:
        return rest
    return None
