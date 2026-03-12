"""
LLM-based Intent Router with Function Calling
Uses LLM to analyze intent and select tools
"""
from typing import Dict, Any, List, Optional

from openai import AsyncOpenAI  # type: ignore[reportMissingImports]

from app.utils.logger import get_logger
from app.utils.system_prompt import get_intent_analyzer_prompt

logger = get_logger(__name__)

# Keywords that indicate the user wants data from the system (not general chat).
# If LLM returns intent=general with no tools but message contains these, we override to db_query.
DATA_KEYWORDS_LEADS = (
    "ลีด", "lead", "ลูกค้า", "ข้อมูลลีด", "ลีดวันนี้", "ลีดเมื่อวาน", "ลีดสัปดาห์", "ลีดเดือน",
    "รอรับ", "กำลังติดตาม", "ปิดการขาย", "ยังปิดการขายไม่สำเร็จ",
)
DATA_KEYWORDS_APPOINTMENTS = ("นัด", "appointment", "นัดหมาย", "นัดช่าง", "นัดติดตาม", "นัดชำระเงิน")
DATA_KEYWORDS_TEAM_KPI = ("ทีมขาย", "ทีม", "team", "kpi", "สถิติ", "dashboard", "แดชบอร์ด", "พนักงานขาย", "เซลล์")
DATA_KEYWORDS_SALES_CLOSED = (
    "ยอดขายที่ปิด", "ยอดขายวันนี้", "ยอดขาย", "sales closed", "ปิดการขายแล้ว", "ยอดแยกรายเดือน", "ยอดรายเดือน",
    "package", "wholesales", "แพ็กเกจ", "โฮลเซล", "แยก package", "แยก wholesales", "แยกรายการ",
    "แพลตฟอร์ม", "platform", "แยกตามแพลตฟอร์ม", "ยอดตามแพลตฟอร์ม",
    "เดือนที่แล้ว", "ปิดได้กี่ราย", "ปิดการขายได้กี่ราย", "จำนวนที่ปิด", "กี่รายที่ปิด",
)
# ปิดการขายไม่สำเร็จ — ต้องตรวจก่อน LEADS (เพราะ "ปิดไม่ได้" อาจ match LEADS)
DATA_KEYWORDS_SALES_UNSUCCESSFUL = (
    "ปิดการขายไม่ได้", "ปิดไม่ได้", "ปิดไม่สำเร็จ", "ปิดไม่สำเร็จกี่ราย",
    "เดือนที่แล้วปิดไม่ได้", "กี่รายที่ปิดไม่ได้",
)
DATA_KEYWORDS_QUOTATIONS = ("ใบเสนอราคา", "quotation", "โควต้า", "quotations")
DATA_KEYWORDS_DOCS = ("เอกสารการขาย", "ใบแจ้งหนี้", "invoice", "เอกสาร")
DATA_KEYWORDS_PERMITS = ("คำขออนุญาต", "permit", "อนุญาต")
# Union of all data-related keywords for "any match" check
_DATA_KEYWORDS_ALL = (
    DATA_KEYWORDS_LEADS + DATA_KEYWORDS_APPOINTMENTS + DATA_KEYWORDS_TEAM_KPI
    + DATA_KEYWORDS_SALES_CLOSED + DATA_KEYWORDS_SALES_UNSUCCESSFUL
    + DATA_KEYWORDS_QUOTATIONS + DATA_KEYWORDS_DOCS + DATA_KEYWORDS_PERMITS
)


