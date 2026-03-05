# 📊 RPC Functions Summary

## 📈 สรุปจำนวน Functions

**รวมทั้งหมด: 21 Functions**

- ✅ **Existing Functions (มีอยู่แล้ว):** 15 functions
- ✅ **Phase 1 (Enhanced):** 5 functions (ปรับปรุงจากที่มีอยู่)
- ✅ **Phase 2 (Created):** 6 functions (สร้างใหม่)

---

## 📋 รายละเอียด Functions ทั้งหมด

### 🎯 Phase 1: Enhanced Existing Functions (5 functions)

#### 1. **`ai_get_leads`** ✅ (Enhanced in Phase 1)
**Migration:** `20250118000001_phase1_enhance_rpc_functions.sql`

**หน้าที่:**
- ดึงรายชื่อลีดทั้งหมด (Leads List)
- ใช้สำหรับ Dashboard และ Leads List page

**Features:**
- ✅ Filter by `has_contact_info = true` (เฉพาะลีดที่มีข้อมูลติดต่อ)
- ✅ Return ALL fields จากตาราง leads
- ✅ Date range filtering (`p_date_from`, `p_date_to`)
- ✅ Multiple filters (category, status, region, platform)
- ✅ **Enrichment:**
  - `creator_name` (ชื่อผู้สร้างลีด)
  - `latest_productivity_log` (log ล่าสุดของลีด)
- ✅ Limit logic (ไม่ใช้ limit ถ้ามี date filter)

**Parameters:**
```sql
p_user_id UUID,
p_filters JSONB DEFAULT '{}',
p_date_from DATE DEFAULT NULL,
p_date_to DATE DEFAULT NULL,
p_limit INTEGER DEFAULT NULL,
p_user_role TEXT DEFAULT 'staff'
```

---

#### 2. **`ai_get_lead_detail`** ✅ (Enhanced in Phase 1)
**Migration:** `20250118000001_phase1_enhance_rpc_functions.sql`

**หน้าที่:**
- ดึงข้อมูลรายละเอียดลีด (Lead Detail)
- ใช้สำหรับหน้า Lead Detail page

**Features:**
- ✅ Full lead data (ข้อมูลลีดครบถ้วน)
- ✅ **All productivity logs** (logs ทั้งหมด ไม่ใช่แค่ล่าสุด)
- ✅ **Timeline events** (เหตุการณ์ทั้งหมด)
- ✅ **Relations:**
  - `credit_evaluation` (ข้อมูลการประเมินเครดิต)
  - `lead_products` ( products ที่เกี่ยวข้อง)
  - `quotation_documents` (เอกสารใบเสนอราคา)
- ✅ Appointments (นัดหมาย)
- ✅ Quotations (ใบเสนอราคา)

**Parameters:**
```sql
p_lead_id INTEGER,
p_user_id UUID,
p_include_logs BOOLEAN DEFAULT true
```

---

#### 3. **`ai_get_appointments`** ✅ (Enhanced in Phase 1)
**Migration:** `20250118000001_phase1_enhance_rpc_functions.sql`

**หน้าที่:**
- ดึงรายการนัดหมายทั้งหมด
- ใช้สำหรับหน้า Appointments page

**Features:**
- ✅ Engineer appointments (นัดช่าง)
- ✅ Follow-up appointments (นัดติดตาม)
- ✅ Payment appointments (นัดชำระเงิน จาก quotations)
- ✅ Date range filtering
- ✅ Type filtering (upcoming, past, all)
- ✅ **Sales member filtering** (`p_sales_member_id`)
- ✅ **Lead info mapping** (เชื่อมข้อมูลลีด)
- ✅ **Latest log per lead** (log ล่าสุดของแต่ละลีด)

