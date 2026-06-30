"""Tests for RAG routing heuristics and formatters."""
from app.orchestrator.formatters.rag_response import format_rag_response


def test_format_rag_empty():
    out = format_rag_response([], [], "ขั้นตอนการลา")
    assert "ไม่พบเอกสาร" in out
    assert "ห้าม" in out


def test_format_rag_with_citations():
    results = [
        {
            "content": "ขั้นตอนที่ 1: กรอกแบบฟอร์ม",
            "source": "SOP การลา",
            "metadata": {"page_number": 2},
        }
    ]
    citations = ["[1] SOP การลา หน้า 2"]
    out = format_rag_response(results, citations, "ขั้นตอนการลา")
    assert "ขั้นตอนที่ 1" in out
    assert "SOP การลา" in out
    assert "อ้างอิง" in out


def test_sales_query_not_rag_marker():
    """Sanity: sales markers used in router should not match pure RAG questions."""
    rag_markers = ("ขั้นตอน", "วิธีทำ", "sop", "นโยบาย")
    sales_q = "ยอดขายเดือนนี้เท่าไหร่"
    assert not any(m in sales_q for m in rag_markers)
