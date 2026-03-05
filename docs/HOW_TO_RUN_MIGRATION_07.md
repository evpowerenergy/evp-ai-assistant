# 🚀 How to Run Migration 20250117000007

## 📋 Overview

Migration `20250117000007_filter_has_contact_info_and_all_fields.sql` ต้องรันเพื่อ:
1. Filter leads โดย `has_contact_info = true`
2. ดึงข้อมูลทุก field จาก table `leads`

---

## 🎯 Method 1: Run via Supabase Dashboard (แนะนำ)

### ขั้นตอน:

1. **เปิด Supabase Dashboard:**
   - ไปที่: https://supabase.com/dashboard
   - เลือก project ของคุณ

2. **ไปที่ SQL Editor:**
   - คลิกที่ **SQL Editor** ใน sidebar
   - คลิก **New Query**

3. **Copy SQL Query:**
   - เปิดไฟล์: `supabase/migrations/20250117000007_filter_has_contact_info_and_all_fields.sql`
   - Copy ทั้งหมด

4. **Paste และ Run:**
   - Paste SQL query ลงใน SQL Editor
   - คลิก **Run** หรือกด `Ctrl + Enter` (Windows) / `Cmd + Enter` (Mac)

5. **ตรวจสอบผลลัพธ์:**
   - ควรเห็น: `Success. No rows returned` หรือ `Success. Row returned`
   - ถ้ามี error → ตรวจสอบ error message

---

## 🎯 Method 2: Run via Supabase CLI

### Prerequisites:

- ติดตั้ง Supabase CLI แล้ว
- Login แล้ว (`supabase login`)
- Link project แล้ว (`supabase link --project-ref <project-ref>`)

### ขั้นตอน:

```bash
# 1. ไปที่ directory ของ project
cd /home/film/ev-power-energy/evp-ai-assistant

# 2. Run migration
supabase db push

# หรือถ้าต้องการ run specific migration
supabase migration up --file 20250117000007_filter_has_contact_info_and_all_fields.sql
```

---

## 🎯 Method 3: Run SQL Directly (Manual)

### Copy Query นี้ไปรัน:

```sql
-- Filter leads by has_contact_info = true and return all fields
-- Migration: 20250117000007_filter_has_contact_info_and_all_fields.sql
-- Changes:
-- 1. Filter only leads where has_contact_info = true
-- 2. Return ALL fields from leads table (not just selected fields)

-- Function: ai_get_leads (Filter by has_contact_info = true, return all fields)
CREATE OR REPLACE FUNCTION ai_get_leads(
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
    v_leads JSONB;
    v_total_count INTEGER;
    v_stats JSONB;
BEGIN
    -- Count total (for stats) - ONLY leads with has_contact_info = true
    SELECT COUNT(*) INTO v_total_count
    FROM leads
    WHERE is_archived = false
    AND has_contact_info = true  -- CRITICAL: Filter only leads with has_contact_info = true
    AND (
        -- Apply filters
        (p_filters->>'category' IS NULL OR category = p_filters->>'category')
        AND (p_filters->>'status' IS NULL OR status = p_filters->>'status')
        AND (p_filters->>'region' IS NULL OR region = p_filters->>'region')
        AND (p_filters->>'platform' IS NULL OR platform = p_filters->>'platform')
    )
    AND (
        -- Date filter - cast created_at_thai to date for comparison
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            created_at_thai IS NOT NULL 
            AND (created_at_thai::text::timestamp)::date BETWEEN 
                COALESCE(p_date_from, '1900-01-01'::date) AND 
                COALESCE(p_date_to, '2100-12-31'::date)
        )
    );
    
    -- Get leads with ALL fields from leads table
    -- Use to_jsonb(l.*) to automatically include ALL columns from leads table
    SELECT jsonb_agg(
        to_jsonb(l.*)
    ) INTO v_leads
    FROM leads l
    WHERE l.is_archived = false
    AND l.has_contact_info = true  -- CRITICAL: Only leads with contact info
    AND (
        -- Apply filters
        (p_filters->>'category' IS NULL OR l.category = p_filters->>'category')
        AND (p_filters->>'status' IS NULL OR l.status = p_filters->>'status')
        AND (p_filters->>'region' IS NULL OR l.region = p_filters->>'region')
        AND (p_filters->>'platform' IS NULL OR l.platform = p_filters->>'platform')
    )
    AND (
        -- Date filter - cast created_at_thai to date for comparison
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            l.created_at_thai IS NOT NULL 
            AND (l.created_at_thai::text::timestamp)::date BETWEEN 
                COALESCE(p_date_from, '1900-01-01'::date) AND 
                COALESCE(p_date_to, '2100-12-31'::date)
        )
    )
    ORDER BY l.created_at_thai::text::timestamp DESC NULLS LAST
    LIMIT CASE 
        WHEN p_limit IS NULL THEN 100000  -- Very high limit (practically unlimited)
        WHEN p_limit > 0 THEN p_limit
        ELSE 100000  -- Very high limit (practically unlimited)
    END;
    
    -- Build stats
    v_stats := jsonb_build_object(
        'total', v_total_count,
        'returned', jsonb_array_length(COALESCE(v_leads, '[]'::jsonb)),
        'with_contact', v_total_count  -- All returned leads have contact info
    );
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'leads', COALESCE(v_leads, '[]'::jsonb),
            'stats', v_stats
        ),
        'meta', jsonb_build_object(
            'filters_applied', p_filters,
            'date_from', p_date_from,
            'date_to', p_date_to,
            'limit', p_limit,
            'total_returned', jsonb_array_length(COALESCE(v_leads, '[]'::jsonb)),
            'user_role', p_user_role,
            'filter_by_has_contact_info', true
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

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION ai_get_leads(UUID, JSONB, DATE, DATE, INTEGER, TEXT) TO authenticated;
```

