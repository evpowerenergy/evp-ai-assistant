# 🔍 Filter Leads by has_contact_info = true

## 📋 Overview

RPC function `ai_get_leads` ตอนนี้ filter เฉพาะ leads ที่มี `has_contact_info = true` และดึงข้อมูลทุก field จาก table `leads`

---

## ✅ Changes

### 1. **Filter by has_contact_info = true**

**Before:**
```sql
WHERE is_archived = false
-- No filter on has_contact_info
```

**After:**
```sql
WHERE is_archived = false
AND has_contact_info = true  -- CRITICAL: Only leads with contact info
```

---

### 2. **Return ALL Fields from leads Table**

**Before:**
```sql
SELECT jsonb_build_object(
    'id', id,
    'full_name', full_name,
    'display_name', display_name,
    'tel', tel,
    'line_id', line_id,
    'status', status,
    'category', category,
    'region', region,
    'platform', platform,
    'operation_status', operation_status,
    'created_at_thai', created_at_thai,
    'updated_at_thai', updated_at_thai
)
```

**After:**
```sql
SELECT to_jsonb(l.*)  -- Returns ALL fields from leads table automatically
```

**Benefits:**
- ✅ ดึงข้อมูลทุก field อัตโนมัติ
- ✅ ไม่ต้อง list fields ใหม่ทุกครั้งที่มีการเพิ่ม column
- ✅ ได้ข้อมูลครบถ้วนจากตารางหลัก `leads`

---

## 📁 Migration File

**File:** `supabase/migrations/20250117000007_filter_has_contact_info_and_all_fields.sql`

**Changes:**
1. เพิ่ม filter: `has_contact_info = true`
2. เปลี่ยนจาก `jsonb_build_object(...)` เป็น `to_jsonb(l.*)` เพื่อดึงทุก field

---

## 🔍 How It Works

### Query Logic:

```sql
SELECT jsonb_agg(to_jsonb(l.*))
FROM leads l
WHERE l.is_archived = false
AND l.has_contact_info = true  -- Only leads with contact info
AND (
    -- Apply filters (category, status, region, platform)
    ...
)
AND (
    -- Date filter (date_from, date_to)
    ...
)
ORDER BY l.created_at_thai DESC
LIMIT ...
```

---

## 📊 Example Response

### Before:
```json
{
  "success": true,
  "data": {
    "leads": [
      {
        "id": "...",
        "full_name": "...",
        "display_name": "...",
        "tel": "...",
        "line_id": "...",
        "status": "...",
        "category": "...",
        "region": "...",
        "platform": "...",
        "operation_status": "...",
        "created_at_thai": "...",
        "updated_at_thai": "..."
      }
    ]
  }
}
```

### After:
```json
{
  "success": true,
  "data": {
    "leads": [
      {
        "id": "...",
        "full_name": "...",
        "display_name": "...",
        "tel": "...",
        "line_id": "...",
        "status": "...",
        "category": "...",
        "region": "...",
        "platform": "...",
        "operation_status": "...",
        "created_at_thai": "...",
        "updated_at_thai": "...",
        "has_contact_info": true,
        "is_archived": false,
        "sale_owner_id": "...",
        "notes": "...",
        // ... ALL other fields from leads table
      }
    ]
  },
  "meta": {
    "filter_by_has_contact_info": true
  }
}
```

---

## 🎯 Impact

### Benefits:

1. **Data Quality:**
   - ✅ แสดงเฉพาะ leads ที่มี contact info (tel หรือ line_id)
   - ✅ ลด leads ที่ไม่มีข้อมูลติดต่อ

2. **Data Completeness:**
   - ✅ ดึงข้อมูลทุก field จาก table `leads`
   - ✅ ไม่ต้องแก้ code เมื่อเพิ่ม column ใหม่

3. **Performance:**
   - ✅ Filter ที่ database level
   - ✅ ลดข้อมูลที่ต้อง transfer

---

## ⚠️ Important Notes

### has_contact_info Field

- **Type:** Boolean
- **Location:** `leads` table
- **Meaning:** `true` = lead มี tel หรือ line_id

### ถ้า has_contact_info ไม่ได้ถูก set อัตโนมัติ:

ต้องแน่ใจว่า field `has_contact_info` ถูก update เมื่อ:
- เพิ่ม lead ใหม่ที่มี tel หรือ line_id
- Update tel หรือ line_id ของ lead

**Trigger Example:**
```sql
CREATE OR REPLACE FUNCTION update_has_contact_info()
RETURNS TRIGGER AS $$
BEGIN
    NEW.has_contact_info = (NEW.tel IS NOT NULL OR NEW.line_id IS NOT NULL);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER leads_update_has_contact_info
BEFORE INSERT OR UPDATE ON leads
FOR EACH ROW
EXECUTE FUNCTION update_has_contact_info();
```

---

## 🚀 Testing

### Test Cases:

1. **Filter Test:**
   - Query leads → Should only return leads with `has_contact_info = true`
   - Should NOT return leads without contact info

2. **All Fields Test:**
   - Response should include ALL fields from `leads` table
   - Check that new fields are automatically included

3. **Date Filter Test:**
   - Query "ลูกค้าที่ได้มาเมื่อวาน" → Should only return leads with `has_contact_info = true` created yesterday

---

## 📝 Summary

- ✅ Filter: `has_contact_info = true`
- ✅ Return: ALL fields from `leads` table using `to_jsonb(l.*)`
- ✅ Migration: `20250117000007_filter_has_contact_info_and_all_fields.sql`

---

## 🔄 Next Steps

1. **Run Migration:**
   ```bash
   # Run the migration file
   supabase migration up
   ```

2. **Test:**
   - Query leads through the API
   - Verify only leads with `has_contact_info = true` are returned
   - Verify all fields are included in response

3. **Verify has_contact_info is Updated:**
   - Check if `has_contact_info` is updated automatically
   - Create trigger if needed (see above)