def _suggest_default_tool_for_data_request(user_message: str) -> Optional[Dict[str, Any]]:
    """
    When LLM returns general with no tools but the message clearly asks for system data,
    suggest a default tool + params so we still fetch data. Used as fallback only.
    """
    if not (user_message or "").strip():
        return None
    m = user_message.lower().strip()
    # "ลูกค้าใหม่กี่ราย" / "ลีดใหม่กี่ราย" = นับจาก lead ที่สร้างในช่วง → search_leads (ไม่ใช่ get_sales_closed)
    if ("ลูกค้าใหม่" in m or "ลีดใหม่" in m) and "ปิดการขาย" not in m:
        return {"name": "search_leads", "parameters": {"query": user_message.strip()}}
    # More specific intents first (ปิดไม่ได้ ต้องก่อน LEADS เพื่อไม่ไป search_leads)
    if any(k in m for k in DATA_KEYWORDS_SALES_UNSUCCESSFUL):
        return {"name": "get_sales_unsuccessful", "parameters": {}}
    if any(k in m for k in DATA_KEYWORDS_SALES_CLOSED):
        return {"name": "get_sales_closed", "parameters": {}}
    if any(k in m for k in DATA_KEYWORDS_APPOINTMENTS):
        return {"name": "get_appointments", "parameters": {}}
    if any(k in m for k in DATA_KEYWORDS_TEAM_KPI):
        return {"name": "get_team_kpi", "parameters": {}}
    if any(k in m for k in DATA_KEYWORDS_QUOTATIONS):
        return {"name": "get_quotations", "parameters": {}}
    if any(k in m for k in DATA_KEYWORDS_DOCS):
        return {"name": "get_sales_docs", "parameters": {}}
    if any(k in m for k in DATA_KEYWORDS_PERMITS):
        return {"name": "get_permit_requests", "parameters": {}}
    if any(k in m for k in DATA_KEYWORDS_LEADS):
        return {"name": "search_leads", "parameters": {"query": user_message.strip()}}
    return None


def _message_has_data_keyword(user_message: str) -> bool:
    """True if the message contains any keyword that suggests a request for system data."""
    if not (user_message or "").strip():
        return False
    m = user_message.lower()
    return any(kw in m for kw in _DATA_KEYWORDS_ALL)


