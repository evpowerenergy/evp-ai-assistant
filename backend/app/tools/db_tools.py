"""
Database RPC Tools (Allowlist)
AI tools for querying database via RPC functions
"""
import re
from typing import Dict, Any, Optional, List
from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _map_sales_logs_to_leads(sales_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Map RPC salesLogs[] (each item may be { lead: {...} } or a lead object) to salesLeads
    so downstream can use same logic as /reports/sales-closed (totalQuotationCount, totalQuotationAmount, category).
    """
    leads: List[Dict[str, Any]] = []
    for log in sales_logs or []:
        if not isinstance(log, dict):
            continue
        lead = log.get("lead") if isinstance(log.get("lead"), dict) else log
        if not isinstance(lead, dict):
            continue
        # Ensure fields expected by _compute_sales_closed_category_summary
        row = dict(lead)
        if "totalQuotationCount" not in row and "total_quotation_count" in row:
            row["totalQuotationCount"] = row["total_quotation_count"]
        if "totalQuotationAmount" not in row and "total_quotation_amount" in row:
            row["totalQuotationAmount"] = row["total_quotation_amount"]
        if "category" not in row and "lead_category" in row:
            row["category"] = row["lead_category"]
        if row.get("totalQuotationCount") is None:
            row["totalQuotationCount"] = 1
        if row.get("totalQuotationAmount") is None:
            row["totalQuotationAmount"] = 0
        leads.append(row)
    return leads


def _normalize_sales_closed_response(raw: Any) -> Dict[str, Any]:
    """
    Normalize RPC response so we always have data.salesLeads (and totalSalesValue, salesCount).
    RPC may return data.salesLogs (with .lead inside) instead of data.salesLeads.
    """
    if isinstance(raw, list) and len(raw) == 1:
        raw = raw[0]
    if not raw or not isinstance(raw, dict):
        return {"success": False, "error": "No data returned", "data": {"salesLeads": [], "totalSalesValue": 0, "salesCount": 0}}
    data = raw.get("data") if isinstance(raw.get("data"), dict) else (raw if (raw.get("salesLeads") is not None or raw.get("salesLogs") is not None) else None)
    if not data or not isinstance(data, dict):
        return {"success": True, "data": {"salesLeads": [], "totalSalesValue": float(raw.get("totalSalesValue") or 0), "salesCount": int(raw.get("salesCount") or 0)}}
    leads = list(data.get("salesLeads") or [])
    if not leads and data.get("salesLogs"):
        leads = _map_sales_logs_to_leads(data.get("salesLogs"))
    total = float(data.get("totalSalesValue") or raw.get("totalSalesValue") or 0)
    count = int(data.get("salesCount") or raw.get("salesCount") or 0)
    if not count and leads:
        count = sum(int(l.get("totalQuotationCount") or 1) for l in leads)
    return {
        "success": True,
        "data": {
            "salesLeads": leads,
            "totalSalesValue": total,
            "salesCount": count,
        },
    }


async def _get_sales_closed_single_month(
    user_id: str,
    date_from: str,
    date_to: str,
    sales_member_id: Optional[int],
    user_role: Optional[str],
) -> Dict[str, Any]:
    """Call RPC ai_get_sales_closed. Uses same date format as /reports/sales-closed (no timezone) so results match the web."""
    # Match web page: startDate + 'T00:00:00.000', endDate + 'T23:59:59.999' (no +07:00)
    # Web uses Supabase .gte/.lte with timestamps without TZ → Postgres uses session TZ (typically UTC)
    date_from_ts = f"{date_from}T00:00:00.000"
    date_to_ts = f"{date_to}T23:59:59.999"
    supabase = get_supabase_client()
    result = supabase.rpc(
        "ai_get_sales_closed",
        {
            "p_user_id": user_id,
            "p_date_from": date_from_ts,
            "p_date_to": date_to_ts,
            "p_sales_member_id": sales_member_id,
            "p_user_role": user_role or "staff",
        }
    ).execute()
    if result.data:
        return _normalize_sales_closed_response(result.data)
    if result.error:
        return {"success": False, "error": result.error.message}
    return {"success": False, "error": "No data returned", "data": {"salesLeads": [], "totalSalesValue": 0, "salesCount": 0}}


def _lead_sales_value(lead: Dict[str, Any]) -> float:
    """Get sales/quotation value for a lead (for sales closed filtering sum)."""
    v = lead.get("totalQuotationAmount") or lead.get("total_quotation_amount") or lead.get("totalSalesAmount") or lead.get("total_sales_amount") or lead.get("quotation_value") or 0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


async def get_sales_closed(
    user_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sales_member_id: Optional[int] = None,
    user_role: Optional[str] = None,
    platform: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sales Closed report via RPC (matches /reports/sales-closed logic).
    If platform is set, filter salesLeads by that platform so count/value match report filtered by platform.
    RPC: ai_get_sales_closed(user_id, date_from_ts, date_to_ts, sales_member_id, user_role)
    """
    try:
        if not date_from or not date_to:
            date_from_ts = f"{date_from}T00:00:00.000" if date_from else None
            date_to_ts = f"{date_to}T23:59:59.999" if date_to else None
            supabase = get_supabase_client()
            result = supabase.rpc(
                "ai_get_sales_closed",
                {
                    "p_user_id": user_id,
                    "p_date_from": date_from_ts,
                    "p_date_to": date_to_ts,
                    "p_sales_member_id": sales_member_id,
                    "p_user_role": user_role or "staff",
                }
            ).execute()
            if result.data:
                ret = _normalize_sales_closed_response(result.data)
                if platform and ret.get("data"):
                    _apply_platform_filter_sales_closed(ret["data"], platform)
                return ret
            if result.error:
                return {"success": False, "error": result.error.message}
            return {"success": False, "error": "No data returned", "data": {"salesLeads": [], "totalSalesValue": 0, "salesCount": 0}}

        ret = await _get_sales_closed_single_month(
            user_id, date_from, date_to, sales_member_id, user_role
        )
        if ret.get("data") and isinstance(ret["data"], dict):
            ret["data"]["request_date_from"] = date_from
            ret["data"]["request_date_to"] = date_to
            if platform:
                _apply_platform_filter_sales_closed(ret["data"], platform)
        return ret
    except Exception as e:
        logger.error(f"❌ Error in get_sales_closed: {e}")
        return {"success": False, "error": str(e)}


def _apply_platform_filter_sales_closed(data: Dict[str, Any], platform: str) -> None:
    """Filter data['salesLeads'] by platform and recompute salesCount/totalSalesValue. Modifies data in place."""
    platform_canon = _normalize_platform_filter(platform)
    if not platform_canon:
        return
    leads = list(data.get("salesLeads") or [])
    platform_canon_lower = platform_canon.lower()
    filtered = [
        l for l in leads
        if (_lead_platform_value(l) or "").strip().lower() == platform_canon_lower
    ]
    data["salesLeads"] = filtered
    data["salesCount"] = len(filtered)
    data["totalSalesValue"] = sum(_lead_sales_value(l) for l in filtered)
    data["request_platform"] = platform_canon
    logger.info(f"   📊 get_sales_closed filtered by platform={platform_canon}: {len(filtered)} leads")


# Map LLM/platform input to canonical platform value (as stored in leads)
PLATFORM_NORMALIZE = {
    "huawei": "Huawei",
    "atmoc": "ATMOCE",
    "atmoce": "ATMOCE",
    "solar edge": "Solar Edge",
    "solaredge": "Solar Edge",
    "sigenergy": "Sigenergy",
    "facebook": "Facebook",
    "line": "Line",
    "website": "Website",
    "tiktok": "TikTok",
    "ig": "IG",
    "youtube": "YouTube",
    "shopee": "Shopee",
    "lazada": "Lazada",
}


def _normalize_platform_filter(platform: Optional[str]) -> Optional[str]:
    """Return canonical platform value for filtering, or None if empty."""
    if not platform or not str(platform).strip():
        return None
    s = str(platform).strip().lower()
    return PLATFORM_NORMALIZE.get(s) or platform.strip()


def _normalize_sales_unsuccessful_response(raw: Any) -> Dict[str, Any]:
    """Normalize RPC ai_get_sales_unsuccessful response."""
    if isinstance(raw, list) and len(raw) == 1:
        raw = raw[0]
    if not raw or not isinstance(raw, dict):
        return {"success": False, "error": "No data returned", "data": {"unsuccessfulLeads": [], "unsuccessfulCount": 0, "totalQuotationValue": 0}}
    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    if not data or not isinstance(data, dict):
        return {"success": True, "data": {"unsuccessfulLeads": [], "unsuccessfulCount": 0, "totalQuotationValue": 0}}
    leads = list(data.get("unsuccessfulLeads") or [])
    count = int(data.get("unsuccessfulCount") or 0)
    total_val = float(data.get("totalQuotationValue") or 0)
    return {
        "success": True,
        "data": {
            "unsuccessfulLeads": leads,
            "unsuccessfulCount": count,
            "totalQuotationValue": total_val,
            "unsuccessfulLogs": data.get("unsuccessfulLogs", []),
            "quotations": data.get("quotations", []),
        },
    }


def _lead_platform_value(lead: Dict[str, Any]) -> Optional[str]:
    """Get platform from lead dict (may be platform or lead_platform)."""
    return lead.get("platform") or lead.get("lead_platform") or lead.get("platform_name")


def _lead_quotation_amount(lead: Dict[str, Any]) -> float:
    """Get quotation amount for a lead (for filtering sum)."""
    v = lead.get("totalQuotationAmount") or lead.get("total_quotation_amount") or lead.get("quotation_value") or 0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


async def get_sales_unsuccessful(
    user_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sales_member_id: Optional[int] = None,
    user_role: Optional[str] = None,
    platform: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sales Unsuccessful report via RPC (matches /reports/sales-unsuccessful logic).
    ดึงจาก lead_productivity_logs ที่ status = 'ปิดการขายไม่สำเร็จ'
    If platform is set, filter unsuccessfulLeads by that platform so count/value match report filtered by platform.
    RPC: ai_get_sales_unsuccessful(user_id, date_from_ts, date_to_ts, sales_member_id, user_role)
    """
    try:
        date_from_ts = f"{date_from}T00:00:00.000" if date_from else None
        date_to_ts = f"{date_to}T23:59:59.999" if date_to else None
        supabase = get_supabase_client()
        result = supabase.rpc(
            "ai_get_sales_unsuccessful",
            {
                "p_user_id": user_id,
                "p_date_from": date_from_ts,
                "p_date_to": date_to_ts,
                "p_sales_member_id": sales_member_id,
                "p_user_role": user_role or "staff",
            }
        ).execute()
        if result.data:
            ret = _normalize_sales_unsuccessful_response(result.data)
            if ret.get("data") and isinstance(ret["data"], dict):
                ret["data"]["request_date_from"] = date_from
                ret["data"]["request_date_to"] = date_to
                # Optional: filter by platform so count matches report when user asks e.g. "ลีด Huawei ปิดการขายไม่ได้กี่ราย"
                platform_canon = _normalize_platform_filter(platform)
                if platform_canon:
                    leads = list(ret["data"].get("unsuccessfulLeads") or [])
                    platform_canon_lower = platform_canon.lower()
                    filtered = [
                        l for l in leads
                        if (_lead_platform_value(l) or "").strip().lower() == platform_canon_lower
                    ]
                    ret["data"]["unsuccessfulLeads"] = filtered
                    ret["data"]["unsuccessfulCount"] = len(filtered)
                    ret["data"]["totalQuotationValue"] = sum(_lead_quotation_amount(l) for l in filtered)
                    ret["data"]["request_platform"] = platform_canon
                    logger.info(f"   📊 get_sales_unsuccessful filtered by platform={platform_canon}: {len(filtered)} leads")
            return ret
        if result.error:
            return {"success": False, "error": result.error.message}
        return {"success": False, "error": "No data returned", "data": {"unsuccessfulLeads": [], "unsuccessfulCount": 0, "totalQuotationValue": 0}}
    except Exception as e:
        logger.error(f"❌ Error in get_sales_unsuccessful: {e}")
        return {"success": False, "error": str(e)}


async def get_daily_summary(user_id: str, date: Optional[str] = None, user_role: Optional[str] = None) -> Dict[str, Any]:
    """
    Get daily summary via RPC
    RPC: ai_get_daily_summary(user_id, date, role)
    """
    try:
        from datetime import date as date_class
        
        # Use current date if not provided
        if date is None:
            date = str(date_class.today())
        
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_get_daily_summary",
            {
                "p_user_id": user_id,
                "p_date": date,
                "p_user_role": user_role or "staff"  # Pass role as parameter
            }
        ).execute()
        
        logger.info(f"   📞 Calling RPC: ai_get_daily_summary")
        logger.info(f"   Parameters: user_id={user_id}, date={date}, role={user_role or 'staff'}")
        db_result = result.data if result.data else {}
        logger.info(f"   📥 RPC Response: {db_result}")
        return db_result
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_daily_summary): {e}")
        return {"error": str(e)}


async def get_customer_info(customer_name: str, user_id: str) -> Dict[str, Any]:
    """
    Get customer information via RPC
    RPC: ai_get_customer_info(customer_name, user_id)
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_get_customer_info",
            {
                "p_customer_name": customer_name,
                "p_user_id": user_id
            }
        ).execute()
        
        logger.info(f"RPC: ai_get_customer_info, customer={customer_name}, user={user_id}")
        return result.data if result.data else {}
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_customer_info): {e}")
        return {"error": str(e)}