**Parameters:**
```sql
p_user_id UUID,
p_filters JSONB DEFAULT '{}',
p_date_from DATE DEFAULT NULL,
p_date_to DATE DEFAULT NULL,
p_appointment_type TEXT DEFAULT NULL,
p_sales_member_id INTEGER DEFAULT NULL,
p_user_role TEXT DEFAULT 'staff'
```

**Response Structure:**
```json
{
  "followUp": [],
  "engineer": [],
  "payment": []
}
```

---

#### 4. **`ai_get_customer_info`** ✅ (Enhanced in Phase 1)
**Migration:** `20250118000001_phase1_enhance_rpc_functions.sql`

**หน้าที่:**
- ดึงข้อมูลลูกค้า (Customer Information)
- ใช้สำหรับหน้า Customer Services page

**Features:**
- ✅ **Use `customer_services_extended` view** (ใช้ view แทน table)
- ✅ **Comprehensive filters:**
  - `search` (ค้นหาทั่วไป)
  - `province` (จังหวัด)
  - `sale` (พนักงานขาย)
  - `installerName` (ช่างติดตั้ง)
  - `serviceVisit1-5` (นัดเยี่ยมบริการ)
- ✅ **Support both single and list queries:**
  - Single: ค้นหาด้วย `p_customer_id`
  - List: ค้นหาด้วย `p_customer_name` และ filters

**Parameters:**
```sql
p_user_id UUID,
p_customer_name TEXT DEFAULT NULL,
p_filters JSONB DEFAULT '{}',
p_customer_id INTEGER DEFAULT NULL
```

---

#### 5. **`ai_get_team_kpi`** ✅ (Enhanced in Phase 1)
**Migration:** `20250118000001_phase1_enhance_rpc_functions.sql`

**หน้าที่:**
- ดึงข้อมูล KPI ทีมขาย (Team KPI)
- ใช้สำหรับหน้า Sales Team page

**Features:**
- ✅ **Sales team list** (รายชื่อทีมขายทั้งหมด)
- ✅ **Per-member metrics:**
  - `currentLeads` (ลีดปัจจุบัน)
  - `totalLeads` (ลีดทั้งหมด)
  - `closedLeads` (ลีดที่ปิดการขาย)
  - `conversionRate` (อัตราการแปลง)
  - `leadsWithContact` (ลีดที่มีข้อมูลติดต่อ)
  - `contactRate` (อัตรา contact)
- ✅ **Overall statistics:**
  - Total members, Active members
  - Total leads, Total closed leads
  - Average leads per member
  - Overall conversion rate
- ✅ Date range filtering
- ✅ Category filtering

**Parameters:**
```sql
p_user_id UUID,
p_team_id INTEGER DEFAULT NULL,
p_category TEXT DEFAULT NULL,
p_date_from DATE DEFAULT NULL,
p_date_to DATE DEFAULT NULL,
p_user_role TEXT DEFAULT 'staff'
```

---

### 🆕 Phase 2: Created Missing Functions (6 functions)

#### 6. **`ai_get_my_leads`** ✅ (Created in Phase 2)
**Migration:** `20250118000002_phase2_create_missing_functions_part1.sql`

**หน้าที่:**
- ดึงลีดที่ assign ให้ผู้ใช้ปัจจุบัน (My Leads)
- ใช้สำหรับหน้า My Leads page

**Features:**
- ✅ Query both `sale_owner_id` AND `post_sales_owner_id`
- ✅ Filter by `has_contact_info = true`
- ✅ Filter by category (Package/Wholesale)
- ✅ Enrich with `creator_name`
- ✅ Enrich with `latest_productivity_log`
- ✅ **Statistics:**
  - `totalLeads` (ลีดทั้งหมด)
  - `leadsWithContact` (ลีดที่มีข้อมูลติดต่อ)
  - `byStatus` (แยกตามสถานะ)
  - `byPlatform` (แยกตาม platform)

