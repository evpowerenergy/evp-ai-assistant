# 📊 RPC Functions Analysis & Implementation Plan

## 🎯 วัตถุประสงค์

วิเคราะห์ Edge Functions ทั้งหมดที่ใช้ใน Frontend และสร้างแผนการสร้าง RPC Functions สำหรับ AI Assistant เพื่อให้ chatbot สามารถเข้าถึงข้อมูลได้ครบถ้วนและตรงตามที่หน้าเว็บแสดง

---

## 📋 สรุป Edge Functions ทั้งหมด (34 functions)

### 🔵 Core APIs (17 functions)

#### **Leads Management (7 functions)**
1. ✅ `core-leads-lead-management` - ดึงข้อมูลลีดสำหรับ Lead Management
2. ✅ `core-leads-lead-mutations` - สร้าง/แก้ไข/ลบลีด
3. ✅ `core-leads-leads-list` - ดึงรายการลีดทั้งหมด
4. ✅ `core-leads-leads-for-dashboard` - ดึงข้อมูลลีดสำหรับ Dashboard
5. ✅ `core-leads-lead-detail` - ดึงรายละเอียดลีด (รวม relations)
6. ✅ `core-leads-phone-validation` - ตรวจสอบเบอร์โทรซ้ำ
7. ✅ `core-leads-sales-team-list` - ดึงรายชื่อทีมขาย

#### **My Leads (2 functions)**
8. ✅ `core-my-leads-my-leads` - ดึงลีดที่ assign ให้ผู้ใช้
9. ✅ `core-my-leads-my-leads-data` - ดึงข้อมูลลีดที่ assign (read-only)

#### **Sales Team (3 functions)**
10. ✅ `core-sales-team-sales-team` - ดึงรายการทีมขาย
11. ✅ `core-sales-team-sales-team-data` - ดึงข้อมูลทีมขาย (detailed)
12. ✅ `core-sales-team-filtered-sales-team` - ดึงทีมขายที่ผ่านการ filter

#### **Inventory (2 functions)**
13. ✅ `core-inventory-inventory` - ดึงข้อมูลคลังสินค้า
14. ✅ `core-inventory-inventory-mutations` - อัพเดทสต็อก

#### **Appointments (1 function)**
15. ✅ `core-appointments-appointments` - จัดการนัดหมาย

---

### 🟢 Additional APIs (9 functions)

#### **Products (1 function)**
16. ✅ `additional-products-products` - ดึงรายการสินค้า

#### **Inventory Units (1 function)**
17. ✅ `additional-inventory-inventory-units` - ดึง Inventory Units (Serial Numbers)

#### **Purchase Orders (2 functions)**
18. ✅ `additional-purchase-orders-purchase-orders` - ดึงรายการ Purchase Orders
19. ✅ `additional-purchase-orders-purchase-order-mutations` - จัดการ Purchase Orders

#### **Customer Services (4 functions)**
20. ✅ `additional-customer-customer-services` - ดึงรายการ Customer Services
21. ✅ `additional-customer-customer-service-stats` - ดึงสถิติ Customer Services
22. ✅ `additional-customer-customer-service-mutations` - จัดการ Customer Services
23. ✅ `additional-customer-customer-service-filters` - ดึง filter options

#### **Auth (1 function)**
24. ✅ `additional-auth-user-data` - ดึงข้อมูลผู้ใช้ (User Profile + Sales Member)

---

### 🔴 System APIs (10 functions)

#### **Management (2 functions)**
25. ✅ `system-management-sales-team-management` - จัดการทีมขาย
26. ✅ `system-management-products-management` - จัดการสินค้า

#### **Service (2 functions)**
27. ✅ `system-service-service-appointments` - จัดการ Service Appointments
28. ✅ `system-service-service-visits` - จัดการ Service Visits

#### **Follow-up (1 function)**
29. ✅ `system-follow-up-sale-follow-up` - จัดการ Sale Follow-up

