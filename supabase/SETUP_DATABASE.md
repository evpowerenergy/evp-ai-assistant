# 🔧 Database Setup Guide - แก้ปัญหา "chat_sessions does not exist"

## ⚠️ ปัญหา

Error: `relation "public.chat_sessions" does not exist`

**สาเหตุ:** Migration files ยังไม่ได้รันบนฐานข้อมูล Supabase

---

## ✅ วิธีแก้ปัญหา

### วิธีที่ 1: ใช้ Supabase Dashboard (แนะนำสำหรับผู้เริ่มต้น)

1. **เข้า Supabase Dashboard**
   - ไปที่ https://supabase.com/dashboard
   - เลือกโปรเจ็กต์ของคุณ

2. **เปิด SQL Editor**
   - ไปที่เมนู `SQL Editor` ทางซ้าย
   - คลิก `New query`

3. **รัน Migration SQL**
   - เปิดไฟล์ `supabase/migrations/20250116000001_initial_schema.sql`
   - Copy ทั้งหมด (Ctrl+A, Ctrl+C)
   - Paste ลงใน SQL Editor
   - กด `Run` หรือ `Ctrl+Enter`

4. **ตรวจสอบผลลัพธ์**
   - ควรเห็นข้อความ "Success. No rows returned"
   - ไปที่ `Table Editor` ทางซ้าย
   - ตรวจสอบว่ามีตาราง `chat_sessions` แล้ว

5. **รัน Migration เพิ่มเติม (ถ้ามี)**
   - รันไฟล์อื่นๆ ใน `supabase/migrations/` ตามลำดับ:
     - `20250116000002_initial_rpc_functions.sql`
     - `20250116000003_ai_rpc_functions.sql`
     - `20250116000004_vector_search_rpc.sql`
     - `20250116000005_ai_rpc_functions_enhanced.sql`
     - `20250116000006_ai_rpc_functions_complete.sql`

---

### วิธีที่ 2: ใช้ Supabase CLI (สำหรับ Developer)

#### ติดตั้ง Supabase CLI
```bash
# macOS
brew install supabase/tap/supabase

# Windows (using Scoop)
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase

# Linux
npm install -g supabase
```

#### Login และ Link Project
```bash
# Login
supabase login

# Link to your project
cd evp-ai-assistant
supabase link --project-ref <your-project-ref>

# หรือใช้ connection string
supabase db push
```

#### รัน Migrations
```bash
cd evp-ai-assistant

# รัน migration ทั้งหมด
supabase db push

# หรือรัน migration เฉพาะ
supabase migration up
```

---

## 📋 ตารางที่จะถูกสร้าง

หลังจากรัน migration จะได้ตารางดังนี้:

1. **`chat_sessions`** - เก็บ session ของการสนทนา
2. **`chat_messages`** - เก็บข้อความในแต่ละ session
3. **`audit_logs`** - เก็บ log การใช้งาน
4. **`kb_documents`** - เก็บเอกสาร knowledge base
5. **`kb_chunks`** - เก็บ chunks ของเอกสาร (พร้อม embeddings)
6. **`line_identities`** - เก็บ LINE user IDs ที่ผูกกับ user

---

## 🔍 ตรวจสอบว่า Migration สำเร็จ

### วิธีที่ 1: ใช้ SQL Editor
```sql
-- ตรวจสอบว่ามีตาราง chat_sessions หรือไม่
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name = 'chat_sessions';

-- ควรเห็นผลลัพธ์: chat_sessions

-- ตรวจสอบโครงสร้างตาราง
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'chat_sessions';

-- ควรเห็นคอลัมน์: id, user_id, title, created_at, updated_at
```

### วิธีที่ 2: ใช้ Table Editor
- ไปที่ `Table Editor` ใน Supabase Dashboard
- ตรวจสอบว่ามีตาราง `chat_sessions` แสดงในรายการ

---

## ⚠️ หมายเหตุสำคัญ

1. **RLS (Row Level Security)**
   - ทุกตารางมี RLS เปิดใช้งาน
   - ผู้ใช้จะเห็นและจัดการได้เฉพาะข้อมูลของตัวเอง

2. **Foreign Key Constraints**
   - `chat_sessions.user_id` → `auth.users(id)`
   - `chat_messages.session_id` → `chat_sessions(id)`
   - ต้องมีข้อมูล user ก่อนที่จะสร้าง session

3. **Extensions ที่ต้องการ**
   - `uuid-ossp` - สำหรับ UUID generation
   - `vector` (pgvector) - สำหรับ embeddings (ถ้าใช้ RAG)

---

## 🚨 หากเจอปัญหา

### ปัญหา: "extension vector does not exist"
**แก้ไข:**
- ไปที่ Supabase Dashboard → Database → Extensions
- Enable extension `vector`

### ปัญหา: "permission denied"
**แก้ไข:**
- ตรวจสอบว่าคุณใช้ Service Role Key หรือ Admin access
- หรือใช้ SQL Editor ที่มีสิทธิ์ admin

### ปัญหา: "relation already exists"
**แก้ไข:**
- แสดงว่า migration รันไปแล้ว
- ข้ามขั้นตอนนี้ได้

---

## 📚 เอกสารเพิ่มเติม

- [Supabase Migration Guide](https://supabase.com/docs/guides/cli/local-development#database-migrations)
- [Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)
