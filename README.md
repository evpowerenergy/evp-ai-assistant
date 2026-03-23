# 🤖 AI Assistant - Internal AI Assistant & Knowledge Chatbot

> **Status:** ✅ Phase 3 Complete | Ready for Testing  
> **Version:** 0.1.0

---

## 📋 Overview

Internal AI Assistant & Knowledge Chatbot สำหรับ EV Power Energy ที่สามารถ:
- ตอบคำถามจาก **Database** (ผ่าน RPC functions)
- ตอบคำถามจาก **เอกสาร** (ผ่าน RAG)
- ควบคุมสิทธิ์ข้อมูลตาม role
- ใช้งานผ่าน **Web** และ **LINE**

---

## 🏗️ Architecture

```
Frontend (Next.js 14)
    ↓
Backend API (FastAPI)
    ↓
AI Orchestrator (LangGraph)
    ├─→ Database RPC Tools (15 functions)
    ├─→ Document RAG (pgvector)
    └─→ Intent Router
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Supabase account
- OpenAI API key

### 1. Setup Backend

```bash
cd backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your credentials

# Run migrations on Supabase
# (Use Supabase Dashboard or CLI)

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Setup environment variables
cp .env.example .env.local
# Edit .env.local with your credentials

# Start frontend
npm run dev
```

### 3. Access Application

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## 📁 Project Structure

```
evp-ai-assistant/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Auth, permissions, audit
│   │   ├── orchestrator/# LangGraph workflow
│   │   ├── services/    # Supabase, LLM, Vector Store
│   │   └── tools/       # DB, RAG, LINE tools
│   └── requirements.txt
├── frontend/             # Next.js 14 frontend
│   ├── src/
│   │   ├── app/         # Pages (App Router)
│   │   ├── components/  # React components
│   │   ├── hooks/       # Custom hooks
│   │   └── lib/         # Utilities
│   └── package.json
├── supabase/
│   └── migrations/      # Database migrations
└── docs/                # Documentation
```

---

## 🗄️ Database

### Migrations (4 files)
1. `20250116000001_initial_schema.sql` - Core tables
2. `20250116000003_ai_rpc_functions.sql` - Simple RPC functions (4)
3. `20250116000005_ai_rpc_functions_enhanced.sql` - Enhanced RPC functions (5)
4. `20250116000006_ai_rpc_functions_complete.sql` - Complete RPC functions (6)

### RPC Functions (15 functions)
- Simple: 4 functions
- Enhanced: 5 functions
- Complete: 6 functions

**Coverage:** ~67% (including partial)

---

## 🔧 Configuration

### Backend Environment Variables
```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
OPENAI_API_KEY=your_openai_api_key
CORS_ORIGINS=http://localhost:3000
```

**Production (Cloud Run + custom domain):** ตั้ง `CORS_ORIGINS` ให้รวม **origin ของหน้าเว็บจริง** (เช่น `https://assistant.evpowerenergy.com`) คั่นด้วย comma ร่วมกับ URL แบบ `*.run.app` ถ้ายังเปิดผ่าน URL เดิมได้ — ถ้าไม่ใส่ custom domain จะเกิด error แบบ *No `Access-Control-Allow-Origin` header* ในเบราว์เซอร์

### Frontend Environment Variables
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 📚 Documentation

- [Development Plan](./docs/DEVELOPMENT_PLAN.md) - Complete development plan
- [Getting Started](./docs/GETTING_STARTED.md) - Setup guide
- [Testing Guide](./docs/TESTING_GUIDE.md) - Testing instructions
- [RPC Functions Guide](./docs/RPC_FUNCTIONS_GUIDE.md) - RPC functions documentation
- [Phase 1 Complete](./docs/PHASE_1_COMPLETE.md) - Phase 1 summary
- [Phase 2 Progress](./docs/PHASE_2_PROGRESS.md) - Phase 2 status
- [Phase 3 Complete](./docs/PHASE_3_COMPLETE.md) - Phase 3 summary

---

## ✅ Current Status

### Phase 1: Foundation & Setup ✅
- Repository structure
- Backend foundation
- Frontend foundation
- Database migrations
- CI/CD workflows

### Phase 2: Backend Core ✅ (80%)
- Authentication & Authorization ✅
- Database RPC Tools ✅ (15 functions)
- AI Orchestration ✅
- Document RAG ✅
- API Endpoints ✅
- Audit & Logging ✅

### Phase 3: Frontend Core ✅
- Authentication UI ✅
- Chat Interface ✅
- Session Management ✅
- Admin Console ✅
- UI/UX Polish ✅

### Phase 4: LINE Integration ⏳
- LINE Webhook
- LINE User Linking
- LINE Notifications

### Phase 5: Testing & Polish ⏳
- Comprehensive testing
- Bug fixes
- Documentation

---

## 🧪 Testing

**Status:** ✅ Ready for Testing

**Quick Test:**
1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `npm run dev`
3. Login at http://localhost:3000
4. Send test message

**See:** [TESTING_GUIDE.md](./docs/TESTING_GUIDE.md)

---

## 📝 License

Internal use only - EV Power Energy

---

**Last Updated:** 2025-01-16  
**Status:** ✅ Ready for Testing
