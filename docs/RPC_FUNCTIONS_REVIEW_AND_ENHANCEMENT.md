# 🔍 RPC Functions Review & Enhancement Plan

## 📋 Executive Summary

ตรวจสอบ RPC Functions ที่มีอยู่แล้วทั้งหมด และเปรียบเทียบกับ Edge Functions logic เพื่อให้ครอบคลุมทุกส่วนและถูกต้องครบถ้วน

---

## 📊 RPC Functions ที่มีอยู่แล้ว (Current State)

### ✅ มีอยู่แล้ว (10 functions)

#### 1. **`ai_get_leads`** ✅ (Enhanced)
- **Migration:** `20250117000007_filter_has_contact_info_and_all_fields.sql`
- **Covers:** 
  - `core-leads-leads-for-dashboard`
  - `core-leads-leads-list`
- **Features:**
  - ✅ Filter by `has_contact_info = true`
  - ✅ Return ALL fields (`to_jsonb(l.*)`)
  - ✅ Date range filtering
  - ✅ Multiple filters (category, status, region, platform)
  - ✅ Subquery pattern (avoids GROUP BY issues)

#### 2. **`ai_get_lead_status`** ✅ (Basic)
- **Migration:** `20250116000003_ai_rpc_functions.sql`
- **Covers:** 
  - `core-leads-lead-detail` (partial - only basic info)
- **Features:**
  - ✅ Search by name (full_name or display_name)
  - ✅ Basic lead info
  - ⚠️ **Missing:** Timeline, Productivity logs, Related data

#### 3. **`ai_get_lead_detail`** ✅ (Enhanced)
- **Migration:** `20250116000005_ai_rpc_functions_enhanced.sql`
- **Covers:**
  - `core-leads-lead-detail` (action=detail)
- **Features:**
  - ✅ Full lead data
  - ✅ Latest productivity log
  - ✅ Appointments
  - ✅ Quotations
  - ⚠️ **Missing:** All productivity logs, Timeline events

#### 4. **`ai_get_daily_summary`** ✅
- **Migration:** `20250117000002_fix_ai_get_daily_summary_role.sql`
- **Covers:**
  - Dashboard statistics
- **Features:**
  - ✅ Daily statistics
  - ✅ New leads count
  - ✅ Total leads count

#### 5. **`ai_get_customer_info`** ✅ (Basic)
- **Migration:** `20250116000003_ai_rpc_functions.sql`
- **Covers:**
  - `additional-customer-customer-services` (partial - only single customer)
- **Features:**
  - ✅ Search by customer name
  - ✅ Basic customer info
  - ⚠️ **Missing:** Filters (search, province, sale, installerName, serviceVisits), Extended view (`customer_services_extended`)

#### 6. **`ai_get_team_kpi`** ✅ (Basic)
- **Migration:** `20250116000003_ai_rpc_functions.sql`
- **Covers:**
  - `core-sales-team-sales-team-data` (partial - only basic stats)
- **Features:**
  - ✅ Basic team stats
  - ⚠️ **Missing:** Sales team list, Performance metrics (deals_closed, pipeline_value, conversion_rate), Date range filtering

#### 7. **`ai_get_appointments`** ✅ (Enhanced)
- **Migration:** `20250116000005_ai_rpc_functions_enhanced.sql`
- **Covers:**
  - `core-appointments-appointments`
- **Features:**
  - ✅ Engineer appointments
  - ✅ Follow-up appointments
  - ✅ Payment appointments (from quotations)
  - ✅ Date range filtering
  - ✅ Type filtering (upcoming, past, all)

#### 8. **`ai_get_service_appointments`** ✅
- **Migration:** `20250116000006_ai_rpc_functions_complete.sql`
- **Covers:**
  - `system-service-service-appointments`
- **Features:**
  - ✅ Service appointments query

