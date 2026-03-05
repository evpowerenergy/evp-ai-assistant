# 🚀 Getting Started - AI Assistant Project

> **Quick Start Guide** สำหรับเริ่มพัฒนาโปรเจกต์

---

## ✅ สิ่งที่สร้างเสร็จแล้ว

### 1. โครงสร้าง Repository ✅
- ✅ Monorepo structure (`frontend/`, `backend/`, `docs/`)
- ✅ `.gitignore` สำหรับทั้ง FE และ BE
- ✅ CI/CD workflows (GitHub Actions)
- ✅ README files

### 2. Development Plan ✅
- ✅ Task breakdown ละเอียด (12 weeks)
- ✅ Phase-by-phase plan
- ✅ Backend-first strategy

### 3. Backend Foundation ✅
- ✅ FastAPI project structure
- ✅ `requirements.txt` (dependencies)
- ✅ Basic FastAPI app (`app/main.py`)
- ✅ Configuration (`app/config.py`)
- ✅ Dockerfile
- ✅ `.env.example`

### 4. Frontend Foundation ✅
- ✅ `package.json` (Next.js 14)
- ✅ Basic structure
- ✅ `.env.example`

---

## 📋 Next Steps (ตาม Development Plan)

### Phase 1: Foundation & Setup (Week 1-2)

#### Backend Setup (ทำต่อ)
```bash
cd backend

# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment variables
cp .env.example .env
# Edit .env with your credentials

# 4. Test run
uvicorn app.main:app --reload
# Should see: http://localhost:8000/health
```

#### Frontend Setup (ทำต่อ)
```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Copy environment variables
cp .env.example .env.local
# Edit .env.local with your credentials

# 3. Initialize Next.js (if needed)
# npx create-next-app@latest . --typescript --tailwind --app

# 4. Test run
npm run dev
# Should see: http://localhost:3000
```

---

## 🎯 Development Order (แนะนำ)

### Week 1-2: Foundation
1. ✅ Setup repository structure (Done)
2. ⏳ Complete Backend foundation
   - [ ] Add API route structure
   - [ ] Add logging setup
   - [ ] Add error handling
3. ⏳ Complete Frontend foundation
   - [ ] Initialize Next.js properly
   - [ ] Setup TailwindCSS + shadcn/ui
   - [ ] Create basic layout

### Week 3-5: Backend Core
1. Authentication & Authorization
2. Database RPC Tools
3. AI Orchestration (LangGraph)
4. Document RAG
5. API Endpoints

### Week 6-8: Frontend Core
1. Authentication UI
2. Chat Interface
3. Session Management
4. Admin Console (minimal)

### Week 9-10: LINE Integration
1. LINE Webhook
2. LINE User Linking
3. LINE Notifications

### Week 11-12: Testing & Polish
1. Testing
2. Bug fixes
3. Documentation
4. Deployment

---

## 🔧 Required Setup

### Prerequisites
- ✅ Node.js 18+
- ✅ Python 3.11+
- ⏳ Supabase account
- ⏳ OpenAI API key
- ⏳ LINE Messaging API credentials

### Environment Variables

**Backend** (`.env`):
```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
OPENAI_API_KEY=your_openai_api_key
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_line_access_token
```

**Frontend** (`.env.local`):
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 📚 Documentation

- [Development Plan](./DEVELOPMENT_PLAN.md) - Task breakdown ละเอียด
- [Repository Structure Decision](../REPO_STRUCTURE_DECISION.md) - Monorepo decision
- [Structure Analysis](../STRUCTURE_ANALYSIS.md) - โครงสร้างโปรเจกต์

---

## 🐛 Troubleshooting

### Backend Issues
- **Import errors**: Make sure virtual environment is activated
- **Port already in use**: Change port in `uvicorn` command
- **Missing dependencies**: Run `pip install -r requirements.txt`

### Frontend Issues
- **Module not found**: Run `npm install`
- **Port already in use**: Change port in `package.json` scripts
- **Build errors**: Check TypeScript configuration

---

## ✅ Checklist: Ready to Start Development

- [x] Repository structure created
- [x] Development plan documented
- [x] Backend foundation files created
- [x] Frontend foundation files created
- [ ] Backend dependencies installed
- [ ] Frontend dependencies installed
- [ ] Environment variables configured
- [ ] Backend runs successfully (`/health` endpoint)
- [ ] Frontend runs successfully (dev server)

---

**Last Updated:** 2025-01-16  
**Status:** 🟢 Ready for Phase 1 Development
