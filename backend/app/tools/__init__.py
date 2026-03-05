"""
AI Tools: DB Tools, RAG Tools, LINE Tools
"""
from app.tools.db_tools import (
    # Simple functions
    get_lead_status,
    get_daily_summary,
    get_customer_info,
    get_team_kpi,
    search_leads,
    # Enhanced functions (if they exist)
    # get_leads,  # Not implemented yet
    # get_lead_detail,  # Not implemented yet
    # get_sales_performance,  # Not implemented yet
    # get_inventory_status,  # Not implemented yet
    # get_appointments,  # Not implemented yet
    # Complete functions (if they exist)
    # get_service_appointments,  # Not implemented yet
    # get_sales_docs,  # Not implemented yet
    # get_quotations,  # Not implemented yet
    # get_permit_requests,  # Not implemented yet
    # get_stock_movements,  # Not implemented yet
    # get_user_info  # Not implemented yet
)
from app.tools.rag_tools import (
    search_documents,
    format_citations
)
from app.tools.line_tools import (
    notify_new_lead,
    notify_exception
)

__all__ = [
    # DB Tools - Simple
    "get_lead_status",
    "get_daily_summary",
    "get_customer_info",
    "get_team_kpi",
    "search_leads",
    # RAG Tools
    "search_documents",
    "format_citations",
    # LINE Tools
    "notify_new_lead",
    "notify_exception"
]
