# 🏗️ สถาปัตยกรรมปัจจุบัน (Current Architecture)

## 📊 Overview

ระบบใช้ **LangGraph** สำหรับ orchestration workflow และ **OpenAI API** โดยตรงสำหรับ function calling

---

## 🔧 Technology Stack

### 1. **LangGraph** (Orchestration)
- **ใช้สำหรับ**: Workflow orchestration และ state management
- **Location**: `app/orchestrator/graph.py`
- **หน้าที่**:
  - จัดการ workflow flow (router → db_query/rag_query → generate_response)
  - State management ผ่าน `AIAssistantState`
  - Conditional routing ตาม intent

### 2. **LangChain** (LLM Integration)
- **ใช้สำหรับ**: LLM service wrapper (ChatOpenAI)
- **Location**: `app/services/llm.py`
- **หน้าที่**:
  - Wrapper สำหรับ OpenAI GPT-4
  - ใช้ในการ generate response (Stage 4)

### 3. **OpenAI API** (Function Calling - Direct)
- **ใช้สำหรับ**: Intent analysis และ tool selection
- **Location**: `app/orchestrator/llm_router.py`
- **หน้าที่**:
  - เรียก OpenAI API โดยตรง (ไม่ผ่าน LangChain)
  - Function calling สำหรับเลือก tools
  - ใช้ `AsyncOpenAI` client

### 4. **LangSmith** (Monitoring)
- **Status**: ❌ **ไม่ใช้ในตอนนี้**
- **Note**: ไม่มีการ configure LangSmith tracing/monitoring

---

## 🔄 Current Architecture Flow

```
┌─────────────────────────────────────────────────┐
│  User Message                                   │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Stage 1: LLM Intent Analysis                   │
│  (app/orchestrator/llm_router.py)               │
│  - OpenAI API (Direct Call)                     │
│  - Function Calling                             │
│  - Tool Selection                               │
│  Output: intent, selected_tools, entities       │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  LangGraph Router                               │
│  (app/orchestrator/graph.py)                    │
│  - Conditional routing based on intent          │
│  Routes: db_query | rag_query | clarify         │
└─────────────────────────────────────────────────┘
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
┌──────────────┐      ┌──────────────┐
│ DB Query     │      │ RAG Query    │
│ (if db_query)│      │ (if rag_query)│
│              │      │              │
│ Execute:     │      │ Vector Search│
│ - search_leads│      │ - match_kb_  │
│ - get_daily_ │      │   chunks     │
│   summary    │      │              │
│ - etc.       │      │              │
└──────────────┘      └──────────────┘
        └───────────┬───────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Stage 4: LLM Response Generation               │
│  (app/orchestrator/nodes/generate_response.py)  │
│  - LangChain ChatOpenAI                         │
│  - Format tool results                          │
│  - Generate natural language                    │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Response to User                               │
└─────────────────────────────────────────────────┘
```

---

## 🛠️ Tools & Functions

### Database Tools (`app/tools/db_tools.py`)
- `get_lead_status` - Get lead by name
- `get_daily_summary` - Daily statistics
- `search_leads` - Search/list leads
- `get_customer_info` - Customer information
- `get_team_kpi` - Team metrics

### RAG Tools (`app/tools/rag_tools.py`)
- Vector search via Supabase RPC
- Document retrieval

### Tool Selection Mechanism
- **Method**: OpenAI Function Calling (Direct API)
- **Location**: `app/orchestrator/llm_router.py`
- **Process**:
  1. LLM วิเคราะห์ message
  2. เลือก tools ผ่าน function calling
  3. Return `selected_tools` list
  4. `db_query_node` execute tools

---

## 📝 State Management (LangGraph)