#### **Productivity (1 function)**
30. ✅ `system-productivity-productivity-log-submission` - ส่ง Productivity Log

#### **Infrastructure (4 functions)**
31. ✅ `system-openai-sync` - Sync OpenAI usage data
32. ✅ `system-keep-alive` - Keep Edge Functions warm
33. ✅ `system-csp-report` - Receive CSP violation reports
34. ✅ `system-health` - Health check endpoint

---

## 🔍 RPC Functions ที่มีอยู่แล้ว (Current)

### ✅ มีอยู่แล้ว (5 functions)

1. **`ai_get_leads`** ✅
   - ครอบคลุม: `core-leads-leads-list`, `core-leads-leads-for-dashboard`
   - Status: ✅ Ready

2. **`ai_get_lead_status`** ✅
   - ครอบคลุม: `core-leads-lead-detail` (บางส่วน)
   - Status: ✅ Ready

3. **`ai_get_daily_summary`** ✅
   - ครอบคลุม: Dashboard statistics
   - Status: ✅ Ready

4. **`ai_get_customer_info`** ✅
   - ครอบคลุม: `additional-customer-customer-services` (บางส่วน)
   - Status: ✅ Ready

5. **`ai_get_team_kpi`** ✅
   - ครอบคลุม: `core-sales-team-sales-team-data` (บางส่วน)
   - Status: ✅ Ready

---

## ❌ RPC Functions ที่ยังไม่มี (Missing)

### 🔴 Priority 1: Core CRM Functions (High Priority)

#### 1. **Lead Detail & Relations**
- **Edge Function:** `core-leads-lead-detail`
- **RPC Function:** `ai_get_lead_detail`
- **Purpose:** ดึงรายละเอียดลีดครบถ้วน (Timeline, Productivity Logs, Relations)
- **Parameters:**
  - `p_lead_id` (UUID)
  - `p_user_id` (UUID)
  - `p_user_role` (TEXT)
- **Returns:**
  - Lead data (full)
  - Timeline events
  - Productivity logs
  - Related appointments
  - Related follow-ups

#### 2. **My Leads**
- **Edge Function:** `core-my-leads-my-leads`
- **RPC Function:** `ai_get_my_leads`
- **Purpose:** ดึงลีดที่ assign ให้ผู้ใช้ปัจจุบัน
- **Parameters:**
  - `p_user_id` (UUID)
  - `p_category` (TEXT) - 'Package' | 'Wholesale'
  - `p_filters` (JSONB) - status, platform, etc.
  - `p_date_from` (DATE, optional)
  - `p_date_to` (DATE, optional)
- **Returns:**
  - Array of leads (assigned to user)
  - User data
  - Sales member data

#### 3. **Sales Team List**
- **Edge Function:** `core-sales-team-sales-team-list`, `core-sales-team-sales-team`
- **RPC Function:** `ai_get_sales_team`
- **Purpose:** ดึงรายการทีมขาย
- **Parameters:**
  - `p_user_id` (UUID)
  - `p_category` (TEXT, optional) - 'Package' | 'Wholesale'
  - `p_filters` (JSONB, optional) - status, role
- **Returns:**
  - Array of sales team members
  - Performance stats (optional)

#### 4. **Appointments**
- **Edge Function:** `core-appointments-appointments`
- **RPC Function:** `ai_get_appointments`
- **Purpose:** ดึงนัดหมายของผู้ใช้
- **Parameters:**
  - `p_user_id` (UUID)
  - `p_date_from` (DATE, optional)
  - `p_date_to` (DATE, optional)
  - `p_lead_id` (UUID, optional)
- **Returns:**
  - Array of appointments
  - Related lead data

#### 5. **Phone Validation**
- **Edge Function:** `core-leads-phone-validation`
- **RPC Function:** `ai_validate_phone`
- **Purpose:** ตรวจสอบเบอร์โทรซ้ำ
- **Parameters:**
  - `p_phone` (TEXT)
  - `p_exclude_lead_id` (UUID, optional)
