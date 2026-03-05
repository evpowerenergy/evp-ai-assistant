# 🧪 Testing Guide - AI Assistant

> **Status:** Ready for Testing  
> **Date:** 2025-01-16

---

## ✅ สิ่งที่พร้อมแล้ว

### Backend ✅
- ✅ FastAPI application structure
- ✅ API endpoints (`/chat`, `/health`)
- ✅ Authentication & Authorization
- ✅ AI Orchestration (LangGraph)
- ✅ RPC Functions (15 functions)
- ✅ Database migrations (3 files)

### Frontend ✅
- ✅ Next.js 14 application
- ✅ Authentication UI
- ✅ Chat Interface
- ✅ Session Management
- ✅ Admin Console

### Database ✅
- ✅ Migrations ready (3 files)
- ✅ RPC Functions ready (15 functions)

---

## 🚀 ขั้นตอนการทดสอบ

### 1. Setup Environment Variables

#### Backend (`.env`)
```bash
cd evp-ai-assistant/backend
cp .env.example .env  # ถ้ามี
# หรือสร้างไฟล์ .env ใหม่
```

**Required Variables:**
```env
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# LINE (optional for now)
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_line_access_token

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

#### Frontend (`.env.local`)
```bash
cd evp-ai-assistant/frontend
cp .env.example .env.local  # ถ้ามี
# หรือสร้างไฟล์ .env.local ใหม่
```

**Required Variables:**
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

### 2. Setup Database

#### Run Migrations
```bash
# ใช้ Supabase CLI หรือ Supabase Dashboard
# Migration files:
# 1. 20250116000001_initial_schema.sql
# 2. 20250116000003_ai_rpc_functions.sql
# 3. 20250116000005_ai_rpc_functions_enhanced.sql
# 4. 20250116000006_ai_rpc_functions_complete.sql
```

**ตรวจสอบ:**
- ✅ Tables created: `chat_sessions`, `chat_messages`, `audit_logs`, `kb_documents`, `kb_chunks`, `line_identities`
- ✅ RPC Functions created: 15 functions
- ✅ RLS policies enabled

---

### 3. Install Dependencies

#### Backend
```bash
cd evp-ai-assistant/backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Frontend
```bash
cd evp-ai-assistant/frontend

# Install dependencies
npm install
```

---

### 4. Start Backend

```bash
cd evp-ai-assistant/backend
source venv/bin/activate  # ถ้ายังไม่ได้ activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**ตรวจสอบ:**
- ✅ Backend running: http://localhost:8000
- ✅ Health check: http://localhost:8000/api/v1/health
- ✅ API docs: http://localhost:8000/docs

---

### 5. Start Frontend

```bash
cd evp-ai-assistant/frontend
npm run dev
```

**ตรวจสอบ:**
- ✅ Frontend running: http://localhost:3000
- ✅ Redirect to login page

---

### 6. ทดสอบ Authentication

1. เปิด http://localhost:3000
2. ควร redirect ไป `/login`
3. Login ด้วย Supabase credentials
4. ควร redirect ไป `/chat`

---

### 7. ทดสอบ Chat Interface

1. เปิด `/chat` page
2. ส่งข้อความ: "สถานะ lead A"
3. ตรวจสอบ:
   - ✅ Message ส่งได้
   - ✅ Response กลับมา
   - ✅ Citations แสดง (ถ้ามี)
   - ✅ Feedback buttons แสดง

---

### 8. ทดสอบ Session Management

1. สร้าง session ใหม่
2. ส่งข้อความหลายข้อความ
3. สลับ session
4. ลบ session

---

### 9. ทดสอบ Admin Console (ถ้าเป็น admin/manager)

1. เปิด `/admin`
2. ทดสอบ Document Upload
3. ทดสอบ Log Viewer
4. ทดสอบ LINE Linking

---

## ⚠️ สิ่งที่ต้องระวัง

### 1. Database Connection
- ✅ ตรวจสอบ Supabase URL และ Service Role Key
- ✅ ตรวจสอบว่า migrations รันแล้ว
- ✅ ตรวจสอบ RPC functions สร้างแล้ว

### 2. Authentication
- ✅ ตรวจสอบ Supabase Auth ตั้งค่าแล้ว
- ✅ ตรวจสอบ user มี role ใน metadata
- ✅ ตรวจสอบ JWT token validation

### 3. API Connection
- ✅ ตรวจสอบ Backend running (port 8000)
- ✅ ตรวจสอบ CORS settings
- ✅ ตรวจสอบ API URL ใน frontend

### 4. RPC Functions
- ✅ ตรวจสอบว่า migrations รันแล้ว
- ✅ ตรวจสอบว่า functions สร้างแล้ว
- ✅ ตรวจสอบ permissions (GRANT EXECUTE)

---

## 🐛 Troubleshooting

### Backend Issues

**Error: Module not found**
```bash
# ตรวจสอบ virtual environment
source venv/bin/activate
pip install -r requirements.txt
```

**Error: Database connection failed**
```bash
# ตรวจสอบ .env file
# ตรวจสอบ Supabase URL และ Service Role Key
```

**Error: RPC function not found**
```bash
# ตรวจสอบว่า migrations รันแล้ว
# ตรวจสอบใน Supabase Dashboard: Database > Functions
```

### Frontend Issues

**Error: Cannot connect to API**
```bash
# ตรวจสอบ Backend running
# ตรวจสอบ NEXT_PUBLIC_API_URL
# ตรวจสอบ CORS settings
```

**Error: Authentication failed**
```bash
# ตรวจสอบ Supabase credentials
# ตรวจสอบ NEXT_PUBLIC_SUPABASE_URL
# ตรวจสอบ NEXT_PUBLIC_SUPABASE_ANON_KEY
```

---

## ✅ Checklist: Ready to Test

### Prerequisites
- [ ] Python 3.12 installed
- [ ] Node.js 18+ installed
- [ ] Supabase project created
- [ ] OpenAI API key obtained
- [ ] Environment variables configured

### Database
- [ ] Migrations run successfully
- [ ] RPC Functions created (15 functions)
- [ ] Tables created
- [ ] RLS policies enabled

### Backend
- [ ] Dependencies installed
- [ ] Environment variables set
- [ ] Backend runs successfully
- [ ] Health check works
- [ ] API docs accessible

### Frontend
- [ ] Dependencies installed
- [ ] Environment variables set
- [ ] Frontend runs successfully
- [ ] Login page accessible

---

## 🎯 Test Scenarios

### Scenario 1: Basic Chat
1. Login
2. ส่งข้อความ: "ยอด lead วันนี้"
3. ตรวจสอบ response

### Scenario 2: Database Query
1. ส่งข้อความ: "สถานะ lead [ชื่อ lead]"
2. ตรวจสอบว่าเรียก RPC function
3. ตรวจสอบ response

### Scenario 3: Session Management
1. สร้าง session ใหม่
2. ส่งข้อความหลายข้อความ
3. สลับ session
4. ตรวจสอบ messages ถูกต้อง

### Scenario 4: Admin Functions
1. Login as admin
2. Upload document
3. View logs
4. Manage LINE linking

---

## 📊 Expected Results

### Backend
- ✅ Health check returns `{"status": "healthy"}`
- ✅ `/api/v1/chat` accepts POST requests
- ✅ Authentication works
- ✅ RPC functions called successfully

### Frontend
- ✅ Login page accessible
- ✅ Chat interface works
- ✅ Messages send/receive
- ✅ Sessions manage correctly

---

**Last Updated:** 2025-01-16  
**Status:** ✅ **READY FOR TESTING**
