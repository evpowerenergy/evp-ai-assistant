# 📊 RPC Functions Coverage Analysis

> **วิเคราะห์:** RPC Functions ครอบคลุมข้อมูลครบหรือยัง?  
> **Date:** 2025-01-16

---

## 📋 สรุป RPC Functions ที่มีอยู่

### Simple Functions (4 functions)
1. ✅ `ai_get_lead_status` - ค้นหา lead โดยชื่อ
2. ✅ `ai_get_daily_summary` - สรุปประจำวัน
3. ✅ `ai_get_customer_info` - ข้อมูลลูกค้า
4. ✅ `ai_get_team_kpi` - KPI ทีม (basic)

### Enhanced Functions (5 functions)
5. ✅ `ai_get_leads` - Enhanced lead query (filters, date range)
6. ✅ `ai_get_lead_detail` - Lead detail + related data
7. ✅ `ai_get_sales_performance` - Sales metrics
8. ✅ `ai_get_inventory_status` - Inventory with filters
9. ✅ `ai_get_appointments` - Appointments with filters

**รวม: 9 RPC Functions**

---

## 📊 Coverage Analysis: Tables ใน CRM

### ✅ ครอบคลุมแล้ว (Core Tables)

| Table | RPC Function | Status | Notes |
|-------|--------------|--------|-------|
| **leads** | `ai_get_lead_status`, `ai_get_leads`, `ai_get_lead_detail` | ✅ Complete | 3 functions |
| **customer_services** | `ai_get_customer_info` | ✅ Complete | 1 function |
| **sales_team_with_user_info** | `ai_get_team_kpi`, `ai_get_sales_performance` | ✅ Complete | 2 functions |
| **products** | `ai_get_inventory_status` | ✅ Complete | Included |
| **inventory_units** | `ai_get_inventory_status` | ✅ Complete | Included |
| **appointments** | `ai_get_appointments` | ✅ Complete | 1 function |

**Coverage: 6/27 tables (22%)**

---

### ⚠️ ครอบคลุมบางส่วน (Related Data)

| Table | RPC Function | Status | Notes |
|-------|--------------|--------|-------|
| **lead_productivity_logs** | `ai_get_lead_detail` | ⚠️ Partial | Included in lead detail only |
| **quotations** | `ai_get_lead_detail`, `ai_get_sales_performance` | ⚠️ Partial | Included but no dedicated function |
| **suppliers** | `ai_get_inventory_status` | ⚠️ Partial | May be included in inventory |
| **purchase_orders** | `ai_get_inventory_status` | ⚠️ Partial | May be included in inventory |
| **customers** | `ai_get_inventory_status` | ⚠️ Partial | May be included in inventory |

**Coverage: 5 tables (partial)**

---

### ❌ ยังไม่ครอบคลุม (Missing Tables)

| Table | Priority | Use Case | Recommended Function |
|-------|----------|----------|---------------------|
| **service_appointments** | 🔴 High | Service appointments | `ai_get_service_appointments` |
| **permit_requests** | 🟡 Medium | Permit requests | `ai_get_permit_requests` |
| **sales_docs** | 🔴 High | Sales documents (QT/BL/INV) | `ai_get_sales_docs` |
| **sales_doc_items** | 🟡 Medium | Sales doc items | Included in sales_docs |
| **stock_movements** | 🟡 Medium | Stock movements | `ai_get_stock_movements` |
| **ads_campaigns** | 🟡 Medium | Ad campaigns | `ai_get_ad_campaigns` |
| **credit_evaluation** | 🟡 Medium | Credit evaluation | `ai_get_credit_evaluation` |
| **users** | 🟡 Medium | User information | `ai_get_user_info` |
| **conversations** | 🟢 Low | Conversations | `ai_get_conversations` |
| **bookings** | 🟢 Low | Bookings | `ai_get_bookings` |
| **resources** | 🟢 Low | Resources | `ai_get_resources` |
| **office_equipment** | 🟢 Low | Office equipment | `ai_get_office_equipment` |
| **platforms** | 🟢 Low | Platforms | `ai_get_platforms` |
| **n8n_chat_histories** | 🟢 Low | Chat histories | Not needed for AI |
| **openai_costs** | 🟢 Low | OpenAI costs | Not needed for AI |
| **chat_state** | 🟢 Low | Chat state | Not needed for AI |

**Missing: 16 tables**

---

## 🎯 Priority Analysis

### 🔴 High Priority (ควรมี)

**1. `ai_get_service_appointments`**
- **Why:** Service appointments เป็นข้อมูลสำคัญ
- **Use Case:** "นัดหมาย service ของลูกค้า X"
- **Tables:** `service_appointments`

**2. `ai_get_sales_docs`**
- **Why:** Sales documents (QT/BL/INV) เป็นข้อมูลสำคัญ
- **Use Case:** "ใบเสนอราคาของ lead X" หรือ "ใบกำกับภาษี"
- **Tables:** `sales_docs`, `sales_doc_items`

**3. `ai_get_quotations` (Dedicated)**
- **Why:** Quotations มีข้อมูลสำคัญ (amount, payment date)
- **Use Case:** "ใบเสนอราคาล่าสุด" หรือ "ยอด quotation"
- **Tables:** `quotations`, `quotation_documents`

### 🟡 Medium Priority (ควรมีใน Phase 2/3)