- **Returns:**
  - `is_duplicate` (BOOLEAN)
  - `existing_lead` (JSONB, optional)

---

### 🟡 Priority 2: Inventory & Products (Medium Priority)

#### 6. **Products**
- **Edge Function:** `additional-products-products`
- **RPC Function:** `ai_get_products`
- **Purpose:** ดึงรายการสินค้า
- **Parameters:**
  - `p_user_id` (UUID)
  - `p_category` (TEXT, optional) - 'Package' | 'Wholesale'
  - `p_search` (TEXT, optional)
  - `p_filters` (JSONB, optional)
- **Returns:**
  - Array of products
  - Product details

#### 7. **Inventory**
- **Edge Function:** `core-inventory-inventory`
- **RPC Function:** `ai_get_inventory`
- **Purpose:** ดึงข้อมูลคลังสินค้า
- **Parameters:**
  - `p_user_id` (UUID)
  - `p_product_id` (UUID, optional)
  - `p_supplier_id` (UUID, optional)
  - `p_filters` (JSONB, optional)
- **Returns:**
  - Inventory data
  - Stock levels
  - Suppliers
  - Low stock alerts

#### 8. **Purchase Orders**
- **Edge Function:** `additional-purchase-orders-purchase-orders`
- **RPC Function:** `ai_get_purchase_orders`
- **Purpose:** ดึงรายการ Purchase Orders
- **Parameters:**
  - `p_user_id` (UUID)
  - `p_supplier_id` (UUID, optional)
  - `p_status` (TEXT, optional)
  - `p_date_from` (DATE, optional)
  - `p_date_to` (DATE, optional)
- **Returns:**
  - Array of purchase orders
  - PO details

---

### 🟢 Priority 3: Service Tracking (Medium Priority)

#### 9. **Customer Services**
- **Edge Function:** `additional-customer-customer-services`
- **RPC Function:** `ai_get_customer_services`
- **Purpose:** ดึงรายการ Customer Services
- **Parameters:**
  - `p_user_id` (UUID)
  - `p_status` (TEXT, optional)
  - `p_customer_id` (UUID, optional)
  - `p_date_from` (DATE, optional)
  - `p_date_to` (DATE, optional)
- **Returns:**
  - Array of customer services
  - Service details

#### 10. **Service Appointments**
- **Edge Function:** `system-service-service-appointments`
- **RPC Function:** `ai_get_service_appointments`
- **Purpose:** ดึง Service Appointments
- **Parameters:**
  - `p_user_id` (UUID)
  - `p_service_id` (UUID, optional)
  - `p_date_from` (DATE, optional)
  - `p_date_to` (DATE, optional)
- **Returns:**
  - Array of service appointments

#### 11. **Service Visits**
- **Edge Function:** `system-service-service-visits`
- **RPC Function:** `ai_get_service_visits`
- **Purpose:** ดึง Service Visits
- **Parameters:**
  - `p_user_id` (UUID)
  - `p_service_id` (UUID, optional)
  - `p_date_from` (DATE, optional)
  - `p_date_to` (DATE, optional)
- **Returns:**
  - Array of service visits

#### 12. **Service Stats**
- **Edge Function:** `additional-customer-customer-service-stats`
- **RPC Function:** `ai_get_service_stats`
- **Purpose:** ดึงสถิติ Customer Services
- **Parameters:**
  - `p_user_id` (UUID)
  - `p_date_from` (DATE, optional)
  - `p_date_to` (DATE, optional)
- **Returns:**
  - Statistics object
  - Charts data

---

### 🔵 Priority 4: Follow-up & Productivity (Low Priority)

