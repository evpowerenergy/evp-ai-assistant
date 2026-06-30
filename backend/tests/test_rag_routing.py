"""Tests for RAG routing heuristics and formatters."""
from app.orchestrator.formatters.rag_response import format_rag_response
from app.orchestrator.llm_router import _message_has_rag_keyword


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


def test_explicit_company_profile_is_rag():
    assert _message_has_rag_keyword("ข้อมูลพื้นฐานของบริษัทมีอะไรบ้าง")
    assert _message_has_rag_keyword("ตามเอกสาร Super EV HUB มีกี่ kW")
    assert _message_has_rag_keyword("เกี่ยวกับบริษัท EV Power")


def test_sales_doc_not_rag():
    assert not _message_has_rag_keyword("รายละเอียด QT2026030013")
    assert not _message_has_rag_keyword("ยอดขายเดือนนี้เท่าไหร่")


def test_crm_tools_win_over_ambiguous_company_questions():
    """CRM vocabulary must block RAG even for company-adjacent topics."""
    assert not _message_has_rag_keyword("โครงสร้างทีมของบริษัทเป็นยังไง")
    assert not _message_has_rag_keyword("KPI อ้างอิงของบริษัทมีอะไรบ้าง")
    assert not _message_has_rag_keyword("Workflow จาก Marketing ไป Engineering")
    assert not _message_has_rag_keyword("ลีดวันนี้มีกี่ราย")


def test_live_data_signals_block_rag():
    assert not _message_has_rag_keyword("ตามเอกสาร รายได้เดือนนี้เท่าไหร่")
    assert not _message_has_rag_keyword("Super EV HUB วันนี้มีกี่ราย")


def test_vague_topic_without_kb_phrase_not_rag():
    """Without explicit KB intent, do not steal from CRM/general."""
    assert not _message_has_rag_keyword("Super EV HUB เชียงใหม่ กี่ kW")
    assert not _message_has_rag_keyword("Solvana ทำธุรกิจอะไร")
    assert not _message_has_rag_keyword("ชื่อบริษัทเต็มคืออะไร")


def test_rag_heuristic_irrelevant_when_mode_is_crm():
    """Heuristic may match KB phrases; CRM mode blocks them in analyze_intent_with_llm."""
    from app.orchestrator.llm_router import _message_has_rag_keyword

    msg = "ข้อมูลพื้นฐานของบริษัทมีอะไรบ้าง"
    assert _message_has_rag_keyword(msg)
    # Routing is enforced by chat_mode in graph + analyze_intent_with_llm, not keyword alone.


def test_expand_kb_company_query():
    from app.services.query_rewrite import expand_kb_company_query

    expanded = expand_kb_company_query("บริษัทเราทำอะไรบ้าง")
    assert expanded is not None
    assert "EV POWER" in expanded
    assert expand_kb_company_query("ลีดวันนี้มีกี่ราย") is None
