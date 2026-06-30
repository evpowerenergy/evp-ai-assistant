"""
LINE webhook event dispatch and message handling.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.config import settings
from app.core.audit import log_audit
from app.core.rate_limit import check_rate_limit
from app.orchestrator.formatters.line_response import format_for_line
from app.services.active_session import get_active_session
from app.services.chat_processor import run_chat_turn
from app.services.line import push_message, reply_message, start_ai_search_feedback
from app.services.line_identity import resolve_line_user, unlink_by_line_user_id
from app.services.line_link import consume_link_code, parse_link_command
from app.utils.logger import get_logger

logger = get_logger(__name__)

WELCOME_MESSAGE = """สวัสดีครับ! ยินดีต้อนรับสู่ EV Power AI Assistant

ก่อนใช้งาน กรุณาเชื่อมต่อบัญชี:
1. Login ที่เว็บ AI Assistant
2. ไปหน้า LINE Integration
3. กดสร้างรหัสเชื่อมต่อ
4. พิมพ์ LINK ตามด้วยรหัส 6 หลัก ในแชทนี้

พิมพ์ HELP เพื่อดูคำสั่ง"""

LINK_INSTRUCTIONS = """ยังไม่ได้เชื่อมต่อบัญชี

1. Login ที่เว็บ AI Assistant
2. ไปหน้า LINE Integration (/admin/line)
3. สร้างรหัสเชื่อมต่อ
4. พิมพ์ LINK ตามด้วยรหัส 6 หลัก ในแชทนี้"""

HELP_MESSAGE = """คำสั่งที่ใช้ได้:
• LINK 123456 — เชื่อมต่อบัญชี (รหัสจากเว็บ)
• UNLINK — ยกเลิกการเชื่อมต่อ
• HELP — แสดงความช่วยเหลือ

ถามคำถามเกี่ยวกับ CRM หรือเอกสารได้โดยตรงหลังเชื่อมต่อแล้ว"""


def _line_user_id_from_event(event: Dict[str, Any]) -> Optional[str]:
    source = event.get("source") or {}
    return source.get("userId")


async def dispatch_line_event(event: Dict[str, Any]) -> None:
    """Route a single LINE webhook event."""
    event_type = event.get("type")
    line_user_id = _line_user_id_from_event(event)

    if event_type == "follow":
        if line_user_id:
            await reply_message(
                event.get("replyToken", ""),
                WELCOME_MESSAGE,
            )
            await log_audit(
                user_id="line-system",
                action="line_follow",
                resource="line",
                metadata={"line_user_id": line_user_id},
            )
        return

    if event_type == "unfollow":
        if line_user_id:
            await log_audit(
                user_id="line-system",
                action="line_unfollow",
                resource="line",
                metadata={"line_user_id": line_user_id},
            )
        return

    if event_type != "message":
        return

    message = event.get("message") or {}
    if message.get("type") != "text":
        if line_user_id and event.get("replyToken"):
            await reply_message(
                event.get("replyToken"),
                "ขออภัยครับ รองรับเฉพาะข้อความตัวอักษรเท่านั้น",
            )
        return

    text = (message.get("text") or "").strip()
    if not text or not line_user_id:
        return

    await handle_line_text_message(event, line_user_id, text)


async def handle_line_text_message(
    event: Dict[str, Any],
    line_user_id: str,
    text: str,
) -> None:
    reply_token = event.get("replyToken")
    upper = text.upper()

    if upper == "HELP":
        await _reply_or_push(reply_token, line_user_id, HELP_MESSAGE)
        return

    if upper == "UNLINK":
        await unlink_by_line_user_id(line_user_id)
        await _reply_or_push(
            reply_token,
            line_user_id,
            "ยกเลิกการเชื่อมต่อแล้ว สามารถเชื่อมต่อใหม่ได้จากเว็บ",
        )
        await log_audit(
            user_id="line-system",
            action="line_unlink",
            resource="line",
            metadata={"line_user_id": line_user_id},
        )
        return

    link_code = parse_link_command(text)
    if link_code:
        result = await consume_link_code(link_code, line_user_id)
        await log_audit(
            user_id=result.get("user_id") or "line-system",
            action="line_link" if result.get("success") else "line_link_failed",
            resource="line",
            request_data={"code": link_code},
            response_data={"message": result.get("message")},
            metadata={"line_user_id": line_user_id},
        )
        await _reply_or_push(reply_token, line_user_id, result.get("message", "เกิดข้อผิดพลาด"))
        return

    user = await resolve_line_user(line_user_id)
    if not user:
        await log_audit(
            user_id="line-system",
            action="line_access_denied",
            resource="line",
            metadata={"line_user_id": line_user_id, "reason": "not_linked"},
        )
        await _reply_or_push(reply_token, line_user_id, LINK_INSTRUCTIONS)
        return

    if user.get("denied"):
        allowed = ", ".join(settings.ai_assistant_allowed_roles_list)
        await log_audit(
            user_id=user["id"],
            action="line_access_denied",
            resource="line",
            metadata={"line_user_id": line_user_id, "reason": "role", "role": user.get("role")},
        )
        await _reply_or_push(
            reply_token,
            line_user_id,
            f"บัญชีของคุณไม่มีสิทธิ์ใช้งาน AI Assistant\nต้องมี role: {allowed}",
        )
        return

    user_id = user["id"]
    user_role = user["role"]

    is_allowed, _ = await check_rate_limit(user_id=user_id, endpoint="chat")
    if not is_allowed:
        await _reply_or_push(
            reply_token,
            line_user_id,
            "คุณส่งข้อความบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่",
        )
        return

    await start_ai_search_feedback(line_user_id, reply_token=reply_token)

    try:
        session_id = await get_active_session(user_id, first_message=text)
        result = await run_chat_turn(
            user_id=user_id,
            user_role=user_role,
            message=text,
            session_id=session_id,
            source="line",
            line_user_id=line_user_id,
        )
        formatted = format_for_line(
            result.get("response", ""),
            result.get("citations"),
        )
        await push_message(line_user_id, formatted)
        await log_audit(
            user_id=user_id,
            action="line_message",
            resource="line",
            request_data={"message": text[:200]},
            metadata={"line_user_id": line_user_id, "session_id": session_id},
        )
    except Exception as e:
        logger.error("LINE AI error: %s", e)
        await push_message(
            line_user_id,
            "ขออภัยครับ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง",
        )


async def _reply_or_push(
    reply_token: Optional[str],
    line_user_id: str,
    text: str,
) -> None:
    if reply_token:
        ok = await reply_message(reply_token, text)
        if ok:
            return
    await push_message(line_user_id, text)