#### 9. **`ai_get_sales_performance`** ✅ (Enhanced)
- **Migration:** `20250116000005_ai_rpc_functions_enhanced.sql`
- **Covers:**
  - `core-sales-team-sales-team-data` (partial)
- **Features:**
  - ✅ Sales performance metrics
  - ✅ Date range filtering
  - ⚠️ **Missing:** Full sales team list, All metrics from edge function

#### 10. **Other Functions** ✅
- `ai_get_sales_docs`, `ai_get_quotations`, `ai_get_permit_requests`, `ai_get_stock_movements`, `ai_get_user_info` (from complete migration)

---

## ❌ RPC Functions ที่ยังไม่มี (Missing)

### 🔴 Priority 1: Core CRM Functions (Missing)

#### 1. **`ai_get_my_leads`** ❌
- **Edge Function:** `core-my-leads-my-leads`
- **Purpose:** ดึงลีดที่ assign ให้ผู้ใช้ปัจจุบัน
- **Missing Features:**
  - ✅ Query both `sale_owner_id` AND `post_sales_owner_id`
  - ✅ Filter by `has_contact_info = true`
  - ✅ Enrich with `creator_name`
  - ✅ Enrich with `latest_productivity_log`
  - ✅ Calculate statistics (byStatus, byPlatform, leadsWithContact)

#### 2. **`ai_get_sales_team`** ❌
- **Edge Function:** `core-sales-team-sales-team`
- **Purpose:** ดึงรายการทีมขาย
- **Missing Features:**
  - ✅ Full sales team list from `sales_team_with_user_info`
  - ✅ Performance metrics (currentLeads, totalLeads, closedLeads, conversionRate, leadsWithContact, contactRate)
  - ✅ Filter by status, category

#### 3. **`ai_get_sales_team_list`** ❌
- **Edge Function:** `core-leads-sales-team-list`
- **Purpose:** ดึงรายชื่อทีมขายสำหรับ dropdown
- **Missing Features:**
  - ✅ Simple list from `sales_team_with_user_info`
  - ✅ Filter by status='active'

#### 4. **`ai_validate_phone`** ❌
- **Edge Function:** `core-leads-phone-validation`
- **Purpose:** ตรวจสอบเบอร์โทรซ้ำ
- **Missing Features:**
  - ✅ Normalize phone numbers (remove non-digits)
  - ✅ Check duplicates in all leads
  - ✅ Support excludeId for updates

#### 5. **`ai_get_lead_management`** ❌
- **Edge Function:** `core-leads-lead-management`
- **Purpose:** ดึงข้อมูล Lead Management page (leads + salesTeam + user)
- **Missing Features:**
  - ✅ Parallel queries (user, salesTeam, leads)
  - ✅ Enrich leads with creator_name
  - ✅ Calculate statistics (assignedLeads, unassignedLeads, assignmentRate, leadsWithContact, contactRate)

---

## 🔍 Detailed Comparison: Edge Functions vs RPC Functions

### 1. **Leads Management**

#### Edge Function: `core-leads-leads-for-dashboard`
**Logic:**
- ✅ Filter by `has_contact_info = true`
- ✅ Select specific fields (id, full_name, tel, line_id, status, platform, region, created_at_thai, updated_at_thai, sale_owner_id, post_sales_owner_id, category, operation_status, avg_electricity_bill, notes, display_name, created_by, is_from_ppa_project)
- ✅ Date range filtering (gte, lte on created_at_thai)
- ✅ Limit logic: No limit if date filter exists, else limit 5000
- ✅ Enrich with `creator_name` (join with users table)
- ✅ Order by `created_at_thai DESC`

#### RPC Function: `ai_get_leads`
**Current:**
- ✅ Filter by `has_contact_info = true`
- ✅ Return ALL fields (`to_jsonb(l.*)`)
- ✅ Date range filtering
- ✅ Multiple filters
- ⚠️ **Missing:** `creator_name` enrichment
- ⚠️ **Missing:** Limit logic (no limit if date filter exists)

