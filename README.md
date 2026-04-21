# EVP AI Assistant

Internal AI Assistant and knowledge chatbot for EV Power Energy.  
The system serves authorized internal users with role-based access, combines database RPC tools and document RAG, and provides a web-first experience with LINE integration planned as a follow-up phase.

## Product Snapshot

- **Project:** `evp-ai-assistant`
- **Version:** `0.1.0`
- **Primary Channel:** Web app (Next.js + FastAPI)
- **Core Capabilities:** CRM data Q&A (RPC), document Q&A (RAG), sessioned chat, audit logging
- **Current Maturity:** Internal-use deployment with production infrastructure on Cloud Run

## Why This Project Exists

EVP AI Assistant is designed to reduce time spent finding business information by:

- answering data questions from CRM via controlled RPC tools
- answering policy/process questions from internal documents using vector search
- enforcing role-based access control for AI features
- logging important AI usage events for auditability

## High-Level Architecture

```text
Browser (Next.js Frontend)
  -> FastAPI Backend (Auth, API, Orchestrator)
     -> LangGraph Workflow (intent -> tools -> response)
        -> Supabase RPC (CRM data)
        -> Supabase pgvector (RAG)
        -> OpenAI (generation + reasoning)
```

Key architectural principles:

- Frontend uses Supabase anon credentials only.
- Backend holds Supabase service role and OpenAI API key.
- All AI business-data access is mediated through allowlisted backend tools.

## Core Features

- **Authentication and authorization**
  - Supabase login flow
  - Backend role check via allowed roles list
- **Chat orchestration**
  - Intent routing (database, rag, clarify, general)
  - Sync and SSE streaming chat endpoints
  - Session and message history
- **Database intelligence**
  - RPC-based tool execution against CRM data
  - Controlled tool surface via backend allowlist
- **Document intelligence (RAG)**
  - Document ingest pipeline
  - Embedding + vector retrieval with pgvector
- **Admin operations**
  - Document ingestion flows
  - Prompt testing and logs support surfaces

## Technology Stack

- **Frontend:** Next.js 14, React 18, TypeScript, Tailwind
- **Backend:** Python 3.12, FastAPI, Uvicorn, LangGraph/LangChain
- **Data platform:** Supabase (PostgreSQL, Auth, RPC, pgvector)
- **LLM provider:** OpenAI
- **Deployment target:** Google Cloud Run (frontend and backend)

## Repository Structure

```text
evp-ai-assistant/
├── backend/                  # FastAPI app + orchestrator + tools
├── frontend/                 # Next.js app (App Router)
├── supabase/migrations/      # DB schema and RPC migrations
├── docs/                     # Product and technical documents
├── scripts/                  # Deployment scripts
└── .github/workflows/        # CI/CD workflows
```

## Prerequisites

- Python 3.12+
- Node.js 18+
- Supabase project with required tables/RPC/migrations
- OpenAI API key

## Local Development Quick Start

### 1) Backend setup

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# update .env values
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend setup

```bash
cd frontend
npm install
cp .env.example .env.local
# update .env.local values
npm run dev
```

### 3) Open local services

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Environment Variables

### Backend (`backend/.env`)

```env
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
OPENAI_API_KEY=...
OPENAI_MODEL=...
AI_ASSISTANT_ALLOWED_ROLES=super_admin,manager_sale,manager_marketing,manager_hr
CORS_ORIGINS=http://localhost:3000
```

### Frontend (`frontend/.env.local`)

```env
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Production note:

- Set `CORS_ORIGINS` to include the real frontend origin(s), including custom domain and any active Cloud Run domain used by clients.
- `NEXT_PUBLIC_*` values are embedded at build time; changing them requires rebuilding frontend image.

## Security Notes

- Do not commit secrets; use env vars / secret manager / CI secrets.
- Keep Supabase service role key on backend only.
- Current auth flow validates expiry and resolves user role from DB.
- JWT signature verification against JWKS is an improvement item for hardening.
- Current rate limiting is in-memory per instance, not distributed global throttling.

## Deployment Summary

- **Backend:** Cloud Build -> Cloud Run (see `cloudbuild-backend.yaml`, `scripts/deploy-backend.sh`)
- **Frontend:** Cloud Build -> Cloud Run (see `frontend/cloudbuild.yaml`, `scripts/deploy-frontend.sh`)
- **Runtime config template:** `env.cloudrun.example`
- **Detailed guide:** `docs/CLOUD_DEPLOY.md`

## API Surface (Important Endpoints)

- `POST /api/v1/chat`
- `POST /api/v1/chat/stream`
- `GET /api/v1/chat/history/{session_id}`
- `POST /api/v1/ingest`
- `GET /api/v1/me`
- `GET /api/v1/health`

## Testing

- Backend unit/integration: `pytest` (see `backend/tests` and `backend/pytest.ini`)
- Smoke test flow:
  1. start backend and frontend
  2. log in with allowed role
  3. send chat prompts for DB and RAG scenarios
  4. verify response, steps, and citations

## Known Scope Boundaries

- LINE webhook path exists but full production-grade LINE integration is still partial.
- Distributed/global rate limiting is not yet implemented.
- Security hardening around JWT cryptographic verification is tracked as future work.

## Documentation Index

- `docs/PRD.md` - Product requirements and scope
- `docs/TECHNICAL_ARCHITECTURE.md` - Technical architecture and module flow
- `docs/CLOUD_DEPLOY.md` - Cloud Run deployment guide
- `docs/GETTING_STARTED.md` - Environment setup
- `docs/TESTING_GUIDE.md` - Testing scenarios and checklist
- `docs/RPC_FUNCTIONS_GUIDE.md` - RPC tool references

## Roadmap (Current Direction)

- **Phase 1-3:** foundation, core backend, core frontend - completed for internal use
- **Phase 4:** complete LINE integration
- **Phase 5:** hardening, broader testing, operational polish

## License

Internal use only - EV Power Energy.

---

Last updated: 2026-04