#### 13. **Sale Follow-up**
- **Edge Function:** `system-follow-up-sale-follow-up`
- **RPC Function:** `ai_get_sale_follow_ups`
- **Purpose:** ดึง Sale Follow-up
- **Parameters:**
  - `p_user_id` (UUID)
  - `p_lead_id` (UUID, optional)
  - `p_sales_team_id` (UUID, optional)
  - `p_date_from` (DATE, optional)
  - `p_date_to` (DATE, optional)
- **Returns:**
  - Array of follow-ups

#### 14. **Productivity Logs**
- **Edge Function:** `system-productivity-productivity-log-submission` (POST only)
- **RPC Function:** `ai_get_productivity_logs`
- **Purpose:** ดึง Productivity Logs
- **Parameters:**
  - `p_user_id` (UUID)
  - `p_lead_id` (UUID, optional)
  - `p_date_from` (DATE, optional)
  - `p_date_to` (DATE, optional)
- **Returns:**
  - Array of productivity logs

---

### ⚪ Priority 5: User & Auth (Low Priority)

#### 15. **User Data**
- **Edge Function:** `additional-auth-user-data`
- **RPC Function:** `ai_get_user_data`
- **Purpose:** ดึงข้อมูลผู้ใช้ (User Profile + Sales Member)
- **Parameters:**
  - `p_user_id` (UUID)
- **Returns:**
  - User profile data
  - Sales member data (if exists)

---

## 📊 Mapping: Edge Functions → RPC Functions

### ✅ Already Mapped (5 functions)

| Edge Function | RPC Function | Status |
|--------------|--------------|--------|
| `core-leads-leads-list` | `ai_get_leads` | ✅ Ready |
| `core-leads-leads-for-dashboard` | `ai_get_leads` | ✅ Ready |
| `core-leads-lead-detail` (partial) | `ai_get_lead_status` | ✅ Ready |
| `additional-customer-customer-services` (partial) | `ai_get_customer_info` | ✅ Ready |
| `core-sales-team-sales-team-data` (partial) | `ai_get_team_kpi` | ✅ Ready |
| Dashboard statistics | `ai_get_daily_summary` | ✅ Ready |

### ❌ Missing Mappings (29 functions)

| Priority | Edge Function | Proposed RPC Function | Complexity |
|----------|---------------|----------------------|------------|
| **P1** | `core-leads-lead-detail` | `ai_get_lead_detail` | High |
| **P1** | `core-my-leads-my-leads` | `ai_get_my_leads` | Medium |
| **P1** | `core-sales-team-sales-team` | `ai_get_sales_team` | Medium |
| **P1** | `core-appointments-appointments` | `ai_get_appointments` | Medium |
| **P1** | `core-leads-phone-validation` | `ai_validate_phone` | Low |
| **P2** | `additional-products-products` | `ai_get_products` | Medium |
| **P2** | `core-inventory-inventory` | `ai_get_inventory` | High |
| **P2** | `additional-purchase-orders-purchase-orders` | `ai_get_purchase_orders` | Medium |
| **P3** | `additional-customer-customer-services` | `ai_get_customer_services` | Medium |
| **P3** | `system-service-service-appointments` | `ai_get_service_appointments` | Medium |
| **P3** | `system-service-service-visits` | `ai_get_service_visits` | Medium |
| **P3** | `additional-customer-customer-service-stats` | `ai_get_service_stats` | Medium |
| **P4** | `system-follow-up-sale-follow-up` | `ai_get_sale_follow_ups` | Medium |
| **P4** | Productivity Logs (GET) | `ai_get_productivity_logs` | Medium |
| **P5** | `additional-auth-user-data` | `ai_get_user_data` | Low |

---

## 🎯 Implementation Strategy

### Phase 1: Core CRM Functions (Priority 1) ⚡

**Goal:** ให้ chatbot สามารถตอบคำถามเกี่ยวกับ Leads, Sales Team, Appointments ได้ครบถ้วน

