# 📋 Migration Guide - evp-ai-assistant

## ⚠️ สิ่งสำคัญที่ต้องรู้

**002 และ 003 มีการซ้ำซ้อนกัน!**

- **002** = RPC functions แบบ placeholder (ยังไม่ทำงานจริง)
- **003** = RPC functions แบบ implement จริง (จะ override 002)

**คำแนะนำ:** ข้าม 002 ไปเลย ใช้แค่ 003

---

## ✅ ลำดับการรัน Migration (แนะนำ)

### 📌 Option 1: รันครบทุกตัว (แนะนำ)

รันตามลำดับนี้:

1. **001** - `20250116000001_initial_schema.sql` ⭐ **จำเป็น**
   - สร้างตารางทั้งหมด (chat_sessions, chat_messages, etc.)
   - สร้าง RLS policies
   - ต้องรันก่อนทุกอย่าง

2. **003** - `20250116000003_ai_rpc_functions.sql` ⭐ **จำเป็น**
   - สร้าง RPC functions พื้นฐาน (implement จริง)
   - ฟังก์ชัน: ai_get_lead_status, ai_get_daily_summary, ai_get_customer_info, ai_get_team_kpi

3. **004** - `20250116000004_vector_search_rpc.sql` ⭐ **จำเป็น**
   - สร้าง vector search function สำหรับ RAG
   - ฟังก์ชัน: match_kb_chunks

4. **005** - `20250116000005_ai_rpc_functions_enhanced.sql` ⭐ **แนะนำ**
   - สร้าง enhanced RPC functions (มี filters, date ranges)
   - ฟังก์ชัน: ai_get_leads, ai_get_lead_detail, ai_get_sales_performance, ai_get_inventory_status, ai_get_appointments

5. **006** - `20250116000006_ai_rpc_functions_complete.sql` ⭐ **แนะนำ**
   - สร้าง complete RPC functions
   - ฟังก์ชัน: ai_get_service_appointments, ai_get_sales_docs, ai_get_quotations, ai_get_permit_requests, ai_get_stock_movements, ai_get_user_info

### ❌ ไม่ต้องรัน

- **002** - `20250116000002_initial_rpc_functions.sql` 
  - เป็น placeholder ยังไม่ทำงานจริง
  - ถูก override โดย 003 อยู่แล้ว
  - **ข้ามไปได้เลย**

---

## 🔄 Option 2: รันเฉพาะขั้นพื้นฐาน (Minimum)

หากต้องการรันเฉพาะขั้นพื้นฐาน:

1. **001** - Initial Schema ⭐
2. **003** - Basic RPC Functions ⭐

> ⚠️ หมายเหตุ: การรันเฉพาะขั้นพื้นฐานจะไม่ได้รับฟีเจอร์ enhanced และ complete functions

---

## 📊 สรุป Comparison

| Migration | Type | Status | Functions Created | Override |
|-----------|------|--------|-------------------|----------|
| 001 | Schema | ✅ Required | Tables + RLS | - |
| 002 | RPC (Placeholder) | ❌ Skip | 3 placeholder functions | ⚠️ Overridden by 003 |
| 003 | RPC (Basic) | ✅ Required | 4 working functions | - |
| 004 | RPC (Vector) | ✅ Required | 1 vector search function | - |
| 005 | RPC (Enhanced) | ⭐ Recommended | 5 enhanced functions | - |
| 006 | RPC (Complete) | ⭐ Recommended | 6 complete functions | - |

---

## 🚀 วิธีรัน Migration

### วิธีที่ 1: ใช้ Supabase Dashboard

1. ไปที่ Supabase Dashboard → SQL Editor
2. รันไฟล์ทีละไฟล์ตามลำดับ:
   - 001 → 003 → 004 → 005 → 006
3. ตรวจสอบว่าแต่ละไฟล์รันสำเร็จ (ควรเห็น "Success. No rows returned")

### วิธีที่ 2: ใช้ Supabase CLI

```bash
cd evp-ai-assistant
supabase db push
```

> ⚠️ หมายเหตุ: `supabase db push` จะรันทุก migration files ที่ยังไม่ได้รัน แต่จะข้ามไฟล์ที่รันไปแล้วอัตโนมัติ

---

## 🔍 ตรวจสอบว่า Migration รันไปแล้วหรือยัง

### ตรวจสอบ Tables

```sql
-- ตรวจสอบว่ามีตาราง chat_sessions หรือไม่
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('chat_sessions', 'chat_messages', 'kb_documents', 'kb_chunks');
```

### ตรวจสอบ Functions

```sql
-- ตรวจสอบว่ามี functions หรือไม่
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_name LIKE 'ai_%'
ORDER BY routine_name;
```

ควรเห็น:
- ai_get_lead_status
- ai_get_daily_summary
- ai_get_customer_info
- ai_get_team_kpi
- match_kb_chunks
- ai_get_leads (from 005)
- ai_get_lead_detail (from 005)
- ... และอื่นๆ

---

## ⚠️ ปัญหาที่อาจเจอ

### 1. Error: "function already exists"

**สาเหตุ:** รัน migration ซ้ำ

**แก้ไข:** ไม่ต้องแก้! `CREATE OR REPLACE FUNCTION` จะ override function เก่าอัตโนมัติ

### 2. Error: "relation does not exist"

**สาเหตุ:** รัน migration ไม่ครบ หรือรันผิดลำดับ

**แก้ไข:** ตรวจสอบว่าได้รัน 001 ก่อนแล้ว

### 3. Error: "extension vector does not exist"

**สาเหตุ:** pgvector extension ยังไม่ได้ enable

**แก้ไข:** 
- ไปที่ Supabase Dashboard → Database → Extensions
- Enable extension `vector`

---

## 📝 คำแนะนำสำหรับการใช้งาน

### หากต้องการแก้ไข Functions

ใช้ `CREATE OR REPLACE FUNCTION` ใน SQL Editor:

```sql
CREATE OR REPLACE FUNCTION ai_get_lead_status(...)
-- your updated code
```

### หากต้องการสร้าง Migration ใหม่

1. สร้างไฟล์ใหม่ใน `supabase/migrations/`
2. ตั้งชื่อตาม format: `YYYYMMDDHHMMSS_description.sql`
3. รันตามลำดับ

---

## 🎯 สรุป

**สำหรับผู้ใช้ใหม่:**
- รัน **001, 003, 004, 005, 006** ตามลำดับ
- ข้าม **002** ไปเลย

**สำหรับผู้ใช้ที่มี 003, 004, 006 อยู่แล้ว:**
- เพิ่มรัน **001** (เพื่อสร้าง tables)
- เพิ่มรัน **005** (เพื่อเพิ่ม enhanced functions)