**Parameters:**
```sql
p_user_id UUID,
p_category TEXT DEFAULT 'Package',
p_filters JSONB DEFAULT '{}',
p_date_from DATE DEFAULT NULL,
p_date_to DATE DEFAULT NULL,
p_user_role TEXT DEFAULT 'staff'
```

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "leads": [],
    "user": {},
    "salesMember": {}
  },
  "stats": {
    "totalLeads": 0,
    "leadsWithContact": 0,
    "byStatus": {},
    "byPlatform": {}
  }
}
```

---

#### 7. **`ai_get_sales_team`** ✅ (Created in Phase 2)
**Migration:** `20250118000002_phase2_create_missing_functions_part1.sql`

**หน้าที่:**
- ดึงรายการทีมขายพร้อม metrics (Sales Team)
- ใช้สำหรับหน้า Sales Team page

**Features:**
- ✅ Full sales team list from `sales_team_with_user_info`
- ✅ **Per-member metrics:**
  - `currentLeads` (ลีดปัจจุบัน - status = 'กำลังติดตาม', 'ปิดการขาย')
  - `totalLeads` (ลีดทั้งหมดสำหรับคำนวณ conversion rate)
  - `closedLeads` (ลีดที่ปิดการขาย - จาก productivity logs)
  - `conversionRate` (อัตราการแปลง: closedLeads / totalLeads * 100)
  - `leadsWithContact` (ลีดที่มีข้อมูลติดต่อ)
  - `contactRate` (อัตรา contact: leadsWithContact / totalLeads * 100)
- ✅ **Overall statistics:**
  - Total members, Active members
  - Total leads, Total closed leads
  - Average leads per member
  - Overall conversion rate
- ✅ Filter by category
- ✅ Date range filtering

**Parameters:**
```sql
p_user_id UUID,
p_category TEXT DEFAULT NULL,
p_filters JSONB DEFAULT '{}',
p_date_from DATE DEFAULT NULL,
p_date_to DATE DEFAULT NULL,
p_user_role TEXT DEFAULT 'staff'
```

---

#### 8. **`ai_get_sales_team_list`** ✅ (Created in Phase 2)
**Migration:** `20250118000002_phase2_create_missing_functions_part1.sql`

**หน้าที่:**
- ดึงรายชื่อทีมขายแบบง่ายสำหรับ dropdown (Sales Team List)
- ใช้สำหรับ dropdown/select components

**Features:**
- ✅ Simple list from `sales_team_with_user_info`
- ✅ Filter by status (default: 'active')
- ✅ Return: id, user_id, current_leads, status, name, email, phone, department, position

**Parameters:**
```sql
p_user_id UUID,
p_category TEXT DEFAULT NULL,
p_status TEXT DEFAULT 'active',
p_user_role TEXT DEFAULT 'staff'
```

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "salesTeam": [
      {
        "id": 1,
        "user_id": "uuid",
        "current_leads": 5,
        "status": "active",
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "0812345678",
        "department": "Sales",
        "position": "Sales Manager"
      }
    ]
  }
}
```

---

#### 9. **`ai_get_sales_team_data`** ✅ (Created in Phase 2)
**Migration:** `20250118000003_phase2_create_missing_functions_part2.sql`

**หน้าที่:**
- ดึงข้อมูลทีมขายพร้อม metrics และ data (Sales Team Data)
- ใช้สำหรับหน้า Sales Team Data page

**Features:**
- ✅ Sales team list from `sales_team_with_user_info`
- ✅ **Leads data** (sale_owner_id OR post_sales_owner_id)
- ✅ Filter by `has_contact_info = true`
- ✅ **Filter by platforms:**
  - EV platforms: Facebook, Line, Website, TikTok, IG, YouTube, Shopee, Lazada, แนะนำ, Outbound, โทร, ลูกค้าเก่า service ครบ
  - Partner platforms: Huawei, ATMOCE, Solar Edge, Sigenergy