async def get_team_kpi(
    team_id: Optional[int],
    user_id: str,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user_role: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get team KPI via RPC
    RPC: ai_get_team_kpi(user_id, team_id, category, date_from, date_to)
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_get_team_kpi",
            {
                "p_user_id": user_id,
                "p_team_id": team_id,
                "p_category": category,
                "p_date_from": date_from,
                "p_date_to": date_to
            }
        ).execute()
        
        logger.info(f"📞 Calling RPC: ai_get_team_kpi")
        logger.info(f"   Parameters: team_id={team_id}, user_id={user_id}, category={category}, date_from={date_from}, date_to={date_to}")
        db_result = result.data if result.data else {}
        logger.info(f"   📥 RPC Response received")
        return db_result
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_team_kpi): {e}")
        return {"error": str(e), "success": False}


async def search_leads(
    query: str,
    user_id: str,
    filters: Optional[Dict[str, Any]] = None,
    user_role: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    platform: Optional[str] = None  # From LLM / context (applies PLATFORM RULE)
) -> Dict[str, Any]:
    """
    Search/List leads via RPC
    RPC: ai_get_leads(user_id, filters, date_from, date_to, limit)
    
    Supports date range extraction from natural language:
    - "เมื่อวาน" → yesterday
    - "สัปดาห์นี้" → this week
    - "เดือนนี้" → this month
    - "วันที่ 15 มกราคม" → specific date
    - "ระหว่าง 1-5 มกราคม" → date range
    
    Supports sales/closed detection:
    - If query indicates "ปิดการขายไม่สำเร็จ" (ปิดไม่ได้ / ปิดไม่สำเร็จ): use ai_get_leads with status='ยังปิดการขายไม่สำเร็จ'.
      Do NOT route to ai_get_sales_closed — it returns only successfully closed sales.
    - If query/status indicates SALES CLOSED SUCCESS (ยอดขาย / ปิดการขายได้ / closed), route to ai_get_sales_closed
      which matches /reports/sales-closed logic (lead_productivity_logs + quotation_documents).
    """
    try:
        from app.utils.date_extractor import extract_date_range
        
        supabase = get_supabase_client()
        
        # Extract structured data from query if it's a dict (LLM might send structured query)
        query_dict = None
        query_string = ""
        if isinstance(query, dict):
            # Store dict for extracting structured fields
            query_dict = query
            # Extract platform/brand/source from dict
            # Support multiple field names: platform, brand, source
            platform = query_dict.get("platform") or query_dict.get("brand") or query_dict.get("source")
            if platform:
                # Initialize filters if not exists
                if filters is None:
                    filters = {}
                filters['platform'] = str(platform)
                logger.info(f"   📊 Extracted platform/brand from query dict: {platform}")
            
            # Extract category if present
            category = query_dict.get("category")
            if category:
                if filters is None:
                    filters = {}
                filters['category'] = str(category)
                logger.info(f"   📊 Extracted category from query dict: {category}")
            
            # Convert dict to string for text processing
            query_string = query_dict.get("query", query_dict.get("text", str(query_dict)))
        else:
            query_string = str(query) if query is not None else ""
        
        # Extract date range from query string if not provided
        if date_from is None and date_to is None:
            date_from, date_to = extract_date_range(query_string)
            if date_from or date_to:
                logger.info(f"   📅 Extracted date range from query: {date_from} to {date_to}")
        
        # Also check query_dict for date_range if present
        if query_dict and (date_from is None or date_to is None):
            date_range = query_dict.get("date_range")
            if date_range:
                date_from, date_to = extract_date_range(str(date_range))
                if date_from or date_to:
                    logger.info(f"   📅 Extracted date range from query_dict.date_range: {date_from} to {date_to}")
        
        # Detect "ปิดการขายไม่สำเร็จ" — ใช้ get_sales_unsuccessful (ai_get_sales_unsuccessful)
        # ไม่ใช่ ai_get_leads — เพราะต้องใช้ log.created_at_thai (วันที่บันทึก) ให้ตรงหน้า /reports/sales-unsuccessful
        query_lower = query_string.lower() if query_string else ""
        failed_close_markers = (
            "ปิดการขายไม่ได้",
            "ปิดไม่ได้",
            "ปิดไม่สำเร็จ",
            "ยังปิดการขายไม่สำเร็จ",
        )
        is_failed_close_query = any(m in query_lower for m in failed_close_markers)
        if is_failed_close_query or status == "ยังปิดการขายไม่สำเร็จ":
            # Route to ai_get_sales_unsuccessful (ตรงกับหน้า /reports/sales-unsuccessful)
            # ต้องมี date_from/date_to — ถ้าไม่มีจะ extract จาก query
            if date_from is None or date_to is None:
                date_from, date_to = extract_date_range(query_string)
            if date_from and date_to:
                logger.info(f"   📊 Routing to ai_get_sales_unsuccessful (ปิดการขายไม่สำเร็จ)")
                return await get_sales_unsuccessful(
                    user_id=user_id,
                    date_from=date_from,
                    date_to=date_to,
                    sales_member_id=None,
                    user_role=user_role
                )
            # ถ้าไม่มี date ให้ใช้ ai_get_leads ตามเดิม
            status = "ยังปิดการขายไม่สำเร็จ"
            is_sales_closed_query = False
        else:
            # Detect sales-closed (SUCCESS) intent from query or status
            # IMPORTANT: If LLM passes status='ปิดการขายแล้ว' (operation_status wording),
            # we must route to ai_get_sales_closed (productivity logs), not ai_get_leads.
            is_sales_closed_query = False
            sales_closed_status_markers = {
                "sales_closed",
                "closed",
                "ปิดการขายแล้ว",
                "ปิดการขาย",
            }
            if any(keyword in query_lower for keyword in ["ยอดขาย", "ปิดการขาย", "closed", "sales closed"]):
                is_sales_closed_query = True
            if status is not None and str(status).strip() in sales_closed_status_markers:
                is_sales_closed_query = True
                status = "sales_closed"
        
        # If this is a sales/closed (SUCCESS) query, use ai_get_sales_closed instead
        if is_sales_closed_query or status == "sales_closed":
            # Match /reports/sales-closed: no timezone (created_at_thai already +7 via trigger)
            date_from_ts = None
            date_to_ts = None
            
            if date_from:
                date_from_ts = f"{date_from}T00:00:00.000"
            
            if date_to:
                date_to_ts = f"{date_to}T23:59:59.999"
            
            logger.info(f"   📊 Using ai_get_sales_closed for sales/closed query")
            result = supabase.rpc(
                "ai_get_sales_closed",
                {
                    "p_user_id": user_id,
                    "p_date_from": date_from_ts,
                    "p_date_to": date_to_ts,
                    "p_sales_member_id": None,  # Can be added later if needed
                    "p_user_role": user_role or "staff"
                }
            ).execute()
            
            logger.info(f"   📞 Calling RPC: ai_get_sales_closed")
            logger.info(f"   Parameters: user_id={user_id}, date_from={date_from_ts}, date_to={date_to_ts}, query={query_string}")
            db_result = result.data if result.data else {}
            logger.info(f"   📥 RPC Response: {db_result}")
            return db_result
        
        # Build filters dict for regular leads query
        final_filters = filters.copy() if filters else {}
        if status and status != 'sales_closed':
            final_filters['status'] = status
            logger.info(f"   📊 Status filter: {status}")
        # Explicit platform from LLM/conversation context (PLATFORM RULE)
        if platform and 'platform' not in final_filters:
            platform_canon = _normalize_platform_filter(platform)
            if platform_canon:
                final_filters['platform'] = platform_canon
                logger.info(f"   📊 Platform from context/params: {platform_canon}")
        
        # Extract phone number from query if not already in filters
        # Supports: "เบอร์โทร 0886030830", "เบอร์ 0886030830", "0886030830", etc.
        if 'tel' not in final_filters and query_string:
            tel_match = re.search(r'0\d{8,9}', query_string)
            if tel_match:
                extracted_tel = tel_match.group(0)
                final_filters['tel'] = extracted_tel
                logger.info(f"   📱 Extracted phone from query: {extracted_tel}")
        
        # Also extract platform from query string if not already in filters
        if 'platform' not in final_filters and query_string:
            # Try to detect platform keywords in query string
            platform_keywords = {
                'huawei': 'Huawei',
                'atmoc': 'ATMOCE',
                'solar edge': 'Solar Edge',
                'sigenergy': 'Sigenergy',
                'facebook': 'Facebook',
                'line': 'Line',
                'website': 'Website',
                'tiktok': 'TikTok',
                'ig': 'IG',
                'youtube': 'YouTube',
                'shopee': 'Shopee',
                'lazada': 'Lazada',
            }
            query_lower_check = query_string.lower()
            for keyword, platform_value in platform_keywords.items():
                if keyword in query_lower_check:
                    final_filters['platform'] = platform_value
                    logger.info(f"   📊 Detected platform from query string: {platform_value}")
                    break
        
        # Use ai_get_leads for regular listing
        # No limit - get all results based on user query
        result = supabase.rpc(
            "ai_get_leads",
            {
                "p_user_id": user_id,
                "p_filters": final_filters,
                "p_date_from": date_from,
                "p_date_to": date_to,
                "p_limit": None,  # No limit - get all results
                "p_user_role": user_role or "staff"
            }
        ).execute()
        
        logger.info(f"   📞 Calling RPC: ai_get_leads")
        logger.info(f"   Parameters: user_id={user_id}, date_from={date_from}, date_to={date_to}, status={status}, query={query}")
        db_result = result.data if result.data else {}
        logger.info(f"   📥 RPC Response: {db_result}")
        return db_result
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Search leads error: {e}")
        logger.error(f"   Error type: {type(e)}")
        
        # Check if RPC function doesn't exist
        if "function" in error_msg.lower() and ("does not exist" in error_msg.lower() or "not found" in error_msg.lower()):
            logger.error(f"   ❌ RPC function 'ai_get_leads' might not exist. Please run migration: 20250117000003_fix_ai_get_leads_role.sql")
            return {
                "error": f"RPC function not found: {error_msg}",
                "success": False,
                "message": "Please ensure migration 20250117000003_fix_ai_get_leads_role.sql has been run"
            }
        
        # Return error details for debugging
        return {
            "error": error_msg,
            "success": False,
            "message": f"Failed to search leads: {error_msg}"
        }


