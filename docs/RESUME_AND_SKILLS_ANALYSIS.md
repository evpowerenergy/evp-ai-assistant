# 📋 EVP AI Assistant — วิเคราะห์โปรเจ็คสำหรับ Resume & สัมภาษณ์

> เอกสารนี้สรุป Architecture, การออกแบบ โค้ด และทักษะที่ได้จากโปรเจ็ค **evp-ai-assistant** เพื่อใช้เขียน Resume และเตรียมตอบคำถามสัมภาษณ์ (ทำคนเดียวทั้งโปรเจ็ค)

---

## 1. สรุปโปรเจ็คในหนึ่งบรรทัด (Elevator Pitch)

**Internal AI Assistant & Knowledge Chatbot** ที่ตอบคำถามจากทั้ง **Database** (ผ่าน Supabase RPC 15+ ฟังก์ชัน) และ **เอกสาร** (RAG + pgvector) มี **Role-Based Access Control** และ PII masking ใช้งานผ่าน Web และ LINE — สร้างด้วย **Next.js 14 + FastAPI + LangGraph + OpenAI**

---

## 2. สถาปัตยกรรม (Architecture)

### 2.1 High-Level

```
User (Web / LINE)
    ↓
Frontend (Next.js 14, App Router, TypeScript)
    ↓  REST API + JWT
Backend (FastAPI, Python 3.12)
    ↓
AI Orchestrator (LangGraph)
    ├─ Stage 1: Intent + Tool Selection (OpenAI Function Calling)
    ├─ Router: db_query | rag_query | clarify | general
    ├─ DB path → Supabase RPC (15+ functions)
    ├─ RAG path → pgvector, embeddings
    └─ Stage 4: Generate Response (LangChain ChatOpenAI)
Supabase: Auth, PostgreSQL, RPC, pgvector
```

### 2.2 Tech Stack (สำหรับ Resume)

| Layer | Technologies |
|-------|--------------|
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Supabase Auth, TanStack React Query, Axios, Zod |
| **Backend** | FastAPI, Pydantic, Uvicorn, Python 3.12 |
| **AI/LLM** | LangGraph (orchestration), LangChain (ChatOpenAI), OpenAI API (function calling) |
| **Database** | Supabase (PostgreSQL), pgvector (vector search), 15+ RPC functions |
| **Auth & Security** | Supabase Auth, JWT, RBAC, PII masking, rate limiting |
| **DevOps** | Docker (multi-stage), GitHub Actions, Google Cloud Run (asia-southeast1) |

### 2.3 จุดเด่นทางสถาปัตยกรรม

- **Single repo, two deployable services**: Frontend และ Backend แยก deploy (path-based trigger ใน CI)
- **LangGraph workflow**: State machine ชัดเจน (state.py), conditional routing ตาม intent
- **Hybrid AI pipeline**: Intent → Tool selection (OpenAI) → Execute (RPC / RAG) → Generate (LangChain)
- **RPC-first data layer**: ข้อมูลจาก CRM ผ่าน Supabase RPC เท่านั้น ไม่ expose table โดยตรง

---

## 3. การออกแบบและเขียนโค้ด (Design & Code Quality)

### 3.1 โครงสร้าง Backend

