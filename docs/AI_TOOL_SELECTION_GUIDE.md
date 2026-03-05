# 🤖 AI Tool Selection Guide

## 📖 Overview

This document is designed to help the AI Chatbot learn and correctly select RPC functions for data retrieval.

**Total Available Tools: 17** (out of 21 RPC functions in database)

**Note:** Inventory-related functions are NOT available:
- `get_stock_movements` - Stock movements (inventory system not in use)
- `get_inventory_status` - Inventory status (inventory system not in use)
- `get_customer_info` - Customer info for inventory system (NOT for sales customer info)

---

## 🎯 Tool Selection Strategy

### When to Use Which Tool?

#### 🎯 Leads Management (5 tools)

**1. `search_leads`** - สำหรับค้นหา/แสดงรายชื่อลีดทั้งหมด
- **Use when:** User asks about leads in general, list of leads, leads by date/status/category
- **Examples:**
  - "ลีดวันนี้มีใครบ้าง" → `search_leads` with date_from="today"
  - "ลูกค้าที่ได้มาเมื่อวาน" → `search_leads` with date_from="yesterday"
  - "ลีดที่ status เป็น 'กำลังติดตาม'" → `search_leads` with filters={"status": "กำลังติดตาม"}
  - "แสดงลีดทั้งหมด" → `search_leads` with query="all leads"
  - **"เดือนที่แล้วปิดการขายไม่ได้กี่ราย"** / **"ปิดการขายไม่ได้กี่ราย"** (จำนวนที่ปิดไม่สำเร็จ) → ใช้ `get_sales_unsuccessful` (ตัวเลขตรงกับหน้า /reports/sales-unsuccessful)
- **Supports:** Date range (เมื่อวาน, สัปดาห์นี้, เดือนนี้, specific dates), Filters (category, status, region, platform)
- **⚠️ ปิดสำเร็จ vs ปิดไม่สำเร็จ:** "ปิดการขายได้กี่ราย" → ใช้ `get_sales_closed`. "ปิดการขายไม่ได้กี่ราย" → ใช้ `get_sales_unsuccessful` (ไม่ใช่ search_leads)

**2. `get_lead_status`** - สำหรับค้นหาลีดด้วยชื่อ (specific lead)
- **Use when:** User asks about a SPECIFIC lead by name
- **Examples:**
  - "สถานะของลีดชื่อ John Doe" → `get_lead_status` with lead_name="John Doe"
  - "ลีด Tupsuri Paitoon สถานะอะไร" → `get_lead_status` with lead_name="Tupsuri Paitoon"
- **Difference from search_leads:** This is for finding ONE specific lead by name, not listing multiple leads

**3. `get_my_leads`** - สำหรับลีดที่ assign ให้ผู้ใช้ปัจจุบัน (My Leads)
- **Use when:** User asks about THEIR OWN leads
- **Examples:**
  - "ลีดของฉันมีอะไรบ้าง" → `get_my_leads`
  - "ลีดที่ assign ให้ฉัน" → `get_my_leads`
  - "ลีดของฉัน category Package" → `get_my_leads` with category="Package"
- **Returns:** Leads where user is `sale_owner_id` OR `post_sales_owner_id`, with statistics

**4. `get_lead_detail`** - สำหรับรายละเอียดลีด (full detail)
- **Use when:** User asks for DETAILED information about a specific lead
- **Examples:**
  - "แสดงรายละเอียดลีด ID 123" → `get_lead_detail` with lead_id=123
  - "ข้อมูลเต็มของลีด John Doe" → First use `get_lead_status` to find ID, then `get_lead_detail`
- **Returns:** Full lead data, ALL productivity logs, timeline, relations (credit_evaluation, lead_products, quotations)

**5. `get_lead_management`** - สำหรับข้อมูล Lead Management page
- **Use when:** User asks about lead management overview (leads + sales team + statistics)
- **Examples:**
  - "ข้อมูล Lead Management" → `get_lead_management`
  - "แสดงสถานะการจัดการลีด" → `get_lead_management`
- **Returns:** Leads, sales team, user info, statistics (assigned/unassigned, assignment rate, contact rate)

---

#### 👥 Sales Team (4 tools)

**6. `get_team_kpi`** - สำหรับ KPI ทีมขาย (Team KPI with metrics)
- **Use when:** User asks about team performance, KPI, conversion rates
- **Examples:**
  - "KPI ของทีมขาย" → `get_team_kpi`
  - "ประสิทธิภาพทีมขาย" → `get_team_kpi`
  - "อัตราการแปลงของทีม" → `get_team_kpi`
