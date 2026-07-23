"""
LINE integration unit tests
"""
import base64
import hashlib
import hmac
import json

import pytest

from app.orchestrator.formatters.line_response import (
    build_ai_flex_message,
    build_dynamic_quick_replies,
    format_for_line,
)
from app.services.line import split_text_for_line, verify_line_signature, parse_webhook_events

LINK_CODE_PATTERN = "LINK"


def parse_link_command(text: str):
    t = (text or "").strip().upper()
    if not t.startswith(LINK_CODE_PATTERN):
        return None
    rest = t[len(LINK_CODE_PATTERN) :].strip()
    if rest.isdigit() and len(rest) == 6:
        return rest
    return None


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def test_verify_line_signature_valid():
    body = b'{"events":[]}'
    secret = "test_secret"
    sig = _sign(body, secret)
    assert verify_line_signature(body, sig, secret) is True


def test_verify_line_signature_invalid():
    body = b'{"events":[]}'
    assert verify_line_signature(body, "bad", "secret") is False


def test_parse_webhook_events():
    body = json.dumps({"events": [{"type": "message"}]}).encode()
    events = parse_webhook_events(body)
    assert len(events) == 1
    assert events[0]["type"] == "message"


def test_split_text_for_line():
    long_text = "a" * 5000
    chunks = split_text_for_line(long_text, max_len=4000)
    assert len(chunks) == 2
    assert all(len(c) <= 4000 for c in chunks)


def test_parse_link_command():
    assert parse_link_command("LINK 482913") == "482913"
    assert parse_link_command("link 482913") == "482913"
    assert parse_link_command("LINK482913") == "482913"
    assert parse_link_command("hello") is None


def test_format_for_line_strips_markdown():
    text = format_for_line("**ยอดขาย** วันนี้", citations=["https://example.com/doc"])
    assert "**" not in text
    assert "อ้างอิง" in text
    assert "example.com" in text


def test_build_ai_flex_message_hides_runtime_and_model():
    message = build_ai_flex_message(
        "**ยอดขาย** เดือนนี้ 1,000,000 บาท",
        runtime=1.25,
        model="gpt-5.6-luna",
        engine="hermes",
        question="ยอดขายเดือนนี้",
    )

    assert message["type"] == "flex"
    assert len(message["altText"]) <= 400
    assert message["contents"]["type"] == "bubble"
    assert message["contents"]["size"] == "giga"
    payload = json.dumps(message)
    assert "footer" not in message["contents"]
    assert "1.2s" not in payload
    assert "gpt-5.6-luna" not in payload
    assert "Confidence" not in payload


def test_dynamic_quick_replies_follow_marketing_context():
    items = build_dynamic_quick_replies(
        question="ROAS เดือนนี้เป็นอย่างไร",
        response="ROAS เท่ากับ 4.2",
    )

    labels = [item["action"]["label"] for item in items]
    assert labels == ["📈 เทียบช่วงก่อน", "🎯 เจาะ ROAS", "🔍 ดู Conversion"]
    assert all(len(item["action"]["label"]) <= 20 for item in items)
    assert all(len(item["action"]["text"]) <= 300 for item in items)


def test_dynamic_quick_replies_do_not_offer_appointments():
    items = build_dynamic_quick_replies(
        question="ช่วยสรุปลีดใหม่",
        response="มีลีดใหม่ 10 ราย",
    )

    labels = [item["action"]["label"] for item in items]
    assert labels == ["🔍 เจาะรายละเอียด", "📊 สรุปตามสถานะ"]
    assert "📅 ดูนัดหมาย" not in labels


def test_dynamic_quick_replies_offer_citations_when_available():
    items = build_dynamic_quick_replies(
        question="ยอดขายเดือนนี้",
        response="ยอดขายรวม 1,000,000 บาท",
        citations=["https://example.com/source"],
    )

    assert items[-1]["action"]["label"] == "📚 ดูแหล่งอ้างอิง"
