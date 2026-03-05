# 📊 Edge Functions Pattern Analysis

> **วิเคราะห์:** Pattern จาก Supabase Edge Functions ใน CRM repo  
> **Purpose:** ออกแบบ RPC Functions ให้ครอบคลุมและสอดคล้องกับ pattern ที่ใช้จริง

---

## 🔍 Pattern ที่พบ (Common Patterns)

### 1. **Date Filtering Pattern** ⭐ (ใช้บ่อยมาก)

**Pattern:**
```typescript
// Query params
const dateFrom = queryParams.get('from');
const dateTo = queryParams.get('to');
const limit = queryParams.get('limit');

// Apply filter
if (dateFrom && dateTo) {
  query = query
    .gte('created_at_thai', dateFrom)
    .lte('created_at_thai', dateTo);
  // ✅ ไม่ใช้ limit เมื่อมี Date Filter
} else if (limit) {
  query = query.limit(parseInt(limit));
} else {
  query = query.limit(100); // Default limit
}
```

**พบใน:**
- `core-leads-leads-list` ✅
- `core-leads-leads-for-dashboard` ✅
- `core-inventory-inventory` ✅
- `core-sales-team-sales-team-data` ✅

**Key Points:**
- ✅ Date filter = ดึงทั้งหมดในช่วงเวลา (no limit)
- ✅ No date filter = ใช้ limit (default 100-5000)
- ✅ ใช้ `created_at_thai` สำหรับ date filtering
- ✅ Support `dateRange` string ('today', '7', '30') หรือ `from/to`

---

### 2. **Category/Status Filtering Pattern**

**Pattern:**
```typescript
const category = queryParams.get('category');
const status = queryParams.get('status');

if (category) {
  query = query.eq('category', category);
}

if (status) {
  query = query.eq('status', status);
}
```

**พบใน:**
- `core-leads-leads-list` (category) ✅
- `core-leads-leads-for-dashboard` (implicit) ✅

---

### 3. **Platform Filtering Pattern**

**Pattern:**
```typescript
const evPlatforms = ['Facebook', 'Line', 'Website', ...];
const partnerPlatforms = ['Huawei', 'ATMOCE', ...];
const allPlatforms = [...evPlatforms, ...partnerPlatforms];

query = query.in('platform', allPlatforms);
```

**พบใน:**
- `core-sales-team-sales-team-data` ✅

---

### 4. **Contact Info Filtering Pattern**

**Pattern:**
```typescript
// ใช้ computed column
query = query.eq('has_contact_info', true);

// หรือใช้ or condition (legacy)
query = query.or('tel.not.is.null,line_id.not.is.null');
```

**พบใน:**
- `core-leads-leads-list` ✅
- `core-leads-leads-for-dashboard` ✅
- `core-sales-team-sales-team-data` ✅

---

### 5. **Select Specific Fields Pattern**

**Pattern:**
```typescript
// ไม่ใช้ select('*') เสมอ - เลือกเฉพาะ fields ที่ต้องการ
query = query.select(`
  id,
  full_name,
  display_name,
  tel,
  status,
  created_at_thai,
  updated_at_thai
`);
```

**พบใน:**
- ทุก Edge Function ✅

**Why:**
- Performance: ลด data transfer
- Security: ไม่ส่ง fields ที่ไม่จำเป็น
- Clarity: รู้ชัดว่าต้องการ fields อะไร

---

### 6. **Join Related Tables Pattern**

**Pattern:**
```typescript
// Join with related table
query = query.select(`
  *,
  related_table:foreign_key (
    field1,
    field2
  )
`);

// Multiple joins
query = query.select(`
  *,
  table1:fk1 (*),
  table2:fk2 (*)
`);
```

**พบใน:**
- `core-inventory-inventory` (products, suppliers, customers) ✅
- `core-leads-lead-detail` (appointments, quotations) ✅

---

### 7. **Ordering Pattern**