- **Returns:** Sales team list with per-member metrics (currentLeads, totalLeads, closedLeads, conversionRate, contactRate), overall statistics

**7. `get_sales_team`** - สำหรับรายการทีมขายพร้อม metrics (Sales Team)
- **Use when:** User asks about sales team list with performance metrics
- **Examples:**
  - "รายการทีมขาย" → `get_sales_team`
  - "ทีมขายและประสิทธิภาพ" → `get_sales_team`
  - "ทีมขาย category Package" → `get_sales_team` with category="Package"
- **Similar to get_team_kpi:** But may have slightly different response structure

**8. `get_sales_team_list`** - สำหรับรายชื่อทีมขายแบบง่าย (dropdown)
- **Use when:** User asks for SIMPLE list of sales team members (for selection/dropdown)
- **Examples:**
  - "รายชื่อทีมขาย" → `get_sales_team_list`
  - "ทีมขายที่ active" → `get_sales_team_list` with status="active"
- **Returns:** Simple list (id, name, email, phone, department, position) - minimal data

**9. `get_sales_team_data`** - สำหรับข้อมูลทีมขายพร้อม data (leads, quotations)
- **Use when:** User asks about sales team with detailed data (leads, quotations, deals, pipeline value)
- **Examples:**
  - "ข้อมูลทีมขายพร้อม leads" → `get_sales_team_data`
  - "ทีมขายและ deals" → `get_sales_team_data`
  - "มูลค่าพอร์ตของทีม" → `get_sales_team_data`
- **Returns:** Sales team with metrics (deals_closed, pipeline_value, conversion_rate) + leads + quotations data

---

#### 📅 Appointments (1 tool)

**10. `get_appointments`** - สำหรับรายการนัดหมาย
- **Use when:** User asks about appointments
- **Examples:**
  - "นัดหมายวันนี้" → `get_appointments` with date_from="today"
  - "นัดช่าง" → `get_appointments` with appointment_type="engineer"
  - "นัดติดตาม" → `get_appointments` with appointment_type="follow-up"
  - "นัดชำระเงิน" → `get_appointments` with appointment_type="payment"
- **Returns:** Categorized appointments (engineer, follow-up, payment)

---

#### 📅 Appointments (2 tools)

**11. `get_service_appointments`** - สำหรับนัดหมายบริการ (Service Appointments)
- **Use when:** User asks about service/maintenance appointments (NOT sales appointments)
- **Examples:**
  - "นัดหมายบริการ" → `get_service_appointments`
  - "นัดบริการซ่อม" → `get_service_appointments`
- **Difference from get_appointments:** This is for service/maintenance, not sales appointments

---

#### 📄 Documents & Quotations (2 tools)

**12. `get_sales_docs`** - สำหรับเอกสารการขาย (Sales Documents)
- **Use when:** User asks about sales documents (QT/Quotation, BL/Bill of Lading, INV/Invoice)
- **Examples:**
  - "เอกสารการขาย" → `get_sales_docs`
  - "ใบแจ้งหนี้" → `get_sales_docs`
  - "เอกสารเดือนนี้" → `get_sales_docs` with date_from/date_to

**13. `get_quotations`** - สำหรับใบเสนอราคา (Quotations)
- **Use when:** User asks about quotations specifically
- **Examples:**
  - "ใบเสนอราคา" → `get_quotations`
  - "QT เดือนนี้" → `get_quotations` with date_from/date_to
- **Returns:** Quotations data

---

#### 📋 Permits (1 tool)

**14. `get_permit_requests`** - สำหรับคำขออนุญาต (Permit Requests)
- **Use when:** User asks about permit requests or permits
- **Examples:**
  - "คำขออนุญาต" → `get_permit_requests`
  - "Permit requests" → `get_permit_requests`

---

#### 📊 Performance (1 tool)

**15. `get_sales_performance`** - สำหรับประสิทธิภาพการขายของพนักงานขายคนใดคนหนึ่ง (Sales Performance)
- **Use when:** User asks about performance of a SPECIFIC sales person (by sales_id)
- **Examples:**
  - "ประสิทธิภาพของพนักงานขาย ID 5" → `get_sales_performance` with sales_id=5
  - "Performance ของ John" → First find sales_id, then `get_sales_performance`
- **Note:** Only admin and manager can view sales performance
- **Returns:** Sales member info with metrics (total_leads, deals_closed, pipeline_value, conversion_rate)

---

#### 👤 User (1 tool)

**16. `get_user_info`** - สำหรับข้อมูลผู้ใช้ (User Information)
- **Use when:** User asks about user information or user details
- **Examples:**
  - "ข้อมูลผู้ใช้" → `get_user_info`
  - "รายชื่อผู้ใช้" → `get_user_info`
