# 🤖 AI Chatbot Tools - Complete Summary

## 📊 สรุป Tools สำหรับ AI Chatbot

**รวมทั้งหมด: 17 Tools** (จาก 21 RPC Functions ใน Database)

### ✅ Available Tools (17 tools)
### ❌ Excluded Tools (4 functions - Inventory System ไม่ได้ใช้จริง)

---

## 📋 Tools ทั้งหมด (17 tools)

### 🎯 Leads Management (5 tools)

1. **`search_leads`** → `ai_get_leads`
   - **ใช้เมื่อ:** User ถามเกี่ยวกับลีดทั่วไป, รายชื่อลีด, ลีดตามวันที่/สถานะ/หมวดหมู่
   - **Examples:** "ลีดวันนี้มีใครบ้าง", "ลูกค้าที่ได้มาเมื่อวาน"

2. **`get_lead_status`** → `ai_get_lead_status`
   - **ใช้เมื่อ:** User ถามเกี่ยวกับลีดชื่อเฉพาะ
   - **Examples:** "สถานะของลีดชื่อ John Doe"

3. **`get_my_leads`** → `ai_get_my_leads`
   - **ใช้เมื่อ:** User ถามเกี่ยวกับลีดของตัวเอง
   - **Examples:** "ลีดของฉัน", "ลีดที่ assign ให้ฉัน"

4. **`get_lead_detail`** → `ai_get_lead_detail`
   - **ใช้เมื่อ:** User ถามรายละเอียดลีดแบบเต็ม
   - **Examples:** "รายละเอียดลีด ID 123"

5. **`get_lead_management`** → `ai_get_lead_management`
   - **ใช้เมื่อ:** User ถามเกี่ยวกับ lead management overview
   - **Examples:** "ข้อมูล Lead Management"

---

### 👥 Sales Team (4 tools)

6. **`get_team_kpi`** → `ai_get_team_kpi`
   - **ใช้เมื่อ:** User ถามเกี่ยวกับ KPI ทีมขาย, ประสิทธิภาพทีม
   - **Examples:** "KPI ของทีมขาย", "ประสิทธิภาพทีม"

7. **`get_sales_team`** → `ai_get_sales_team`
   - **ใช้เมื่อ:** User ถามเกี่ยวกับรายการทีมขายพร้อม metrics
   - **Examples:** "รายการทีมขาย"

8. **`get_sales_team_list`** → `ai_get_sales_team_list`
   - **ใช้เมื่อ:** User ถามรายชื่อทีมขายแบบง่าย (สำหรับ dropdown)
   - **Examples:** "รายชื่อทีมขาย", "ทีมขายที่ active"

9. **`get_sales_team_data`** → `ai_get_sales_team_data`
   - **ใช้เมื่อ:** User ถามเกี่ยวกับทีมขายพร้อม data (leads, quotations, deals, pipeline value)
   - **Examples:** "ทีมขายและ deals", "มูลค่าพอร์ตของทีม"

---

### 📅 Appointments (2 tools)

10. **`get_appointments`** → `ai_get_appointments`
    - **ใช้เมื่อ:** User ถามเกี่ยวกับนัดหมายขาย (sales appointments)
    - **Examples:** "นัดหมายวันนี้", "นัดช่าง", "นัดติดตาม", "นัดชำระเงิน"

11. **`get_service_appointments`** → `ai_get_service_appointments`
    - **ใช้เมื่อ:** User ถามเกี่ยวกับนัดหมายบริการ (service/maintenance appointments)
    - **Examples:** "นัดหมายบริการ", "นัดบริการซ่อม"
    - **Difference:** `get_appointments` = sales, `get_service_appointments` = service/maintenance

---

### 📄 Documents & Quotations (2 tools)

12. **`get_sales_docs`** → `ai_get_sales_docs`
    - **ใช้เมื่อ:** User ถามเกี่ยวกับเอกสารการขาย (QT/Quotation, BL/Bill of Lading, INV/Invoice)
    - **Examples:** "เอกสารการขาย", "ใบแจ้งหนี้"

13. **`get_quotations`** → `ai_get_quotations`
    - **ใช้เมื่อ:** User ถามเกี่ยวกับใบเสนอราคา
    - **Examples:** "ใบเสนอราคา", "QT เดือนนี้"

---

### 📋 Permits (1 tool)

14. **`get_permit_requests`** → `ai_get_permit_requests`
    - **ใช้เมื่อ:** User ถามเกี่ยวกับคำขออนุญาต
    - **Examples:** "คำขออนุญาต", "Permit requests"

---

### 📊 Performance (1 tool)

15. **`get_sales_performance`** → `ai_get_sales_performance`
    - **ใช้เมื่อ:** User ถามเกี่ยวกับประสิทธิภาพของพนักงานขายคนใดคนหนึ่ง (by sales_id)
    - **Examples:** "ประสิทธิภาพของพนักงานขาย ID 5"
    - **Note:** Only admin and manager can view sales performance
    - **Returns:** Sales member info with metrics (total_leads, deals_closed, pipeline_value, conversion_rate)

---

### 👤 User (1 tool)

16. **`get_user_info`** → `ai_get_user_info`
    - **ใช้เมื่อ:** User ถามเกี่ยวกับข้อมูลผู้ใช้
    - **Examples:** "ข้อมูลผู้ใช้", "รายชื่อผู้ใช้"

---

