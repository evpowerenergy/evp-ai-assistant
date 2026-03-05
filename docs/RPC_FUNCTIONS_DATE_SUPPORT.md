# 📅 RPC Functions Date Range Support

## 📋 สรุป: RPC Functions ที่รองรับ Date Range

### ✅ Functions ที่รองรับ Date Range แล้ว:

| Function | date_from | date_to | Date Field Used |
|----------|-----------|---------|----------------|
| `ai_get_leads` | ✅ | ✅ | `created_at_thai` |
| `ai_get_service_appointments` | ✅ | ✅ | (check migration) |
| `ai_get_sales_docs` | ✅ | ✅ | (check migration) |
| `ai_get_quotations` | ✅ | ✅ | (check migration) |
| `ai_get_permit_requests` | ✅ | ✅ | (check migration) |
| `ai_get_stock_movements` | ✅ | ✅ | (check migration) |

---

## 🔍 `ai_get_leads` - Date Filter Details

### Current Implementation:

**Date Field:** `created_at_thai` (วันที่สร้าง)

**SQL Filter:**
```sql
AND (
    -- Date filter - cast created_at_thai to date for comparison
    (p_date_from IS NULL AND p_date_to IS NULL)
    OR (
        created_at_thai IS NOT NULL 
        AND (created_at_thai::text::timestamp)::date BETWEEN 
            COALESCE(p_date_from, '1900-01-01'::date) AND 
            COALESCE(p_date_to, '2100-12-31'::date)
    )
)
```

---

## 🔄 ถ้าต้องการใช้ `updated_at_thai` แทน

### Option 1: เปลี่ยนเป็น `updated_at_thai` ทั้งหมด

**Migration:** `20250117000007_use_updated_at_thai.sql`

```sql
-- Change date filter to use updated_at_thai instead of created_at_thai
CREATE OR REPLACE FUNCTION ai_get_leads(...)
...
AND (
    -- Date filter - use updated_at_thai
    (p_date_from IS NULL AND p_date_to IS NULL)
    OR (
        updated_at_thai IS NOT NULL 
        AND (updated_at_thai::text::timestamp)::date BETWEEN 
            COALESCE(p_date_from, '1900-01-01'::date) AND 
            COALESCE(p_date_to, '2100-12-31'::date)
    )
)
```

---

### Option 2: ให้เลือกได้ (Flexible)

**Migration:** เพิ่ม parameter `p_date_field` เพื่อเลือก field

```sql
CREATE OR REPLACE FUNCTION ai_get_leads(
    ...
    p_date_field TEXT DEFAULT 'created'  -- 'created' or 'updated'
)
...
AND (
    -- Date filter - use selected field
    (p_date_from IS NULL AND p_date_to IS NULL)
    OR (
        CASE 
            WHEN p_date_field = 'updated' THEN
                updated_at_thai IS NOT NULL 
                AND (updated_at_thai::text::timestamp)::date BETWEEN ...
            ELSE
                created_at_thai IS NOT NULL 
                AND (created_at_thai::text::timestamp)::date BETWEEN ...
        END
    )
)
```

---

## 📝 Functions อื่นๆ ที่ต้องตรวจสอบ

### `ai_get_service_appointments`
- ตรวจสอบว่าใช้ date field อะไร
- อาจจะต้องใช้ `appointment_date` หรือ `created_at`

### `ai_get_sales_docs`
- ตรวจสอบว่าใช้ date field อะไร
- อาจจะต้องใช้ `doc_date` หรือ `created_at`

---

## 🎯 คำแนะนำ

### ถ้าต้องการให้ยืดหยุ่น:

1. **ใช้ `created_at_thai` สำหรับ "ได้มา" (created)**
   - "ลูกค้าที่ได้มาเมื่อวาน" → ใช้ `created_at_thai`

2. **ใช้ `updated_at_thai` สำหรับ "อัพเดท" (updated)**
   - "ลูกค้าที่อัพเดทเมื่อวาน" → ใช้ `updated_at_thai`

3. **ให้ LLM เลือก field ตาม context:**
   - เพิ่ม parameter `date_field` ใน tool schema
   - LLM จะเลือก field ตามที่ user ถาม

---

## ✅ สรุป

- **RPC function `ai_get_leads` รองรับ date range แล้ว** (ใช้ `created_at_thai`)
- **Backend tools รองรับ date extraction แล้ว** (จาก natural language)
- **LLM router รองรับ date_from และ date_to parameters แล้ว**

**ถ้าต้องการใช้ `updated_at_thai`:**
- ต้องแก้ RPC function (สร้าง migration ใหม่)
- หรือเพิ่ม parameter เพื่อเลือก field