- **Returns:** User information

---

#### 📈 Summary (1 tool)

**17. `get_daily_summary`** - สำหรับสรุปข้อมูลรายวัน (Daily Summary)
- **Use when:** User asks about daily summary or statistics
- **Examples:**
  - "ยอดวันนี้" → `get_daily_summary` with date="today"
  - "สรุปวันนี้" → `get_daily_summary`
- **Returns:** Daily statistics (new leads, total leads, etc.)

---

### ⚠️ ปิดสำเร็จ vs ปิดไม่สำเร็จ (สำคัญ!)

| คำถาม | Tool ที่ใช้ | Parameters |
|--------|-------------|------------|
| "เดือนที่แล้วปิดการขาย**ได้**กี่ราย" / "ปิดการขาย**ได้**กี่ราย" (จำนวนที่ปิดสำเร็จ) | `get_sales_closed` | date_from, date_to |
| "เดือนที่แล้วปิดการขาย**ไม่ได้**กี่ราย" / "ปิดการขาย**ไม่ได้**กี่ราย" (จำนวนที่ปิดไม่สำเร็จ) | `get_sales_unsuccessful` | date_from, date_to |

**เหตุผล:** `get_sales_closed` ดึงเฉพาะรายที่ปิดสำเร็จ (จาก lead_productivity_logs). `get_sales_unsuccessful` ดึงรายที่ปิดไม่สำเร็จจาก lead_productivity_logs ที่ status='ปิดการขายไม่สำเร็จ' (วันที่ log.created_at_thai) — ตัวเลขตรงกับหน้า /reports/sales-unsuccessful. ห้ามใช้ search_leads สำหรับ "ปิดการขายไม่ได้กี่ราย" เพราะจะได้ตัวเลขไม่ตรงกับหน้า report.

---

## 🔍 Decision Tree

```
User asks about...

├── Leads?
│   ├── Specific lead by name? → get_lead_status
│   ├── Detailed info (all logs, timeline)? → get_lead_detail
│   ├── MY leads (assigned to me)? → get_my_leads
│   ├── Lead management overview? → get_lead_management
│   └── General list/search? → search_leads
│
├── Sales Team?
│   ├── Simple list (dropdown)? → get_sales_team_list
│   ├── With detailed data (leads, quotations)? → get_sales_team_data
│   ├── With metrics (KPI, conversion rate)? → get_team_kpi or get_sales_team
│   ├── Performance/statistics (team)? → get_team_kpi
│   └── Performance (specific sales person)? → get_sales_performance (needs sales_id)
│
├── Appointments?
│   ├── Sales appointments? → get_appointments
│   └── Service/maintenance appointments? → get_service_appointments
│
├── Documents?
│   ├── Quotations specifically? → get_quotations
│   └── Sales documents (QT/BL/INV)? → get_sales_docs
│
├── Permits?
│   └── Permit requests → get_permit_requests
│
├── User Info?
│   └── User information → get_user_info
│
└── Summary?
    └── Daily summary/statistics → get_daily_summary
```

---

## 📋 Tool Schemas

### 1. search_leads
```json
{
  "name": "search_leads",
  "description": "Search or list leads based on query criteria with date range support. Use for general lead listing/searching. Supports natural language dates: 'เมื่อวาน' (yesterday), 'สัปดาห์นี้' (this week), 'เดือนนี้' (this month). Always extract date_from and date_to when user mentions dates.",
  "parameters": {
    "query": "string (required) - Search query from user message",
    "date_from": "string (optional) - Start date YYYY-MM-DD (extract from query if user mentions dates)",
    "date_to": "string (optional) - End date YYYY-MM-DD (extract from query if user mentions date ranges)"
  }
}
```

### 2. get_lead_status
```json
{
  "name": "get_lead_status",
  "description": "Get status of a SPECIFIC lead by name. Use when user asks about ONE specific lead by name, not for listing multiple leads.",
  "parameters": {
    "lead_name": "string (required) - Name of the specific lead to search for"
  }
}
```

### 3. get_my_leads
```json
{
  "name": "get_my_leads",
  "description": "Get leads assigned to the current user (where user is sale_owner_id OR post_sales_owner_id). Use when user asks about THEIR OWN leads.",
  "parameters": {
    "category": "string (optional, default: 'Package') - Filter by category (Package/Wholesale)",
    "date_from": "string (optional) - Start date YYYY-MM-DD",
    "date_to": "string (optional) - End date YYYY-MM-DD"
  }
}
```