async def get_service_appointments(
    user_id: str,
    filters: Optional[Dict[str, Any]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    appointment_type: str = "all"
) -> Dict[str, Any]:
    """
    Get service appointments via RPC
    RPC: ai_get_service_appointments(user_id, filters, date_from, date_to, type)
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_get_service_appointments",
            {
                "p_user_id": user_id,
                "p_filters": filters or {},
                "p_date_from": date_from,
                "p_date_to": date_to,
                "p_type": appointment_type
            }
        ).execute()
        
        logger.info(f"RPC: ai_get_service_appointments, user={user_id}, type={appointment_type}")
        return result.data if result.data else {}
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_service_appointments): {e}")
        return {"error": str(e)}


async def get_sales_docs(
    user_id: str,
    filters: Optional[Dict[str, Any]] = None,
    query: Optional[str] = None,
    document_number: Optional[str] = None,
    doc_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get sales documents (QT/BL/INV) via RPC
    RPC: ai_get_sales_docs(user_id, filters, date_from, date_to, limit)
    """
    try:
        supabase = get_supabase_client()
        # Post-filter by document number when user asks a specific QT/INV/BL id.
        # ai_get_sales_docs currently does not provide document_number filter in SQL.
        target_doc = (document_number or "").strip()
        if not target_doc and query:
            m = re.search(r"([A-Za-z]{2,5}\d{6,})", str(query), flags=re.IGNORECASE)
            if m:
                target_doc = m.group(1)

        # ai_get_sales_docs currently has a DB-side type mismatch on doc_type filter.
        # For QT queries, use dedicated ai_get_quotations and normalize response shape.
        wants_qt = bool(
            (doc_type and str(doc_type).strip().upper() == "QT")
            or (target_doc and target_doc.strip().upper().startswith("QT"))
            or ("qt" in str(query or "").lower())
            or ("quotation" in str(query or "").lower())
            or ("ใบเสนอราคา" in str(query or ""))
        )
        if wants_qt:
            # Prefer RPC-first for stable response contract and DB-side execution.
            # Fallback to direct table query if the new RPC is unavailable.
            try:
                rpc_result = supabase.rpc(
                    "ai_get_qt_doc_detail",
                    {
                        "p_user_id": user_id,
                        "p_document_number": target_doc if target_doc else None,
                        "p_date_from": date_from,
                        "p_date_to": date_to,
                        "p_limit": limit,
                    },
                ).execute()
                rpc_payload = rpc_result.data if rpc_result.data else {}
                if isinstance(rpc_payload, dict) and rpc_payload.get("success"):
                    logger.info(
                        f"RPC: ai_get_qt_doc_detail, doc_number={target_doc or '-'}"
                    )
                    return rpc_payload
            except Exception as rpc_exc:
                logger.warning(
                    f"RPC ai_get_qt_doc_detail unavailable/failed, fallback to table query. details={rpc_exc}"
                )

            # Robust QT detail path: query quotation_documents directly and enrich
            # with lead/productivity/sales owner context.
            try:
                qd_query = supabase.table("quotation_documents").select(
                    "id,document_number,amount,productivity_log_id,document_type,created_at_thai"
                )
                if target_doc:
                    qd_query = qd_query.ilike("document_number", f"%{target_doc}%")
                qd_rows_res = qd_query.limit(max(limit, 200)).execute()
                qd_rows = list(qd_rows_res.data or [])
            except Exception:
                # Some environments may not have created_at_thai on quotation_documents.
                qd_query = supabase.table("quotation_documents").select(
                    "id,document_number,amount,productivity_log_id,document_type"
                )
                if target_doc:
                    qd_query = qd_query.ilike("document_number", f"%{target_doc}%")
                qd_rows_res = qd_query.limit(max(limit, 200)).execute()
                qd_rows = list(qd_rows_res.data or [])

            # Keep only quotation/QT docs and exact target when available
            qd_filtered = []
            for r in qd_rows:
                if not isinstance(r, dict):
                    continue
                doc_type_raw = str(r.get("document_type", "")).strip().lower()
                if doc_type_raw and doc_type_raw not in ["quotation", "qt"]:
                    continue
                if target_doc:
                    dn = str(r.get("document_number", "")).strip().lower()
                    td = target_doc.lower()
                    if dn != td and td not in dn:
                        continue
                qd_filtered.append(r)

            log_ids = [r.get("productivity_log_id") for r in qd_filtered if r.get("productivity_log_id") is not None]
            logs_by_id: Dict[int, Dict[str, Any]] = {}
            leads_by_id: Dict[int, Dict[str, Any]] = {}
            sales_by_id: Dict[int, Dict[str, Any]] = {}

            if log_ids:
                logs_res = supabase.table("lead_productivity_logs").select(
                    "id,lead_id,sale_id,status,created_at_thai"
                ).in_("id", log_ids).execute()
                for row in (logs_res.data or []):
                    if isinstance(row, dict) and row.get("id") is not None:
                        logs_by_id[int(row["id"])] = row

            lead_ids = [
                int(v.get("lead_id"))
                for v in logs_by_id.values()
                if v.get("lead_id") is not None
            ]
            if lead_ids:
                leads_res = supabase.table("leads").select(
                    "id,display_name,full_name,status,sale_owner_id,post_sales_owner_id"
                ).in_("id", lead_ids).execute()
                for row in (leads_res.data or []):
                    if isinstance(row, dict) and row.get("id") is not None:
                        leads_by_id[int(row["id"])] = row

            sale_ids = {
                int(v.get("sale_id"))
                for v in logs_by_id.values()
                if v.get("sale_id") is not None
            }
            if sale_ids:
                try:
                    sales_res = supabase.table("sales_team_with_user_info").select(
                        "id,name,first_name,last_name,email,phone"
                    ).in_("id", list(sale_ids)).execute()
                except Exception:
                    # Some environments expose only a subset of columns on this view.
                    try:
                        sales_res = supabase.table("sales_team_with_user_info").select(
                            "id,name,email,phone"
                        ).in_("id", list(sale_ids)).execute()
                    except Exception:
                        sales_res = supabase.table("sales_team_with_user_info").select(
                            "id,name"
                        ).in_("id", list(sale_ids)).execute()
                for row in (sales_res.data or []):
                    if isinstance(row, dict) and row.get("id") is not None:
                        sales_by_id[int(row["id"])] = row

            sales_docs = []
            for r in qd_filtered:
                log = logs_by_id.get(int(r.get("productivity_log_id") or 0), {})
                lead = leads_by_id.get(int(log.get("lead_id") or 0), {})
                sale = sales_by_id.get(int(log.get("sale_id") or 0), {})
                sale_name = (
                    sale.get("name")
                    or " ".join([str(sale.get("first_name") or "").strip(), str(sale.get("last_name") or "").strip()]).strip()
                    or None
                )
                customer_name = lead.get("display_name") or lead.get("full_name")
                sales_docs.append(
                    {
                        "id": r.get("id"),
                        "doc_number": r.get("document_number"),
                        "doc_type": "QT",
                        "doc_date": r.get("created_at_thai") or log.get("created_at_thai"),
                        "total_amount": r.get("amount") or 0,
                        "lead_id": log.get("lead_id"),
                        "customer_name": customer_name,
                        "lead_status": lead.get("status"),
                        "sale_id": log.get("sale_id"),
                        "sale_name": sale_name,
                        "sale_email": sale.get("email"),
                        "sale_phone": sale.get("phone"),
                        "productivity_log_id": r.get("productivity_log_id"),
                        "source": "quotation_documents",
                    }
                )
            payload = {
                "success": True,
                "data": {
                    "sales_docs": sales_docs,
                    "stats": {
                        "returned": len(sales_docs),
                        "source_total": len(qd_rows),
                    },
                },
                "meta": {
                    "source_rpc": "quotation_documents",
                    "document_number_filter": target_doc or None,
                    "doc_type_filter": "QT",
                    "date_from": date_from,
                    "date_to": date_to,
                },
            }
            logger.info(
                f"QT detail query via quotation_documents, doc_number={target_doc or '-'}, matched={len(sales_docs)}"
            )
            return payload

        rpc_filters = (filters or {}).copy()
        result = supabase.rpc(
            "ai_get_sales_docs",
            {
                "p_user_id": user_id,
                "p_filters": rpc_filters,
                "p_date_from": date_from,
                "p_date_to": date_to,
                "p_limit": limit
            }
        ).execute()
        payload = result.data if result.data else {}
        if isinstance(payload, dict):
            docs = list(((payload.get("data") or {}).get("sales_docs") or []))
            filtered = docs

            # Apply doc_type filter in Python to avoid DB type mismatch
            if doc_type:
                doc_type_u = str(doc_type).strip().upper()
                filtered = [d for d in filtered if str(d.get("doc_type", "")).strip().upper() == doc_type_u]

            if target_doc:
                target_doc_l = target_doc.lower()
                filtered_exact = [d for d in filtered if str(d.get("doc_number", "")).lower() == target_doc_l]
                filtered = filtered_exact if filtered_exact else [d for d in filtered if target_doc_l in str(d.get("doc_number", "")).lower()]

            # If any post-filter was applied, write filtered result back
            if doc_type or target_doc:
                payload.setdefault("data", {})
                payload["data"]["sales_docs"] = filtered
                payload.setdefault("meta", {})
                if target_doc:
                    payload["meta"]["document_number_filter"] = target_doc
                if doc_type:
                    payload["meta"]["doc_type_filter"] = doc_type
                if isinstance(payload["data"].get("stats"), dict):
                    payload["data"]["stats"]["returned"] = len(filtered)
                logger.info(
                    f"RPC: ai_get_sales_docs post-filter doc_type={doc_type or '-'} doc_number={target_doc or '-'} matched={len(filtered)}"
                )

        logger.info(f"RPC: ai_get_sales_docs, user={user_id}")
        return payload
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_sales_docs): {e}")
        return {"error": str(e)}