**4. `ai_get_permit_requests`**
- **Why:** Permit requests เป็นข้อมูลสำคัญสำหรับ O&M
- **Use Case:** "สถานะ permit request"
- **Tables:** `permit_requests`

**5. `ai_get_stock_movements`**
- **Why:** Stock movements สำหรับ inventory tracking
- **Use Case:** "การเคลื่อนไหวสินค้า X"
- **Tables:** `stock_movements`

**6. `ai_get_user_info`**
- **Why:** User information สำหรับ queries
- **Use Case:** "ข้อมูลพนักงาน X"
- **Tables:** `users`

### 🟢 Low Priority (ไม่จำเป็น)

- `conversations`, `bookings`, `resources`, `office_equipment`, `platforms`
- `n8n_chat_histories`, `openai_costs`, `chat_state` (system tables)

---

## 📊 Coverage Summary

### By Category

| Category | Tables | Covered | Partial | Missing | Coverage % |
|----------|--------|---------|---------|---------|------------|
| **Leads & Sales** | 5 | 3 | 1 | 1 | 60% |
| **Customers** | 2 | 1 | 1 | 0 | 50% |
| **Inventory** | 6 | 2 | 3 | 1 | 33% |
| **Appointments** | 2 | 1 | 0 | 1 | 50% |
| **Documents** | 3 | 0 | 1 | 2 | 0% |
| **System** | 9 | 0 | 0 | 9 | 0% |
| **Total** | **27** | **7** | **6** | **14** | **26%** |

### Overall Coverage

- **✅ Fully Covered:** 7 tables (26%)
- **⚠️ Partially Covered:** 6 tables (22%)
- **❌ Not Covered:** 14 tables (52%)

**Total Coverage: ~48%** (including partial)

---

## 🚨 Critical Missing Functions

### 1. Service Appointments
- **Function:** `ai_get_service_appointments`
- **Priority:** 🔴 High
- **Reason:** ข้อมูลสำคัญสำหรับ O&M team

### 2. Sales Documents
- **Function:** `ai_get_sales_docs`
- **Priority:** 🔴 High
- **Reason:** เอกสารการขาย (QT/BL/INV) เป็นข้อมูลสำคัญ

### 3. Quotations (Dedicated)
- **Function:** `ai_get_quotations`
- **Priority:** 🔴 High
- **Reason:** มีข้อมูลสำคัญ (amount, payment date) แต่ยังไม่มี dedicated function

---

## ✅ Recommendations

### Phase 2 (ตอนนี้) - เพิ่ม High Priority Functions

**ควรเพิ่ม 3 functions:**
1. `ai_get_service_appointments` - Service appointments
2. `ai_get_sales_docs` - Sales documents (QT/BL/INV)
3. `ai_get_quotations` - Quotations (dedicated)

**ผลลัพธ์:**
- Coverage เพิ่มเป็น ~60% (fully covered)
- ครอบคลุม use cases หลัก

### Phase 2/3 - เพิ่ม Medium Priority Functions

**ควรเพิ่ม 3 functions:**
4. `ai_get_permit_requests` - Permit requests
5. `ai_get_stock_movements` - Stock movements
6. `ai_get_user_info` - User information

**ผลลัพธ์:**
- Coverage เพิ่มเป็น ~70% (fully covered)

### Phase 3+ - Low Priority (Optional)

- `ai_get_ad_campaigns`
- `ai_get_credit_evaluation`
- และอื่นๆ (ถ้าจำเป็น)

---

## 📝 Implementation Plan

### Step 1: Create High Priority Functions (3 functions)

**Migration File:** `supabase/migrations/20250116000006_ai_rpc_functions_high_priority.sql`

**Functions:**
1. `ai_get_service_appointments`
2. `ai_get_sales_docs`
3. `ai_get_quotations`

### Step 2: Update Python Wrappers

**File:** `backend/app/tools/db_tools.py`

เพิ่ม functions:
- `get_service_appointments()`
- `get_sales_docs()`
- `get_quotations()`

### Step 3: Update AI Orchestrator

**File:** `backend/app/orchestrator/nodes/db_query.py`

เพิ่ม tool selection logic

---

## 🎯 Coverage Goals

### Current Status
- **Coverage:** ~48% (including partial)
- **Fully Covered:** 26%
- **Functions:** 9 functions

### Target (Phase 2)
- **Coverage:** ~60% (fully covered)
- **Functions:** 12 functions (+3 high priority)

### Target (Phase 3)
- **Coverage:** ~70% (fully covered)
- **Functions:** 15 functions (+3 medium priority)

---

## ✅ สรุป

### Current Coverage: ~48% (including partial)

**ครอบคลุมแล้ว:**
- ✅ Leads (3 functions)
- ✅ Customers (1 function)
- ✅ Sales Team (2 functions)
- ✅ Inventory (1 function)
- ✅ Appointments (1 function)

**ยังไม่ครอบคลุม:**
- ❌ Service Appointments (High Priority)
- ❌ Sales Documents (High Priority)
- ❌ Quotations (Dedicated) (High Priority)
- ❌ Permit Requests (Medium Priority)
- ❌ Stock Movements (Medium Priority)
- ❌ User Info (Medium Priority)

**Next Action:** สร้าง High Priority Functions (3 functions)

---

**Last Updated:** 2025-01-16