### 📈 Summary (1 tool)

17. **`get_daily_summary`** → `ai_get_daily_summary`
    - **ใช้เมื่อ:** User ถามเกี่ยวกับสรุปข้อมูลรายวัน
    - **Examples:** "ยอดวันนี้", "สรุปวันนี้"

---

## ❌ Excluded Tools (Inventory System - ไม่ได้ใช้จริง)

### Inventory-Related Functions (4 functions)

1. **`get_stock_movements`** → `ai_get_stock_movements`
   - **เหตุผล:** Inventory system ยังไม่ได้ใช้จริง
   - **Status:** ❌ NOT available for AI Chatbot

2. **`get_inventory_status`** → `ai_get_inventory_status`
   - **เหตุผล:** Inventory system ยังไม่ได้ใช้จริง
   - **Status:** ❌ NOT available for AI Chatbot

3. **`get_customer_info`** → `ai_get_customer_info`
   - **เหตุผล:** Customer ของฝั่ง inventory system ยังไม่ได้ใช้จริง
   - **Status:** ❌ NOT available for AI Chatbot
   - **Note:** ใช้สำหรับ inventory customer (NOT sales customer info)

4. **`validate_phone`** → `ai_validate_phone`
   - **เหตุผล:** ใช้สำหรับ form validation (ไม่ใช่สำหรับ AI Chatbot queries)
   - **Status:** ❌ NOT available for AI Chatbot

---

## 📊 Comparison Table

| Category | Total Functions | Available Tools | Excluded |
|----------|----------------|-----------------|----------|
| Leads Management | 7 | 5 | 2 (validate_phone, -) |
| Sales Team | 4 | 4 | 0 |
| Appointments | 2 | 2 | 0 |
| Documents & Quotations | 2 | 2 | 0 |
| Permits | 1 | 1 | 0 |
| Performance | 1 | 1 | 0 |
| User | 1 | 1 | 0 |
| Summary | 1 | 1 | 0 |
| **Customer (Inventory)** | 1 | 0 | 1 |
| **Inventory** | 2 | 0 | 2 |
| **TOTAL** | **21** | **17** | **4** |

---

## ✅ Implementation Status

### ✅ Completed
- ✅ Added `get_sales_performance` wrapper in `db_tools.py`
- ✅ Added 6 new tools in `TOOL_SCHEMAS` (llm_router.py)
- ✅ Added handlers for 6 new tools in `db_query_node.py`
- ✅ Updated imports in `db_query_node.py`
- ✅ Updated system prompt with tool descriptions
- ✅ Updated `AI_TOOL_SELECTION_GUIDE.md` documentation
- ✅ Removed `get_customer_info` from TOOL_SCHEMAS (inventory customer)
- ✅ Removed `get_customer_info` handler from db_query_node
- ✅ Excluded inventory-related functions (stock_movements, inventory_status, customer_info)

### 📝 Files Modified
1. `backend/app/tools/db_tools.py` - Added `get_sales_performance` wrapper
2. `backend/app/orchestrator/llm_router.py` - Added 6 tools to TOOL_SCHEMAS, removed `get_customer_info`
3. `backend/app/orchestrator/nodes/db_query.py` - Added handlers for 6 tools, removed `get_customer_info`
4. `docs/AI_TOOL_SELECTION_GUIDE.md` - Updated with all 17 tools

---

## 🎯 Tool Selection Examples

| User Query | Tool Selected | Parameters |
|------------|---------------|------------|
| "ลีดวันนี้มีใครบ้าง" | `search_leads` | query="today", date_from="today" |
| "ลีดของฉัน" | `get_my_leads` | category="Package" |
| "KPI ทีมขาย" | `get_team_kpi` | - |
| "ประสิทธิภาพของพนักงานขาย ID 5" | `get_sales_performance` | sales_id=5 |
| "นัดหมายวันนี้" | `get_appointments` | date_from="today" |
| "นัดบริการ" | `get_service_appointments` | - |
| "เอกสารการขาย" | `get_sales_docs` | - |
| "ใบเสนอราคา" | `get_quotations` | - |
| "คำขออนุญาต" | `get_permit_requests` | - |
| "ข้อมูลผู้ใช้" | `get_user_info` | - |
| "ยอดวันนี้" | `get_daily_summary` | date="today" |

---

## ⚠️ Important Notes

1. **Inventory System NOT Available** - `get_stock_movements`, `get_inventory_status`, and `get_customer_info` (inventory customer) are excluded because inventory system is not in use yet.

2. **get_appointments vs get_service_appointments** - `get_appointments` is for sales appointments, `get_service_appointments` is for service/maintenance appointments.

3. **get_sales_performance requires sales_id** - This is for a SPECIFIC sales person, not the whole team. Use `get_team_kpi` for team performance.

4. **get_sales_performance access control** - Only admin and manager can view sales performance.

5. **Always extract dates from natural language** - Thai dates like "เมื่อวาน", "สัปดาห์นี้", "เดือนนี้" should be converted to `date_from` and `date_to` parameters.

---

## 📚 References

- **Full RPC Functions Summary:** `/docs/RPC_FUNCTIONS_SUMMARY.md`
- **AI Tool Selection Guide:** `/docs/AI_TOOL_SELECTION_GUIDE.md`
- **Review & Enhancement Plan:** `/docs/RPC_FUNCTIONS_REVIEW_AND_ENHANCEMENT.md`
