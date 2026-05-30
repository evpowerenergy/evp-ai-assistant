"""Tests for marketing dashboard response formatter."""
from app.orchestrator.formatters.tool_response import format_tool_response


def test_format_marketing_dashboard_all_metrics():
    output = {
        "success": True,
        "data": {
            "totalSales": 1500000,
            "totalAdBudget": 50000,
            "facebookAds": {"total": 30000, "package": 20000, "wholesales": 8000, "others": 2000},
            "googleAds": {"total": 20000, "package": 12000, "wholesales": 6000, "others": 2000},
            "adCostPerLead": 250,
            "totalNewLeads": 200,
            "package": {
                "sales": 900000,
                "newLeads": 120,
                "pkOutQt": 5,
                "totalQtDocuments": 15,
                "win": 10,
                "conversionRate": 12.5,
                "winRateQt": 66.7,
            },
            "wholesales": {
                "sales": 600000,
                "newLeads": 80,
                "whOutQt": 3,
                "totalQtDocuments": 8,
                "winQt": 5,
                "winRateQt": 62.5,
                "conversionRate": 10.0,
            },
            "totalInboxFromAds": 150,
            "inboxBreakdown": {
                "packageMessages": 90,
                "packageCostPerMessage": 222.22,
                "wholesalesMessages": 40,
                "wholesalesCostPerMessage": 200,
                "otherMessages": 20,
                "otherCostPerMessage": 100,
            },
            "overallRoas": 3000.0,
            "packageRoas": 4500.0,
            "wholesalesRoas": 5000.0,
            "meta": {
                "dateFrom": "2026-03-01T00:00:00.000",
                "dateTo": "2026-03-30T23:59:59.999",
                "facebookApiConnected": True,
                "googleApiConnected": True,
            },
        },
        "metric_focus": "all",
        "date_from": "2026-03-01",
        "date_to": "2026-03-30",
    }

    text = format_tool_response(
        [{"tool": "get_marketing_dashboard", "output": output, "input": {}}],
        "ROAS เดือนนี้เท่าไหร่",
    )

    assert "Marketing Dashboard" in text
    assert "ยอดขายทั้งหมด" in text
    assert "งบ Ads ทั้งหมด" in text
    assert "Overall ROAS" in text
    assert "3000.0%" in text
    assert "Win Rate (QT)" in text
    assert "Conversion Rate (Lead)" in text


def test_format_marketing_dashboard_roas_focus():
    output = {
        "success": True,
        "data": {
            "overallRoas": 150.5,
            "packageRoas": 200.0,
            "wholesalesRoas": 100.0,
            "meta": {"facebookApiConnected": False, "googleApiConnected": True},
        },
        "metric_focus": "roas",
        "date_from": "2026-03-30",
        "date_to": "2026-03-30",
    }

    text = format_tool_response(
        [{"tool": "get_marketing_dashboard", "output": output, "input": {}}],
        "Overall ROAS วันนี้",
    )

    assert "Overall ROAS" in text
    assert "150.5%" in text
    assert "Package ROAS" in text
    # sales section omitted when focus=roas in output metric_focus - formatter uses output metric_focus
    assert "ยอดขายทั้งหมด" not in text


def test_format_marketing_dashboard_error():
    text = format_tool_response(
        [{"tool": "get_marketing_dashboard", "output": {"success": False, "error": "startDate required"}, "input": {}}],
        "marketing dashboard",
    )
    assert "เกิดข้อผิดพลาด" in text
    assert "startDate required" in text
