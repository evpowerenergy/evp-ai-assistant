# 🔄 Flow การถามตอบ (Chat Flow)

## 📋 สารบัญ
1. [ภาพรวม Flow](#ภาพรวม-flow)
2. [ขั้นตอนละเอียด](#ขั้นตอนละเอียด)
3. [Flow Diagram](#flow-diagram)
4. [ตัวอย่างการทำงาน](#ตัวอย่างการทำงาน)
5. [State Management](#state-management)

---

## 🎯 ภาพรวม Flow

Flow การถามตอบใช้ **LangGraph** เป็น orchestrator หลัก โดยมี 4 ขั้นตอนหลัก:

```
User Message 
    ↓
[1] Router Node (LLM Intent Analysis + Tool Selection)
    ↓
[2] Query Node (DB Query หรือ RAG Query)
    ↓
[3] Generate Response Node (LLM สร้างคำตอบ)
    ↓
[4] Return Response to User
```

---

## 📝 ขั้นตอนละเอียด

### **Step 0: API Entry Point**
📁 `app/api/v1/chat.py`

```python
POST /api/v1/chat
{
  "message": "ลีดวันนี้มีใครบ้าง",
  "session_id": "optional-session-id"
}
```

**สิ่งที่ทำ:**
1. ✅ ตรวจสอบ JWT token (authentication)
2. ✅ สร้างหรือดึง session_id
3. ✅ สร้าง initial state:
   ```python
   {
     "user_message": "ลีดวันนี้มีใครบ้าง",
     "user_id": "uuid-from-jwt",
     "user_role": "staff",  # จาก JWT token
     "session_id": "session-uuid",
     "intent": None,
     "confidence": 0.0,
     "tool_calls": [],
     "tool_results": [],
     "rag_results": [],
     "citations": [],
     "response": None
   }
   ```
4. ✅ เรียก `process_message(initial_state)` → เข้า LangGraph workflow

---

### **Step 1: Router Node** 🎯
📁 `app/orchestrator/graph.py` → `router_node()`
📁 `app/orchestrator/llm_router.py` → `analyze_intent_with_llm()`

**หน้าที่:**
- วิเคราะห์ intent จาก user message
- เลือก tools ที่เหมาะสม (function calling)
- Extract entities (เช่น ชื่อ lead, วันที่)

**กระบวนการ:**

#### 1.1 LLM Function Calling
```python
# เรียก OpenAI API ด้วย function calling
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
response = await client.chat.completions.create(
    model=settings.OPENAI_MODEL,  # gpt-4o-mini
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "ลีดวันนี้มีใครบ้าง"}
    ],
    tools=TOOL_SCHEMAS,  # รายการ tools ที่มี
    tool_choice="auto",  # ให้ LLM เลือกเอง
    temperature=0.3
)
```

#### 1.2 Tool Schemas ที่มี
```python
TOOL_SCHEMAS = [
    {
        "name": "search_leads",
        "description": "Search or list leads...",
        "parameters": {
            "query": "string",
            "date_from": "YYYY-MM-DD",
            "date_to": "YYYY-MM-DD"
        }
    },
    {
        "name": "get_lead_status",
        "description": "Get status of a specific lead...",
        "parameters": {
            "lead_name": "string"
        }
    },
    {
        "name": "get_daily_summary",
        "description": "Get daily summary statistics...",
        "parameters": {
            "date": "YYYY-MM-DD"
        }
    },
    # ... อื่นๆ
]
```

#### 1.3 LLM Response
```json
{
  "tool_calls": [
    {
      "id": "call_123",
      "type": "function",
      "function": {
        "name": "search_leads",
        "arguments": "{\"query\": \"today\", \"date_from\": \"2026-01-17\", \"date_to\": \"2026-01-17\"}"
      }
    }
  ]
}
```

#### 1.4 Parse และ Extract
```python
# Extract tool calls
selected_tools = [
    {
        "name": "search_leads",
        "parameters": {
            "query": "today",
            "date_from": "2026-01-17",
            "date_to": "2026-01-17"
        }
    }
]

# Extract entities
entities = {
    "date": "2026-01-17",
    "query_type": "list_leads"
}

# Determine intent
intent = "db_query"  # เพราะเลือกใช้ database tool
confidence = 0.9
```

#### 1.5 Update State
```python
state["intent"] = "db_query"
state["confidence"] = 0.9
state["selected_tools"] = selected_tools
state["tool_parameters"] = {"search_leads": {...}}
state["entities"] = entities
```

#### 1.6 Route Decision
```python
def route_intent(state):
    intent = state.get("intent", "general")
    confidence = state.get("confidence", 0.0)
    
    if confidence < 0.3:
        return "clarify"  # ถามซ้ำ
    
    return intent  # "db_query", "rag_query", "general"
```

**ผลลัพธ์:** ไปที่ node ถัดไปตาม intent

---

### **Step 2: Query Node** 🔍

#### **2.1 DB Query Node** (ถ้า intent = "db_query")
📁 `app/orchestrator/nodes/db_query.py`

**หน้าที่:**
- Execute tools ที่ LLM เลือก
- เรียก database RPC functions
- เก็บผลลัพธ์ใน state

**กระบวนการ:**

```python
# ดึง tools ที่ LLM เลือก
selected_tools = state.get("selected_tools", [])

# Execute แต่ละ tool
for tool_info in selected_tools:
    tool_name = tool_info.get("name")
    params = tool_info.get("parameters")
    
    if tool_name == "search_leads":
        result = await search_leads(
            query=params.get("query"),
            user_id=user_id,
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
            user_role=user_role
        )
        
        tool_results.append({
            "tool": "search_leads",
            "input": params,
            "output": result
        })
```

**Database RPC Call:**
```python
# app/tools/db_tools.py
result = supabase.rpc(
    "ai_get_leads",
    {
        "p_user_id": user_id,
        "p_filters": {},
        "p_date_from": "2026-01-17",
        "p_date_to": "2026-01-17",
        "p_limit": None,  # ไม่จำกัด
        "p_user_role": "staff"
    }
).execute()
```

**Update State:**
```python
state["tool_calls"] = tool_results
state["tool_results"] = tool_results
```

**ผลลัพธ์:** ไปที่ `generate_response` node

---

#### **2.2 RAG Query Node** (ถ้า intent = "rag_query")
📁 `app/orchestrator/nodes/rag_query.py`

**หน้าที่:**
- ค้นหาเอกสารด้วย vector similarity
- ใช้สำหรับคำถามเกี่ยวกับ documentation, how-to

**กระบวนการ:**
```python
# ค้นหาเอกสาร
rag_results = await search_documents(user_message, limit=5)

# Format citations
citations = format_citations(rag_results)

# Update state
state["rag_results"] = rag_results
state["citations"] = citations
```

**ผลลัพธ์:** ไปที่ `generate_response` node

---

#### **2.3 Clarify Node** (ถ้า confidence < 0.3)
📁 `app/orchestrator/nodes/clarify.py`

**หน้าที่:**
- ถามซ้ำเมื่อ intent ไม่ชัดเจน

**กระบวนการ:**
```python
response = "ขออภัยครับ คำถามของคุณไม่ชัดเจนพอ คุณต้องการถามเกี่ยวกับอะไรครับ?"

state["response"] = response
state["intent"] = "clarify"
```

**ผลลัพธ์:** ไปที่ `END` (ไม่ต้อง generate response)

---

### **Step 3: Generate Response Node** 💬
📁 `app/orchestrator/nodes/generate_response.py`

**หน้าที่:**
- Format tool results หรือ RAG results
- สร้าง prompt สำหรับ LLM
- เรียก LLM เพื่อสร้างคำตอบภาษาไทย

**กระบวนการ:**

#### 3.1 Format Tool Results
```python
def format_tool_response(tool_results, user_message):
    # Format search_leads results
    if tool_name == "search_leads":
        leads = output.get("data", {}).get("leads", [])
        
        lead_list = []
        for i, lead in enumerate(leads, 1):
            name = lead.get("display_name") or lead.get("full_name", "N/A")
            tel = lead.get("tel")
            status = lead.get("status", "N/A")
            region = lead.get("region", "")
            
            lead_info = f"{i}. {name}"
            if region:
                lead_info += f" ({region})"
            if status:
                lead_info += f" - สถานะ: {status}"
            if tel:
                lead_info += f" - โทร: {tel}"
            lead_list.append(lead_info)
        
        return f"พบ {len(leads)} leads:\n" + "\n".join(lead_list)
```

#### 3.2 Build LLM Prompt
```python
prompt = f"""You are a helpful AI assistant for EV Power Energy. Answer the user's question based on the provided context.

User Question: {user_message}

Context Information:
{formatted_context}

Instructions:
- Answer in Thai language
- Be friendly, concise, and helpful
- If the context contains a list (e.g., leads list), show ALL items from the list, don't skip any
- If the context contains contact information (phone numbers, Line ID), include them in your response
- If the context contains data, show ALL available information including phone numbers, names, status, region, etc.
- When showing lists, include all items mentioned in the context with all available details

Response:"""
```

#### 3.3 Call LLM
```python
llm = get_llm(temperature=0.7)  # ใช้ LangChain ChatOpenAI
response = await llm.ainvoke(prompt)
```

#### 3.4 Update State
```python
state["response"] = response.content
```

**ผลลัพธ์:** ไปที่ `END`

---

### **Step 4: Return Response** ✅

**สิ่งที่ทำ:**
1. ✅ Save messages ลง database
2. ✅ Log tool calls (audit)
3. ✅ Log chat request (audit)
4. ✅ Return response ไปยัง client

```python
response = ChatResponse(
    response=result_state.get("response"),
    session_id=session_id,
    citations=result_state.get("citations"),
    tool_calls=result_state.get("tool_calls"),
    intent=result_state.get("intent")
)
```

---

## 🔀 Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User sends message                        │
│              POST /api/v1/chat                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              [0] API Entry Point                              │
│  - Authenticate (JWT)                                        │
│  - Create/get session                                        │
│  - Create initial state                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              [1] Router Node (LLM Intent Analysis)            │
│  - Call OpenAI API with function calling                     │
│  - LLM selects tools (search_leads, get_lead_status, etc.)   │
│  - Extract entities (dates, names)                          │
│  - Determine intent (db_query, rag_query, clarify, general)  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  db_query    │ │  rag_query   │ │   clarify    │
│              │ │              │ │              │
│ - Execute    │ │ - Vector     │ │ - Ask for    │
│   tools      │ │   search     │ │   clarifi-   │
│ - Call RPC   │ │ - Get docs   │ │   cation     │
│   functions  │ │              │ │              │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       │                │                │
       └────────┬───────┴────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│         [3] Generate Response Node                           │
│  - Format tool/RAG results                                  │
│  - Build LLM prompt                                          │
│  - Call LLM to generate Thai response                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              [4] Return Response                              │
│  - Save messages to DB                                       │
│  - Log tool calls (audit)                                    │
│  - Return JSON response                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 ตัวอย่างการทำงาน

### **ตัวอย่าง 1: "ลีดวันนี้มีใครบ้าง"**

```
[1] Router Node
    ├─ LLM วิเคราะห์: "ลีดวันนี้" = ต้องการ list leads
    ├─ LLM เลือก tool: search_leads
    ├─ Extract: date_from="2026-01-17", date_to="2026-01-17"
    └─ Intent: "db_query" (confidence: 0.95)

[2] DB Query Node
    ├─ Execute: search_leads(query="today", date_from="2026-01-17", ...)
    ├─ Call RPC: ai_get_leads(p_date_from="2026-01-17", ...)
    ├─ Database returns: 26 leads
    └─ Format: tool_results = [{tool: "search_leads", output: {...}}]

[3] Generate Response Node
    ├─ Format: "พบ 26 leads:\n1. Tupsuri Paitoon - โทร: 081-xxx\n..."
    ├─ LLM Prompt: "Answer based on context: 26 leads..."
    └─ LLM Response: "พบลูกค้า 26 ท่านที่ได้มาในวันนี้:\n1. Tupsuri Paitoon..."

[4] Return
    └─ Response: "พบลูกค้า 26 ท่านที่ได้มาในวันนี้:\n1. Tupsuri Paitoon..."
```

---

### **ตัวอย่าง 2: "วิธีติดตั้งระบบ"**

```
[1] Router Node
    ├─ LLM วิเคราะห์: "วิธีติดตั้ง" = ต้องการ documentation
    ├─ LLM ไม่เลือก tool (ไม่มี tool ที่เหมาะสม)
    └─ Intent: "rag_query" (confidence: 0.8)

[2] RAG Query Node
    ├─ Search documents: "วิธีติดตั้งระบบ"
    ├─ Vector similarity search
    └─ Found: 3 relevant documents

[3] Generate Response Node
    ├─ Format: "Document 1: ...\nDocument 2: ..."
    ├─ LLM Prompt: "Answer based on documents..."
    └─ LLM Response: "ขั้นตอนการติดตั้งระบบ..."

[4] Return
    └─ Response: "ขั้นตอนการติดตั้งระบบ..." + citations
```

---

### **ตัวอย่าง 3: "สถานะ lead ชื่อ Tupsuri"**

```
[1] Router Node
    ├─ LLM วิเคราะห์: "สถานะ lead" = ต้องการ lead status
    ├─ LLM เลือก tool: get_lead_status
    ├─ Extract: lead_name="Tupsuri"
    └─ Intent: "db_query" (confidence: 0.9)

[2] DB Query Node
    ├─ Execute: get_lead_status(lead_name="Tupsuri", ...)
    ├─ Call RPC: get_lead_status_by_name(...)
    └─ Database returns: {status: "qualified", ...}

[3] Generate Response Node
    ├─ Format: "Lead: Tupsuri Paitoon\nStatus: qualified\n..."
    └─ LLM Response: "สถานะของ lead Tupsuri Paitoon คือ qualified..."

[4] Return
    └─ Response: "สถานะของ lead Tupsuri Paitoon คือ qualified..."
```

---

## 🗂️ State Management

### **State Schema**
```python
class AIAssistantState(TypedDict, total=False):
    # Input
    user_message: str
    user_id: str
    user_role: Optional[str]
    session_id: Optional[str]
    
    # Intent Analysis
    intent: Optional[str]  # "db_query", "rag_query", "clarify", "general"
    confidence: float
    entities: Optional[Dict[str, Any]]
    selected_tools: List[Dict[str, Any]]
    tool_parameters: Optional[Dict[str, Dict[str, Any]]]
    
    # Results
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    rag_results: List[Dict[str, Any]]
    citations: List[str]
    
    # Output
    response: Optional[str]
    error: Optional[str]
```

### **State Flow**
```
Initial State
    ↓
Router Node → เพิ่ม: intent, confidence, selected_tools, entities
    ↓
Query Node → เพิ่ม: tool_results หรือ rag_results
    ↓
Generate Response → เพิ่ม: response
    ↓
Final State → Return to API
```

---

## 🔧 Technologies Used

1. **LangGraph**: Workflow orchestration
2. **LangChain**: LLM wrapper (สำหรับ generate response)
3. **OpenAI API (Direct)**: Function calling สำหรับ intent analysis
4. **Supabase RPC**: Database functions
5. **Vector Search**: RAG document search

---

## 📝 Notes

- **Model**: ใช้ `gpt-4o-mini` (configurable via `OPENAI_MODEL` env var)
- **Temperature**: 
  - Intent analysis: 0.3 (เพื่อความแม่นยำ)
  - Response generation: 0.7 (เพื่อความเป็นธรรมชาติ)
- **Tool Selection**: LLM เลือกเองผ่าน function calling (ไม่ใช่ rule-based)
- **Date Extraction**: รองรับ natural language เช่น "เมื่อวาน", "สัปดาห์นี้", "เดือนนี้"
- **No Limits**: ไม่จำกัดจำนวน results (แสดงทั้งหมด)

---

## 🚀 Performance

- **Intent Analysis**: ~500-1000ms (OpenAI API call)
- **DB Query**: ~200-500ms (Supabase RPC)
- **Response Generation**: ~1000-2000ms (LLM)
- **Total**: ~2-4 seconds per request

---

## 📚 Related Documents

- [CURRENT_ARCHITECTURE.md](./CURRENT_ARCHITECTURE.md) - สถาปัตยกรรมโดยรวม
- [LLM_PROMPT_LOCATIONS.md](./LLM_PROMPT_LOCATIONS.md) - ตำแหน่ง prompts
- [HOW_TO_CHANGE_MODEL.md](./HOW_TO_CHANGE_MODEL.md) - วิธีเปลี่ยน model
- [DATE_RANGE_SUPPORT.md](./DATE_RANGE_SUPPORT.md) - รองรับ date range
