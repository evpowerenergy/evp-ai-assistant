"""
Marketing dashboard tools — calls marketing-dashboard-summary Edge Function.
"""
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

MARKETING_DASHBOARD_FUNCTION = "marketing-dashboard-summary"


def _function_url(name: str) -> str:
    base = settings.SUPABASE_URL.rstrip("/")
    return f"{base}/functions/v1/{name}"


async def get_marketing_dashboard(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    metric_focus: Optional[str] = "all",
    user_id: Optional[str] = None,
    user_role: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch Marketing Dashboard summary (same data as /marketing page).

    Args:
        date_from: Start date YYYY-MM-DD
        date_to: End date YYYY-MM-DD
        metric_focus: all | sales | ads | inbox | roas (hint for response formatting)
        user_id: Requesting user (logged only)
        user_role: User role (logged only)
    """
    if not date_from or not date_to:
        return {
            "success": False,
            "error": "date_from and date_to are required (YYYY-MM-DD)",
        }

    url = _function_url(MARKETING_DASHBOARD_FUNCTION)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    }
    payload = {
        "startDate": date_from[:10],
        "endDate": date_to[:10],
    }

    logger.info(
        "Calling %s date_from=%s date_to=%s user=%s role=%s focus=%s",
        MARKETING_DASHBOARD_FUNCTION,
        date_from,
        date_to,
        user_id,
        user_role,
        metric_focus,
    )

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
        body = response.json() if response.content else {}

        if response.status_code >= 400 or not body.get("success"):
            error = body.get("error") or f"HTTP {response.status_code}"
            logger.error("Marketing dashboard error: %s", error)
            return {"success": False, "error": error}

        data = body.get("data") or {}
        return {
            "success": True,
            "data": data,
            "metric_focus": metric_focus or "all",
            "date_from": date_from[:10],
            "date_to": date_to[:10],
        }
    except Exception as exc:
        logger.error("Marketing dashboard request failed: %s", exc)
        return {"success": False, "error": str(exc)}
