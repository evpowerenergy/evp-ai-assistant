# 📋 Development Plan: Internal AI Assistant & Knowledge Chatbot

> **Version:** 1.0  
> **Last Updated:** 2025-01-16  
> **Based on:** PRD v1.1

---

## 🎯 Executive Summary

**Project:** Internal AI Assistant & Knowledge Chatbot  
**Architecture:** Monorepo (Frontend + Backend)  
**Deployment:** GCP Cloud Run (2 separate services)  
**Timeline:** Phase 1 (MVP) - 8-12 weeks

**Development Strategy:** **Backend-First** approach
- ✅ Start with Backend (API foundation)
- ✅ Then Frontend (consume API)
- ✅ Parallel development possible after API contracts defined

---

## 📊 Development Phases

### Phase 1: Foundation & Setup (Week 1-2)

**Goal:** Setup project structure, infrastructure, and basic configurations

#### Tasks:

**1.1 Repository Setup** ✅
- [x] Create monorepo structure
- [x] Setup `.gitignore`
- [x] Create README files
- [x] Setup workspace configuration

**1.2 Backend Foundation** ✅
- [x] Initialize FastAPI project
- [x] Setup project structure (`app/`, `tests/`, `scripts/`)
- [x] Configure dependencies (`requirements.txt`) - Python 3.12
- [x] Setup environment variables (`.env.example`)
- [x] Create basic FastAPI app with health check
- [x] Setup logging (structured logging)
- [x] Create Dockerfile for Cloud Run
- [x] Create API routes structure (chat, line, ingest, health)
- [x] Create core modules (auth, permissions, audit)
- [x] Create services (supabase, llm, embedding, vector_store, line)
- [x] Create tools (db_tools, rag_tools, line_tools)
- [x] Create orchestrator structure (LangGraph workflow)
- [x] Create utilities (logger, exceptions, pii_masker)

**1.3 Frontend Foundation** ✅
- [x] Initialize Next.js 14+ project (App Router)
- [x] Setup project structure (`src/app/`, `src/components/`, etc.)
- [x] Configure dependencies (`package.json`)
- [x] Setup TypeScript configuration
- [x] Setup TailwindCSS
- [x] Create basic layout and routing
- [x] Create Dockerfile for Cloud Run
- [x] Create lib utilities (supabase client, API client)
- [x] Create basic pages (home, login, chat)

**1.4 Database Setup** ✅
- [x] Create Supabase migration files
- [x] Create tables: `chat_sessions`, `chat_messages`, `audit_logs`
- [x] Create tables: `kb_documents`, `kb_chunks` (pgvector)
- [x] Create table: `line_identities`
- [x] Setup RLS policies
- [x] Create initial RPC functions (3 functions - placeholder)
  - `ai_get_lead_status`
  - `ai_get_daily_summary`
  - `ai_get_customer_info`