### 4. get_lead_detail
```json
{
  "name": "get_lead_detail",
  "description": "Get FULL DETAILED information about a specific lead including all productivity logs, timeline, relations (credit_evaluation, lead_products, quotations). Use when user asks for detailed/complete information about a lead.",
  "parameters": {
    "lead_id": "integer (required) - ID of the lead to get details for"
  }
}
```

### 5. get_lead_management
```json
{
  "name": "get_lead_management",
  "description": "Get Lead Management page data (leads + sales team + user + statistics). Use when user asks about lead management overview or statistics.",
  "parameters": {
    "category": "string (optional, default: 'Package') - Filter by category",
    "date_from": "string (optional) - Start date YYYY-MM-DD",
    "date_to": "string (optional) - End date YYYY-MM-DD"
  }
}
```

### 6. get_team_kpi
```json
{
  "name": "get_team_kpi",
  "description": "Get team KPI and performance metrics with per-member statistics (currentLeads, totalLeads, closedLeads, conversionRate, contactRate). Use when user asks about team performance, KPI, or conversion rates.",
  "parameters": {
    "team_id": "integer (optional) - Specific team ID (default: all teams)",
    "category": "string (optional) - Filter by category",
    "date_from": "string (optional) - Start date YYYY-MM-DD",
    "date_to": "string (optional) - End date YYYY-MM-DD"
  }
}
```

### 7. get_sales_team
```json
{
  "name": "get_sales_team",
  "description": "Get sales team list with performance metrics. Similar to get_team_kpi but may have different response structure.",
  "parameters": {
    "category": "string (optional) - Filter by category",
    "date_from": "string (optional) - Start date YYYY-MM-DD",
    "date_to": "string (optional) - End date YYYY-MM-DD"
  }
}
```

### 8. get_sales_team_list
```json
{
  "name": "get_sales_team_list",
  "description": "Get simple sales team list for dropdown/selection. Returns minimal data (id, name, email, phone, department, position). Use when user asks for simple list of sales team members.",
  "parameters": {
    "status": "string (optional, default: 'active') - Filter by status"
  }
}
```

### 9. get_sales_team_data
```json
{
  "name": "get_sales_team_data",
  "description": "Get sales team data with detailed metrics (deals_closed, pipeline_value, conversion_rate) and data (leads, quotations). Use when user asks about sales team with detailed data or pipeline value.",
  "parameters": {
    "date_from": "string (optional) - Start date YYYY-MM-DD",
    "date_to": "string (optional) - End date YYYY-MM-DD"
  }
}
```

### 10. get_appointments
```json
{
  "name": "get_appointments",
  "description": "Get appointments categorized by type (engineer, follow-up, payment). Use when user asks about appointments.",
  "parameters": {
    "appointment_type": "string (optional) - Type: 'engineer', 'follow-up', 'payment', or 'all'",
    "date_from": "string (optional) - Start date YYYY-MM-DD",
    "date_to": "string (optional) - End date YYYY-MM-DD",
    "sales_member_id": "integer (optional) - Filter by sales member ID"
  }
}
```

### 11. get_service_appointments
```json
{
  "name": "get_service_appointments",
  "description": "Get service appointments (for service/maintenance appointments, not sales appointments). Use when user asks about service appointments or maintenance appointments.",
  "parameters": {
    "appointment_type": "string (optional) - Type of appointment (default: 'all')",
    "date_from": "string (optional) - Start date YYYY-MM-DD",
    "date_to": "string (optional) - End date YYYY-MM-DD"
  }
}
```

### 12. get_sales_docs
```json
{
  "name": "get_sales_docs",
  "description": "Get sales documents (QT/Quotation, BL/Bill of Lading, INV/Invoice). Use when user asks about sales documents or invoices.",
  "parameters": {
    "date_from": "string (optional) - Start date YYYY-MM-DD",
    "date_to": "string (optional) - End date YYYY-MM-DD",
    "limit": "integer (optional, default: 100) - Limit number of results"
  }
}
```