async def get_permit_requests(
    user_id: str,
    filters: Optional[Dict[str, Any]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get permit requests via RPC
    RPC: ai_get_permit_requests(user_id, filters, date_from, date_to, limit)
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_get_permit_requests",
            {
                "p_user_id": user_id,
                "p_filters": filters or {},
                "p_date_from": date_from,
                "p_date_to": date_to,
                "p_limit": limit
            }
        ).execute()
        
        logger.info(f"RPC: ai_get_permit_requests, user={user_id}")
        return result.data if result.data else {}
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_permit_requests): {e}")
        return {"error": str(e)}


async def get_stock_movements(
    user_id: str,
    filters: Optional[Dict[str, Any]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get stock movements via RPC
    RPC: ai_get_stock_movements(user_id, filters, date_from, date_to, limit)
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_get_stock_movements",
            {
                "p_user_id": user_id,
                "p_filters": filters or {},
                "p_date_from": date_from,
                "p_date_to": date_to,
                "p_limit": limit
            }
        ).execute()
        
        logger.info(f"RPC: ai_get_stock_movements, user={user_id}")
        return result.data if result.data else {}
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_stock_movements): {e}")
        return {"error": str(e)}


async def get_lead_detail(
    lead_id: int,
    user_id: str,
    include_logs: bool = True
) -> Dict[str, Any]:
    """
    Get full detailed lead information via RPC
    RPC: ai_get_lead_detail(lead_id, user_id, include_logs)
    
    Returns full lead data with all productivity logs, timeline, relations
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_get_lead_detail",
            {
                "p_lead_id": lead_id,
                "p_user_id": user_id,
                "p_include_logs": include_logs
            }
        ).execute()
        
        logger.info(f"📞 Calling RPC: ai_get_lead_detail")
        logger.info(f"   Parameters: lead_id={lead_id}, user_id={user_id}")
        db_result = result.data if result.data else {}
        logger.info(f"   📥 RPC Response received")
        return db_result
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_lead_detail): {e}")
        return {"error": str(e), "success": False}


async def get_appointments(
    user_id: str,
    filters: Optional[Dict[str, Any]] = None,
    user_role: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    appointment_type: Optional[str] = None,
    sales_member_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get appointments via RPC
    RPC: ai_get_appointments(user_id, filters, date_from, date_to, appointment_type, sales_member_id, user_role)
    
    Returns categorized appointments: {followUp: [], engineer: [], payment: []}
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_get_appointments",
            {
                "p_user_id": user_id,
                "p_filters": filters or {},
                "p_date_from": date_from,
                "p_date_to": date_to,
                "p_appointment_type": appointment_type,
                "p_sales_member_id": sales_member_id,
                "p_user_role": user_role or "staff"
            }
        ).execute()
        
        logger.info(f"📞 Calling RPC: ai_get_appointments")
        logger.info(f"   Parameters: user_id={user_id}, type={appointment_type}, date_from={date_from}, date_to={date_to}")
        db_result = result.data if result.data else {}
        logger.info(f"   📥 RPC Response received")
        return db_result
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_appointments): {e}")
        return {"error": str(e), "success": False}


async def get_sales_team(
    user_id: str,
    category: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    user_role: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get sales team list with performance metrics via RPC
    RPC: ai_get_sales_team(user_id, category, filters, date_from, date_to, user_role)
    
    Returns sales team with per-member metrics (currentLeads, totalLeads, closedLeads, conversionRate, contactRate)
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_get_sales_team",
            {
                "p_user_id": user_id,
                "p_category": category,
                "p_filters": filters or {},
                "p_date_from": date_from,
                "p_date_to": date_to,
                "p_user_role": user_role or "staff"
            }
        ).execute()
        
        logger.info(f"📞 Calling RPC: ai_get_sales_team")
        logger.info(f"   Parameters: user_id={user_id}, category={category}, date_from={date_from}, date_to={date_to}")
        db_result = result.data if result.data else {}
        logger.info(f"   📥 RPC Response received")
        return db_result
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_sales_team): {e}")
        return {"error": str(e), "success": False}


async def get_sales_team_list(
    user_id: str,
    category: Optional[str] = None,
    status: str = "active",
    user_role: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get simple sales team list for dropdown via RPC
    RPC: ai_get_sales_team_list(user_id, category, status, user_role)
    
    Returns simple list (id, name, email, phone, department, position)
    
    Note: If status='all', pass NULL to RPC function to get all statuses.
    RPC function now supports p_status = NULL to return all statuses.
    """
    try:
        supabase = get_supabase_client()
        
        # If status is 'all', pass NULL to RPC function to get all statuses
        # RPC function now supports: WHERE (p_status IS NULL OR st.status = p_status)
        actual_status = None if status == "all" else status
        
        result = supabase.rpc(
            "ai_get_sales_team_list",
            {
                "p_user_id": user_id,
                "p_category": category,
                "p_status": actual_status,  # NULL if 'all', otherwise use provided status
                "p_user_role": user_role or "staff"
            }
        ).execute()
        
        logger.info(f"📞 Calling RPC: ai_get_sales_team_list")
        logger.info(f"   Parameters: user_id={user_id}, status={actual_status} (requested: {status})")
        db_result = result.data if result.data else {}
        logger.info(f"   📥 RPC Response received")
        return db_result
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_sales_team_list): {e}")
        return {"error": str(e), "success": False}