# Define tool schemas for LLM function calling
# These are just schemas - actual execution happens in db_query_node
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_lead_status",
            "description": "Get status of a specific lead by name",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_name": {
                        "type": "string",
                        "description": "Name of the lead to search for"
                    }
                },
                "required": ["lead_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_leads",
            "description": "Search or list leads with FULL DETAILS: platform, category, status, dates, contact info, etc. Returns complete lead data. ✅ Use for: listing leads, dashboard by status (รอรับ/กำลังติดตาม/ปิดการขาย), leads by date/platform. ✅ Use for 'ลูกค้าใหม่กี่ราย' / 'เดือนที่แล้วมีลูกค้าใหม่กี่ราย' / 'ลีดใหม่กี่ราย' (นับรายที่สร้างในช่วง) with date_from/date_to. ⚠️ Do NOT use for 'ปิดการขายไม่ได้กี่ราย' — use get_sales_unsuccessful. ⚠️ Do NOT use for 'ปิดการขายได้กี่ราย' — use get_sales_closed. STATUS RULE: When user does NOT ask for ONE specific status ('ขอข้อมูลลีดวันนี้', 'ลีดวันนี้'), omit status. Only set status when user EXPLICITLY asks one status. Always extract date_from/date_to when user mentions dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query or description (e.g., 'leads today', 'leads yesterday', 'leads this week', 'all leads', 'ลูกค้าที่ได้มาเมื่อวาน', 'ยอดขายวันนี้', 'ลีดที่ปิดการขายแล้ว'). For sales/closed leads, include keywords like 'ยอดขาย', 'ปิดการขาย', 'closed' in query. ⚠️ IMPORTANT: Do NOT use dict format like {'source': 'Huawei', 'created_from_months_ago': 5}. Use simple string query instead. Platform/brand will be automatically extracted from query text."
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by lead status. ONLY set when user EXPLICITLY asks for one specific status. Examples: 'ลีดที่รอรับวันนี้'→status='รอรับ'. When user asks generally ('ขอข้อมูลลีดวันนี้', 'ลีดวันนี้') omit status. Valid: 'รอรับ', 'กำลังติดตาม', 'ปิดการขาย', 'ยังปิดการขายไม่สำเร็จ'. ⚠️ 'ปิดการขายได้กี่ราย'→get_sales_closed. 'ปิดการขายไม่ได้กี่ราย'→get_sales_unsuccessful (ไม่ใช่ search_leads).",
                        "enum": ["รอรับ", "กำลังติดตาม", "ปิดการขาย", "ยังปิดการขายไม่สำเร็จ"]
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (e.g., '2026-01-16' for yesterday). Extract from query if user mentions dates like 'เมื่อวาน', 'สัปดาห์นี้', 'เดือนนี้', or specific dates.",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (e.g., '2026-01-16' for yesterday, or '2026-01-17' for today if query is 'this week'). Extract from query if user mentions date ranges.",
                        "format": "date"
                    },
                    "platform": {
                        "type": "string",
                        "description": "Optional. Filter by platform. Set from current message OR from previous conversation (PLATFORM RULE). If not specified and no context → omit (all platforms). Values: Huawei, ATMOCE, Solar Edge, Sigenergy, Facebook, Line, etc."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_closed",
            "description": "Sales Closed report (SUCCESSFULLY closed only). ตัวเลขยึดตามหน้า /reports/sales-closed. ✅ Use for: 'ปิดการขายได้กี่ราย', 'ยอดขายที่ปิดแล้ว', 'ยอดตามแพลตฟอร์ม', 'ลีด Huawei ปิดได้กี่ราย'. เมื่อผู้ใช้ระบุแพลตฟอร์มหรือจากบทสนทนาก่อนหน้า → ส่ง platform. ไม่ระบุและไม่มีบริบท = ทุกแพลตฟอร์ม (ไม่ส่ง platform). เมื่อถามช่วงหลายเดือน: ส่ง date_from/date_to ครั้งเดียว.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD (วันแรกของช่วง). ช่วงหลายเดือน: ใช้วันแรกของช่วง เช่น พย 2025 ถึง มค 2026 → 2025-11-01",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD (วันสุดท้ายของช่วง). ช่วงหลายเดือน: ใช้วันสุดท้ายของช่วง เช่น พย 2025 ถึง มค 2026 → 2026-01-31",
                        "format": "date"
                    },
                    "sales_member_id": {
                        "type": "integer",
                        "description": "Optional sales member id to filter by who closed the sale (sale_id in lead_productivity_logs)"
                    },
                    "platform": {
                        "type": "string",
                        "description": "Optional. Filter by platform. Set from current message OR from previous conversation (e.g. user previously asked about Huawei → follow-up 'ยอดปิดได้กี่ราย' = same platform). If not specified and no context → omit (all platforms). Values: Huawei, ATMOCE, Solar Edge, Sigenergy, Facebook, Line, etc."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_unsuccessful",
            "description": "Sales Unsuccessful report (ปิดการขายไม่สำเร็จ). ตัวเลขตรงกับหน้า /reports/sales-unsuccessful. ✅ Use for: 'ปิดการขายไม่ได้กี่ราย', 'ลีด Huawei ปิดการขายไม่ได้กี่ราย'. ส่ง platform จากข้อความปัจจุบัน หรือจากบทสนทนาก่อนหน้า (เช่น เคยถามลีด Huawei แล้วถามตาม 'แล้วปิดไม่ได้กี่ราย' = ใช้ Huawei). ไม่ระบุและไม่มีบริบท = ทุกแพลตฟอร์ม (ไม่ส่ง platform). ต้องส่ง date_from/date_to เมื่อผู้ใช้ระบุช่วงเวลา.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD (วันแรกของช่วง). เช่น เดือนที่แล้ว → 2026-01-01",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD (วันสุดท้ายของช่วง). เช่น เดือนที่แล้ว → 2026-01-31",
                        "format": "date"
                    },
                    "sales_member_id": {
                        "type": "integer",
                        "description": "Optional sales member id to filter by"
                    },
                    "platform": {
                        "type": "string",
                        "description": "Optional. Filter by platform. Set from current message OR from previous conversation. If not specified and no context → omit (all platforms). Values: Huawei, ATMOCE, Solar Edge, Sigenergy, Facebook, Line, etc."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_kpi",
            "description": "Get team KPI and performance metrics with per-member statistics (currentLeads, totalLeads, closedLeads, conversionRate, contactRate). Use when user asks about team performance, KPI, or conversion rates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "integer",
                        "description": "Optional team ID (default: all teams)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (Package/Wholesale)"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "format": "date"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_leads",
            "description": "Get leads assigned to the current user (My Leads page). Returns leads where user is sale_owner_id OR post_sales_owner_id. Use when user asks about THEIR OWN leads (e.g., 'ลีดของฉัน', 'ลีดที่ assign ให้ฉัน', 'ลีดที่ฉันรับผิดชอบ'). Includes user data, sales member data, and statistics (byStatus, byPlatform).",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category filter (Package/Wholesale, default: Package)"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "format": "date"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lead_detail",
            "description": "Get FULL DETAILED information about a specific lead including all productivity logs, timeline, relations (credit_evaluation, lead_products, quotations). Use when user asks for detailed/complete information about a lead (e.g., 'รายละเอียดลีด ID 123', 'ข้อมูลเต็มของลีด John').",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {
                        "type": "integer",
                        "description": "ID of the lead to get details for (required)"
                    }
                },
                "required": ["lead_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_appointments",
            "description": "Get sales appointments categorized by type (used in My Appointments page /my-appointments). Returns categorized appointments: engineer appointments (นัดช่าง), follow-up appointments (นัดติดตาม), payment appointments (นัดชำระเงิน from quotations). Use when user asks about sales appointments (e.g., 'นัดหมายวันนี้', 'นัดช่าง', 'นัดติดตาม', 'นัดชำระเงิน', 'นัดหมายของฉัน'). Returns structure with followUp, engineer, and payment arrays.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_type": {
                        "type": "string",
                        "description": "Type of appointment: 'engineer', 'follow-up', 'payment', or 'all' (optional)"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "sales_member_id": {
                        "type": "integer",
                        "description": "Optional sales member ID to filter appointments"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_team",
            "description": "Get sales team list with performance metrics. Similar to get_team_kpi but may have different response structure. Use when user asks about sales team list with performance metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (Package/Wholesale)"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "format": "date"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_team_list",
            "description": "Get simple sales team list for dropdown/selection (used in Lead forms like Add Lead, Lead Management). Returns minimal data (id, user_id, current_leads, status, name, email, phone, department, position). Use when user asks for simple list of sales team members, active sales team, or sales team list (e.g., 'รายชื่อทีมขาย', 'ทีมขายที่ active', 'เลือกทีมขาย', 'รายชื่อเซลล์', 'พนักงานขายที่ active', 'รายชื่อพนักงานขายทั้งหมด'). This is the dropdown list used in forms. Filter by status='active' by default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status (default: 'active')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_team_data",
            "description": "Get sales team data with detailed metrics (deals_closed, pipeline_value, conversion_rate) and data (leads, quotations). Use when user asks about sales team with detailed data or pipeline value (e.g., 'ข้อมูลทีมขายพร้อม leads', 'ทีมขายและ deals', 'มูลค่าพอร์ตของทีม').",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "format": "date"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lead_management",
            "description": "Get Lead Management page data (/lead-management) - used for managing Package leads. Returns: leads list, sales team data, user data, sales member data, and statistics (totalLeads, assignedLeads, unassignedLeads, assignmentRate, leadsWithContact, contactRate). Use when user asks about lead management overview, statistics, or managing leads (e.g., 'ข้อมูล Lead Management', 'แสดงสถานะการจัดการลีด', 'สถิติการ assign ลีด').",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category filter (default: 'Package')"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "format": "date"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_service_appointments",
            "description": "Get service appointments (used in Service Appointments page /service-tracking/service-appointments). These are service/maintenance appointments (NOT sales appointments). Use when user asks about service appointments, maintenance appointments, or service tracking (e.g., 'นัดหมายบริการ', 'นัดบริการซ่อม', 'Service appointments'). Difference: get_appointments = sales appointments (CRM), get_service_appointments = service appointments (Service Tracking).",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_type": {
                        "type": "string",
                        "description": "Type of appointment (optional, default: 'all')"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "format": "date"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_performance",
            "description": "Get sales performance for a SPECIFIC sales member (by sales_id). Use when user asks about performance of a specific sales person. Note: Only admin and manager can view sales performance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sales_id": {
                        "type": "integer",
                        "description": "ID of the sales member to get performance for (required)"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "period": {
                        "type": "string",
                        "description": "Period: 'day', 'week', 'month', 'year' (default: 'month')"
                    }
                },
                "required": ["sales_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_docs",
            "description": "Get sales documents (QT/Quotation, BL/Bill of Lading, INV/Invoice). Use when user asks about sales documents or invoices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results (default: 100)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_quotations",
            "description": "Get quotations (ใบเสนอราคา). Use when user asks about quotations specifically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results (default: 100)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_permit_requests",
            "description": "Get permit requests (คำขออนุญาต). Use when user asks about permit requests or permits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                        "format": "date"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results (default: 100)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_info",
            "description": "Get user information. Use when user asks about user information or user details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results (default: 100)"
                    }
                },
                "required": []
            }
        }
    }
]