**Functions to Create:**
1. `ai_get_lead_detail` - Lead detail with relations
2. `ai_get_my_leads` - My leads
3. `ai_get_sales_team` - Sales team list
4. `ai_get_appointments` - Appointments
5. `ai_validate_phone` - Phone validation

**Estimated Time:** 2-3 days

---

### Phase 2: Inventory & Products (Priority 2) 📦

**Goal:** ให้ chatbot สามารถตอบคำถามเกี่ยวกับ Inventory, Products, Purchase Orders

**Functions to Create:**
1. `ai_get_products` - Products list
2. `ai_get_inventory` - Inventory data
3. `ai_get_purchase_orders` - Purchase orders

**Estimated Time:** 2-3 days

---

### Phase 3: Service Tracking (Priority 3) 🛠️

**Goal:** ให้ chatbot สามารถตอบคำถามเกี่ยวกับ Service Tracking

**Functions to Create:**
1. `ai_get_customer_services` - Customer services
2. `ai_get_service_appointments` - Service appointments
3. `ai_get_service_visits` - Service visits
4. `ai_get_service_stats` - Service statistics

**Estimated Time:** 2-3 days

---

### Phase 4: Follow-up & Productivity (Priority 4) 📈

**Goal:** ให้ chatbot สามารถตอบคำถามเกี่ยวกับ Follow-up และ Productivity

**Functions to Create:**
1. `ai_get_sale_follow_ups` - Sale follow-ups
2. `ai_get_productivity_logs` - Productivity logs

**Estimated Time:** 1-2 days

---

### Phase 5: User & Auth (Priority 5) 👤

**Goal:** ให้ chatbot สามารถตอบคำถามเกี่ยวกับ User data

**Functions to Create:**
1. `ai_get_user_data` - User profile and sales member data

**Estimated Time:** 0.5 days

---

## 📝 RPC Function Template

### Standard Template

```sql
CREATE OR REPLACE FUNCTION ai_get_{function_name}(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_limit INTEGER DEFAULT NULL,
    p_user_role TEXT DEFAULT 'staff'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_data JSONB;
    v_total_count INTEGER;
BEGIN
    -- Count total
    SELECT COUNT(*) INTO v_total_count
    FROM {table_name}
    WHERE {conditions}
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            {date_column} IS NOT NULL
            AND {date_column}::date BETWEEN
                COALESCE(p_date_from, '1900-01-01'::date) AND
                COALESCE(p_date_to, '2100-12-31'::date)
        )
    );

    -- Get data
    SELECT jsonb_agg(to_jsonb(t.*)) INTO v_data
    FROM (
        SELECT *
        FROM {table_name}
        WHERE {conditions}
        AND (
            (p_date_from IS NULL AND p_date_to IS NULL)
            OR (
                {date_column} IS NOT NULL
                AND {date_column}::date BETWEEN
                    COALESCE(p_date_from, '1900-01-01'::date) AND
                    COALESCE(p_date_to, '2100-12-31'::date)
            )
        )
        ORDER BY {order_column} DESC
        LIMIT CASE
            WHEN p_limit IS NULL THEN 100000
            WHEN p_limit > 0 THEN p_limit
            ELSE 100000
        END
    ) t;

    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            '{entity_name}', COALESCE(v_data, '[]'::jsonb),
            'stats', jsonb_build_object(
                'total', v_total_count,
                'returned', jsonb_array_length(COALESCE(v_data, '[]'::jsonb))
            )
        ),
        'meta', jsonb_build_object(
            'filters_applied', p_filters,
            'date_from', p_date_from,
            'date_to', p_date_to,
            'limit', p_limit,
            'user_role', p_user_role
        )
    );

    RETURN v_result;
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', true,
            'message', SQLERRM
        );
END;
$$;

GRANT EXECUTE ON FUNCTION ai_get_{function_name}(UUID, JSONB, DATE, DATE, INTEGER, TEXT) TO authenticated;
```