**Action Required:**
- ✅ Add `creator_name` enrichment (join with users)
- ✅ Add limit logic (no limit if date filter exists)

---

#### Edge Function: `core-leads-leads-list`
**Logic:**
- ✅ Filter by `has_contact_info = true`
- ✅ Select specific fields
- ✅ Category filtering
- ✅ Date range filtering (priority over limit)
- ✅ Limit logic: No limit if date filter exists, else limit 100
- ✅ Enrich with `creator_name`
- ✅ Enrich with `latest_productivity_log` (join with lead_productivity_logs)

#### RPC Function: `ai_get_leads`
**Current:**
- ✅ Filter by `has_contact_info = true`
- ✅ Return ALL fields
- ✅ Category filtering
- ✅ Date range filtering
- ⚠️ **Missing:** `creator_name` enrichment
- ⚠️ **Missing:** `latest_productivity_log` enrichment
- ⚠️ **Missing:** Limit logic (no limit if date filter exists)

**Action Required:**
- ✅ Add `creator_name` enrichment
- ✅ Add `latest_productivity_log` enrichment

---

#### Edge Function: `core-leads-lead-detail`
**Logic:**
- ✅ Action `detail`: Get full lead data (select `*`)
- ✅ Action `latest-log`: Get latest productivity log with relations:
  - `appointments(*)`
  - `credit_evaluation(*)`
  - `lead_products(*, products(*))`
  - `quotations` (from productivity_log_id)
  - `quotation_documents` (from productivity_log_id)

#### RPC Function: `ai_get_lead_detail`
**Current:**
- ✅ Get full lead data
- ✅ Latest productivity log
- ✅ Appointments
- ✅ Quotations
- ⚠️ **Missing:** All productivity logs (not just latest)
- ⚠️ **Missing:** Timeline events
- ⚠️ **Missing:** Relations (credit_evaluation, lead_products)

**Action Required:**
- ✅ Add all productivity logs query
- ✅ Add timeline events
- ✅ Add credit_evaluation relation
- ✅ Add lead_products relation
- ✅ Add quotation_documents relation

---

### 2. **My Leads**

#### Edge Function: `core-my-leads-my-leads`
**Logic:**
- ✅ Get user data from `users` table (by auth_user_id)
- ✅ Get sales member data from `sales_team_with_user_info` (by user_id)
- ✅ Query leads where `sale_owner_id = salesMember.id` AND `has_contact_info = true`
- ✅ Query leads where `post_sales_owner_id = salesMember.id` AND `has_contact_info = true`
- ✅ Combine and distinct leads
- ✅ Enrich with `creator_name` (join with users)
- ✅ Enrich with `latest_productivity_log` (join with lead_productivity_logs)
- ✅ Calculate statistics:
  - `totalLeads`
  - `leadsWithContact`
  - `byStatus` (กำลังติดตาม, ปิดการขาย, ปิดการขายแล้ว, ปิดการขายไม่สำเร็จ)
  - `byPlatform` (Facebook, Line, Website, Phone)
- ✅ Filter by `category` (Package | Wholesale)

#### RPC Function: `ai_get_my_leads` ❌ **DOES NOT EXIST**

**Action Required:**
- ✅ Create `ai_get_my_leads` function
- ✅ Implement all logic from edge function

---

### 3. **Sales Team**

#### Edge Function: `core-sales-team-sales-team`
**Logic:**
- ✅ Get sales team from `sales_team_with_user_info`
- ✅ Get all leads (sale_owner_id OR post_sales_owner_id)
- ✅ Filter by `has_contact_info = true`
- ✅ Filter by status IN ('กำลังติดตาม', 'ปิดการขาย')
- ✅ Get productivity logs where status = 'ปิดการขายแล้ว'
- ✅ Calculate metrics per member:
  - `currentLeads` (from filtered leads)
  - `totalLeads` (all leads for conversion rate)
  - `closedLeads` (from productivity logs by sale_id)
  - `conversionRate` (closedLeads / totalLeads * 100)
  - `leadsWithContact` (count leads with tel)
  - `contactRate` (leadsWithContact / totalLeads * 100)
