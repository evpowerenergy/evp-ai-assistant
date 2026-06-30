"""
Format RAG results as natural language for LLM context (grounded).
"""
from app.config import settings


def format_rag_response(rag_results: list, citations: list, user_message: str) -> str:
    """Format RAG results with chunk labels for grounded generation."""
    if not rag_results:
        return (
            "ไม่พบเอกสารที่เกี่ยวข้องกับคำถามนี้ใน knowledge base "
            "กรุณาตอบผู้ใช้ว่าไม่พบข้อมูลในเอกสารภายในเท่านั้น ห้ามเดาหรือใช้ความรู้ทั่วไปเติม"
        )

    max_chars = settings.KB_RAG_CONTEXT_MAX_CHARS
    parts = []
    total = 0

    for i, result in enumerate(rag_results, 1):
        content = result.get("content", "")
        source = result.get("source", "Unknown")
        meta = result.get("metadata") or {}
        page = meta.get("page_number")
        section = meta.get("section_title")
        label = f"[chunk {i} จาก {source}"
        if page:
            label += f" หน้า {page}"
        if section:
            label += f" — {section}"
        label += "]"

        block = f"{label}\n{content}"
        if total + len(block) > max_chars:
            remaining = max_chars - total
            if remaining > 200:
                parts.append(block[:remaining] + "...")
            break
        parts.append(block)
        total += len(block)

    response = "\n\n".join(parts)

    if citations:
        response += f"\n\nอ้างอิง: {', '.join(citations)}"

    response += (
        "\n\n⚠️ ตอบจากเอกสารด้านบนเท่านั้น ห้ามสร้างข้อมูลเพิ่ม "
        "ถ้าเอกสารไม่มีคำตอบ ให้บอกว่าไม่พบในเอกสาร"
    )

    return response
