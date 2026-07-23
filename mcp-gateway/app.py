from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx
import jwt
from mcp.server.fastmcp import FastMCP

BACKEND_URL = os.environ.get("EVP_BACKEND_URL", "http://host.docker.internal:8000").rstrip("/")
BACKEND_TIMEOUT = float(os.environ.get("EVP_BACKEND_TIMEOUT_SECONDS", "60"))
PUBLIC_KEY = os.environ.get("EVP_EXECUTION_PUBLIC_KEY", "").replace("\\n", "\n")
TOOL_SCOPES = {
    "get_daily_summary": "crm.read",
    "search_leads": "crm.read",
    "get_sales_closed": "sales.read",
    "get_sales_unsuccessful": "sales.read",
    "get_marketing_dashboard": "marketing.read",
    "search_knowledge": "knowledge.read",
    "get_sales_team_overview": "sales.read",
    "get_sales_team_list": "sales.read",
    "get_sales_performance": "sales.read",
    "get_appointments": "crm.read",
    "get_lead_detail": "crm.read",
    "get_sales_docs": "sales.read",
}

mcp = FastMCP(
    "EVP Business Tools",
    host=os.environ.get("HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", "8001")),
    stateless_http=True,
    json_response=True,
)


async def _execute(tool: str, token: str, arguments: Dict[str, Any]) -> Any:
    if not token or not PUBLIC_KEY:
        raise ValueError("EVP execution-token verification is not configured")
    try:
        actor = jwt.decode(
            token,
            PUBLIC_KEY,
            algorithms=["EdDSA"],
            audience="evp-mcp",
            issuer="evp-api",
            options={"require": ["exp", "iat", "sub", "jti", "session_id"]},
        )
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid EVP execution context") from exc
    required_scope = TOOL_SCOPES[tool]
    if required_scope not in set(actor.get("scopes") or []):
        raise PermissionError(f"Missing execution scope: {required_scope}")
    async with httpx.AsyncClient(timeout=BACKEND_TIMEOUT) as client:
        response = await client.post(
            f"{BACKEND_URL}/api/v1/internal/tools/{tool}:execute",
            headers={"X-EVP-Execution-Token": token},
            json={"arguments": arguments},
        )
    response.raise_for_status()
    return response.json()["output"]


@mcp.tool(description="Get CRM daily lead summary for an optional YYYY-MM-DD date.")
async def get_daily_summary(evp_execution_token: str, date: Optional[str] = None) -> Any:
    return await _execute("get_daily_summary", evp_execution_token, {"date": date})


@mcp.tool(description="Search CRM leads with optional date, status, and platform filters.")
async def search_leads(
    evp_execution_token: str,
    query: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    platform: Optional[str] = None,
) -> Any:
    return await _execute("search_leads", evp_execution_token, locals_without_token(locals()))


@mcp.tool(description="Get successfully closed sales for a date range and optional salesperson/platform.")
async def get_sales_closed(
    evp_execution_token: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sales_member_id: Optional[int] = None,
    platform: Optional[str] = None,
) -> Any:
    return await _execute("get_sales_closed", evp_execution_token, locals_without_token(locals()))


@mcp.tool(description="Get unsuccessful sales for a date range and optional salesperson/platform.")
async def get_sales_unsuccessful(
    evp_execution_token: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sales_member_id: Optional[int] = None,
    platform: Optional[str] = None,
) -> Any:
    return await _execute("get_sales_unsuccessful", evp_execution_token, locals_without_token(locals()))


@mcp.tool(description="Get marketing dashboard metrics for an inclusive YYYY-MM-DD date range.")
async def get_marketing_dashboard(
    evp_execution_token: str,
    date_from: str,
    date_to: str,
    metric_focus: str = "all",
) -> Any:
    return await _execute("get_marketing_dashboard", evp_execution_token, locals_without_token(locals()))


@mcp.tool(description="Search internal EVP policies, product documents, and knowledge-base content.")
async def search_knowledge(
    evp_execution_token: str,
    query: str,
    limit: int = 5,
    category_filter: Optional[str] = None,
) -> Any:
    return await _execute("search_knowledge", evp_execution_token, locals_without_token(locals()))


@mcp.tool(description="Authoritative sales-team ranking for a date range. Use for sales-by-person, top seller, team KPI, revenue ranking, or performance questions. Returns a compact sorted ranking with employee names, deals_closed, sales_value, and conversion_rate. Do not call get_sales_closed per employee to validate this result.")
async def get_sales_team_overview(
    evp_execution_token: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sales_id: Optional[int] = None,
    period: str = "month",
) -> Any:
    return await _execute("get_sales_team_overview", evp_execution_token, locals_without_token(locals()))


@mcp.tool(description="Get active sales employees with names and work contact/profile fields. Use to resolve a sales ID to a name or list sales team members; do not use for performance ranking.")
async def get_sales_team_list(
    evp_execution_token: str,
    category: Optional[str] = None,
    status: str = "active",
) -> Any:
    return await _execute("get_sales_team_list", evp_execution_token, locals_without_token(locals()))


@mcp.tool(description="Get detailed performance for one salesperson ID over a date range. Use only when a specific sales_id is known; use get_sales_team_overview for rankings.")
async def get_sales_performance(
    evp_execution_token: str,
    sales_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    period: str = "month",
) -> Any:
    return await _execute("get_sales_performance", evp_execution_token, locals_without_token(locals()))


@mcp.tool(description="Get categorized CRM appointments for a date range: follow-up, engineer, payment, or all. Optionally filter by salesperson.")
async def get_appointments(
    evp_execution_token: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    appointment_type: Optional[str] = None,
    sales_member_id: Optional[int] = None,
) -> Any:
    return await _execute("get_appointments", evp_execution_token, locals_without_token(locals()))


@mcp.tool(description="Get complete authorized CRM detail for one lead ID, optionally including productivity logs and timeline. Use only when the user identifies a specific lead.")
async def get_lead_detail(
    evp_execution_token: str,
    lead_id: int,
    include_logs: bool = True,
) -> Any:
    return await _execute("get_lead_detail", evp_execution_token, locals_without_token(locals()))


@mcp.tool(description="Search authorized sales documents such as quotation (QT), billing, or invoice records by document number, type, query, or date range.")
async def get_sales_docs(
    evp_execution_token: str,
    query: Optional[str] = None,
    document_number: Optional[str] = None,
    doc_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> Any:
    return await _execute("get_sales_docs", evp_execution_token, locals_without_token(locals()))


def locals_without_token(values: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in values.items() if key != "evp_execution_token" and value is not None}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