- ✅ Calculate overall statistics

#### RPC Function: `ai_get_team_kpi`
**Current:**
- ✅ Basic team stats (total_leads, active_leads)
- ⚠️ **Missing:** Sales team list
- ⚠️ **Missing:** Per-member metrics
- ⚠️ **Missing:** Conversion rate calculation
- ⚠️ **Missing:** Contact rate calculation

**Action Required:**
- ✅ Create `ai_get_sales_team` function (full version)
- ✅ Update `ai_get_team_kpi` to include per-member metrics

---

#### Edge Function: `core-sales-team-sales-team-data`
**Logic:**
- ✅ Get sales team from `sales_team_with_user_info`
- ✅ Get leads (sale_owner_id OR post_sales_owner_id)
- ✅ Filter by `has_contact_info = true`
- ✅ Filter by platforms (EV + Partner platforms)
- ✅ Filter by date range (if provided)
- ✅ Get productivity logs where status = 'ปิดการขายแล้ว'
- ✅ Get quotations from closed logs
- ✅ Calculate metrics per member:
  - `deals_closed` (count quotations)
  - `pipeline_value` (sum total_amount from quotations)
  - `conversion_rate` (deals_closed / total_leads * 100)
  - `total_leads` (all leads for conversion)
- ✅ Return leads and quotations data

#### RPC Function: `ai_get_sales_performance`
**Current:**
- ✅ Sales performance for single sales member
- ✅ Metrics (total_leads, deals_closed, pipeline_value, conversion_rate)
- ⚠️ **Missing:** Full team data (not just single member)
- ⚠️ **Missing:** Leads and quotations data in response

**Action Required:**
- ✅ Create `ai_get_sales_team_data` function (full version with all members)

---

#### Edge Function: `core-leads-sales-team-list`
**Logic:**
- ✅ Simple query from `sales_team_with_user_info`
- ✅ Filter by `status = 'active'`
- ✅ Select: id, user_id, current_leads, status, name, email, phone, department, position

#### RPC Function: `ai_get_sales_team_list` ❌ **DOES NOT EXIST**

**Action Required:**
- ✅ Create `ai_get_sales_team_list` function

---

### 4. **Appointments**

#### Edge Function: `core-appointments-appointments`
**Logic:**
- ✅ Get sales member by `salesMemberId` (from `sales_team_with_user_info`)
- ✅ Get all productivity logs for this sales member (filter by `sale_id`)
- ✅ Get latest log per lead (group by lead_id, take most recent)
- ✅ Get appointments from logIds:
  - Engineer appointments (appointment_type = 'engineer')
  - Follow-up appointments (appointment_type = 'follow-up')
  - Payment appointments (from quotations.estimate_payment_date)
- ✅ Map appointments with lead info from productivity logs
- ✅ Return categorized: `{ followUp: [], engineer: [], payment: [] }`

#### RPC Function: `ai_get_appointments`
**Current:**
- ✅ Engineer appointments
- ✅ Follow-up appointments
- ✅ Payment appointments
- ⚠️ **Missing:** Filter by sales member (salesMemberId)
- ⚠️ **Missing:** Lead info mapping
- ⚠️ **Missing:** Latest log per lead logic

**Action Required:**
- ✅ Add sales member filtering
- ✅ Add lead info mapping
- ✅ Add latest log per lead logic

---

### 5. **Phone Validation**

#### Edge Function: `core-leads-phone-validation`
**Logic:**
- ✅ Normalize phone numbers (remove all non-digits)
- ✅ Fetch all leads with phone numbers
- ✅ Filter out null, empty, and whitespace-only values
- ✅ Compare normalized input with normalized existing phones
- ✅ Support `excludeId` for updates
- ✅ Return `isDuplicate: boolean` and `phone: string`