- ✅ Date range filtering
- ✅ **Productivity logs** where status = 'ปิดการขายแล้ว'
- ✅ **Quotations** from closed logs
- ✅ **Per-member metrics:**
  - `deals_closed` (จำนวนดีลที่ปิด - นับจาก quotations)
  - `pipeline_value` (มูลค่าพอร์ต - sum total_amount จาก quotations)
  - `conversion_rate` (deals_closed / total_leads * 100)
  - `total_leads` (ลีดทั้งหมด)
- ✅ Return leads and quotations data

**Parameters:**
```sql
p_user_id UUID,
p_date_from DATE DEFAULT NULL,
p_date_to DATE DEFAULT NULL,
p_user_role TEXT DEFAULT 'staff'
```

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "salesTeam": [
      {
        "id": 1,
        "name": "John Doe",
        "deals_closed": 10,
        "pipeline_value": 5000000,
        "conversion_rate": 25.5,
        "total_leads": 40
      }
    ],
    "leads": [],
    "quotations": []
  }
}
```

---

#### 10. **`ai_validate_phone`** ✅ (Created in Phase 2)
**Migration:** `20250118000003_phase2_create_missing_functions_part2.sql`

**หน้าที่:**
- ตรวจสอบเบอร์โทรซ้ำ (Phone Validation)
- ใช้สำหรับฟอร์มเพิ่ม/แก้ไขลีด

**Features:**
- ✅ **Normalize phone number** (ลบ non-digits ทั้งหมด)
- ✅ Fetch all leads with phone numbers (not null, not empty, not whitespace-only)
- ✅ Normalize existing phone numbers
- ✅ Compare normalized input with normalized existing phones
- ✅ Exclude current lead if `p_exclude_lead_id` is provided (สำหรับการแก้ไข)
- ✅ Return existing lead information if duplicate found

**Parameters:**
```sql
p_phone TEXT,
p_exclude_lead_id INTEGER DEFAULT NULL,
p_user_id UUID DEFAULT NULL
```

**Response Structure:**
```json
{
  "isDuplicate": false,
  "phone": "0812345678"
}

// If duplicate:
{
  "isDuplicate": true,
  "phone": "0812345678",
  "existingLead": {
    "id": 123,
    "tel": "081-234-5678",
    "full_name": "John Doe",
    "display_name": "John"
  }
}
```

---

#### 11. **`ai_get_lead_management`** ✅ (Created in Phase 2)
**Migration:** `20250118000003_phase2_create_missing_functions_part2.sql`

**หน้าที่:**
- ดึงข้อมูล Lead Management page (Lead Management)
- ใช้สำหรับหน้า Lead Management page

**Features:**
- ✅ **Parallel queries:**
  - User data (if `p_include_user_data = true`)
  - Sales team data (if `p_include_sales_team = true`)
  - Leads data (if `p_include_leads = true`)
- ✅ **Leads query:**
  - Filter by category
  - Filter by `has_contact_info = true`
  - Date range filtering (no limit if date filter exists)
  - Enrich with `creator_name`
- ✅ **Statistics:**
  - `totalLeads` (ลีดทั้งหมด)
  - `assignedLeads` (ลีดที่ assign แล้ว)
  - `unassignedLeads` (ลีดที่ยังไม่ได้ assign)
  - `assignmentRate` (อัตราการ assign)
  - `leadsWithContact` (ลีดที่มีข้อมูลติดต่อ)
  - `contactRate` (อัตรา contact)
- ✅ Return: leads, salesTeam, user, salesMember, stats

**Parameters:**
```sql
p_user_id UUID,
p_category TEXT DEFAULT 'Package',
p_include_user_data BOOLEAN DEFAULT true,
p_include_sales_team BOOLEAN DEFAULT true,
p_include_leads BOOLEAN DEFAULT true,
p_date_from DATE DEFAULT NULL,
p_date_to DATE DEFAULT NULL,
p_limit INTEGER DEFAULT NULL,
p_user_role TEXT DEFAULT 'staff'
```

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "leads": [],
    "salesTeam": [],
    "user": {},
    "salesMember": {},
    "stats": {
      "totalLeads": 100,
      "assignedLeads": 80,
      "unassignedLeads": 20,
      "assignmentRate": 80.0,
      "leadsWithContact": 95,
      "contactRate": 95.0
    }
  }
}
```

