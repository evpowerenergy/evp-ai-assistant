"""Tests for marketing keyword routing in llm_router."""
from app.orchestrator.llm_router import (
    _extract_date_params_from_message,
    _is_marketing_query,
    _message_has_data_keyword,
    _normalize_message_for_keywords,
    _suggest_default_tool_for_data_request,
    DATA_KEYWORDS_MARKETING,
)


def test_marketing_keywords_detected():
    assert _message_has_data_keyword("ROAS เดือนนี้เท่าไหร่") is True
    assert _message_has_data_keyword("งบ Facebook Ads ฝั่ง Package") is True
    assert _message_has_data_keyword("Inbox จาก Ads วันนี้") is True
    assert _message_has_data_keyword("Win Rate QT ฝั่ง Wholesales") is True


def test_thai_marketing_keywords_detected():
    assert _message_has_data_keyword("โฆษณาใช้เงินไปเท่าไหร่เดือนนี้") is True
    assert _message_has_data_keyword("แคมเปญ Facebook เดือนนี้") is True
    assert _message_has_data_keyword("หน้า marketing ยอดขาย Package") is True
    assert _message_has_data_keyword("วันนี้ยิงแอดไปเท่าไหร่") is True
    assert _message_has_data_keyword("วันนี้ยิงเเอดไปเท่าไหร่") is True  # typo เเ
    assert _message_has_data_keyword("งบแอดวันนี้") is True


def test_is_marketing_query_ying_ad_slang():
    m = _normalize_message_for_keywords("วันนี้ยิงเเอดไปเท่าไหร่")
    assert _is_marketing_query(m) is True


def test_suggest_marketing_for_ying_ad_today():
    suggestion = _suggest_default_tool_for_data_request("วันนี้ยิงเเอดไปเท่าไหร่")
    assert suggestion is not None
    assert suggestion["name"] == "get_marketing_dashboard"
    assert suggestion["parameters"].get("date_from") == suggestion["parameters"].get("date_to")


def test_suggest_marketing_dashboard_tool():
    suggestion = _suggest_default_tool_for_data_request("Marketing dashboard วันนี้ ROAS เท่าไหร่")
    assert suggestion is not None
    assert suggestion["name"] == "get_marketing_dashboard"


def test_suggest_marketing_dashboard_includes_dates():
    suggestion = _suggest_default_tool_for_data_request("ROAS เดือนนี้เท่าไหร่")
    assert suggestion is not None
    assert suggestion["name"] == "get_marketing_dashboard"
    assert "date_from" in suggestion["parameters"]
    assert "date_to" in suggestion["parameters"]
    assert suggestion["parameters"]["date_from"] <= suggestion["parameters"]["date_to"]


def test_extract_date_params_from_message_month():
    params = _extract_date_params_from_message("งบ Ads เดือนนี้")
    assert "date_from" in params
    assert "date_to" in params


def test_extract_date_params_empty_for_no_date():
    assert _extract_date_params_from_message("ROAS คืออะไร") == {}


def test_negative_leads_not_marketing():
    suggestion = _suggest_default_tool_for_data_request("ลีดวันนี้มีกี่ราย")
    assert suggestion is not None
    assert suggestion["name"] == "search_leads"


def test_negative_sales_closed_not_marketing():
    suggestion = _suggest_default_tool_for_data_request("ยอดขายที่ปิดแล้วเดือนนี้")
    assert suggestion is not None
    assert suggestion["name"] == "get_sales_closed"


def test_negative_team_kpi_not_marketing():
    suggestion = _suggest_default_tool_for_data_request("ทีมขาย KPI เดือนนี้")
    assert suggestion is not None
    assert suggestion["name"] == "get_sales_team_overview"


def test_marketing_before_team_kpi_dashboard():
    """Marketing dashboard should win over team KPI when both keywords present."""
    suggestion = _suggest_default_tool_for_data_request("Marketing dashboard KPI ทีม")
    assert suggestion is not None
    assert suggestion["name"] == "get_marketing_dashboard"


def test_marketing_keywords_tuple_not_empty():
    assert len(DATA_KEYWORDS_MARKETING) > 0
    assert "โฆษณา" in DATA_KEYWORDS_MARKETING
    assert "แคมเปญ" in DATA_KEYWORDS_MARKETING