### 13. get_quotations
```json
{
  "name": "get_quotations",
  "description": "Get quotations (ใบเสนอราคา). Use when user asks about quotations specifically.",
  "parameters": {
    "date_from": "string (optional) - Start date YYYY-MM-DD",
    "date_to": "string (optional) - End date YYYY-MM-DD",
    "limit": "integer (optional, default: 100) - Limit number of results"
  }
}
```
```

### 14. get_permit_requests
```json
{
  "name": "get_permit_requests",
  "description": "Get permit requests (คำขออนุญาต). Use when user asks about permit requests or permits.",
  "parameters": {
    "date_from": "string (optional) - Start date YYYY-MM-DD",
    "date_to": "string (optional) - End date YYYY-MM-DD",
    "limit": "integer (optional, default: 100) - Limit number of results"
  }
}
```

### 15. get_sales_performance
```json
{
  "name": "get_sales_performance",
  "description": "Get sales performance for a SPECIFIC sales member (by sales_id). Use when user asks about performance of a specific sales person. Note: Only admin and manager can view sales performance.",
  "parameters": {
    "sales_id": "integer (required) - ID of the sales member to get performance for",
    "date_from": "string (optional) - Start date YYYY-MM-DD",
    "date_to": "string (optional) - End date YYYY-MM-DD",
    "period": "string (optional, default: 'month') - Period: 'day', 'week', 'month', 'year'"
  }
}
```

### 16. get_user_info
```json
{
  "name": "get_user_info",
  "description": "Get user information. Use when user asks about user information or user details.",
  "parameters": {
    "limit": "integer (optional, default: 100) - Limit number of results"
  }
}
```

### 17. get_daily_summary
```json
{
  "name": "get_daily_summary",
  "description": "Get daily summary statistics (leads, customers, sales) for a specific date. Use when user asks about daily summary or statistics.",
  "parameters": {
    "date": "string (optional) - Date in YYYY-MM-DD format (default: today)"
  }
}
```

---

## 🎯 Common Use Cases & Tool Selection

| User Query | Tool | Parameters |
|------------|------|------------|
| "ลีดวันนี้มีใครบ้าง" | `search_leads` | query="today", date_from="today" |
| "ลูกค้าที่ได้มาเมื่อวาน" | `search_leads` | query="yesterday", date_from="yesterday", date_to="yesterday" |
| "เดือนที่แล้วปิดการขายไม่ได้กี่ราย" | `get_sales_unsuccessful` | date_from/date_to=เดือนที่แล้ว |
| "ลีดของฉัน" | `get_my_leads` | category="Package" |
| "สถานะลีดชื่อ John" | `get_lead_status` | lead_name="John" |
| "รายละเอียดลีด ID 123" | `get_lead_detail` | lead_id=123 |
| "KPI ทีมขาย" | `get_team_kpi` | - |
| "รายชื่อทีมขาย" | `get_sales_team_list` | status="active" |
| "ทีมขายและ deals" | `get_sales_team_data` | - |
| "นัดหมายวันนี้" | `get_appointments` | date_from="today", date_to="today" |
| "นัดบริการ" | `get_service_appointments` | - |
| "เอกสารการขาย" | `get_sales_docs` | - |
| "ใบเสนอราคา" | `get_quotations` | - |
| "คำขออนุญาต" | `get_permit_requests` | - |
| "ประสิทธิภาพของพนักงานขาย ID 5" | `get_sales_performance` | sales_id=5 |
| "ข้อมูลผู้ใช้" | `get_user_info` | - |

---

## ⚠️ Important Notes

1. **Always extract dates from natural language** - Thai dates like "เมื่อวาน", "สัปดาห์นี้", "เดือนนี้" should be converted to `date_from` and `date_to` parameters.

2. **Use search_leads for general listing** - When user asks about "leads" in general, use `search_leads`, not `get_lead_status`.

3. **Use get_lead_status for specific names** - Only when user mentions a SPECIFIC lead name.

4. **get_my_leads vs search_leads** - `get_my_leads` is for leads assigned to current user, `search_leads` is for all leads.

5. **ปิดสำเร็จ vs ปิดไม่สำเร็จ** - "ปิดการขายได้กี่ราย" → `get_sales_closed`. "ปิดการขายไม่ได้กี่ราย" → `get_sales_unsuccessful` (ตัวเลขตรงหน้า /reports/sales-unsuccessful).

6. **get_team_kpi vs get_sales_team** - Both return team metrics, choose based on specific requirements.

7. **get_sales_team_list for simple lists** - Use when minimal data is needed (for dropdown/selection).

8. **get_appointments vs get_service_appointments** - `get_appointments` is for sales appointments, `get_service_appointments` is for service/maintenance appointments.

9. **get_sales_performance requires sales_id** - This is for a SPECIFIC sales person, not the whole team. Use `get_team_kpi` for team performance.

10. **Inventory-related functions NOT available** - `get_stock_movements`, `get_inventory_status`, and `get_customer_info` (inventory customer) are NOT available because the inventory system is not in use.

11. **get_sales_performance access control** - Only admin and manager can view sales performance.

---

## 📚 Reference

- **Full RPC Functions Summary:** `docs/RPC_FUNCTIONS_SUMMARY.md`
- **Review & Enhancement Plan:** `docs/RPC_FUNCTIONS_REVIEW_AND_ENHANCEMENT.md`