---

### 📦 Existing Functions (15 functions)

#### 12. **`ai_get_lead_status`** ✅
**Migration:** `20250116000003_ai_rpc_functions.sql`

**หน้าที่:**
- ค้นหาลีดด้วยชื่อ (Lead Status Search)
- ใช้สำหรับค้นหาลีดแบบง่ายๆ

**Features:**
- ✅ Search by name (full_name or display_name)
- ✅ Basic lead info

---

#### 13. **`ai_get_daily_summary`** ✅
**Migration:** `20250117000002_fix_ai_get_daily_summary_role.sql`

**หน้าที่:**
- ดึงสรุปข้อมูลรายวัน (Daily Summary)
- ใช้สำหรับ Dashboard statistics

**Features:**
- ✅ Daily statistics
- ✅ New leads count
- ✅ Total leads count

---

#### 14. **`ai_get_service_appointments`** ✅
**Migration:** `20250116000006_ai_rpc_functions_complete.sql`

**หน้าที่:**
- ดึงรายการนัดหมายบริการ (Service Appointments)
- ใช้สำหรับหน้า Service Appointments page

---

#### 15. **`ai_get_sales_performance`** ✅
**Migration:** `20250116000005_ai_rpc_functions_enhanced.sql`

**หน้าที่:**
- ดึงข้อมูลประสิทธิภาพการขาย (Sales Performance)
- ใช้สำหรับหน้า Sales Performance page

**Features:**
- ✅ Sales performance metrics
- ✅ Date range filtering

---

#### 16. **`ai_get_sales_docs`** ✅
**Migration:** `20250116000006_ai_rpc_functions_complete.sql`

**หน้าที่:**
- ดึงเอกสารการขาย (Sales Documents)

---

#### 17. **`ai_get_quotations`** ✅
**Migration:** `20250116000006_ai_rpc_functions_complete.sql`

**หน้าที่:**
- ดึงใบเสนอราคา (Quotations)

---

#### 18. **`ai_get_permit_requests`** ✅
**Migration:** `20250116000006_ai_rpc_functions_complete.sql`

**หน้าที่:**
- ดึงคำขออนุญาต (Permit Requests)

---

#### 19. **`ai_get_stock_movements`** ✅
**Migration:** `20250116000006_ai_rpc_functions_complete.sql`

**หน้าที่:**
- ดึงการเคลื่อนไหวสต็อก (Stock Movements)

---

#### 20. **`ai_get_user_info`** ✅
**Migration:** `20250116000006_ai_rpc_functions_complete.sql`

**หน้าที่:**
- ดึงข้อมูลผู้ใช้ (User Information)

---

#### 21. **`ai_get_inventory_status`** ✅
**Migration:** `20250116000005_ai_rpc_functions_enhanced.sql`

**หน้าที่:**
- ดึงสถานะสินค้าคงคลัง (Inventory Status)

---

## 📊 สรุปตามหมวดหมู่

### 🎯 Leads Management (7 functions)
1. `ai_get_leads` - ดึงรายชื่อลีดทั้งหมด
2. `ai_get_lead_status` - ค้นหาลีดด้วยชื่อ
3. `ai_get_lead_detail` - ดึงรายละเอียดลีด
4. `ai_get_my_leads` - ดึงลีดของฉัน
5. `ai_get_lead_management` - ดึงข้อมูล Lead Management page
6. `ai_validate_phone` - ตรวจสอบเบอร์โทรซ้ำ
7. `ai_get_daily_summary` - สรุปข้อมูลรายวัน