#### RPC Function: `ai_validate_phone` ❌ **DOES NOT EXIST**

**Action Required:**
- ✅ Create `ai_validate_phone` function
- ✅ Implement normalization logic
- ✅ Implement duplicate check logic

---

### 6. **Lead Management**

#### Edge Function: `core-leads-lead-management`
**Logic:**
- ✅ Parallel queries:
  - Get user data (if includeUserData = true)
  - Get sales team data (if includeSalesTeam = true)
  - Get leads data (if includeLeads = true)
- ✅ Leads query:
  - Filter by `category`
  - Filter by `has_contact_info = true`
  - Date range filtering (no limit if date filter exists)
  - Enrich with `creator_name`
- ✅ Calculate statistics:
  - `totalLeads`
  - `assignedLeads`
  - `unassignedLeads`
  - `assignmentRate`
  - `leadsWithContact`
  - `contactRate`
- ✅ Return: `{ leads, salesTeam, user, salesMember, stats }`

#### RPC Function: `ai_get_lead_management` ❌ **DOES NOT EXIST**

**Action Required:**
- ✅ Create `ai_get_lead_management` function
- ✅ Implement parallel queries logic
- ✅ Implement statistics calculation

---

### 7. **Customer Services**

#### Edge Function: `additional-customer-customer-services`
**Logic:**
- ✅ Use `customer_services_extended` view (not table)
- ✅ Support single item query (by id)
- ✅ Support list query with filters:
  - `search` (ilike on customer_group, tel, installer_name)
  - `province` (eq)
  - `sale` (eq)
  - `installerName` (eq)
  - `serviceVisit1` through `serviceVisit5` (boolean eq)
- ✅ Order by id ASC

#### RPC Function: `ai_get_customer_info`
**Current:**
- ✅ Search by customer name
- ✅ Basic customer info
- ⚠️ **Missing:** Use `customer_services_extended` view
- ⚠️ **Missing:** All filters (search, province, sale, installerName, serviceVisits)
- ⚠️ **Missing:** Support for list query (not just single item)

**Action Required:**
- ✅ Update to use `customer_services_extended` view
- ✅ Add all filters
- ✅ Support both single and list queries

---

## 📝 Enhancement Plan

### Phase 1: Enhance Existing RPC Functions ✅

#### 1.1. **Enhance `ai_get_leads`**
**Changes:**
1. ✅ Add `creator_name` enrichment (join with users table)
2. ✅ Add `latest_productivity_log` enrichment (join with lead_productivity_logs)
3. ✅ Add limit logic (no limit if date filter exists, else use limit)

**Edge Function Reference:**
- `core-leads-leads-for-dashboard` (creator_name)
- `core-leads-leads-list` (latest_productivity_log)

---

#### 1.2. **Enhance `ai_get_lead_detail`**
**Changes:**
1. ✅ Add all productivity logs query (not just latest)
2. ✅ Add timeline events query
3. ✅ Add credit_evaluation relation
4. ✅ Add lead_products relation
5. ✅ Add quotation_documents relation

**Edge Function Reference:**
- `core-leads-lead-detail` (action=latest-log)

---

#### 1.3. **Enhance `ai_get_appointments`**
**Changes:**
1. ✅ Add sales member filtering (salesMemberId parameter)
2. ✅ Add lead info mapping from productivity logs
3. ✅ Add latest log per lead logic (group by lead_id)

**Edge Function Reference:**
- `core-appointments-appointments`

---

#### 1.4. **Enhance `ai_get_customer_info`**
**Changes:**
1. ✅ Use `customer_services_extended` view instead of table
2. ✅ Add all filters (search, province, sale, installerName, serviceVisits)
3. ✅ Support both single (by id) and list queries

**Edge Function Reference:**
- `additional-customer-customer-services`

---

