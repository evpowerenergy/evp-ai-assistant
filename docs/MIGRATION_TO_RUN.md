# 📋 Migrations ที่ต้อง Run

## ✅ Migration ที่ต้อง Run (ลำดับความสำคัญ)

### **Migration 1: 20250117000002_fix_ai_get_daily_summary_role.sql** ⭐ **สำคัญที่สุด**

**แก้ไข:**
- ✅ เพิ่ม parameter `p_user_role` เพื่อรับ role จาก backend (แทนการ query `auth.users`)
- ✅ ใช้ `p_date` โดยตรง (default CURRENT_DATE)
- ✅ แก้ปัญหา `is_active` column ที่ไม่มีใน `customer_services` table

**วิธี Run:**
```sql
-- Copy SQL จากไฟล์: supabase/migrations/20250117000002_fix_ai_get_daily_summary_role.sql
-- ไปที่ Supabase Dashboard → SQL Editor → Paste และ Run
```

**หรือใช้ Supabase CLI:**
```bash
cd /home/film/ev-power-energy/evp-ai-assistant
supabase db push
```

---

## 📝 สรุป Migration Files

| Migration File | Status | คำอธิบาย |
|---------------|--------|---------|
| `20250116000001_initial_schema.sql` | ✅ Should run | Initial schema (chat_sessions, etc.) |
| `20250116000002_initial_rpc_functions.sql` | ⚠️ Optional | Placeholder functions (superseded by 003) |
| `20250116000003_ai_rpc_functions.sql` | ✅ Should run | Main RPC functions (แต่มี bug) |
| `20250116000004_vector_search_rpc.sql` | ✅ Should run | Vector search functions |
| `20250116000005_ai_rpc_functions_enhanced.sql` | ✅ Should run | Enhanced RPC functions |
| `20250116000006_ai_rpc_functions_complete.sql` | ✅ Should run | Complete RPC functions |
| `20250117000001_fix_ai_get_daily_summary.sql` | ⚠️ Skip | Superseded by 20250117000002 |
| **`20250117000002_fix_ai_get_daily_summary_role.sql`** | ✅ **MUST RUN** | **Fix role parameter + date + is_active** |

---

## 🎯 ขั้นตอนการ Run Migration

### **Option 1: ใช้ Supabase Dashboard (แนะนำ)**

1. ไปที่ **Supabase Dashboard** → **SQL Editor**
2. Copy เนื้อหา SQL จากไฟล์: `supabase/migrations/20250117000002_fix_ai_get_daily_summary_role.sql`
3. Paste ใน SQL Editor
4. Click **Run**

### **Option 2: ใช้ Supabase CLI**

```bash
cd /home/film/ev-power-energy/evp-ai-assistant
supabase db push
```

**หมายเหตุ:** ต้อง setup Supabase CLI ก่อน

---

## ✅ หลัง Run Migration แล้ว

### **ตรวจสอบว่า Migration สำเร็จ:**

```sql
-- ตรวจสอบว่า function มี parameter p_user_role หรือไม่
SELECT 
    p.proname as function_name,
    pg_get_function_arguments(p.oid) as arguments
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public' 
AND p.proname = 'ai_get_daily_summary';
```

**ผลลัพธ์ที่คาดหวัง:**
```
function_name           | arguments
------------------------|-----------------------------------
ai_get_daily_summary    | p_user_id uuid, p_date date DEFAULT CURRENT_DATE, p_user_role text DEFAULT 'staff'::text
```

---

## 🔍 ตรวจสอบหลัง Run Migration

### **Test Function:**

```sql
-- Test 1: เรียกด้วย role parameter
SELECT ai_get_daily_summary(
    '9f39067b-f803-4cb4-b3c6-c0f2e3403fd8'::uuid,
    CURRENT_DATE,
    'staff'::text
);

-- Test 2: เรียกด้วย default parameters
SELECT ai_get_daily_summary(
    '9f39067b-f803-4cb4-b3c6-c0f2e3403fd8'::uuid
);
```

**ผลลัพธ์ที่คาดหวัง:**
```json
{
  "date": "2026-01-17",
  "new_leads_today": 0,
  "role": "staff"
}
```

---

## ⚠️ หมายเหตุ

1. **Migration 20250117000002 จะ replace function เดิม** (ใช้ `CREATE OR REPLACE FUNCTION`)
2. **ไม่ต้อง run 20250117000001** เพราะ 20250117000002 รวมการแก้ไขทั้งหมดแล้ว
3. **หลัง run แล้ว ต้อง restart backend** เพื่อให้ backend code ใหม่ทำงาน

---

## 🚀 หลัง Run Migration เสร็จ

1. ✅ Restart backend server
2. ✅ ทดสอบ chatbot ด้วยคำถาม: "ยอดขายวันนี้"
3. ✅ ตรวจสอบ log ว่า role และ date ถูกส่งไปที่ RPC function ถูกต้อง