### State Schema (`app/orchestrator/state.py`)
```python
class AIAssistantState(TypedDict, total=False):
    # User input
    user_message: str
    user_id: str
    user_role: Optional[str]
    session_id: Optional[str]
    
    # Intent (from LLM)
    intent: Optional[str]
    confidence: float
    entities: Optional[Dict[str, Any]]
    selected_tools: List[Dict[str, Any]]  # From LLM function calling
    tool_parameters: Optional[Dict[str, Dict[str, Any]]]
    
    # Results
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    rag_results: List[Dict[str, Any]]
    
    # Response
    response: Optional[str]
    error: Optional[str]
```

---

## 🎯 Key Components

### 1. LLM Router (`llm_router.py`)
- **Technology**: OpenAI API (Direct)
- **Function**: Intent analysis + Tool selection
- **Input**: User message, user_id, user_role
- **Output**: Intent, selected_tools, entities

### 2. LangGraph Workflow (`graph.py`)
- **Technology**: LangGraph StateGraph
- **Function**: Orchestration
- **Nodes**:
  - `router` - LLM intent analysis
  - `db_query` - Execute database tools
  - `rag_query` - Vector search
  - `generate_response` - LLM response generation

### 3. Database Query Node (`nodes/db_query.py`)
- **Technology**: Python async functions
- **Function**: Execute selected tools
- **Process**:
  1. Read `selected_tools` from state
  2. Execute each tool (async)
  3. Collect results
  4. Update state

### 4. Response Generation (`nodes/generate_response.py`)
- **Technology**: LangChain ChatOpenAI
- **Function**: Synthesize final response
- **Process**:
  1. Format tool results
  2. Build prompt with context
  3. Call LLM (LangChain)
  4. Return natural language response

---

## 🔍 Monitoring & Observability

### Current Status
- ✅ **Logging**: ใช้ Python logging
- ❌ **LangSmith**: ไม่ได้ configure
- ❌ **Tracing**: ไม่มี distributed tracing
- ❌ **Metrics**: ไม่มี metrics collection

### Logging Locations
- `app/utils/logger.py` - Logger setup
- All nodes log actions and results
- Structured logging with context

---

## 📦 Dependencies

### LangChain Stack
```python
langchain-core
langchain-openai
langgraph  # For workflow orchestration
```

### Other Key Libraries
```python
openai  # Direct API calls for function calling
supabase  # Database client
httpx  # HTTP client (used by Supabase)
```

---

## 🔄 Algorithm: Tool Selection

### Current Approach: LLM Function Calling

1. **Input**: User message
2. **LLM Analysis** (OpenAI API):
   - Analyze message
   - Understand intent
   - Select tools via function calling
3. **Output**: List of selected tools with parameters
4. **Execution**: Execute tools in sequence

### Tool Schema Format
```python
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_leads",
            "description": "...",
            "parameters": {...}
        }
    },
    ...
]
```

### Advantages
- ✅ LLM understands context better than rules
- ✅ Flexible - can select multiple tools
- ✅ Handles complex queries
- ✅ Self-documenting (tool descriptions guide LLM)

### Disadvantages
- ⚠️ Requires OpenAI API call (cost + latency)
- ⚠️ Not deterministic (LLM may make mistakes)
- ⚠️ Needs good tool descriptions

---

## 🚀 Future Improvements

### Potential Enhancements
1. **LangSmith Integration**
   - Tracing และ monitoring
   - Performance metrics
   - Cost tracking

2. **Caching**
   - Cache LLM responses
   - Cache tool results

3. **Parallel Tool Execution**
   - Execute independent tools in parallel
   - Reduce latency

4. **Error Handling & Retries**
   - Better error recovery
   - Automatic retries with backoff

5. **Streaming Responses**
   - Stream LLM responses to frontend
   - Better UX

---

## 📚 Summary

**Current Stack:**
- **Orchestration**: LangGraph (workflow)
- **LLM Service**: LangChain ChatOpenAI (response generation)
- **Intent Analysis**: OpenAI API Direct (function calling)
- **Monitoring**: Python Logging only (no LangSmith)

**Key Feature:**
- LLM-based tool selection via OpenAI function calling
- LangGraph manages workflow state and flow
- Async tool execution in `db_query_node`
