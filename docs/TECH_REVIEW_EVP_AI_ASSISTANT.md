# ทบทวน Technical Terms + สถาปัตยกรรม โปรเจกต์ EV Power AI Assistant

เอกสารนี้อธิบายศัพท์เทคนิค สถาปัตยกรรม และ Tech Stack ของโปรเจกต์ **EV Power AI Assistant** (Internal AI Assistant & Knowledge Chatbot) พร้อมยกตัวอย่างโค้ดจริง เพื่อใช้ในการนำเสนอและอธิบายโปรเจกต์แบบครบถ้วน

---

## สรุปภาพรวมโปรเจกต์

| รายการ | รายละเอียด |
|--------|-------------|
| **ชื่อโปรเจกต์** | EV Power AI Assistant |
| **วัตถุประสงค์** | AI Assistant ภายในองค์กร EV Power Energy สำหรับตอบคำถามจาก **Database (CRM)** และจาก **เอกสาร (RAG)** ควบคุมสิทธิ์ตาม role ใช้งานผ่าน Web และ (แผน) LINE |
| **สถานะ** | Phase 3 Complete, Ready for Testing |
| **เวอร์ชัน** | 0.1.0 |

### ความสามารถหลัก
- **ตอบจาก Database:** ผ่าน RPC functions บน Supabase (ลีด, นัดหมาย, ทีมขาย, ยอดปิดการขาย, ใบเสนอราคา ฯลฯ)
- **ตอบจากเอกสาร:** RAG (Retrieval-Augmented Generation) ด้วย pgvector
- **Intent Router:** แยกประเภทคำถาม (db_query / rag_query / general / clarify) ด้วย LLM + Function Calling
- **สิทธิ์ข้อมูล:** ใช้ JWT + role (admin, manager, staff) และ RPC ฝั่ง DB กรองข้อมูลตาม user

---

## สรุป Tech Stack และสถาปัตยกรรม

### Tech Stack สรุป

| ชั้น | เทคโนโลยี | หน้าที่ในโปรเจกต์ |
|------|-----------|---------------------|
| **Frontend** | **Next.js 14** (React 18, TypeScript) | หน้า Web, App Router, Chat UI, Login, Admin |
| **Backend API** | **FastAPI** (Python 3.12+) | REST API, Auth (JWT), Chat endpoint, Ingest, Config |
| **AI Orchestration** | **LangGraph** | State graph: Router → Verifier → DB/RAG → Grader → Generate |
| **LLM** | **OpenAI API** (LangChain OpenAI) | Intent analysis (function calling), สร้างคำตอบ |
| **Database & Auth** | **Supabase** | PostgreSQL, Auth (JWT), RPC functions, Chat sessions/messages |
| **Vector Store** | **pgvector** (Supabase) | Embedding เก็บใน `kb_chunks.embedding`, ค้นเอกสาร RAG |
| **Deploy** | **Google Cloud Run** (Docker, Cloud Build) | Backend + Frontend เป็น container |

