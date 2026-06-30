"""
Shared chat mode preference: CRM vs knowledge-base documents.
"""
from __future__ import annotations

import re
from typing import Literal, Optional

from app.orchestrator.llm_router import (
    _message_has_data_keyword,
    _message_has_live_data_intent,
)
from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

ChatMode = Literal["crm", "kb"]
VALID_MODES = frozenset({"crm", "kb"})
DEFAULT_MODE: ChatMode = "crm"

KB_MODE_SWITCH_HINT = (
    "คำถามนี้เกี่ยวกับข้อมูล CRM สด (ลีด/ยอดขาย/นัด ฯลฯ) "
    "กรุณาสลับเป็นโหมด **CRM** แล้วถามใหม่"
)

_MODE_COMMAND_RE = re.compile(
    r"^MODE\s+(CRM|KB|DOC|DOCUMENTS?)\s*$",
    re.IGNORECASE,
)


def normalize_chat_mode(mode: Optional[str]) -> ChatMode:
    m = (mode or "").strip().lower()
    if m in ("kb", "doc", "documents", "document"):
        return "kb"
    return "crm"


def mode_display_label(mode: ChatMode) -> str:
    return "CRM" if mode == "crm" else "เอกสารบริษัท"


def parse_mode_command(text: str) -> Optional[ChatMode]:
    """Parse MODE CRM / MODE KB / Quick Reply payloads."""
    raw = (text or "").strip()
    if not raw:
        return None

    upper = raw.upper()
    if upper in ("MODE CRM", "📊 CRM", "CRM"):
        return "crm"
    if upper in ("MODE KB", "MODE DOC", "📄 เอกสารบริษัท", "เอกสารบริษัท"):
        return "kb"

    m = _MODE_COMMAND_RE.match(raw)
    if m:
        token = m.group(1).upper()
        if token == "CRM":
            return "crm"
        return "kb"
    return None


def is_crm_style_question(text: str) -> bool:
    """True if message should use CRM tools, not KB RAG."""
    return _message_has_data_keyword(text) or _message_has_live_data_intent(text)


async def get_chat_mode(user_id: str) -> ChatMode:
    try:
        supabase = get_supabase_client()
        result = (
            supabase.table("user_chat_preferences")
            .select("chat_mode")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        row = (result.data or [None])[0]
        if row and row.get("chat_mode"):
            return normalize_chat_mode(row["chat_mode"])
    except Exception as e:
        logger.warning("get_chat_mode fallback to crm: %s", e)
    return DEFAULT_MODE


async def set_chat_mode(user_id: str, mode: str) -> ChatMode:
    normalized = normalize_chat_mode(mode)
    if normalized not in VALID_MODES:
        raise ValueError(f"Invalid chat_mode: {mode}")

    supabase = get_supabase_client()
    existing = (
        supabase.table("user_chat_preferences")
        .select("user_id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    payload = {"chat_mode": normalized, "updated_at": "now()"}
    if existing.data:
        supabase.table("user_chat_preferences").update(payload).eq(
            "user_id", user_id
        ).execute()
    else:
        supabase.table("user_chat_preferences").insert(
            {"user_id": user_id, **payload}
        ).execute()
    return normalized


def line_quick_reply_items() -> list:
    """Quick Reply actions for switching chat mode on LINE."""
    return [
        {
            "type": "action",
            "action": {"type": "message", "label": "CRM", "text": "MODE CRM"},
        },
        {
            "type": "action",
            "action": {
                "type": "message",
                "label": "เอกสารบริษัท",
                "text": "MODE KB",
            },
        },
    ]


def prefix_response_with_mode(text: str, mode: ChatMode) -> str:
    label = mode_display_label(mode)
    body = (text or "").strip()
    prefix = f"โหมดปัจจุบัน: {label}"
    return f"{prefix}\n\n{body}" if body else prefix
