"""
LINE Messaging API Service (httpx — no line-bot-sdk).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_LOADING_URL = "https://api.line.me/v2/bot/chat/loading/start"

MAX_LINE_TEXT_LEN = 4000


def verify_line_signature(body: bytes, signature: Optional[str], secret: str) -> bool:
    """Verify X-Line-Signature (HMAC-SHA256, base64)."""
    if not signature or not secret:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, signature)


def parse_webhook_events(body: bytes) -> List[Dict[str, Any]]:
    """Parse LINE webhook JSON body into events list."""
    try:
        payload = json.loads(body.decode("utf-8"))
        events = payload.get("events", [])
        return events if isinstance(events, list) else []
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("Failed to parse LINE webhook body: %s", e)
        return []


def split_text_for_line(text: str, max_len: int = MAX_LINE_TEXT_LEN) -> List[str]:
    """Split long text into LINE-safe chunks."""
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]

    chunks: List[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            split_at = max_len
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    return chunks


def _text_messages(text: str) -> List[Dict[str, str]]:
    return [{"type": "text", "text": chunk} for chunk in split_text_for_line(text)]


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


async def reply_message(reply_token: str, text: str) -> bool:
    """Reply to a webhook event (must be within ~1 minute)."""
    if not settings.LINE_CHANNEL_ACCESS_TOKEN or not reply_token:
        return False
    messages = _text_messages(text)
    # LINE allows max 5 messages per reply
    messages = messages[:5]
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                LINE_REPLY_URL,
                headers=_headers(),
                json={"replyToken": reply_token, "messages": messages},
            )
            if resp.status_code >= 400:
                logger.error("LINE reply failed: %s %s", resp.status_code, resp.text)
                return False
            return True
    except Exception as e:
        logger.error("LINE reply error: %s", e)
        return False


async def push_message(line_user_id: str, text: str) -> bool:
    """Push message to a LINE user."""
    if not settings.LINE_CHANNEL_ACCESS_TOKEN or not line_user_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for chunk in split_text_for_line(text):
                resp = await client.post(
                    LINE_PUSH_URL,
                    headers=_headers(),
                    json={
                        "to": line_user_id,
                        "messages": [{"type": "text", "text": chunk}],
                    },
                )
                if resp.status_code >= 400:
                    logger.error("LINE push failed: %s %s", resp.status_code, resp.text)
                    return False
        return True
    except Exception as e:
        logger.error("LINE push error: %s", e)
        return False


async def send_loading_indicator(line_user_id: str, seconds: int = 60) -> bool:
    """Show native LINE loading animation (typing dots) — does not add a chat bubble."""
    if not settings.LINE_CHANNEL_ACCESS_TOKEN or not line_user_id:
        return False
    duration = max(5, min(int(seconds), 60))
    # LINE API expects multiples of 5 seconds
    duration = (duration // 5) * 5 or 5
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                LINE_LOADING_URL,
                headers=_headers(),
                json={"chatId": line_user_id, "loadingSeconds": duration},
            )
            if resp.status_code >= 400:
                logger.warning(
                    "LINE loading animation failed: %s %s — enable 'Use loading animation' in LINE OA Console",
                    resp.status_code,
                    resp.text[:200],
                )
                return False
            return True
    except Exception as e:
        logger.warning("LINE loading indicator error: %s", e)
        return False


async def push_sticker(line_user_id: str, package_id: str, sticker_id: str) -> bool:
    """Send a LINE sticker message."""
    if not settings.LINE_CHANNEL_ACCESS_TOKEN or not line_user_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                LINE_PUSH_URL,
                headers=_headers(),
                json={
                    "to": line_user_id,
                    "messages": [
                        {
                            "type": "sticker",
                            "packageId": str(package_id),
                            "stickerId": str(sticker_id),
                        }
                    ],
                },
            )
            if resp.status_code >= 400:
                logger.warning("LINE sticker push failed: %s %s", resp.status_code, resp.text[:200])
                return False
            return True
    except Exception as e:
        logger.warning("LINE sticker error: %s", e)
        return False


async def start_ai_search_feedback(
    line_user_id: str,
    reply_token: Optional[str] = None,
    text: str = "🔍 กำลังค้นหาข้อมูล...",
) -> None:
    """
    Immediate visible feedback while AI runs.
    Always sends a chat message (reply preferred), plus native loading animation when available.
    """
    if reply_token:
        replied = await reply_message(reply_token, text)
        if not replied:
            await push_message(line_user_id, text)
    else:
        await push_message(line_user_id, text)

    seconds = getattr(settings, "LINE_LOADING_SECONDS", 60) or 60
    await send_loading_indicator(line_user_id, seconds=seconds)

    pkg = (getattr(settings, "LINE_STICKER_PACKAGE_ID", "") or "").strip()
    sticker = (getattr(settings, "LINE_STICKER_ID_LOADING", "") or "").strip()
    if pkg and sticker:
        await push_sticker(line_user_id, pkg, sticker)


async def send_line_message(
    user_id: str,
    message: str,
    quick_replies: Optional[list] = None,
) -> bool:
    """Send message via LINE Push API."""
    _ = quick_replies  # reserved for future Quick Reply items
    return await push_message(user_id, message)


async def send_line_notification(
    user_id: str,
    title: str,
    message: str,
    link_url: Optional[str] = None,
) -> bool:
    """Send notification via LINE."""
    notification_text = f"{title}\n\n{message}"
    if link_url:
        notification_text += f"\n\nดูเพิ่มเติม: {link_url}"
    return await send_line_message(user_id, notification_text)