async def analyze_intent_with_llm(
    user_message: str,
    user_id: str,
    user_role: str = "staff",
    session_context: Optional[Dict[str, Any]] = None,
    history_context: Optional[str] = None  # NEW: Chat history context
) -> Dict[str, Any]:
    """
    Use LLM with function calling to analyze intent and select tools
    
    Returns:
        {
            "intent": "db_query" | "rag_query" | "general" | "clarify",
            "confidence": float,
            "entities": Dict[str, Any],
            "selected_tools": List[Dict[str, Any]],
            "tool_parameters": Dict[str, Dict[str, Any]]
        }
    """
    try:
        # Get system prompt with vocabulary context
        base_prompt = get_intent_analyzer_prompt()
        
        # Build history context section
        history_section = ""
        if history_context:
            history_section = f"""

=== Previous Conversation History ===
{history_context}

=== Current User Message ===
"""
        else:
            history_section = "\n=== Current User Message ===\n"
        
        # Add user context
        system_prompt = f"""{base_prompt}

User context:
- User ID: {user_id}
- User Role: {user_role}
{history_section}

Available tools (ALWAYS use function calling for data queries):

=== LEADS MANAGEMENT (5 tools) ===
1. search_leads - For Dashboard, Lead Management, and lead queries (listing leads, breakdown by status)
   Use when: Listing leads, dashboard statistics, leads by date/platform/category.
   ⚠️ Do NOT use for "เดือนที่แล้วปิดการขายไม่ได้กี่ราย" / "ปิดการขายไม่ได้กี่ราย" — use get_sales_unsuccessful instead (ตัวเลขตรงหน้า /reports/sales-unsuccessful).
   ⚠️ Do NOT use for "ปิดการขายได้กี่ราย" — use get_sales_closed instead.
   ⚠️ STATUS RULE: When user does NOT ask for ONE specific status ("ขอข้อมูลลีดวันนี้", "ลีดวันนี้"), omit status. Only set status when user EXPLICITLY asks one status ("ลีดที่รอรับวันนี้", "closed leads").
   Examples: "ขอข้อมูลลีดวันนี้" → search_leads with query="today", no status. "เดือนที่แล้วปิดการขายไม่ได้กี่ราย" → get_sales_unsuccessful with date_from/date_to=last month. "ลีด huawei ปิดการขายไม่ได้กี่ราย" / "ลีด Huawei ย้อนหลัง 30 วัน ปิดไม่ได้กี่ราย" → get_sales_unsuccessful with date_from/date_to and platform="Huawei".

2. get_lead_status - For finding ONE SPECIFIC lead by name (like phone validation lookup)
   Use when: User asks about a SPECIFIC lead by name (e.g., "สถานะของลีดชื่อ John Doe", "ลีดชื่อ สมชาย")
   ⚠️ NOT for listing multiple leads - use search_leads instead
   Context: Similar to phone validation in Add Lead form

3. get_my_leads - For My Leads page (/my-leads) - leads assigned to CURRENT USER
   Use when: User asks about THEIR OWN leads (e.g., "ลีดของฉัน", "ลีดที่ assign ให้ฉัน")
   Returns: Leads where user is sale_owner_id OR post_sales_owner_id + user data + statistics
   Context: Used in My Leads page

4. get_lead_detail - For Lead Detail page (/leads/:id) and Lead Timeline page (/leads/:id/timeline)
   Use when: User asks for detailed/complete information (e.g., "รายละเอียดลีด ID 123", "Timeline ของลีด")
   Returns: Full lead data, ALL productivity logs, timeline, relations (credit_evaluation, lead_products, quotation_documents)
   Context: Used in Lead Detail and Lead Timeline pages

5. get_lead_management - For Lead Management page (/lead-management) - managing Package leads
   Use when: User asks about lead management overview, statistics, or managing leads
   Returns: Leads list + sales team + user + statistics (totalLeads, assignedLeads, assignmentRate, etc.)
   Context: Used in Lead Management page for Package sales

=== SALES TEAM (4 tools) ===
6. get_team_kpi - For Dashboard and Sales Team page - team KPI and performance metrics
   Use when: User asks about team performance, KPI, conversion rates (e.g., "KPI ของทีมขาย", "Dashboard ทีมขาย")
   Returns: Sales team list with per-member metrics (currentLeads, totalLeads, closedLeads, conversionRate, contactRate) + overall statistics
   Context: Used in Dashboard (/) and Sales Team (/sales-team) pages

7. get_sales_team - For Dashboard and Sales Team page - sales team list with performance metrics
   Use when: User asks about sales team list with performance (e.g., "รายการทีมขาย", "ทีมขายพร้อมสถิติ")
   Similar to get_team_kpi but may have different response structure
   Context: Used in Dashboard and Sales Team pages

8. get_sales_team_list - For simple list of active sales team members (dropdown/selection)
   Use when: User asks for simple list of sales team, active sales team, or sales team list (e.g., "รายชื่อทีมขาย", "ทีมขายที่ active", "เลือกทีมขาย", "รายชื่อเซลล์", "พนักงานขายที่ active", "รายชื่อพนักงานขายทั้งหมด")
   Returns: Minimal data (id, user_id, current_leads, status, name, email, phone, department, position)
   Context: Used in Lead forms for dropdown selection, but also useful for listing active sales team members

9. get_sales_team_data - For Sales Team page (/sales-team) - detailed data with leads and quotations
   Use when: User asks about sales team with detailed performance data, deals, or pipeline value
   Returns: Sales team with metrics (deals_closed, pipeline_value, conversion_rate) + leads + quotations data
   Context: Used in Sales Team page for detailed view

=== APPOINTMENTS (2 tools) ===
10. get_appointments - For My Appointments page (/my-appointments) - sales appointments
    Use when: User asks about sales appointments (e.g., "นัดหมายวันนี้", "นัดช่าง", "นัดติดตาม", "นัดชำระเงิน", "นัดหมายของฉัน")
    Returns: Categorized appointments with structure containing followUp, engineer, and payment arrays
    Context: Used in My Appointments page (CRM)

11. get_service_appointments - For Service Appointments page (/service-tracking/service-appointments) - service/maintenance
    Use when: User asks about service appointments, maintenance appointments, or service tracking
    Examples: "นัดหมายบริการ", "นัดบริการซ่อม", "Service appointments"
    Difference: get_appointments = sales appointments (CRM), get_service_appointments = service appointments (Service Tracking)
    Context: Used in Service Tracking module

=== DOCUMENTS & QUOTATIONS (2 tools) ===
12. get_sales_docs - For sales documents (QT/Quotation, BL/Bill of Lading, INV/Invoice)
    Use when: User asks about sales documents or invoices (e.g., "เอกสารการขาย", "ใบแจ้งหนี้")

13. get_quotations - For quotations specifically (ใบเสนอราคา)
    Use when: User asks about quotations specifically

=== PERMITS (1 tool) ===
14. get_permit_requests - For permit requests (คำขออนุญาต)
    Use when: User asks about permit requests or permits

=== PERFORMANCE (1 tool) ===
15. get_sales_performance - For sales performance of a SPECIFIC sales member (by sales_id)
    Use when: User asks about performance of a specific sales person
    Note: Only admin and manager can view sales performance

=== USER (1 tool) ===
16. get_user_info - For user information
    Use when: User asks about user information or user details


=== IMPORTANT: INVENTORY-RELATED FUNCTIONS (NOT AVAILABLE) ===
⚠️  The following functions are NOT available for AI Chatbot (inventory system not in use):
- get_stock_movements - Stock movements (inventory)
- get_inventory_status - Inventory status (inventory)
- get_customer_info - Customer info (inventory customer - NOT the sales customer info)

=== PLATFORM RULE (ใช้กับ get_sales_unsuccessful, get_sales_closed, search_leads) ===
- **พิจารณา platform เสมอ:** จาก (1) ข้อความปัจจุบัน (เช่น "ลีด Huawei ปิดไม่ได้กี่ราย") หรือ (2) บทสนทนาก่อนหน้า (เช่น ผู้ใช้เพิ่งถามเรื่องลีด Huawei แล้วถามตาม "แล้วปิดไม่ได้กี่ราย" = ใช้ platform เดิม).
- **ถ้าผู้ใช้ไม่ระบุและไม่มีบริบทจากบทสนทนาก่อนหน้า** = ทุกแพลตฟอร์ม → ไม่ต้องส่ง platform (omit).
- เมื่อมีบริบทแพลตฟอร์มชัด → ส่ง platform ให้ตรงกับนั้น (e.g. Huawei, ATMOCE) เพื่อให้ตัวเลขตรงหน้ารายงานที่กรองแพลตฟอร์ม.

=== IMPORTANT TOOL SELECTION RULES ===
✅ "ลูกค้าใหม่กี่ราย" / "เดือนที่แล้วมีลูกค้าใหม่กี่ราย" / "ลีดใหม่กี่ราย" (รายที่เข้ามาใหม่ในช่วง) → search_leads with date_from/date_to. Do NOT use get_sales_closed.
✅ "ปิดการขายได้กี่ราย" / "เดือนที่แล้วปิดการขายได้กี่ราย" (SUCCESS) → get_sales_closed with date_from/date_to. Apply PLATFORM RULE (from message or conversation context).
✅ "ปิดการขายไม่ได้กี่ราย" / "เดือนที่แล้วปิดการขายไม่ได้กี่ราย" (FAILED) → get_sales_unsuccessful with date_from/date_to. Apply PLATFORM RULE (from message or conversation context).
✅ Use get_sales_closed for: ยอดขายที่ปิด, ขอยอดขาย, ยอดตามแพลตฟอร์ม, แยก Package/Wholesales, ปิดการขายได้กี่ราย (with period + platform when relevant)
✅ Use search_leads for: listing leads, dashboard by status, "ขอข้อมูลลีดวันนี้", "ลีดวันนี้มีกี่ราย". Apply PLATFORM RULE when user or context specifies a platform (e.g. "ลีด Huawei วันนี้" → query + platform)
✅ Only set search_leads status when user EXPLICITLY asks one status ("ลีดที่รอรับวันนี้", "closed leads")
✅ search_leads returns FULL lead data - LLM can calculate counts, group by status/platform/category
✅ Use get_lead_status ONLY when user mentions a SPECIFIC lead name
✅ Use get_my_leads when user asks about THEIR OWN leads (not all leads)
✅ Use get_team_kpi for team performance/KPI queries
✅ Use get_sales_team_list for simple lists (dropdown/selection)
✅ Use get_sales_team_data for detailed data (leads, quotations, pipeline value)
✅ Always extract dates from natural language Thai dates (เมื่อวาน, สัปดาห์นี้, เดือนนี้)
✅ **Follow-up "แยก Package/Wholesales", "แยกรายการ", "อยากได้รายชื่อ", "ยอดขายตามแพลตฟอร์ม", "แยกตามแพลตฟอร์ม":** MUST call get_sales_closed with the date range from the previous user message (e.g. previous was ธันวา → use date_from=2025-12-01, date_to=2025-12-31). Do NOT answer from conversation memory — always use function calling to fetch data.
"""
        
        # Convert to OpenAI format for function calling
        import json
        openai_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Call OpenAI API directly with function calling
        from app.config import settings
        
        # When user message suggests a data request (leads, appointments, team, etc.), force tool use
        # so we fetch data instead of risking intent=general with no tools.
        tool_choice = "required" if _message_has_data_keyword(user_message) else "auto"
        logger.info(f"🔧 Calling OpenAI API with function calling...")
        logger.info(f"   Tools available: {[t['function']['name'] for t in TOOL_SCHEMAS]}")
        logger.info(f"   Tool choice: {tool_choice}")
        
        try:
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Mini models (gpt-4o-mini, gpt-5-mini) only support temperature=1.0 (default)
            # Remove temperature parameter to use default (1.0)
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,  # Use model from settings (default: gpt-5-mini)
                messages=openai_messages,
                tools=TOOL_SCHEMAS,
                tool_choice=tool_choice  # "required" when message has data keywords so we fetch data
                # Note: temperature not set - mini models only support default (1.0)
            )
            
            # Extract response
            message = response.choices[0].message
            
            logger.info(f"✅ OpenAI API call successful")
            logger.info(f"   Has tool_calls: {bool(hasattr(message, 'tool_calls') and message.tool_calls)}")
            if hasattr(message, 'tool_calls') and message.tool_calls:
                logger.info(f"   Tool calls count: {len(message.tool_calls)}")
            
        except Exception as e:
            logger.error(f"❌ OpenAI API call failed: {e}")
            raise
        
        # Extract intent from response
        intent = "general"  # Default to general for questions without tools
        confidence = 0.7
        
        # Check for tool calls
        tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls = message.tool_calls
            intent = "db_query"
            confidence = 0.9
        
        # Check response content and message for intent clues
        content = (message.content or "").lower()
        message_lower = user_message.lower()
        
        # Check for RAG query patterns
        if "document" in content or "procedure" in content or "how to" in message_lower or "ขั้นตอน" in message_lower or "วิธีทำ" in message_lower:
            intent = "rag_query"
            confidence = 0.8
        
        # Check for clarify patterns
        elif "unclear" in content or "clarify" in content or len(user_message.strip()) < 5:
            intent = "clarify"
            confidence = 0.5
        
        # Parse tool calls
        selected_tools = []
        tool_parameters = {}
        
        if tool_calls:
            for tool_call in tool_calls:
                # Handle OpenAI tool_call format
                if hasattr(tool_call, "function"):
                    # OpenAI format
                    tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments
                    # Parse JSON arguments
                    import json
                    try:
                        tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                    except:
                        tool_args = {}
                elif isinstance(tool_call, dict):
                    tool_name = tool_call.get("name", "") or tool_call.get("function", {}).get("name", "")
                    tool_args = tool_call.get("args", {}) or tool_call.get("function", {}).get("arguments", {})
                else:
                    # Skip unknown format
                    continue
                
                if not tool_name:
                    continue
                
                # Ensure required parameters are added
                tool_call_params = tool_args.copy() if isinstance(tool_args, dict) else {}
                
                # Map tool names to actual function parameters
                if tool_name == "get_lead_status":
                    # user_id will be added in db_query_node
                    pass
                elif tool_name == "search_leads":
                    # Extract query from message if not in args
                    if "query" not in tool_call_params:
                        tool_call_params["query"] = user_message
                    
                    # Auto-detect status from user message if LLM didn't set it
                    # This is a fallback to ensure status is set when user asks about closed leads
                    user_message_lower = user_message.lower()
                    if "status" not in tool_call_params or tool_call_params.get("status") is None:
                        # Check for closed/sold leads keywords
                        closed_keywords = ["ปิดการขาย", "closed", "ปิดการขายได้", "ปิดการขายแล้ว", "closed leads", "sold"]
                        if any(keyword in user_message_lower for keyword in closed_keywords):
                            # Check if it's asking about closed leads (not sales closed report)
                            if "ยอดขาย" not in user_message_lower and "sales closed" not in user_message_lower:
                                tool_call_params["status"] = "ปิดการขาย"
                                logger.info(f"   🔧 Auto-detected status='ปิดการขาย' from user message keywords")
                    
                    # Extract date_from and date_to from LLM parameters if provided
                    # The LLM should extract dates from natural language
                    # date_from and date_to will be passed to search_leads function
                    # user_role will be added in db_query_node
                
                selected_tools.append({
                    "name": tool_name,
                    "parameters": tool_call_params
                })
                tool_parameters[tool_name] = tool_call_params
        
        # Extract entities
        entities = {}
        if "วันนี้" in message_lower or "today" in message_lower:
            entities["date"] = "today"
        elif "สัปดาห์" in message_lower or "week" in message_lower:
            entities["period"] = "week"
        elif "เดือน" in message_lower or "month" in message_lower:
            entities["period"] = "month"
        
        result = {
            "intent": intent,
            "confidence": confidence,
            "entities": entities,
            "selected_tools": selected_tools,
            "tool_parameters": tool_parameters
        }
        
        # Data-keyword fallback: if LLM returned general with no tools but message clearly asks for system data,
        # override to db_query and inject a default tool so we still fetch data (user expects data regardless of phrasing).
        if result["intent"] == "general" and not result["selected_tools"] and _message_has_data_keyword(user_message):
            suggested = _suggest_default_tool_for_data_request(user_message)
            if suggested:
                result["intent"] = "db_query"
                result["confidence"] = 0.85
                result["selected_tools"] = [{"name": suggested["name"], "parameters": suggested["parameters"]}]
                result["tool_parameters"] = {suggested["name"]: suggested["parameters"]}
                logger.info(f"   📌 Data-keyword fallback: overriding to db_query with tool={suggested['name']} (user message suggests data request)")
        
        logger.info(f"🤖 LLM Intent Analysis:")
        logger.info(f"   Intent: {intent}")
        logger.info(f"   Confidence: {confidence:.2%}")
        logger.info(f"   Selected Tools: {[t['name'] for t in selected_tools]}")
        logger.info(f"   Entities: {entities}")
        logger.info(f"   Tool Calls Found: {len(tool_calls)}")
        logger.info(f"   Response Content: {content[:100] if content else 'None'}")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ LLM intent analysis error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Fallback: if message suggests data request, still try to fetch data
        if _message_has_data_keyword(user_message):
            suggested = _suggest_default_tool_for_data_request(user_message)
            if suggested:
                logger.info(f"   📌 Error fallback: using db_query with tool={suggested['name']}")
                return {
                    "intent": "db_query",
                    "confidence": 0.75,
                    "entities": {},
                    "selected_tools": [{"name": suggested["name"], "parameters": suggested["parameters"]}],
                    "tool_parameters": {suggested["name"]: suggested["parameters"]},
                    "error": str(e)
                }
        return {
            "intent": "general",
            "confidence": 0.5,
            "entities": {},
            "selected_tools": [],
            "tool_parameters": {},
            "error": str(e)
        }
