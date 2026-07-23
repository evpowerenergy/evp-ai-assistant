"""Format AI responses for LINE text, Flex Messages, and guided actions."""
import re
from typing import Any, Dict, List, Optional

MAX_FLEX_ANSWER_LEN = 3800


def _strip_markdown(text: str) -> str:
    """Light markdown cleanup for LINE plain text."""
    t = text
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\*(.+?)\*", r"\1", t)
    t = re.sub(r"`(.+?)`", r"\1", t)
    t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"^\s*[-*]\s+", "• ", t, flags=re.MULTILINE)
    return t


def format_for_line(response: str, citations: Optional[List[str]] = None) -> str:
    """Convert AI response + citations to LINE-friendly text."""
    text = _strip_markdown(response or "").strip()
    if citations:
        unique = []
        for c in citations:
            if c and c not in unique:
                unique.append(c)
        if unique:
            text += "\n\n---\nอ้างอิง:\n" + "\n".join(f"• {u}" for u in unique[:5])
    return text


def _message_action(label: str, text: str) -> Dict[str, Any]:
    return {
        "type": "action",
        "action": {
            "type": "message",
            "label": label[:20],
            "text": text[:300],
        },
    }


def _response_topic(question: str, response: str, intent: Optional[str]) -> str:
    content = f"{question} {response} {intent or ''}".lower()
    if any(
        word in content
        for word in ("roas", "ค่า ads", "งบ ads", "marketing", "conversion rate")
    ):
        return "marketing"
    if any(
        word in content
        for word in ("ลีด", "lead", "ลูกค้า", "นัดหมาย", "appointment")
    ):
        return "lead"
    if any(
        word in content
        for word in ("ยอดขาย", "sales", "seller", "ปิดการขาย", "รายได้")
    ):
        return "sales"
    if any(
        word in content
        for word in ("เอกสาร", "นโยบาย", "ขั้นตอน", "คู่มือ", "knowledge", "อ้างอิง")
    ):
        return "knowledge"
    return "general"


def build_dynamic_quick_replies(
    question: str,
    response: str,
    intent: Optional[str] = None,
    citations: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Suggest real follow-up actions that Hermes can handle in context."""
    topic = _response_topic(question, response, intent)
    actions = {
        "marketing": [
            ("📈 เทียบช่วงก่อน", "เปรียบเทียบผลลัพธ์นี้กับช่วงเวลาก่อนหน้า"),
            ("🎯 เจาะ ROAS", "ช่วยเจาะลึก ROAS จากคำตอบล่าสุด"),
            ("🔍 ดู Conversion", "วิเคราะห์ Conversion Rate เพิ่มเติมจากคำตอบล่าสุด"),
        ],
        "lead": [
            ("🔍 เจาะรายละเอียด", "ขอเจาะลึกรายละเอียดของลีดจากคำตอบล่าสุด"),
            ("📊 สรุปตามสถานะ", "สรุปลีดแยกตามสถานะจากข้อมูลล่าสุด"),
        ],
        "sales": [
            ("📈 เทียบช่วงก่อน", "เปรียบเทียบยอดขายนี้กับช่วงเวลาก่อนหน้า"),
            ("🏆 ดู Top Sales", "แสดงอันดับ Top Sales จากช่วงเวลาเดียวกัน"),
            ("🔍 เจาะรายละเอียด", "ขอเจาะลึกรายละเอียดยอดขายจากคำตอบล่าสุด"),
        ],
        "knowledge": [
            ("📝 สรุปสั้น", "สรุปคำตอบล่าสุดให้สั้นและเป็นข้อๆ"),
            ("🔍 อธิบายเพิ่ม", "อธิบายรายละเอียดเพิ่มเติมจากคำตอบล่าสุด"),
            ("💡 ตัวอย่างใช้งาน", "ยกตัวอย่างการนำข้อมูลจากคำตอบล่าสุดไปใช้"),
        ],
        "general": [
            ("🔍 รายละเอียดเพิ่ม", "ขอรายละเอียดเพิ่มเติมจากคำตอบล่าสุด"),
            ("📝 สรุปสั้น", "สรุปคำตอบล่าสุดให้สั้นและเป็นข้อๆ"),
            ("🔄 วิเคราะห์ใหม่", "วิเคราะห์คำถามล่าสุดใหม่อีกครั้งในอีกมุมมอง"),
        ],
    }[topic]
    if citations and topic != "knowledge":
        actions[-1] = ("📚 ดูแหล่งอ้างอิง", "แสดงแหล่งอ้างอิงของคำตอบล่าสุด")
    return [_message_action(label, text) for label, text in actions]


def build_ai_flex_message(
    response: str,
    *,
    citations: Optional[List[str]] = None,
    runtime: Optional[float] = None,
    model: Optional[str] = None,
    engine: Optional[str] = None,
    fallback_used: bool = False,
    question: str = "",
    intent: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a compact cybernetic dashboard-style Flex Message."""
    formatted = format_for_line(response, citations)
    truncated = len(formatted) > MAX_FLEX_ANSWER_LEN
    answer = formatted[:MAX_FLEX_ANSWER_LEN].rstrip()
    if truncated:
        answer += "\n\n…คำตอบถูกย่อให้เหมาะกับการแสดงผลบน LINE"

    topic = _response_topic(question, response, intent)
    titles = {
        "marketing": "MARKETING INTELLIGENCE",
        "lead": "LEAD ANALYSIS",
        "sales": "SALES INTELLIGENCE",
        "knowledge": "KNOWLEDGE BRIEF",
        "general": "AI AGENT ANALYSIS",
    }
    alt_text = re.sub(r"\s+", " ", formatted).strip()[:350] or "EVP AI วิเคราะห์ข้อมูลเรียบร้อยแล้ว"

    message: Dict[str, Any] = {
        "type": "flex",
        "altText": f"EVP AI: {alt_text}"[:400],
        "contents": {
            "type": "bubble",
            "size": "giga",
            "styles": {
                "header": {"backgroundColor": "#07111F"},
            },
            "header": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "18px",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "alignItems": "center",
                        "contents": [
                            {
                                "type": "text",
                                "text": "◉",
                                "color": "#2DE2E6",
                                "size": "xl",
                                "flex": 0,
                            },
                            {
                                "type": "text",
                                "text": " EVP • HERMES",
                                "color": "#E6FBFF",
                                "weight": "bold",
                                "size": "sm",
                                "flex": 1,
                            },
                            {
                                "type": "text",
                                "text": "ONLINE",
                                "color": "#2DE2E6",
                                "size": "xxs",
                                "align": "end",
                                "flex": 0,
                            },
                        ],
                    },
                    {
                        "type": "text",
                        "text": titles[topic],
                        "color": "#8CA7C4",
                        "size": "xxs",
                        "margin": "sm",
                    },
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "20px",
                "contents": [
                    {
                        "type": "text",
                        "text": "สรุปผลการวิเคราะห์",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#10233D",
                    },
                    {
                        "type": "separator",
                        "margin": "md",
                        "color": "#D9E8F2",
                    },
                    {
                        "type": "text",
                        "text": answer or "ไม่พบข้อความตอบกลับ",
                        "wrap": True,
                        "size": "sm",
                        "color": "#243B53",
                        "margin": "lg",
                        "lineSpacing": "6px",
                    },
                ],
            },
        },
    }
    return message
