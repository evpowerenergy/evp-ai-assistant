from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict

from app.tools.db_tools import (
    get_appointments,
    get_daily_summary,
    get_lead_detail,
    get_sales_closed,
    get_sales_docs,
    get_sales_performance,
    get_sales_team_list,
    get_sales_team_overview,
    get_sales_unsuccessful,
    search_leads,
)
from app.tools.marketing_tools import get_marketing_dashboard
from app.tools.rag_tools import search_documents

ToolHandler = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    scope: str
    risk: str
    handler: ToolHandler


async def _daily(args: Dict[str, Any], actor: Dict[str, Any]) -> Any:
    return await get_daily_summary(actor["sub"], date=args.get("date"), user_role=actor.get("role"))


async def _leads(args: Dict[str, Any], actor: Dict[str, Any]) -> Any:
    return await search_leads(
        query=args.get("query") or "all leads",
        user_id=actor["sub"],
        user_role=actor.get("role"),
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
        status=args.get("status"),
        platform=args.get("platform"),
    )


async def _closed(args: Dict[str, Any], actor: Dict[str, Any]) -> Any:
    return await get_sales_closed(
        user_id=actor["sub"], user_role=actor.get("role"),
        date_from=args.get("date_from"), date_to=args.get("date_to"),
        sales_member_id=args.get("sales_member_id"), platform=args.get("platform"),
    )


async def _unsuccessful(args: Dict[str, Any], actor: Dict[str, Any]) -> Any:
    return await get_sales_unsuccessful(
        user_id=actor["sub"], user_role=actor.get("role"),
        date_from=args.get("date_from"), date_to=args.get("date_to"),
        sales_member_id=args.get("sales_member_id"), platform=args.get("platform"),
    )


async def _marketing(args: Dict[str, Any], actor: Dict[str, Any]) -> Any:
    return await get_marketing_dashboard(
        date_from=args.get("date_from"), date_to=args.get("date_to"),
        metric_focus=args.get("metric_focus", "all"),
        user_id=actor["sub"], user_role=actor.get("role"),
    )


async def _knowledge(args: Dict[str, Any], actor: Dict[str, Any]) -> Any:
    results, meta = await search_documents(
        query=str(args.get("query") or ""),
        limit=min(max(int(args.get("limit", 5)), 1), 10),
        category_filter=args.get("category_filter"),
    )
    return {"results": results, "retrieval": meta}


async def _sales_team_overview(args: Dict[str, Any], actor: Dict[str, Any]) -> Any:
    result = await get_sales_team_overview(
        user_id=actor["sub"], user_role=actor.get("role"),
        date_from=args.get("date_from"), date_to=args.get("date_to"),
        sales_id=args.get("sales_id"), period=args.get("period", "month"),
    )
    # Team mode's legacy RPC also returns every lead and quotation for its old
    # dashboard. Those records are unnecessary for ranking and can add a very
    # large amount of model context. Expose only the authoritative per-member
    # metrics through MCP; keep the full response inside the legacy path.
    if args.get("sales_id") is None and isinstance(result, dict):
        data = result.get("data") if isinstance(result.get("data"), dict) else {}
        members = data.get("salesTeam") if isinstance(data, dict) else []
        compact = []
        for member in members or []:
            if not isinstance(member, dict):
                continue
            compact.append({
                "sales_id": member.get("id"),
                "name": member.get("name"),
                "department": member.get("department"),
                "position": member.get("position"),
                "deals_closed": member.get("deals_closed", 0),
                "sales_value": member.get("pipeline_value", 0),
                "conversion_rate": member.get("conversion_rate", 0),
                "total_leads": member.get("total_leads", 0),
            })
        compact.sort(key=lambda item: float(item.get("sales_value") or 0), reverse=True)
        return {
            "success": bool(result.get("success", True)),
            "date_from": args.get("date_from"),
            "date_to": args.get("date_to"),
            "ranking": compact,
            "member_count": len(compact),
        }
    return result


async def _sales_team_list(args: Dict[str, Any], actor: Dict[str, Any]) -> Any:
    return await get_sales_team_list(
        user_id=actor["sub"], user_role=actor.get("role"),
        category=args.get("category"), status=args.get("status", "active"),
    )


async def _sales_performance(args: Dict[str, Any], actor: Dict[str, Any]) -> Any:
    return await get_sales_performance(
        sales_id=int(args["sales_id"]), user_id=actor["sub"],
        user_role=actor.get("role"), date_from=args.get("date_from"),
        date_to=args.get("date_to"), period=args.get("period", "month"),
    )


async def _appointments(args: Dict[str, Any], actor: Dict[str, Any]) -> Any:
    return await get_appointments(
        user_id=actor["sub"], user_role=actor.get("role"),
        date_from=args.get("date_from"), date_to=args.get("date_to"),
        appointment_type=args.get("appointment_type"),
        sales_member_id=args.get("sales_member_id"), filters=args.get("filters"),
    )


async def _lead_detail(args: Dict[str, Any], actor: Dict[str, Any]) -> Any:
    return await get_lead_detail(
        lead_id=int(args["lead_id"]), user_id=actor["sub"],
        include_logs=bool(args.get("include_logs", True)),
    )


async def _sales_docs(args: Dict[str, Any], actor: Dict[str, Any]) -> Any:
    return await get_sales_docs(
        user_id=actor["sub"], query=args.get("query"),
        document_number=args.get("document_number"), doc_type=args.get("doc_type"),
        date_from=args.get("date_from"), date_to=args.get("date_to"),
        filters=args.get("filters"), limit=min(max(int(args.get("limit", 50)), 1), 100),
    )


TOOL_REGISTRY: Dict[str, ToolSpec] = {
    "get_daily_summary": ToolSpec("get_daily_summary", "crm.read", "read", _daily),
    "search_leads": ToolSpec("search_leads", "crm.read", "read", _leads),
    "get_sales_closed": ToolSpec("get_sales_closed", "sales.read", "read", _closed),
    "get_sales_unsuccessful": ToolSpec("get_sales_unsuccessful", "sales.read", "read", _unsuccessful),
    "get_marketing_dashboard": ToolSpec("get_marketing_dashboard", "marketing.read", "read", _marketing),
    "search_knowledge": ToolSpec("search_knowledge", "knowledge.read", "read", _knowledge),
    "get_sales_team_overview": ToolSpec("get_sales_team_overview", "sales.read", "read", _sales_team_overview),
    "get_sales_team_list": ToolSpec("get_sales_team_list", "sales.read", "read", _sales_team_list),
    "get_sales_performance": ToolSpec("get_sales_performance", "sales.read", "read", _sales_performance),
    "get_appointments": ToolSpec("get_appointments", "crm.read", "read", _appointments),
    "get_lead_detail": ToolSpec("get_lead_detail", "crm.read", "read", _lead_detail),
    "get_sales_docs": ToolSpec("get_sales_docs", "sales.read", "read", _sales_docs),
}