#### 1.5. **Enhance `ai_get_team_kpi`**
**Changes:**
1. ✅ Return sales team list with per-member metrics
2. ✅ Add conversion rate calculation
3. ✅ Add contact rate calculation

**Edge Function Reference:**
- `core-sales-team-sales-team`

---

### Phase 2: Create Missing RPC Functions ✅

#### 2.1. **Create `ai_get_my_leads`**
**Edge Function Reference:** `core-my-leads-my-leads`

**Function Signature:**
```sql
CREATE OR REPLACE FUNCTION ai_get_my_leads(
    p_user_id UUID,
    p_category TEXT DEFAULT 'Package',
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_user_role TEXT DEFAULT 'staff'
)
RETURNS JSONB
```

**Logic:**
1. Get user data from `users` (by auth_user_id)
2. Get sales member from `sales_team_with_user_info` (by user_id)
3. Query leads where `sale_owner_id = salesMember.id` AND `has_contact_info = true` AND `category = p_category`
4. Query leads where `post_sales_owner_id = salesMember.id` AND `has_contact_info = true` AND `category = p_category`
5. Combine and distinct leads
6. Enrich with `creator_name`
7. Enrich with `latest_productivity_log`
8. Calculate statistics (totalLeads, leadsWithContact, byStatus, byPlatform)

---

#### 2.2. **Create `ai_get_sales_team`**
**Edge Function Reference:** `core-sales-team-sales-team`

**Function Signature:**
```sql
CREATE OR REPLACE FUNCTION ai_get_sales_team(
    p_user_id UUID,
    p_category TEXT DEFAULT NULL,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_user_role TEXT DEFAULT 'staff'
)
RETURNS JSONB
```

**Logic:**
1. Get sales team from `sales_team_with_user_info`
2. Get all leads (sale_owner_id OR post_sales_owner_id)
3. Filter by `has_contact_info = true`
4. Filter by status IN ('กำลังติดตาม', 'ปิดการขาย') for currentLeads
5. Get all leads for conversion rate calculation
6. Get productivity logs where status = 'ปิดการขายแล้ว'
7. Calculate metrics per member (currentLeads, totalLeads, closedLeads, conversionRate, leadsWithContact, contactRate)
8. Calculate overall statistics

---

#### 2.3. **Create `ai_get_sales_team_list`**
**Edge Function Reference:** `core-leads-sales-team-list`

**Function Signature:**
```sql
CREATE OR REPLACE FUNCTION ai_get_sales_team_list(
    p_user_id UUID,
    p_category TEXT DEFAULT NULL,
    p_status TEXT DEFAULT 'active',
    p_user_role TEXT DEFAULT 'staff'
)
RETURNS JSONB
```

**Logic:**
1. Simple query from `sales_team_with_user_info`
2. Filter by `status = p_status`
3. Return: id, user_id, current_leads, status, name, email, phone, department, position

---

#### 2.4. **Create `ai_get_sales_team_data`**
**Edge Function Reference:** `core-sales-team-sales-team-data`

**Function Signature:**
```sql
CREATE OR REPLACE FUNCTION ai_get_sales_team_data(
    p_user_id UUID,
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_user_role TEXT DEFAULT 'staff'
)
RETURNS JSONB
```

**Logic:**
1. Get sales team from `sales_team_with_user_info`
2. Get leads (sale_owner_id OR post_sales_owner_id)
3. Filter by `has_contact_info = true`
4. Filter by platforms (EV + Partner platforms)
5. Filter by date range (if provided)
6. Get productivity logs where status = 'ปิดการขายแล้ว'
7. Get quotations from closed logs
8. Calculate metrics per member (deals_closed, pipeline_value, conversion_rate, total_leads)
9. Return leads and quotations data

---

#### 2.5. **Create `ai_validate_phone`**
**Edge Function Reference:** `core-leads-phone-validation`