---

## ✅ Verify Migration

### 1. Check Function Exists:

```sql
-- Check if function exists
SELECT proname, prosrc 
FROM pg_proc 
WHERE proname = 'ai_get_leads';
```

### 2. Test Function:

```sql
-- Test function with sample parameters
SELECT ai_get_leads(
    '00000000-0000-0000-0000-000000000000'::UUID,  -- user_id
    '{}'::JSONB,                                    -- filters
    NULL,                                           -- date_from
    NULL,                                           -- date_to
    NULL,                                           -- limit
    'staff'                                         -- user_role
);
```

### 3. Check Response:

- Response ควรมี `filter_by_has_contact_info: true` ใน `meta`
- Leads ที่ return ควรมี `has_contact_info: true` เท่านั้น
- Response ควรมีทุก field จาก `leads` table

---

## 🐛 Troubleshooting

### Error: "column has_contact_info does not exist"

**สาเหตุ:** Table `leads` ไม่มี field `has_contact_info`

**แก้ไข:** 
1. ตรวจสอบว่า table `leads` มี field `has_contact_info` หรือไม่
2. ถ้าไม่มี → สร้าง column:
   ```sql
   ALTER TABLE leads ADD COLUMN has_contact_info BOOLEAN DEFAULT false;
   
   -- Update existing rows
   UPDATE leads SET has_contact_info = (tel IS NOT NULL OR line_id IS NOT NULL);
   ```

### Error: "function ai_get_leads already exists"

**สาเหตุ:** Function มีอยู่แล้ว (อาจรัน migration ไปแล้ว)

**แก้ไข:**
- ไม่ต้องทำอะไร - function จะถูก replace อัตโนมัติ
- หรือ skip migration นี้

---

## 📝 Summary

### วิธีที่ง่ายที่สุด:

1. เปิด Supabase Dashboard
2. ไปที่ SQL Editor
3. Copy SQL query จาก migration file
4. Paste และ Run

### หรือรันผ่าน CLI:

```bash
cd /home/film/ev-power-energy/evp-ai-assistant
supabase db push
```

---

## 🎯 After Migration

หลังรัน migration สำเร็จ:

1. ✅ Function `ai_get_leads` จะ filter เฉพาะ leads ที่มี `has_contact_info = true`
2. ✅ Function จะ return ทุก field จาก `leads` table
3. ✅ ทดสอบด้วย query "ลูกค้าที่ได้มาเมื่อวาน" → ควรแสดงเฉพาะ leads ที่มี contact info
