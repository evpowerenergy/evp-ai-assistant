"""Tests for marketing dashboard tool."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools.marketing_tools import get_marketing_dashboard


@pytest.mark.asyncio
async def test_get_marketing_dashboard_requires_dates():
    result = await get_marketing_dashboard()
    assert result["success"] is False
    assert "date_from" in result["error"]


@pytest.mark.asyncio
async def test_get_marketing_dashboard_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"success": true, "data": {"totalSales": 1000, "meta": {}}}'
    mock_response.json.return_value = {
        "success": True,
        "data": {
            "totalSales": 1000,
            "totalAdBudget": 500,
            "meta": {"facebookApiConnected": True, "googleApiConnected": True},
        },
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.tools.marketing_tools.httpx.AsyncClient", return_value=mock_client):
        result = await get_marketing_dashboard(
            date_from="2026-03-01",
            date_to="2026-03-30",
            user_id="user-1",
            user_role="manager_marketing",
        )

    assert result["success"] is True
    assert result["data"]["totalSales"] == 1000
    assert result["date_from"] == "2026-03-01"
    assert result["date_to"] == "2026-03-30"


@pytest.mark.asyncio
async def test_get_marketing_dashboard_api_error():
    mock_response = MagicMock()
    mock_response.status_code = 502
    mock_response.content = b'{"success": false, "error": "Facebook API error"}'
    mock_response.json.return_value = {"success": False, "error": "Facebook API error"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.tools.marketing_tools.httpx.AsyncClient", return_value=mock_client):
        result = await get_marketing_dashboard(
            date_from="2026-03-01",
            date_to="2026-03-30",
        )

    assert result["success"] is False
    assert "Facebook API error" in result["error"]