**Pattern:**
```typescript
// Order by date (descending = newest first)
query = query.order('created_at_thai', { ascending: false });

// Order by name
query = query.order('name');

// Multiple ordering
query = query.order('status').order('created_at_thai', { ascending: false });
```

**พบใน:**
- ทุก Edge Function ✅

---

### 8. **Parallel Queries Pattern**

**Pattern:**
```typescript
// Execute multiple queries in parallel
const [result1, result2, result3] = await Promise.all([
  supabase.from('table1').select('*'),
  supabase.from('table2').select('*'),
  supabase.from('table3').select('*')
]);
```

**พบใน:**
- `core-inventory-inventory` ✅
- `core-appointments-appointments` ✅

---

### 9. **Enrichment Pattern** (Add related data)

**Pattern:**
```typescript
// 1. Query main data
const { data: leads } = await supabase.from('leads').select('*');

// 2. Get related IDs
const creatorIds = [...new Set(leads.map(l => l.created_by))];

// 3. Query related data
const { data: users } = await supabase
  .from('users')
  .select('id, first_name, last_name')
  .in('id', creatorIds);

// 4. Create map and enrich
const usersMap = new Map(users.map(u => [u.id, u]));
leads.forEach(lead => {
  lead.creator_name = usersMap.get(lead.created_by)?.name;
});
```

**พบใน:**
- `core-leads-leads-list` ✅
- `core-leads-leads-for-dashboard` ✅

---

### 10. **Response Structure Pattern**

**Pattern:**
```typescript
return {
  success: true,
  data: {
    // Main data
    leads: [...],
    // Related data
    users: [...],
    // Stats
    stats: {
      total: 100,
      active: 50
    }
  },
  meta: {
    executionTime: '123.45ms',
    timestamp: '2025-01-16T...',
    dateFrom: '2025-01-01',
    dateTo: '2025-01-16',
    limit: 100,
    totalRecords: 100
  }
};
```

**พบใน:**
- ทุก Edge Function ✅

---

## 📋 RPC Functions Design (ตาม Pattern)

### Design Principles

1. **Support Date Filtering** (from/to)
2. **Support Category/Status Filters**
3. **Support Limit** (when no date filter)
4. **Select Specific Fields** (not *)
5. **Return Enriched Data** (with related info)
6. **Return Meta Information** (execution time, filters)
7. **Support Multiple Filters** (JSONB filters parameter)

---

## 🎯 Proposed RPC Functions (Enhanced)

### 1. `ai_get_leads` (Enhanced version of `ai_get_lead_status`)

**Parameters:**
```sql
CREATE OR REPLACE FUNCTION ai_get_leads(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_limit INTEGER DEFAULT 100
)
RETURNS JSONB
```

**Filters (JSONB):**
```json
{
  "category": "Package",
  "status": "รอรับ",
  "platform": ["Facebook", "Line"],
  "region": "กรุงเทพ",
  "has_contact_info": true,
  "sale_owner_id": 123
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "leads": [...],
    "stats": {
      "total": 100,
      "with_contact": 80
    }
  },
  "meta": {
    "filters_applied": {...},
    "date_from": "2025-01-01",
    "date_to": "2025-01-16",
    "limit": 100,
    "total_returned": 50
  }
}
```

---

### 2. `ai_get_lead_detail` (Enhanced)

**Parameters:**
```sql
CREATE OR REPLACE FUNCTION ai_get_lead_detail(
    p_lead_id INTEGER,
    p_user_id UUID,
    p_include_related BOOLEAN DEFAULT true
)
RETURNS JSONB
```

**Response:**
```json
{
  "success": true,
  "data": {
    "lead": {...},
    "latest_productivity_log": {...},
    "appointments": [...],
    "quotations": [...],
    "creator": {...}
  }
}
```

---

### 3. `ai_get_sales_performance` (Enhanced)

**Parameters:**
```sql
CREATE OR REPLACE FUNCTION ai_get_sales_performance(
    p_sales_id INTEGER,
    p_user_id UUID,
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_period TEXT DEFAULT 'month'  -- 'day', 'week', 'month', 'year'
)
RETURNS JSONB
```