- **api/v1/** — REST endpoints (chat, health, ingest, line, me, config, prompt_tests)
- **core/** — auth (JWT), permissions, audit, rate_limit
- **orchestrator/** — graph.py (LangGraph), state, llm_router, nodes (db_query, rag_query, clarify, generate_response, verifiers, result_grader, rpc_planner)
- **services/** — Supabase, LLM, vector_store, embedding, chat_history, line
- **tools/** — db_tools, rag_tools, line_tools
- **utils/** — exceptions, logger, pii_masker, date_extractor, system_prompt
- **middleware/** — rate_limit_middleware

### 3.2 โครงสร้าง Frontend

- **app/** — App Router (dashboard, admin, auth)
- **components/** — UI components
- **hooks/** — useChat, auth
- **lib/** — api client (Axios), Supabase

### 3.3 Design Patterns ที่ใช้

- **TypedDict state** (AIAssistantState) สำหรับ LangGraph
- **Custom exceptions** (AuthenticationError, PermissionDeniedError, NotFoundError, ValidationError, RateLimitError) + FastAPI handler
- **Dependency Injection** — get_current_user, role จาก JWT หรือ /api/v1/me
- **Interceptor** — Axios request/response (token, 401 → redirect login)
- **Structured logging** (structlog)

### 3.4 Security & Compliance

- **RBAC**: admin / manager / staff — จำกัดข้อมูลตาม role
- **PII masking**: เบอร์โทร, Line ID mask ใน RPC สำหรับ non-admin
- **JWT**: Bearer token, validate ใน backend
- **Rate limiting**: middleware ใน FastAPI
- **Audit**: audit log สำหรับการใช้งาน

---

## 4. วิธีเขียนใส่ Resume

### 4.1 ชื่อโปรเจ็คและบทบาท

- **Project name:** Internal AI Assistant & Knowledge Chatbot (EVP)
- **Role:** Full-stack Developer (Solo / Individual Project)
- **Duration:** ตามจริงที่ทำ (เช่น 3–6 months)

### 4.2 คำอธิบายโปรเจ็ค (Project Description) — 2–4 บรรทัด

**แบบสั้น (2 บรรทัด):**

> Built an internal AI assistant that answers questions from both **CRM database** (via 15+ Supabase RPCs) and **documents** (RAG with pgvector). Implemented **LangGraph** orchestration with OpenAI function calling for tool selection, **role-based access control** with PII masking, streaming chat on **Next.js 14** and **FastAPI**, and **CI/CD** to **Google Cloud Run**.

**แบบยาว (4 บรรทัด):**

> Developed a full-stack **AI chatbot** for internal use: **Next.js 14** (App Router, TypeScript) frontend and **FastAPI** backend with **LangGraph** orchestration. The system routes user intents via **OpenAI function calling**, then executes **Supabase RPC** (15+ functions) for DB queries or **pgvector** for document RAG. Implemented **RBAC** (admin/manager/staff) with PII masking in RPC layer, **JWT auth**, rate limiting, and streaming responses. Deployed frontend and backend separately to **Google Cloud Run** via **GitHub Actions**; optional **LINE** integration.

### 4.3 Bullet Points สำหรับ Resume (เลือก 4–6 ข้อ)

- Designed and implemented **LangGraph** workflow (intent routing, tool selection, DB/RAG execution, response generation) with **OpenAI** function calling and **LangChain**.
- Built **15+ Supabase RPC functions** for CRM data access; documented coverage, date support, and tool-selection behavior in technical docs.
- Implemented **RAG** over internal documents using **pgvector** and embeddings; integrated with orchestrator for hybrid DB + document answers.
- Enforced **role-based access control** and **PII masking** (phone, Line ID) at database RPC layer for admin/manager/staff roles.
- Developed **Next.js 14** chat UI with streaming, session history, and **FastAPI** backend with JWT auth, rate limiting, and audit logging.
- Set up **CI/CD** with **GitHub Actions** (path-based triggers) and **Docker**; deployed frontend and backend to **Google Cloud Run** with secrets management.

### 4.4 Skills / Keywords ที่ควรใส่ใน Resume

**Frontend:** Next.js 14, React 18, TypeScript, Tailwind CSS, TanStack React Query, Axios, Zod, Supabase Auth  

**Backend:** FastAPI, Python 3.12, Pydantic, Uvicorn  

**AI/ML:** LangGraph, LangChain, OpenAI API, Function Calling, RAG, Embeddings, pgvector  

**Database:** PostgreSQL, Supabase, RPC, SQL Migrations  

**Security:** JWT, RBAC, PII Masking, Rate Limiting  

**DevOps:** Docker, GitHub Actions, Google Cloud Run  

**Soft:** Technical documentation, solo full-stack delivery, API design

---

## 5. ทักษะที่ได้จากโปรเจ็คนี้ (Skills Gained)

### 5.1 Full-Stack

- ออกแบบและพัฒนา **REST API** (FastAPI) รวมถึง streaming endpoint
- พัฒนา **SPA** ด้วย Next.js App Router, จัดการ auth และ state
- ใช้ **TypeScript** (strict) และ **Pydantic** สำหรับ type safety ข้าม frontend–backend

### 5.2 AI/LLM

- ใช้ **LangGraph** สำหรับ state machine และ conditional routing
- ใช้ **OpenAI function calling** สำหรับ intent และ tool selection
- ผสม **RAG** (embedding + pgvector) กับ **structured data** (RPC) ใน pipeline เดียว
- ออกแบบ system prompt และ tool definitions ให้ LLM เลือก tool ได้ตรง

### 5.3 Data & Backend

- ออกแบบ **RPC layer** บน PostgreSQL/Supabase แทนการ expose table โดยตรง
- เขียน **migrations** และดูแล schema
- ใช้ **pgvector** สำหรับ vector search

### 5.4 Security & Compliance

- ออกแบบ **RBAC** และ implement ใน RPC (CASE WHEN ตาม role)
- **PII masking** ใน SQL และออกแบบให้สอดคล้องกับ role
- ใช้ **JWT** และ dependency injection สำหรับ auth ใน FastAPI

### 5.5 DevOps & Tooling

- **Docker**: Dockerfile สำหรับ backend (Python) และ frontend (Node, multi-stage)
- **GitHub Actions**: แยก workflow ตาม path (backend/** / frontend/**), deploy ไป Cloud Run
- จัดการ **secrets** ใน CI และ env ใน Cloud Run

### 5.6 Documentation & Design

- เขียน docs หลายฉบับ: สถาปัตยกรรม, RPC coverage, tool selection, RBAC, role-fetching comparison
- ออกแบบ flow และ state ให้ชัดก่อน implement

---

## 6. คำถามสัมภาษณ์ที่อาจถูกถาม และแนวตอบสั้นๆ

- **ทำไมใช้ LangGraph ไม่ใช้แค่ LangChain?**  
  ต้องการ workflow ชัดเจน มี state, routing ตาม intent และขั้นตอนย่อย (tool verifier, result grader) LangGraph ให้ state machine และ conditional edges ที่จัดการง่าย

- **ทำไมใช้ RPC แทนให้ backend query table โดยตรง?**  
  ควบคุมสิทธิ์และ PII ที่ layer เดียว (ใน DB), ลด logic ใน app และให้ reuse ได้จาก client อื่น (เช่น LINE)

- **PII masking ทำที่ไหน?**  
  ใน RPC ผ่าน `CASE WHEN p_user_role = 'admin' THEN tel ELSE NULL END` เพื่อไม่ให้ non-admin เห็นเบอร์โทร/Line ID

- **Streaming ทำยังไง?**  
  Frontend เรียก `POST /api/v1/chat/stream` แล้วอ่าน stream ด้วย fetch; Backend yield chunk จาก LangChain/LangGraph ไปยัง client

- **Role มาจากไหน?**  
  จาก JWT `user_metadata.role` หรือ fallback ไปเรียก `/api/v1/me` (มี doc เปรียบเทียบ DB vs JWT เรื่อง latency และ consistency)

---

## 7. สรุปหนึ่งหน้ากระดาษ

| หัวข้อ | สรุป |
|--------|------|
| **โปรเจ็ค** | Internal AI Assistant — ตอบจาก DB (RPC) + เอกสาร (RAG), RBAC, Web + LINE |
| **Stack** | Next.js 14, FastAPI, LangGraph, LangChain, OpenAI, Supabase, pgvector, Docker, GCP Cloud Run |
| **บทบาท** | Full-stack (solo): design, backend, frontend, RPC, RAG, auth, RBAC, CI/CD, docs |
| **จุดเด่น** | LangGraph pipeline, 15+ RPCs, RAG+DB hybrid, RBAC + PII ใน DB, streaming, deploy แยก front/back |
| **Skills สำหรับ Resume** | Full-stack, AI/LLM (LangGraph, RAG, function calling), PostgreSQL/Supabase, Security (JWT, RBAC, PII), DevOps (Docker, GitHub Actions, Cloud Run), Documentation |

ถ้าต้องการให้ช่วยเขียนเป็นประโยคภาษาไทยสำหรับ resume หรือปรับ bullet ให้สั้น/ยาวตามพื้นที่ใน CV บอกได้เลยครับ