### 👥 Sales Team (4 functions)
8. `ai_get_sales_team` - ดึงรายการทีมขายพร้อม metrics
9. `ai_get_sales_team_list` - ดึงรายชื่อทีมขายสำหรับ dropdown
10. `ai_get_sales_team_data` - ดึงข้อมูลทีมขายพร้อม data
11. `ai_get_team_kpi` - ดึง KPI ทีมขาย

### 📅 Appointments (2 functions)
12. `ai_get_appointments` - ดึงรายการนัดหมาย
13. `ai_get_service_appointments` - ดึงนัดหมายบริการ

### 👤 Customer (1 function)
14. `ai_get_customer_info` - ดึงข้อมูลลูกค้า

### 📊 Performance & Reports (3 functions)
15. `ai_get_sales_performance` - ดึงประสิทธิภาพการขาย
16. `ai_get_quotations` - ดึงใบเสนอราคา
17. `ai_get_daily_summary` - สรุปข้อมูลรายวัน

### 📄 Documents & Other (4 functions)
18. `ai_get_sales_docs` - ดึงเอกสารการขาย
19. `ai_get_permit_requests` - ดึงคำขออนุญาต
20. `ai_get_stock_movements` - ดึงการเคลื่อนไหวสต็อก
21. `ai_get_user_info` - ดึงข้อมูลผู้ใช้
22. `ai_get_inventory_status` - ดึงสถานะสินค้าคงคลัง

---

## ✅ Phase 1 & Phase 2 Summary

### Phase 1: Enhanced Existing Functions (5 functions)
- ✅ `ai_get_leads` - เพิ่ม creator_name และ latest_productivity_log
- ✅ `ai_get_lead_detail` - เพิ่ม all logs, timeline, relations
- ✅ `ai_get_appointments` - เพิ่ม sales member filter และ lead info mapping
- ✅ `ai_get_customer_info` - ใช้ extended view และเพิ่ม filters
- ✅ `ai_get_team_kpi` - เพิ่ม per-member metrics และ conversion rate

### Phase 2: Created Missing Functions (6 functions)
- ✅ `ai_get_my_leads` - สร้างใหม่
- ✅ `ai_get_sales_team` - สร้างใหม่
- ✅ `ai_get_sales_team_list` - สร้างใหม่
- ✅ `ai_get_sales_team_data` - สร้างใหม่
- ✅ `ai_validate_phone` - สร้างใหม่
- ✅ `ai_get_lead_management` - สร้างใหม่

---

## 📝 Common Patterns

### ✅ Features ที่ใช้ในหลาย Functions
1. **Date Range Filtering** - `p_date_from`, `p_date_to`
2. **Has Contact Info Filter** - `has_contact_info = true`
3. **Creator Name Enrichment** - Join with users table
4. **Latest Productivity Log** - Join with lead_productivity_logs
5. **Statistics Calculation** - Metrics และ rates
6. **Error Handling** - EXCEPTION block
7. **Security** - SECURITY DEFINER และ RLS

---

## 🎯 Usage Examples

### Query Leads
```sql
SELECT ai_get_leads(
  'user-uuid',
  '{"category": "Package"}'::jsonb,
  '2024-01-01'::date,
  '2024-01-31'::date,
  100,
  'staff'
);
```

### Get My Leads
```sql
SELECT ai_get_my_leads(
  'user-uuid',
  'Package',
  '{}'::jsonb,
  NULL,
  NULL,
  'staff'
);
```

### Validate Phone
```sql
SELECT ai_validate_phone(
  '081-234-5678',
  NULL,  -- exclude_lead_id
  'user-uuid'
);
```

---

## 📚 References

- **Migration Files:** `/evp-ai-assistant/supabase/migrations/`
- **Review Document:** `/evp-ai-assistant/docs/RPC_FUNCTIONS_REVIEW_AND_ENHANCEMENT.md`
- **Edge Functions:** `/ev-power-energy-crm/supabase/functions/`