**Response:**
```json
{
  "success": true,
  "data": {
    "sales_member": {...},
    "metrics": {
      "total_leads": 100,
      "deals_closed": 20,
      "pipeline_value": 5000000,
      "conversion_rate": 20.0
    },
    "leads": [...],
    "quotations": [...]
  },
  "meta": {
    "period": "month",
    "date_from": "2025-01-01",
    "date_to": "2025-01-31"
  }
}
```

---

### 4. `ai_get_inventory_status` (Enhanced)

**Parameters:**
```sql
CREATE OR REPLACE FUNCTION ai_get_inventory_status(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_limit INTEGER DEFAULT 100
)
RETURNS JSONB
```

**Filters:**
```json
{
  "product_name": "Solar Panel",
  "category": "Inverter",
  "low_stock": true,
  "is_active": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "products": [...],
    "inventory_units": [...],
    "stats": {
      "total_products": 50,
      "low_stock_count": 5,
      "total_value": 1000000
    }
  }
}
```

---

### 5. `ai_get_appointments` (Enhanced)

**Parameters:**
```sql
CREATE OR REPLACE FUNCTION ai_get_appointments(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_type TEXT DEFAULT 'all'  -- 'upcoming', 'past', 'all'
)
RETURNS JSONB
```

**Filters:**
```json
{
  "appointment_type": "engineer",
  "status": "scheduled",
  "sales_id": 123
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "engineer": [...],
    "follow_up": [...],
    "payment": [...],
    "stats": {
      "total": 10,
      "upcoming": 5,
      "past": 5
    }
  }
}
```

---

## 🔄 Migration Strategy

### Phase 1: Keep Existing + Add Enhanced

**Keep:**
- `ai_get_lead_status` (simple, by name)
- `ai_get_daily_summary` (simple summary)
- `ai_get_customer_info` (simple, by name)
- `ai_get_team_kpi` (simple KPI)

**Add Enhanced:**
- `ai_get_leads` (with filters, date range)
- `ai_get_lead_detail` (with related data)
- `ai_get_sales_performance` (with date range, metrics)
- `ai_get_inventory_status` (with filters)
- `ai_get_appointments` (with filters, date range)

### Phase 2: Deprecate Simple Versions

- Mark simple versions as deprecated
- Migrate to enhanced versions
- Remove simple versions in Phase 3

---

## 📊 Comparison: Simple vs Enhanced

| Feature | Simple | Enhanced |
|---------|--------|----------|
| **Date Filtering** | ❌ | ✅ |
| **Multiple Filters** | ❌ | ✅ (JSONB) |
| **Limit Control** | ❌ | ✅ |
| **Related Data** | ❌ | ✅ |
| **Stats/Metrics** | ❌ | ✅ |
| **Meta Information** | ❌ | ✅ |
| **Flexibility** | ⚠️ Low | ✅ High |

---

## ✅ Recommendations

### 1. **Create Enhanced RPC Functions** (Priority 1)

สร้าง 5 functions ใหม่:
1. `ai_get_leads` - Enhanced lead query
2. `ai_get_lead_detail` - Lead detail with related data
3. `ai_get_sales_performance` - Sales metrics with date range
4. `ai_get_inventory_status` - Inventory with filters
5. `ai_get_appointments` - Appointments with filters

### 2. **Keep Simple Functions** (Backward Compatibility)

เก็บ simple functions ไว้:
- `ai_get_lead_status` (by name)
- `ai_get_daily_summary`
- `ai_get_customer_info`
- `ai_get_team_kpi`

### 3. **Use Enhanced for AI Queries**

AI Orchestrator ใช้ enhanced functions:
- Support complex queries
- Better filtering
- More context

---

## 🚀 Next Steps

1. **Create Enhanced RPC Functions** (5 functions)
2. **Update Python Wrappers** (`db_tools.py`)
3. **Update AI Orchestrator** (use enhanced functions)
4. **Test with Real Queries**
5. **Document Usage**

---

**Last Updated:** 2025-01-16