---

## 🔧 Integration with AI Assistant

### 1. **Update Tool Schemas** (`llm_router.py`)

เพิ่ม tool schemas สำหรับ RPC functions ใหม่:

```python
TOOL_SCHEMAS = [
    # Existing tools...
    {
        "type": "function",
        "function": {
            "name": "get_lead_detail",
            "description": "Get detailed lead information including timeline and logs",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "Lead ID (UUID)"}
                },
                "required": ["lead_id"]
            }
        }
    },
    # ... more tools
]
```

### 2. **Update DB Tools** (`db_tools.py`)

เพิ่ม wrapper functions:

```python
async def get_lead_detail(lead_id: str, user_id: str, user_role: str = "staff") -> Dict[str, Any]:
    """Get detailed lead information"""
    # Implementation
```

### 3. **Update DB Query Node** (`db_query.py`)

เพิ่ม tool execution logic:

```python
elif tool_name == "get_lead_detail":
    lead_id = params.get("lead_id", "")
    result = await get_lead_detail(lead_id, user_id, user_role)
    # ...
```

---

## 📊 Coverage Analysis

### Current Coverage: **~15%** (5/34 functions)

### Target Coverage: **~85%** (29/34 functions)

**Excluded Functions (ไม่ต้องสร้าง RPC):**
- `system-keep-alive` - Infrastructure
- `system-csp-report` - Infrastructure
- `system-health` - Infrastructure
- Mutation functions (POST/PUT/DELETE) - AI ไม่ควร mutate data

---

## 🎯 Success Criteria

1. ✅ Chatbot สามารถตอบคำถามเกี่ยวกับ Leads ได้ครบถ้วน
2. ✅ Chatbot สามารถตอบคำถามเกี่ยวกับ Sales Team ได้
3. ✅ Chatbot สามารถตอบคำถามเกี่ยวกับ Inventory ได้
4. ✅ Chatbot สามารถตอบคำถามเกี่ยวกับ Service Tracking ได้
5. ✅ ข้อมูลที่ chatbot ตอบตรงกับที่หน้าเว็บแสดง

---

## 📅 Implementation Timeline

### Week 1: Phase 1 (Core CRM)
- Day 1-2: `ai_get_lead_detail`, `ai_get_my_leads`
- Day 3-4: `ai_get_sales_team`, `ai_get_appointments`
- Day 5: `ai_validate_phone`, Testing

### Week 2: Phase 2 (Inventory & Products)
- Day 1-2: `ai_get_products`, `ai_get_inventory`
- Day 3-4: `ai_get_purchase_orders`, Testing

### Week 3: Phase 3 (Service Tracking)
- Day 1-2: `ai_get_customer_services`, `ai_get_service_appointments`
- Day 3-4: `ai_get_service_visits`, `ai_get_service_stats`, Testing

### Week 4: Phase 4 & 5 (Follow-up & User)
- Day 1-2: `ai_get_sale_follow_ups`, `ai_get_productivity_logs`
- Day 3: `ai_get_user_data`, Testing
- Day 4-5: Integration testing, Documentation

---

## 🚀 Next Steps

1. **Review & Approve Plan** - ตรวจสอบและอนุมัติแผน
2. **Start Phase 1** - เริ่มสร้าง Core CRM functions
3. **Test Each Function** - ทดสอบแต่ละ function
4. **Update AI Assistant** - อัพเดท tool schemas และ wrappers
5. **Integration Testing** - ทดสอบ integration ทั้งหมด

---

## 📚 References

- **Edge Functions Guide:** `/ev-power-energy-crm/docs/FRONTEND_FEATURES_AND_API_GUIDE.md`
- **Current RPC Functions:** `/evp-ai-assistant/backend/app/tools/db_tools.py`
- **Database Schema:** `/ev-power-energy-crm/docs/DATABASE_SCHEMA_MAPPING.md`