**Function Signature:**
```sql
CREATE OR REPLACE FUNCTION ai_validate_phone(
    p_phone TEXT,
    p_exclude_lead_id INTEGER DEFAULT NULL,
    p_user_id UUID DEFAULT NULL
)
RETURNS JSONB
```

**Logic:**
1. Normalize phone number (remove all non-digits)
2. Fetch all leads with phone numbers (not null, not empty, not whitespace-only)
3. Normalize existing phone numbers
4. Compare normalized input with normalized existing phones
5. Exclude current lead if `exclude_lead_id` is provided
6. Return `{ isDuplicate: boolean, phone: string, existingLead?: Lead }`

---

#### 2.6. **Create `ai_get_lead_management`**
**Edge Function Reference:** `core-leads-lead-management`

**Function Signature:**
```sql
CREATE OR REPLACE FUNCTION ai_get_lead_management(
    p_user_id UUID,
    p_category TEXT DEFAULT 'Package',
    p_include_user_data BOOLEAN DEFAULT true,
    p_include_sales_team BOOLEAN DEFAULT true,
    p_include_leads BOOLEAN DEFAULT true,
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_limit INTEGER DEFAULT NULL,
    p_user_role TEXT DEFAULT 'staff'
)
RETURNS JSONB
```

**Logic:**
1. Parallel queries:
   - Get user data (if include_user_data = true)
   - Get sales team data (if include_sales_team = true)
   - Get leads data (if include_leads = true)
2. Leads query:
   - Filter by `category`
   - Filter by `has_contact_info = true`
   - Date range filtering (no limit if date filter exists)
   - Enrich with `creator_name`
3. Calculate statistics (totalLeads, assignedLeads, unassignedLeads, assignmentRate, leadsWithContact, contactRate)
4. Return: `{ leads, salesTeam, user, salesMember, stats }`

---

## 🔧 Implementation Details

### Common Patterns to Implement

#### 1. **Creator Name Enrichment**
```sql
-- Get creator IDs
SELECT DISTINCT created_by FROM leads WHERE ...;

-- Get creator names
SELECT id, first_name, last_name FROM users WHERE id IN (...);

-- Map to leads
-- Use jsonb_build_object or jsonb_set to add creator_name
```

#### 2. **Latest Productivity Log Enrichment**
```sql
-- Get latest log per lead
SELECT DISTINCT ON (lead_id) 
    lead_id, id, sale_id, note, status, created_at_thai
FROM lead_productivity_logs
WHERE lead_id IN (...)
ORDER BY lead_id, created_at_thai DESC;

-- Map to leads using jsonb_set
```

#### 3. **Phone Normalization**
```sql
-- Remove all non-digits
REGEXP_REPLACE(phone, '[^0-9]', '', 'g')
```

#### 4. **Date Range Filtering**
```sql
-- Cast created_at_thai to date
(created_at_thai::text::timestamp)::date BETWEEN p_date_from AND p_date_to
```

#### 5. **Has Contact Info Filter**
```sql
-- Use computed column
has_contact_info = true

-- Or manual check
(tel IS NOT NULL AND tel != '' AND tel != 'ไม่ระบุ') 
OR (line_id IS NOT NULL AND line_id != '' AND line_id != 'ไม่ระบุ')
```

#### 6. **Platform Filter (EV + Partner)**
```sql
-- EV platforms
IN ('Facebook', 'Line', 'Website', 'TikTok', 'IG', 'YouTube', 'Shopee', 'Lazada', 'แนะนำ', 'Outbound', 'โทร', 'ลูกค้าเก่า service ครบ')

-- Partner platforms
IN ('Huawei', 'ATMOCE', 'Solar Edge', 'Sigenergy')

-- Combined
IN (EV platforms + Partner platforms)
```

#### 7. **Sales Owner OR Post Sales Owner**
```sql
-- Use OR condition
OR (sale_owner_id = p_sales_id, post_sales_owner_id = p_sales_id)

-- Or in Supabase
.or('sale_owner_id.eq.X,post_sales_owner_id.eq.X')
```

