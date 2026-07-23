"""Tests for shared chat mode (CRM vs KB)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestrator.graph import (
    route_after_kb_guard,
    route_by_chat_mode,
    route_intent,
)
from app.orchestrator.llm_router import analyze_intent_with_llm
from app.services.chat_mode import (
    KB_MODE_SWITCH_HINT,
    get_chat_mode,
    is_crm_style_question,
    line_quick_reply_items,
    normalize_chat_mode,
    parse_mode_command,
    set_chat_mode,
)


def test_parse_mode_command():
    assert parse_mode_command("MODE CRM") == "crm"
    assert parse_mode_command("MODE KB") == "kb"
    assert parse_mode_command("MODE DOC") == "kb"
    assert parse_mode_command("📊 CRM") == "crm"
    assert parse_mode_command("📄 เอกสารบริษัท") == "kb"
    assert parse_mode_command("ลีดวันนี้") is None


def test_normalize_chat_mode():
    assert normalize_chat_mode("kb") == "kb"
    assert normalize_chat_mode("DOC") == "kb"
    assert normalize_chat_mode(None) == "crm"
    assert normalize_chat_mode("crm") == "crm"


def test_line_mode_quick_replies_hidden_for_hermes(monkeypatch):
    monkeypatch.setattr(
        "app.services.chat_mode.settings.AI_PRIMARY_ENGINE",
        "hermes",
    )
    assert line_quick_reply_items() == []


def test_line_mode_quick_replies_kept_for_langgraph(monkeypatch):
    monkeypatch.setattr(
        "app.services.chat_mode.settings.AI_PRIMARY_ENGINE",
        "langgraph",
    )
    assert len(line_quick_reply_items()) == 2


def test_is_crm_style_question():
    assert is_crm_style_question("ลีดวันนี้มีกี่ราย")
    assert is_crm_style_question("ยอดขายเดือนนี้เท่าไหร่")
    assert not is_crm_style_question("ข้อมูลพื้นฐานของบริษัทมีอะไรบ้าง")


def test_route_by_chat_mode():
    assert route_by_chat_mode({"chat_mode": "crm"}) == "crm"
    assert route_by_chat_mode({"chat_mode": "kb"}) == "kb"
    assert route_by_chat_mode({}) == "crm"


def test_route_after_kb_guard_blocked():
    state = {"intent": "kb_blocked", "response": KB_MODE_SWITCH_HINT}
    assert route_after_kb_guard(state) == "blocked"


def test_route_after_kb_guard_proceed():
    state = {"intent": "rag_query"}
    assert route_after_kb_guard(state) == "proceed"


def test_route_intent_crm_blocks_rag_query():
    state = {
        "chat_mode": "crm",
        "intent": "rag_query",
        "confidence": 0.9,
        "selected_tools": [{"name": "search_leads"}],
    }
    assert route_intent(state) == "db_query"

    state_no_tools = {
        "chat_mode": "crm",
        "intent": "rag_query",
        "confidence": 0.9,
        "selected_tools": [],
    }
    assert route_intent(state_no_tools) == "general"


@pytest.mark.asyncio
async def test_get_chat_mode_default():
    mock_result = MagicMock()
    mock_result.data = []
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        mock_result
    )
    mock_supabase = MagicMock()
    mock_supabase.table.return_value = mock_table

    with patch("app.services.chat_mode.get_supabase_client", return_value=mock_supabase):
        mode = await get_chat_mode("user-1")
    assert mode == "crm"


@pytest.mark.asyncio
async def test_get_set_chat_mode_round_trip():
    select_empty = MagicMock()
    select_empty.data = []

    select_existing = MagicMock()
    select_existing.data = [{"user_id": "user-1"}]

    get_row = MagicMock()
    get_row.data = [{"chat_mode": "kb"}]

    mock_table = MagicMock()

    def table_side_effect(name):
        assert name == "user_chat_preferences"
        return mock_table

    mock_table.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
        get_row,
        select_existing,
    ]
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = table_side_effect

    with patch("app.services.chat_mode.get_supabase_client", return_value=mock_supabase):
        assert await get_chat_mode("user-1") == "kb"
        saved = await set_chat_mode("user-1", "kb")
    assert saved == "kb"
    mock_table.update.assert_called_once()


@pytest.mark.asyncio
@patch("app.orchestrator.llm_router.AsyncOpenAI")
async def test_crm_mode_blocks_rag_intent_from_heuristic(mock_openai_cls):
    """CRM mode must not return rag_query even for explicit KB phrases."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"intent": "general", "confidence": 0.5}'
    mock_response.choices[0].message.tool_calls = None

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_openai_cls.return_value = mock_client

    result = await analyze_intent_with_llm(
        user_message="ข้อมูลพื้นฐานของบริษัทมีอะไรบ้าง",
        user_id="u1",
        chat_mode="crm",
    )
    assert result["intent"] != "rag_query"


@pytest.mark.asyncio
async def test_kb_mode_blocks_crm_question():
    from app.orchestrator.graph import get_graph

    graph = get_graph()
    result = await graph.ainvoke(
        {
            "user_message": "ลีดวันนี้มีกี่ราย",
            "user_id": "u1",
            "user_role": "staff",
            "chat_mode": "kb",
            "confidence": 0.0,
            "tool_calls": [],
            "tool_results": [],
            "rag_results": [],
            "citations": [],
            "retry_count": 0,
            "max_retries": 0,
            "previous_attempts": [],
            "alternative_queries": [],
        }
    )
    assert result.get("intent") == "kb_blocked"
    assert "CRM" in (result.get("response") or "")