### สถาปัตยกรรมระบบ (High-Level)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Client Layer                                    │
│  Next.js 14 (Chat UI, Login, Admin)  │  (แผน) LINE Bot                    │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │ HTTPS / JWT
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Backend API (FastAPI)                              │
│  /api/v1/chat, /api/v1/me, /api/v1/ingest, /api/v1/config, health        │
│  Middleware: CORS, Rate Limit  │  Auth: JWT (Supabase), require_role      │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     AI Orchestrator (LangGraph)                           │
│  Entry: router (LLM intent + tool selection)                              │
│  Nodes: tool_selection_verifier → tool_selection_refiner (loop)          │
│         db_query (RPC tools) / rag_query (pgvector) / clarify            │
│         tool_execution_verifier → result_grader → rpc_planner (retry)     │
│         generate_response → END                                           │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │ 
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌──────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│ Supabase         │    │ OpenAI API            │    │ Vector Store          │
│ - Auth (JWT)     │    │ - Intent (function    │    │ (pgvector)            │
│ - RPC (15+ fn)   │    │   calling)            │    │ - kb_chunks           │
│ - chat_sessions  │    │ - Response generation │    │ - search_similar      │
│ - chat_messages  │    │ - Embeddings          │    │ - RAG citations       │
└──────────────────┘    └──────────────────────┘    └──────────────────────┘
```

### Flow การประมวลผลข้อความ (Chat)

1. **Client** ส่ง `POST /api/v1/chat` พร้อม `message` + JWT
2. **FastAPI** ตรวจ JWT → โหลด chat history (Supabase) → สร้าง `AIAssistantState`
3. **LangGraph** เริ่มที่ **router**: เรียก LLM (OpenAI function calling) วิเคราะห์ intent และเลือก tools
4. **Routing:**  
   - `db_query` → tool_selection_verifier → (ถ้าผ่าน) db_query_node → tool_execution_verifier → result_grader → generate_response  
   - `rag_query` → rag_query_node → result_grader → generate_response  
   - `general` → generate_response  
   - `clarify` → clarify_node → END
5. **db_query_node:** เรียกฟังก์ชันใน `db_tools.py` (เช่น `get_sales_closed`, `search_leads`) ซึ่งภายในเรียก Supabase RPC (`ai_get_sales_closed` ฯลฯ)
6. **rag_query_node:** เรียก `search_documents` → vector_store (pgvector) → ได้ chunks + citations
7. **generate_response_node:** ใช้ LLM รวม tool_results / rag_results เป็นข้อความตอบกลับ
8. **Backend** บันทึกข้อความเข้า `chat_messages`, audit_logs แล้ว return response ให้ Client

---

## 1. Python (Runtime สำหรับ Backend)

### มันคืออะไร
Python เป็น **ภาษาโปรแกรม** ที่ใช้เขียน Backend ของ AI Assistant ตัว Backend รันบน **Python 3.12+** และใช้รูปแบบ **async/await** สำหรับ I/O (เรียก API, DB, RPC)

### กลไกที่เกี่ยวข้องในโปรเจกต์
- **Async I/O:** FastAPI และ uvicorn รองรับ async endpoint; ฟังก์ชันที่เรียก Supabase RPC, OpenAI API เป็น `async def` เพื่อไม่บล็อก event loop
- **Type hints:** ใช้ร่วมกับ Pydantic สำหรับ config และ request/response models

### ตัวอย่างในโปรเจกต์

- **Entry point:** Backend เริ่มที่ `app/main.py` — ใช้ `lifespan` แบบ async และ mount routers

```33:59:backend/app/main.py
app = FastAPI(
    title="AI Assistant API",
    description="Internal AI Assistant & Knowledge Chatbot API",
    version="0.1.0",
    lifespan=lifespan,
)
# ...
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
# ...
```

- **Async ทั่วทั้ง orchestrator และ tools:** เช่น `process_message(state)` เป็น async, `db_query_node`, `analyze_intent_with_llm` ก็เป็น async และภายในเรียก `await` ไปที่ Supabase/OpenAI

**สรุป:** Backend เป็น Python 3.12+, ใช้ async สำหรับทุกจุดที่เกี่ยวกับ network/DB เพื่อรองรับ concurrent requests ได้ดี

---

## 2. FastAPI (Backend Framework)

### มันคืออะไร
FastAPI เป็น **Web Framework** สำหรับสร้าง API บน Python เน้นความเร็ว (async), **type hints**, และ **automatic OpenAPI (Swagger)** docs

### กลไกการทำงานหลัก

| คอนเซปต์ | ความหมาย |
|----------|----------|
| **APIRouter** | จัดกลุ่ม route (เช่น `/chat`, `/me`, `/ingest`) |
| **Depends** | Dependency Injection — เช่น `get_current_user` ใส่ใน parameter แล้ว FastAPI เรียกก่อนเข้า handler |
| **Pydantic BaseModel** | กำหนดรูปแบบ request/response และ validate อัตโนมัติ |

### ตัวอย่างในโปรเจกต์

- **Router + Auth:** Chat endpoint ต้องผ่าน `get_current_user` (ตรวจ JWT) ก่อนถึง logic

```42:56:backend/app/api/v1/chat.py
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Main chat endpoint
    Processes user message and returns AI response
    """
    try:
        user_id = current_user.get("id")
        # ...
```

- **Request/Response models:** ใช้ Pydantic กำหนด body และ response

```22:39:backend/app/api/v1/chat.py
class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    session_id: Optional[str] = None
    context: Optional[dict] = None

class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    session_id: str
    citations: Optional[List[str]] = None
    tool_calls: Optional[List[dict]] = None
    tool_results: Optional[List[dict]] = None
    intent: Optional[str] = None
    process_steps: Optional[List[Dict[str, Any]]] = None
    runtime: Optional[float] = None
    debug_precompute: Optional[Dict[str, Any]] = None
```

- **Middleware:** CORS และ Rate Limit ถูกเพิ่มใน `main.py`

**สรุป:** โปรเจกต์ใช้ FastAPI เป็นแกนหลักของ API — Router, Depends (Auth), Pydantic models และ middleware ครบ

---

## 3. Pydantic (Data Validation & Settings)

### มันคืออะไร
Pydantic ใช้ **type hints** และ **model class** เพื่อ validate ข้อมูล (เช่นจาก JSON body หรือ env) และแปลง type อัตโนมัติ

### ตัวอย่างในโปรเจกต์

- **Config จาก environment:** `app/config.py` ใช้ `pydantic-settings` อ่าน `.env` และมี validator แปลง `CORS_ORIGINS` เป็น list ได้

```11:57:backend/app/config.py
class Settings(BaseSettings):
    """Application settings"""
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-5.1"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        # ... parse string or list to string
```

- **API models:** `ChatRequest`, `ChatResponse` และอื่นๆ เป็น Pydantic BaseModel ทำให้ FastAPI validate และ generate OpenAPI schema ให้

**สรุป:** ใช้ Pydantic สำหรับ Settings และ request/response models ทั้งระบบ

---

## 4. LangGraph (AI Orchestration / State Graph)

### มันคืออะไร
LangGraph เป็น library ที่สร้าง **stateful workflow** แบบกราฟ (nodes + edges) สำหรับ AI pipeline — แต่ละ node รับ/อัปเดต state แล้วส่งต่อหรือแยก branch ตามเงื่อนไข

### กลไกการทำงานหลัก

| คอนเซปต์ | ความหมาย |
|----------|----------|
| **StateGraph** | กราฟที่ state เป็น TypedDict (เช่น `AIAssistantState`) ผ่านทุก node |
| **Node** | ฟังก์ชัน async รับ state คืน state ที่อัปเดตแล้ว |
| **Conditional edges** | จาก node หนึ่งไป node ถัดไปตามค่า return (เช่น "db_query" | "rag_query" | "general") |
| **Entry point** | node แรกที่รัน (ที่นี่คือ `router`) |

### ตัวอย่างในโปรเจกต์

- **State definition:** ทุก field ที่ไหลผ่านกราฟอยู่ที่ `AIAssistantState`

```7:65:backend/app/orchestrator/state.py
class AIAssistantState(TypedDict, total=False):
    user_message: str
    user_id: str
    user_role: Optional[str]
    session_id: Optional[str]
    chat_history: Optional[List[Dict[str, Any]]]
    history_context: Optional[str]
    intent: Optional[str]  # "db_query", "rag_query", "clarify", "general"
    confidence: float
    selected_tools: List[Dict[str, Any]]
    tool_parameters: Optional[Dict[str, Dict[str, Any]]]
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    rag_results: List[Dict[str, Any]]
    citations: List[str]
    # ... verification, retry, response
    response: Optional[str]
    error: Optional[str]
```

- **การสร้างกราฟและ conditional routing:** จาก router ไป db_query / rag_query / clarify / general

```52:144:backend/app/orchestrator/graph.py
def create_graph() -> StateGraph:
    graph = StateGraph(AIAssistantState)
    graph.add_node("router", router_node)
    graph.add_node("tool_selection_verifier", tool_selection_verifier_node)
    graph.add_node("tool_selection_refiner", tool_selection_refiner_node)
    graph.add_node("db_query", db_query_node)
    graph.add_node("tool_execution_verifier", tool_execution_verifier_node)
    graph.add_node("rag_query", rag_query_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("result_grader", result_grader_node)
    graph.add_node("rpc_planner", rpc_planner_node)
    graph.add_node("generate_response", generate_response_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges("router", route_intent, {
        "db_query": "tool_selection_verifier",
        "rag_query": "rag_query",
        "clarify": "clarify",
        "general": "generate_response"
    })
    # ... edges สำหรับ verifier, refiner, grader, rpc_planner
```

- **การรัน workflow:** API เรียก `process_message(initial_state)` ซึ่ง `ainvoke` graph แล้วได้ state สุดท้าย (มี `response`)

```217:228:backend/app/orchestrator/graph.py
async def process_message(state: AIAssistantState) -> AIAssistantState:
    try:
        graph = get_graph()
        state_dict = dict(state)
        result = await graph.ainvoke(state_dict)
        return result
    except Exception as e:
        state["error"] = str(e)
        state["response"] = "ขออภัยครับ เกิดข้อผิดพลาด..."
        return state
```

**สรุป:** LangGraph เป็นหัวใจของ orchestration — router → verifier/refiner → db_query หรือ rag_query → grader → generate_response ครบในกราฟเดียว

---

## 5. OpenAI API & Function Calling (LLM)

### มันคืออะไร
โปรเจกต์ใช้ **OpenAI API** (ผ่าน `openai` SDK และ `langchain-openai`) สำหรับ  
1) **Intent analysis + tool selection** — ใช้ **function calling** ให้ LLM คืน tool name และ parameters  
2) **สร้างคำตอบ** — จาก tool results / RAG results เป็นข้อความภาษาไทย

### กลไกที่ใช้
- **Function calling:** ส่ง `tools=TOOL_SCHEMAS` (รายการฟังก์ชันเช่น `search_leads`, `get_sales_closed`) และ `tool_choice="auto"` หรือ `"required"` (เมื่อข้อความมี keyword ด้านข้อมูล) LLM จะตอบกลับเป็น `tool_calls` พร้อมชื่อและ arguments (JSON)
- **Model:** ใช้จาก config `OPENAI_MODEL` (เช่น gpt-4o-mini, gpt-5-mini)

### ตัวอย่างในโปรเจกต์

- **Tool schemas สำหรับ intent:** ใน `llm_router.py` มี `TOOL_SCHEMAS` หลายตัว เช่น `search_leads`, `get_sales_closed`, `get_team_kpi` ฯลฯ
- **เรียก API ด้วย function calling:**

```469:478:backend/app/orchestrator/llm_router.py
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=openai_messages,
                tools=TOOL_SCHEMAS,
                tool_choice=tool_choice  # "required" when message has data keywords
            )
            message = response.choices[0].message
```

- **LLM service สำหรับ generate response:** ใช้ LangChain `ChatOpenAI` ใน `app/services/llm.py` สำหรับ node สร้างคำตอบ

**สรุป:** OpenAI ใช้สองบทบาท — วิเคราะห์ intent + เลือก tools (function calling) และสร้างข้อความตอบจากข้อมูลที่ดึงมา

---

## 6. Supabase (Database, Auth, RPC)

### มันคืออะไร
Supabase ให้ **PostgreSQL as a Service**, **Auth** (JWT), **REST/Realtime** และ **RPC** โปรเจกต์ใช้เป็นที่เก็บข้อมูลหลัก + Auth + เรียก logic ฝั่ง DB ผ่าน RPC

### กลไกที่ใช้ในโปรเจกต์

| ฟีเจอร์ | การใช้ |
|--------|--------|
| **Auth** | Login ผ่าน Supabase Auth ได้ JWT — Backend ใช้ JWT ตรวจสิทธิ์และดึง user_id/role |
| **Tables** | `chat_sessions`, `chat_messages`, `audit_logs`, `kb_documents`, `kb_chunks`, `line_identities` ฯลฯ |
| **RPC** | ฟังก์ชันเช่น `ai_get_sales_closed`, `ai_get_sales_unsuccessful`, `ai_search_leads` ฯลฯ ถูกเรียกจาก Backend ผ่าน `supabase.rpc(...)` |
| **Service role** | Backend ใช้ `SUPABASE_SERVICE_ROLE_KEY` เพื่อ bypass RLS และเรียก RPC ได้ตามที่ออกแบบ |

### ตัวอย่างในโปรเจกต์

- **เรียก RPC จาก db_tools:** เช่น Sales Closed

```82:98:backend/app/tools/db_tools.py
    date_from_ts = f"{date_from}T00:00:00.000"
    date_to_ts = f"{date_to}T23:59:59.999"
    supabase = get_supabase_client()
    result = supabase.rpc(
        "ai_get_sales_closed",
        {
            "p_user_id": user_id,
            "p_date_from": date_from_ts,
            "p_date_to": date_to_ts,
            "p_sales_member_id": sales_member_id,
            "p_user_role": user_role or "staff",
        }
    ).execute()
```

- **Auth ฝั่ง Backend:** ใช้ JWT decode (และตรวจ user ใน DB ถ้าต้องการ) แล้ว resolve role จากตาราง `users`/`employees`

**สรุป:** Supabase เป็นทั้ง DB, Auth และชั้น RPC สำหรับข้อมูล CRM ที่ AI ใช้ตอบคำถาม

---

## 7. pgvector (Vector Store สำหรับ RAG)

### มันคืออะไร
**pgvector** เป็น extension ของ PostgreSQL สำหรับเก็บและค้นหา **vector** (embedding) เช่น embedding จาก OpenAI text-embedding โปรเจกต์ใช้เก็บ chunk เอกสารใน `kb_chunks.embedding` แล้วค้นแบบ similarity (เช่น cosine) เพื่อ RAG

### กลไกในโปรเจกต์
- **ตาราง:** `kb_chunks` มีคอลัมน์ `embedding vector(1536)` (มิติตาม embedding model)
- **การค้น:** ใช้ RPC หรือ query ที่คำนวณ distance/similarity แล้วเรียงลำดับ — service ฝั่ง Backend เรียก `search_similar` ได้ผลเป็น chunks + similarity score
- **RAG flow:** user ถาม → embed query → ค้น chunks ที่ใกล้ที่สุด → ส่ง chunks + query ให้ LLM สร้างคำตอบ + citations

### ตัวอย่างในโปรเจกต์

- **Schema ตาราง chunks:**

```59:69:supabase/migrations/20250116000001_initial_schema.sql
-- Knowledge Base Chunks Table (with pgvector)
CREATE TABLE IF NOT EXISTS kb_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536), -- OpenAI text-embedding-3-small dimension
    chunk_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    ...
);
```

- **RAG node:** เรียก `search_documents` ซึ่งภายในใช้ `search_similar` (vector_store) แล้ว format เป็น citations

```17:31:backend/app/orchestrator/nodes/rag_query.py
        rag_results = await search_documents(user_message, limit=5)
        citations = format_citations(rag_results) if rag_results else []
        state["rag_results"] = rag_results
        state["citations"] = citations
```

**สรุป:** pgvector เก็บ embedding ของเอกสาร และใช้ค้นเอกสารที่เกี่ยวข้องกับคำถามเพื่อ RAG

---

## 8. Database RPC Tools (Allowlist)

### มันคืออะไร
Backend มี **allowlist ของฟังก์ชัน** ที่ AI เรียกได้ — แต่ละฟังก์ชันใน `app/tools/db_tools.py` map กับ RPC หรือ logic ที่อัปเดตแล้วใน Supabase (เช่น `ai_get_sales_closed`, `ai_search_leads`) และรับพารามิเตอร์เช่น `user_id`, `date_from`, `date_to`, `platform` ฯลฯ เพื่อควบคุมสิทธิ์และความสอดคล้องกับหน้าเว็บ CRM

### ตัวอย่างฟังก์ชันหลัก (จาก db_tools + llm_router TOOL_SCHEMAS)

| หมวด | ฟังก์ชันตัวอย่าง | การใช้ |
|------|-------------------|--------|
| ลีด | `search_leads`, `get_lead_status`, `get_my_leads`, `get_lead_detail`, `get_lead_management` | Dashboard ลีด, สถานะลีด, ลีดของฉัน, รายละเอียดลีด |
| ยอดขาย | `get_sales_closed`, `get_sales_unsuccessful` | รายงานปิดการขายสำเร็จ/ไม่สำเร็จ |
| ทีม | `get_team_kpi`, `get_sales_team`, `get_sales_team_list`, `get_sales_team_data`, `get_sales_performance` | KPI ทีม, รายชื่อทีม, performance รายคน |
| นัดหมาย | `get_appointments`, `get_service_appointments` | นัดขาย / นัดบริการ |
| เอกสาร | `get_quotations`, `get_sales_docs`, `get_permit_requests` | ใบเสนอราคา, เอกสารขาย, คำขออนุญาต |
| อื่นๆ | `get_user_info`, `get_daily_summary` ฯลฯ | ข้อมูลผู้ใช้, สรุปรายวัน |

**สรุป:** RPC tools เป็นชั้นกลางระหว่าง LangGraph (db_query_node) กับ Supabase RPC — รับ parameter จาก LLM แล้วเรียก RPC พร้อม user_id/role เพื่อให้ข้อมูลตรงกับสิทธิ์

---

## 9. Authentication & Authorization (JWT, Role)

### มันคืออะไร
- **Authentication:** ตรวจว่า request มาจากผู้ใช้ที่ login แล้ว ผ่าน **JWT** ใน header `Authorization: Bearer <token>`
- **Authorization:** ตรวจ **role** (super_admin, admin, manager, staff) จากตาราง `users`/`employees` (ผูกกับ `auth_user_id` จาก JWT) — บาง endpoint ใช้ `require_role` เพื่อจำกัดเฉพาะ admin/manager

### ตัวอย่างในโปรเจกต์

- **การตรวจ JWT และดึง user:** `get_current_user` ใช้ `HTTPBearer` แล้ว decode token และ resolve role จาก DB

```17:51:backend/app/core/auth.py
async def verify_jwt_token(token: str) -> dict:
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
        user_id = unverified.get("sub")
        # ... exp check
        return {
            "sub": user_id,
            "email": unverified.get("email", ""),
            "user_metadata": unverified.get("user_metadata", {}),
            ...
        }
```

- **การส่ง user_id / user_role เข้า state:** ใน chat API หลังจากได้ `current_user` จะใส่ `user_id`, `user_role` ลงใน `AIAssistantState` เพื่อให้ RPC และ logic ฝั่ง DB ใช้กรองข้อมูลตามสิทธิ์

**สรุป:** ทุก request ที่ต้อง login ผ่าน `get_current_user`; บาง route ใช้ `require_role` เพิ่มสำหรับ Admin/Prompt tests ฯลฯ

---

## 10. Next.js 14 (Frontend)

### มันคืออะไร
Next.js เป็น **React Framework** ที่มี Server/Client components, **App Router** (โฟลเดอร์ `app/` กำหนด route), และรองรับ SSR/SSG/API routes โปรเจกต์ใช้ Next.js 14 เป็นฝั่ง Web UI

### กลไกที่ใช้
- **App Router:** `app/(auth)/login`, `app/(auth)/callback`, `app/(dashboard)/chat`, `app/(dashboard)/admin` ฯลฯ
- **Client components:** หน้า chat ใช้ `'use client'` และ hooks เช่น `useAuth`, `useConfig`, `useChat`
- **เรียก Backend:** ใช้ axios หรือ fetch ไปที่ `NEXT_PUBLIC_API_URL` (เช่น `http://localhost:8000`) พร้อม JWT ใน header

### ตัวอย่างในโปรเจกต์

- **หน้า Chat:** layout มี header (ชื่อ, ลิงก์ Admin, โมเดลที่ใช้, UserProfile) และ main เป็น `ChatInterface`

```1:41:frontend/src/app/(dashboard)/chat/page.tsx
'use client'
import { ChatInterface } from '@/components/chat/ChatInterface'
import { UserProfile } from '@/components/auth/UserProfile'
import { useAuth } from '@/contexts/AuthContext'
import { useConfig } from '@/hooks/useConfig'

export default function ChatPage() {
  const { userRole } = useAuth()
  const { config: modelConfig } = useConfig()
  return (
    <div className="flex h-screen flex-col">
      <header>...</header>
      <main className="flex-1 overflow-hidden">
        <ChatInterface />
      </main>
    </div>
  )
}
```

- **Dependencies:** Next 14.1, React 18, Supabase JS, TanStack Query, Axios, Zod, Tailwind

**สรุป:** Frontend เป็น SPA-like แบบ Next.js 14 เน้น Chat UI, Login, Session, Admin และเรียก API Backend ด้วย JWT

---

## 11. Docker & Cloud Run (Deployment)

### มันคืออะไร
- **Docker:** แพ็ก Backend และ Frontend เป็น **Container** (มี Dockerfile แต่ละตัว) ให้รันได้เหมือนกันทุก environment
- **Google Cloud Run:** รัน container แบบ serverless — scale ตาม request, จ่ายตามการใช้งาน
- **Cloud Build:** ใช้ `cloudbuild.yaml` / `cloudbuild-backend.yaml` build image และ deploy ขึ้น Cloud Run

### โครงสร้างที่เกี่ยวข้อง
- `backend/Dockerfile`, `backend/cloudbuild.yaml`
- `frontend/Dockerfile`, `frontend/cloudbuild.yaml`
- เอกสารใน `docs/`: DEPLOY_STEPS_DETAILED.md, TROUBLESHOOTING_CLOUD_RUN.md ฯลฯ

**สรุป:** โปรเจกต์พร้อม deploy เป็น container บน GCP Cloud Run และใช้ Cloud Build เป็น CI/CD

---

## สรุปตาราง: โปรเจกต์ EV Power AI Assistant ประกอบกันอย่างไร

| ชั้น | เทคโนโลยี | หน้าที่ในโปรเจกต์ |
|------|-----------|---------------------|
| **Frontend** | **Next.js 14, React 18, TypeScript** | หน้า Login, Chat, Session, Admin เรียก Backend API ด้วย JWT |
| **API** | **FastAPI** | REST /api/v1/chat, /me, /ingest, /config; Middleware CORS, Rate limit; Auth ด้วย Depends(get_current_user) |
| **Config** | **Pydantic Settings** | อ่าน .env (Supabase, OpenAI, CORS ฯลฯ) และ validate |
| **Orchestration** | **LangGraph** | State graph: router → verifier/refiner → db_query / rag_query → grader → generate_response |
| **LLM** | **OpenAI (function calling + Chat)** | วิเคราะห์ intent เลือก tools; สร้างคำตอบจาก tool/RAG results |
| **Database & Auth** | **Supabase** | PostgreSQL, Auth JWT, ตาราง chat/kb/audit, RPC ฝั่ง DB |
| **DB Tools** | **db_tools.py + RPC** | Allowlist ฟังก์ชัน (search_leads, get_sales_closed ฯลฯ) เรียก Supabase RPC ตาม user_id/role |
| **RAG** | **pgvector + rag_tools** | เก็บ embedding ใน kb_chunks; ค้น similar → ส่ง chunks ให้ LLM สร้างคำตอบ + citations |
| **Deploy** | **Docker, Cloud Run, Cloud Build** | Build และรัน Backend/Frontend เป็น container บน GCP |

เมื่อมีคำถามจากผู้ใช้ (ผ่าน Web):

1. **Next.js** ส่ง request ไปที่ FastAPI `/api/v1/chat` พร้อม JWT
2. **FastAPI** ตรวจ JWT โหลด chat history จาก Supabase สร้าง state
3. **LangGraph** เริ่มที่ router → LLM วิเคราะห์ intent และเลือก tools (หรือ general/rag/clarify)
4. **db_query path:** verifier → db_query_node เรียก db_tools → Supabase RPC → tool_execution_verifier → result_grader → generate_response
5. **rag_query path:** rag_query_node ค้น pgvector → result_grader → generate_response
6. **generate_response_node** ใช้ LLM รวมผลเป็นข้อความตอบ
7. Backend บันทึกข้อความและ return response ให้ Frontend แสดงใน Chat UI

---

## โครงสร้างโฟลเดอร์หลัก (สำหรับอ้างอิง)

```
evp-ai-assistant/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── main.py            # Entry, CORS, routers
│   │   ├── config.py          # Pydantic Settings
│   │   ├── api/v1/            # Endpoints: chat, me, ingest, health, config, prompt_tests, line
│   │   ├── core/              # auth.py, audit.py
│   │   ├── orchestrator/       # LangGraph
│   │   │   ├── graph.py       # StateGraph, create_graph, process_message
│   │   │   ├── state.py       # AIAssistantState
│   │   │   ├── llm_router.py  # analyze_intent_with_llm, TOOL_SCHEMAS
│   │   │   ├── nodes/        # router, db_query, rag_query, clarify, generate_response, verifiers, grader, rpc_planner
│   │   │   └── formatters/
│   │   ├── services/          # supabase, llm, vector_store, chat_history, embedding_similarity
│   │   ├── tools/             # db_tools.py (RPC wrappers), rag_tools.py
│   │   ├── middleware/        # rate_limit_middleware
│   │   └── utils/             # logger, system_prompt, exceptions
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Next.js 14
│   ├── src/
│   │   ├── app/               # (auth)/login, (dashboard)/chat, (dashboard)/admin
│   │   ├── components/        # chat/*, auth/*
│   │   ├── contexts/          # AuthContext
│   │   ├── hooks/             # useAuth, useChat, useConfig
│   │   └── lib/               # api client
│   └── package.json
├── supabase/migrations/        # Schema, RPC (ai_get_sales_closed, ai_search_leads, vector search ฯลฯ)
└── docs/                       # เอกสารรวมถึงไฟล์นี้
```

---

*เอกสารนี้จัดทำเพื่อใช้อธิบายและนำเสนอโปรเจกต์ EV Power AI Assistant แบบครบถ้วน รวมถึง Tech Stack และสถาปัตยกรรมระบบ*