async def get_sales_team_data(
    user_id: str,
    user_role: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get sales team data with detailed metrics and data via RPC
    RPC: ai_get_sales_team_data(user_id, date_from, date_to, user_role)
    
    Returns sales team with metrics (deals_closed, pipeline_value, conversion_rate) + leads + quotations
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_get_sales_team_data",
            {
                "p_user_id": user_id,
                "p_date_from": date_from,
                "p_date_to": date_to,
                "p_user_role": user_role or "staff"
            }
        ).execute()
        
        logger.info(f"📞 Calling RPC: ai_get_sales_team_data")
        logger.info(f"   Parameters: user_id={user_id}, date_from={date_from}, date_to={date_to}")
        db_result = result.data if result.data else {}
        logger.info(f"   📥 RPC Response received")
        return db_result
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_sales_team_data): {e}")
        return {"error": str(e), "success": False}


async def get_sales_team_overview(
    user_id: str,
    user_role: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sales_id: Optional[int] = None,
    period: str = "month",
) -> Dict[str, Any]:
    """
    Consolidated Sales Team tool.
    - Team view: delegates to get_sales_team_data (when sales_id is None)
    - Single member view: delegates to get_sales_performance (when sales_id is provided)
    """
    try:
        if sales_id is not None:
            return await get_sales_performance(
                sales_id=sales_id,
                user_id=user_id,
                user_role=user_role,
                date_from=date_from,
                date_to=date_to,
                period=period,
            )
        return await get_sales_team_data(
            user_id=user_id,
            user_role=user_role,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as e:
        logger.error(f"RPC error (get_sales_team_overview): {e}")
        return {"error": str(e), "success": False}


async def validate_phone(
    phone: str,
    user_id: Optional[str] = None,
    exclude_lead_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Validate phone number for duplicates via RPC
    RPC: ai_validate_phone(phone, exclude_lead_id, user_id)
    
    Returns {isDuplicate: boolean, phone: string, existingLead?: Lead}
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_validate_phone",
            {
                "p_phone": phone,
                "p_exclude_lead_id": exclude_lead_id,
                "p_user_id": user_id
            }
        ).execute()
        
        logger.info(f"📞 Calling RPC: ai_validate_phone")
        logger.info(f"   Parameters: phone={phone}, exclude_lead_id={exclude_lead_id}")
        db_result = result.data if result.data else {}
        logger.info(f"   📥 RPC Response received")
        return db_result
    
    except Exception as e:
        logger.error(f"RPC error (ai_validate_phone): {e}")
        return {"error": str(e), "success": False, "isDuplicate": False}


async def get_sales_performance(
    sales_id: int,
    user_id: str,
    user_role: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    period: str = "month"
) -> Dict[str, Any]:
    """
    Get sales performance for a specific sales member via RPC
    RPC: ai_get_sales_performance(sales_id, user_id, date_from, date_to, period)
    
    Note: Only admin and manager can view sales performance
    
    Returns sales member info with metrics (total_leads, deals_closed, pipeline_value, conversion_rate)
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_get_sales_performance",
            {
                "p_sales_id": sales_id,
                "p_user_id": user_id,
                "p_date_from": date_from,
                "p_date_to": date_to,
                "p_period": period
            }
        ).execute()
        
        logger.info(f"📞 Calling RPC: ai_get_sales_performance")
        logger.info(f"   Parameters: sales_id={sales_id}, user_id={user_id}, date_from={date_from}, date_to={date_to}, period={period}")
        db_result = result.data if result.data else {}
        logger.info(f"   📥 RPC Response received")
        return db_result
    
    except Exception as e:
        logger.error(f"RPC error (ai_get_sales_performance): {e}")
        return {"error": str(e), "success": False}