**1.5 CI/CD Setup** ✅
- [x] Create GitHub Actions workflows
- [x] Setup path-based triggers (frontend/**, backend/**)
- [x] Configure Cloud Run deployment
- [x] Update Python version to 3.12

---

### Phase 2: Backend Core (Week 3-5)

**Goal:** Build core backend functionality - API, Auth, AI Orchestration

#### 2.1 Authentication & Authorization
- [x] Implement Supabase Auth validation ✅
- [x] Create auth middleware ✅
- [x] Implement role-based access control (RBAC) ✅
- [x] Create permission checking utilities ✅
- [ ] Implement PII masking utilities (structure ready)
- [ ] Write tests for auth flow

**2.2 Database RPC Tools**
- [x] Design RPC allowlist (15 functions) ✅
- [x] Create RPC functions on Supabase (3 migration files) ✅:
  - [x] `ai_get_lead_status(lead_name, user_id)` ✅
  - [x] `ai_get_daily_summary(user_id, date)` ✅
  - [x] `ai_get_customer_info(customer_name, user_id)` ✅
  - [x] `ai_get_team_kpi(user_id, team_id)` ✅
  - [x] Enhanced functions (5 functions) ✅
  - [x] Complete functions (6 functions) ✅
- [x] Implement RPC tools in Python (`app/tools/db_tools.py`) ✅
- [x] Add RLS and permission checks to all RPCs ✅
- [ ] Write tests for RPC tools

**2.3 AI Orchestration (LangGraph)**
- [x] Setup LangChain + LangGraph ✅
- [x] Create LangGraph workflow structure ✅
- [x] Implement Intent Router ✅:
  - [x] Detect if question needs DB query ✅
  - [x] Detect if question needs RAG ✅
  - [x] Detect if clarification needed ✅
- [x] Create graph nodes ✅:
  - [x] `db_query_node` - Call DB RPC tools ✅
  - [x] `rag_query_node` - Search documents ✅
  - [x] `clarify_node` - Ask for clarification ✅
  - [x] `generate_response_node` - Generate final response ✅
- [x] Implement state management ✅
- [ ] Write tests for orchestration

**2.4 Document RAG**
- [x] Setup pgvector extension (in migrations) ✅
- [x] Implement document ingestion (structure ready) ✅:
  - [x] Chunk documents ✅
  - [x] Generate embeddings (OpenAI) ✅
  - [x] Store in `kb_chunks` table ✅
- [x] Implement vector search ✅
- [x] Implement citation extraction ✅
- [ ] Write tests for RAG

**2.5 API Endpoints**
- [x] `POST /chat` - Main chat endpoint ✅
- [ ] `POST /line/webhook` - LINE webhook (structure ready)
- [ ] `POST /ingest` - Document ingestion (admin) (structure ready)
- [x] `GET /health` - Health check ✅
- [x] Implement request/response models (Pydantic) ✅
- [x] Add error handling ✅
- [x] Add rate limiting ✅
- [ ] Write API tests

**2.6 Audit & Logging**
- [x] Implement audit logging ✅
- [x] Log all requests/tool calls ✅
- [x] Implement PII redaction in logs (structure ready) ✅
- [ ] Create audit log viewer (basic)

---

### Phase 3: Frontend Core (Week 6-8)

**Goal:** Build frontend UI - Chat interface, Auth, Admin

#### 3.1 Authentication UI
- [x] Create login page ✅
- [x] Implement Supabase Auth (client-side) ✅
- [x] Create auth context/hooks ✅
- [x] Implement protected routes ✅
- [x] Create user profile component ✅
- [x] Implement logout ✅

**3.2 Chat Interface**
- [x] Create chat page layout ✅
- [x] Implement chat UI components ✅:
  - [x] `ChatInterface` - Main container ✅
  - [x] `MessageList` - Message display ✅
  - [x] `MessageBubble` - Individual message ✅
  - [x] `CitationBadge` - Show sources ✅
  - [x] `FeedbackButtons` - Thumbs up/down ✅
  - [x] `SessionSidebar` - Session list ✅
- [x] Implement chat state management ✅
- [x] Connect to backend `/chat` API ✅
- [ ] Implement message streaming (optional for Phase 4)
- [x] Add loading states ✅
- [x] Add error handling ✅

**3.3 Session Management**
- [x] Implement session creation ✅
- [x] Load session history ✅
- [x] Switch between sessions ✅
- [x] Delete sessions ✅
- [x] Persist sessions in database ✅

**3.4 Admin Console (Minimal)**
- [x] Create admin layout ✅
- [x] Document upload page ✅
- [x] Log viewer page (basic) ✅
- [x] LINE linking page ✅
- [x] Add admin-only routes ✅

**3.5 UI/UX Polish**
- [x] Responsive design (mobile + desktop) ✅
- [x] Loading skeletons ✅
- [x] Error messages ✅
- [x] Success notifications ✅
- [x] Accessibility improvements ✅

---

### Phase 4: LINE Integration (Week 9-10)

**Goal:** Integrate LINE OA for quick Q&A and notifications

#### 4.1 LINE Webhook
- [ ] Setup LINE Messaging API
- [ ] Implement webhook signature verification
- [ ] Handle LINE events (text, follow, unfollow)
- [ ] Connect to backend `/line/webhook`
- [ ] Implement quick Q&A flow
- [ ] Handle long answers (link to Web)

#### 4.2 LINE User Linking
- [ ] Implement LINE user ↔ app user linking
- [ ] Create linking flow in admin console
- [ ] Store in `line_identities` table
- [ ] Handle unlink

#### 4.3 LINE Notifications
- [ ] Implement notification triggers
- [ ] Send notifications (lead new, exceptions)
- [ ] Add deep links to Web
- [ ] Test notification flow

---

### Phase 5: Testing & Polish (Week 11-12)

**Goal:** Comprehensive testing, bug fixes, and documentation

#### 5.1 Testing
- [ ] Backend unit tests (coverage > 80%)
- [ ] Backend integration tests
- [ ] Frontend unit tests
- [ ] Frontend E2E tests (Playwright/Cypress)
- [ ] Security testing
- [ ] Performance testing

#### 5.2 Bug Fixes
- [ ] Fix critical bugs
- [ ] Fix high-priority bugs
- [ ] Fix medium-priority bugs
- [ ] Code review and refactoring

#### 5.3 Documentation
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Frontend component documentation
- [ ] Deployment guides
- [ ] User guides
- [ ] Developer guides

#### 5.4 Deployment
- [ ] Setup production Cloud Run services
- [ ] Configure production environment variables
- [ ] Setup monitoring and alerts
- [ ] Performance optimization
- [ ] Security audit

---

## 🚀 Development Order: Backend-First Strategy

### Why Backend-First?

1. **API Contracts** - Frontend ต้องรู้ API structure
2. **Core Logic** - AI orchestration, RAG, DB access อยู่ที่ backend
3. **Testing** - Backend test ได้ง่ายกว่า (no UI)
4. **Parallel Development** - หลังจาก API contracts ชัดเจน, FE/BE ทำพร้อมกันได้

### Recommended Sequence:

```
Week 1-2: Foundation (Both FE + BE setup)
    ↓
Week 3-5: Backend Core (API, Auth, AI, RAG)
    ↓
Week 6-8: Frontend Core (UI, Chat, Admin)
    ↓
Week 9-10: LINE Integration (Backend + Frontend)
    ↓
Week 11-12: Testing & Polish
```

### Parallel Development Opportunities:

- **Week 6-8:** Frontend ทำงานพร้อมกับ Backend refinement
- **Week 9-10:** LINE integration (backend + frontend) ทำพร้อมกันได้

---

## 📝 Task Breakdown by Component

### Backend Tasks

#### Core (`app/core/`)
- [x] `auth.py` - Auth validation, permission checks (structure ready, implementation in Phase 2)
- [x] `permissions.py` - RBAC logic, PII masking (structure ready)
- [x] `audit.py` - Audit logging (structure ready)

#### API (`app/api/v1/`)
- [x] `chat.py` - POST /chat (structure ready, implementation in Phase 2)
- [x] `line.py` - POST /line/webhook (structure ready, implementation in Phase 4)
- [x] `ingest.py` - POST /ingest (structure ready, implementation in Phase 2)
- [x] `health.py` - GET /health ✅ Complete

#### Orchestrator (`app/orchestrator/`)
- [x] `graph.py` - LangGraph workflow (structure ready, implementation in Phase 2)
- [x] `router.py` - Intent router (basic implementation ready)
- [ ] `nodes/db_query.py` - DB tool node (Phase 2)
- [ ] `nodes/rag_query.py` - RAG node (Phase 2)
- [ ] `nodes/clarify.py` - Clarification node (Phase 2)
- [x] `state.py` - Graph state types ✅ Complete

#### Tools (`app/tools/`)
- [x] `db_tools.py` - Database RPC tools (structure ready, 3 placeholder functions, expand in Phase 2)
- [x] `rag_tools.py` - Document RAG tools (structure ready, implementation in Phase 2)
- [x] `line_tools.py` - LINE notification tools (structure ready, implementation in Phase 4)

#### Services (`app/services/`)
- [x] `supabase.py` - Supabase client ✅ Complete
- [x] `vector_store.py` - pgvector operations (structure ready, implementation in Phase 2)
- [x] `embedding.py` - Text embedding (OpenAI) ✅ Complete
- [x] `llm.py` - LLM client (OpenAI) ✅ Complete
- [x] `line.py` - LINE Messaging API client (structure ready, implementation in Phase 4)

### Frontend Tasks

#### Pages (`src/app/`)
- [ ] `(auth)/login/page.tsx` - Login page
- [ ] `(auth)/callback/page.tsx` - Auth callback
- [ ] `(dashboard)/chat/page.tsx` - Main chat page
- [ ] `(dashboard)/chat/[sessionId]/page.tsx` - Session page
- [ ] `(dashboard)/admin/documents/page.tsx` - Document upload
- [ ] `(dashboard)/admin/logs/page.tsx` - Log viewer
- [ ] `(dashboard)/admin/line/page.tsx` - LINE linking

#### Components (`src/components/`)
- [ ] `chat/ChatInterface.tsx`
- [ ] `chat/MessageList.tsx`
- [ ] `chat/MessageBubble.tsx`
- [ ] `chat/CitationBadge.tsx`
- [ ] `chat/FeedbackButtons.tsx`
- [ ] `chat/SessionSidebar.tsx`
- [ ] `admin/DocumentUpload.tsx`
- [ ] `admin/LogViewer.tsx`
- [ ] `admin/LineLinking.tsx`

#### Hooks (`src/hooks/`)
- [ ] `useChat.ts` - Chat state management
- [ ] `useAuth.ts` - Auth state
- [ ] `useSession.ts` - Session management
- [ ] `useLine.ts` - LINE integration

#### Lib (`src/lib/`)
- [x] `supabase/client.ts` - Supabase client ✅ Complete
- [ ] `supabase/auth.ts` - Auth helpers (Phase 3)
- [x] `api/client.ts` - Backend API client ✅ Complete
- [ ] `api/types.ts` - API types (Phase 3)

---

## 🗄️ Database Tasks

### Tables to Create

1. **`chat_sessions`**
   - `id` (uuid, PK)
   - `user_id` (uuid, FK)
   - `title` (text)
   - `created_at` (timestamp)
   - `updated_at` (timestamp)

2. **`chat_messages`**
   - `id` (uuid, PK)
   - `session_id` (uuid, FK)
   - `role` (enum: user, assistant, system)
   - `content` (text)
   - `metadata` (jsonb) - citations, tool calls
   - `created_at` (timestamp)

3. **`audit_logs`**
   - `id` (uuid, PK)
   - `user_id` (uuid, FK)
   - `action` (text)
   - `resource` (text)
   - `request_data` (jsonb, redacted)
   - `response_data` (jsonb, redacted)
   - `created_at` (timestamp)

4. **`kb_documents`**
   - `id` (uuid, PK)
   - `title` (text)
   - `file_path` (text)
   - `file_type` (text)
   - `uploaded_by` (uuid, FK)
   - `created_at` (timestamp)

5. **`kb_chunks`**
   - `id` (uuid, PK)
   - `document_id` (uuid, FK)
   - `content` (text)
   - `embedding` (vector) - pgvector
   - `chunk_index` (int)
   - `metadata` (jsonb)
   - `created_at` (timestamp)

6. **`line_identities`**
   - `id` (uuid, PK)
   - `user_id` (uuid, FK)
   - `line_user_id` (text, unique)
   - `linked_at` (timestamp)

### RPC Functions to Create (Priority Order)

**Priority 1 (Core):**
1. `ai_get_lead_status(lead_name, user_id)` - Get lead status
2. `ai_get_daily_summary(user_id, date)` - Daily summary
3. `ai_get_customer_info(customer_name, user_id)` - Customer info

**Priority 2 (Extended):**
4. `ai_get_team_kpi(team_id, user_id)` - Team KPI
5. `ai_get_sales_performance(sales_id, user_id, period)` - Sales performance
6. `ai_get_inventory_status(product_name, user_id)` - Inventory status
7. `ai_get_appointments(user_id, date)` - Appointments

**Priority 3 (Advanced):**
8. `ai_search_leads(query, user_id, filters)` - Search leads
9. `ai_get_reports(report_type, user_id, period)` - Reports
10. `ai_get_notifications(user_id, limit)` - Notifications

---

## ✅ Acceptance Criteria (Phase 1 MVP)

### Functional
- [ ] User can login via Supabase Auth
- [ ] User can chat via Web interface
- [ ] AI can answer questions from Database (via RPC)
- [ ] AI can answer questions from Documents (via RAG)
- [ ] Citations are shown for document answers
- [ ] User can provide feedback (thumbs up/down)
- [ ] LINE webhook receives and processes messages
- [ ] Admin can upload documents
- [ ] Admin can view audit logs

### Non-Functional
- [ ] Response time < 6-8s (median)
- [ ] All DB access goes through RPC (no raw SQL)
- [ ] RLS policies enforced
- [ ] PII masked in logs
- [ ] Audit logs capture all requests
- [ ] Frontend and Backend deploy separately to Cloud Run

---

## 📚 Documentation Deliverables

- [ ] `README.md` - Project overview
- [ ] `docs/DEVELOPMENT_PLAN.md` - This document
- [ ] `docs/API.md` - API documentation
- [ ] `docs/DEPLOYMENT.md` - Deployment guide
- [ ] `docs/ARCHITECTURE.md` - Architecture overview
- [ ] `docs/CONTRIBUTING.md` - Contributing guide

---

## 🔄 Next Steps

1. **Review this plan** with team
2. **Prioritize tasks** based on business needs
3. **Assign owners** to each phase
4. **Start Phase 1** - Foundation & Setup
5. **Daily standups** to track progress

---

**Last Updated:** 2025-01-16  
**Status:** ✅ Phase 3 Complete | Ready for Phase 4: LINE Integration

---

## 📊 Phase 1 Status Summary

### ✅ Phase 1: Foundation & Setup - **COMPLETE**

**Completion Date:** 2025-01-16

**Summary:**
- ✅ Repository structure (Monorepo)
- ✅ Backend foundation (FastAPI + Python 3.12)
- ✅ Frontend foundation (Next.js 14)
- ✅ Database migrations (Supabase)
- ✅ CI/CD workflows (GitHub Actions)

**Key Achievements:**
- Complete project structure with all modules
- API routes structure ready
- Core modules (auth, permissions, audit) foundation ready
- Services (Supabase, LLM, Embeddings) ready
- Tools structure (DB, RAG, LINE) ready
- Database schema with RLS policies
- Initial RPC functions (3 placeholder functions)

**Next Phase:** Phase 2 - Backend Core (Week 3-5)

See [PHASE_1_COMPLETE.md](./PHASE_1_COMPLETE.md) for detailed completion report.
