# 🔍 Troubleshooting: search_leads ไม่มีข้อมูล

## 🐛 ปัญหา

เมื่อทดสอบ `search_leads` tool ได้ผลลัพธ์:
```json
{
  "result": {
    "error": "{'found': False, 'message': 'Lead not found'}"
  }
}
```

## 🔍 สาเหตุที่เป็นไปได้

### 1. RPC Function ยังไม่ได้ Run Migration (น่าจะเป็นสาเหตุหลัก)

`ai_get_leads` RPC function ยังไม่ได้ run migration ใน database

**ตรวจสอบ:**
- Migration `20250117000003_fix_ai_get_leads_role.sql` ยังไม่ได้ run
- หรือ migration `20250116000005_ai_rpc_functions_enhanced.sql` ยังไม่ได้ run

**วิธีแก้:**
```sql
-- Run migration ใน Supabase Dashboard หรือ SQL Editor
-- File: supabase/migrations/20250117000003_fix_ai_get_leads_role.sql
```

### 2. RPC Function Return Error

RPC function อาจจะ return error จาก database

**ตรวจสอบ:**
- ดู backend logs สำหรับ error message
- ตรวจสอบว่า `leads` table มีข้อมูลหรือไม่
- ตรวจสอบว่า column `created_at_thai` มีอยู่จริง

### 3. No Data in Database

Database อาจจะไม่มีข้อมูล leads

**ตรวจสอบ:**
```sql
-- Check if leads table has data
SELECT COUNT(*) FROM leads WHERE is_archived = false;

-- Check leads created today
SELECT COUNT(*) 
FROM leads 
WHERE DATE(created_at_thai::timestamp) = CURRENT_DATE 
AND is_archived = false;
```

## ✅ วิธีแก้ไข

### Step 0: แก้ SQL Error (ถ้าเจอ error นี้)

**Error:** `column "leads.created_at_thai" must appear in GROUP BY clause`

**วิธีแก้:** Run migration `20250117000004_fix_ai_get_leads_date_filter.sql`

Migration นี้จะแก้ปัญหาการใช้ `DATE()` function ใน WHERE clause โดย:
- ใช้ subquery เพื่อแยก aggregation ออกจาก WHERE clause
- Cast `created_at_thai` เป็น date โดยตรง: `(created_at_thai::text::timestamp)::date`

### Step 1: ตรวจสอบว่า RPC Function มีอยู่หรือไม่

Run SQL query ใน Supabase Dashboard:

```sql
-- Check if ai_get_leads function exists
SELECT 
    routine_name,
    routine_type,
    data_type
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name = 'ai_get_leads';
```

**ถ้าไม่มีผลลัพธ์** → Function ยังไม่ได้ run migration

### Step 2: Run Migration

**Option A: ใช้ Supabase Dashboard**
1. ไปที่ Supabase Dashboard → SQL Editor
2. Copy content จาก `supabase/migrations/20250117000003_fix_ai_get_leads_role.sql`
3. Run SQL

**Option B: ใช้ Supabase CLI**
```bash
cd evp-ai-assistant
supabase db reset  # หรือ
supabase migration up
```

### Step 3: ทดสอบ RPC Function โดยตรง

ใช้ Python script:

```bash
cd backend
python test_rpc_ai_get_leads.py
```

หรือทดสอบผ่าน Supabase Dashboard:

```sql
-- Test ai_get_leads function
SELECT ai_get_leads(
    '9f39067b-f803-4cb4-b3c6-c0f2e3403fd8'::uuid,  -- your user_id
    '{}'::jsonb,  -- filters
    CURRENT_DATE,  -- date_from
    CURRENT_DATE,  -- date_to
    10,  -- limit
    'staff'::text  -- user_role
);
```

### Step 4: ทดสอบ Tool อีกครั้ง

ใช้ Postman หรือ curl:

```bash
POST /api/v1/test-tools
{
  "tool_name": "search_leads",
  "parameters": {
    "query": "today",
    "user_role": "staff"
  }
}
```

## 📋 Expected Response Format

เมื่อทำงานถูกต้องควรจะได้ response แบบนี้:

```json
{
  "success": true,
  "tool_name": "search_leads",
  "result": {
    "success": true,
    "data": {
      "leads": [
        {
          "id": 1,
          "full_name": "John Doe",
          "display_name": "John",
          "tel": null,  // Masked for staff role
          "line_id": null,  // Masked for staff role
          "status": "active",
          "category": "EV",
          "region": "Bangkok",
          "platform": "Facebook",
          "operation_status": "pending",
          "created_at_thai": "2026-01-17T10:00:00",
          "updated_at_thai": "2026-01-17T10:00:00"
        }
      ],
      "stats": {
        "total": 5,
        "returned": 5,
        "with_contact": 3
      }
    },
    "meta": {
      "filters_applied": {},
      "date_from": "2026-01-17",
      "date_to": "2026-01-17",
      "limit": 100,
      "total_returned": 5,
      "user_role": "staff"
    }
  }
}
```

## 🔍 Debug Steps

1. **ตรวจสอบ Backend Logs**
   ```
   🔍 [STEP 2/4] DB Query Node: Executing tools
   📞 Calling RPC: ai_get_leads
   Parameters: user_id=..., date_from=2026-01-17, date_to=2026-01-17
   📥 RPC Response: {...}
   ```

2. **ตรวจสอบ Error Message**
   - ถ้าเป็น `function does not exist` → Run migration
   - ถ้าเป็น `column does not exist` → ตรวจสอบ table schema
   - ถ้าเป็น `permission denied` → ตรวจสอบ RLS policies

3. **ตรวจสอบ Database**
   ```sql
   -- Check table structure
   \d leads
   
   -- Check data
   SELECT * FROM leads WHERE is_archived = false LIMIT 5;
   ```

## 💡 Tips

- **ถ้าไม่มีข้อมูล** → RPC จะ return `"leads": []` แต่ยังเป็น `"success": true`
- **ถ้า RPC error** → จะ return `"success": false, "error": true, "message": "..."`