---

## 📊 Comparison Matrix

| Edge Function | RPC Function | Status | Missing Features |
|---------------|--------------|--------|------------------|
| `core-leads-leads-for-dashboard` | `ai_get_leads` | ⚠️ Partial | creator_name, limit logic |
| `core-leads-leads-list` | `ai_get_leads` | ⚠️ Partial | creator_name, latest_productivity_log, limit logic |
| `core-leads-lead-detail` | `ai_get_lead_detail` | ⚠️ Partial | All productivity logs, timeline, credit_evaluation, lead_products, quotation_documents |
| `core-my-leads-my-leads` | ❌ None | ❌ Missing | **Create new function** |
| `core-sales-team-sales-team` | `ai_get_team_kpi` | ⚠️ Partial | Full team list, per-member metrics, conversion rate |
| `core-sales-team-sales-team-data` | `ai_get_sales_performance` | ⚠️ Partial | Full team data, leads and quotations in response |
| `core-leads-sales-team-list` | ❌ None | ❌ Missing | **Create new function** |
| `core-appointments-appointments` | `ai_get_appointments` | ⚠️ Partial | Sales member filter, lead info mapping, latest log logic |
| `core-leads-phone-validation` | ❌ None | ❌ Missing | **Create new function** |
| `core-leads-lead-management` | ❌ None | ❌ Missing | **Create new function** |
| `additional-customer-customer-services` | `ai_get_customer_info` | ⚠️ Partial | Extended view, filters, list query |

---

## ✅ Action Items

### Immediate (Phase 1): Enhance Existing Functions

1. ✅ Enhance `ai_get_leads`
   - Add `creator_name` enrichment
   - Add `latest_productivity_log` enrichment
   - Fix limit logic

2. ✅ Enhance `ai_get_lead_detail`
   - Add all productivity logs
   - Add timeline events
   - Add relations (credit_evaluation, lead_products, quotation_documents)

3. ✅ Enhance `ai_get_appointments`
   - Add sales member filtering
   - Add lead info mapping
   - Add latest log per lead logic

4. ✅ Enhance `ai_get_customer_info`
   - Use `customer_services_extended` view
   - Add all filters
   - Support list query

5. ✅ Enhance `ai_get_team_kpi` or create `ai_get_sales_team`
   - Return full team list with metrics

---

### Next (Phase 2): Create Missing Functions

1. ✅ Create `ai_get_my_leads`
2. ✅ Create `ai_get_sales_team` (if not enhancing ai_get_team_kpi)
3. ✅ Create `ai_get_sales_team_list`
4. ✅ Create `ai_get_sales_team_data`
5. ✅ Create `ai_validate_phone`
6. ✅ Create `ai_get_lead_management`

---

## 📝 Next Steps

1. **Review & Approve Plan** - ตรวจสอบและอนุมัติแผน
2. **Start Phase 1** - เริ่ม enhance existing functions
3. **Test Each Enhancement** - ทดสอบแต่ละ enhancement
4. **Start Phase 2** - เริ่มสร้าง missing functions
5. **Integration Testing** - ทดสอบ integration ทั้งหมด
6. **Documentation** - เขียนเอกสารสรุปการเปลี่ยนแปลง

---

## 🎯 Success Criteria

1. ✅ RPC Functions ครอบคลุมทุก Edge Functions
2. ✅ Logic ตรงกับ Edge Functions 100%
3. ✅ Performance ดี (query optimization)
4. ✅ Security ดี (RLS, PII masking)
5. ✅ Error handling ดี

---

## 📚 References

- **Edge Functions:** `/ev-power-energy-crm/supabase/functions/`
- **RPC Functions:** `/evp-ai-assistant/supabase/migrations/`
- **Frontend Guide:** `/ev-power-energy-crm/docs/FRONTEND_FEATURES_AND_API_GUIDE.md`
