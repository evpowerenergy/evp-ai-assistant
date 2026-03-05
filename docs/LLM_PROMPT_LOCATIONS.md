# 📝 LLM Prompt Locations & Key Files

## 🎯 จุดสำคัญที่ต้องปรับ LLM Prompt

### 1. **Intent Analysis & Tool Selection** (จุดสำคัญที่สุด!)
📁 **File:** `backend/app/orchestrator/llm_router.py`
📍 **Function:** `analyze_intent_with_llm()`
📍 **Lines:** 127-157

**หน้าที่:**
- วิเคราะห์ intent จาก user message
- เลือก tools ที่เหมาะสม
- Extract parameters จาก message

**Prompt Structure:**
```python
system_prompt = f"""You are an intelligent intent analyzer for EV Power Energy CRM system.
...
IMPORTANT: When user asks about data (leads, customers, sales, KPI), you MUST use function calling.
...
Available tools (ALWAYS use function calling for data queries):
1. search_leads: Use this for listing/searching leads...
...
"""
```

**ปรับที่นี่:**
- เพิ่ม/แก้ไข tool descriptions
- เปลี่ยน logic การเลือก tools
- ปรับ instructions สำหรับ LLM

---

### 2. **Response Generation** (จุดสำคัญ!)
📁 **File:** `backend/app/orchestrator/nodes/generate_response.py`
📍 **Function:** `generate_response_node()`
📍 **Lines:** 75-94 (Main prompt)

**หน้าที่:**
- สร้าง final response จาก tool results
- Format ข้อมูลให้เป็น natural language
- ควบคุม tone และ style ของ response

**Prompt Structure:**
```python
prompt = f"""You are a helpful AI assistant for EV Power Energy. Answer the user's question based on the provided context.

User Question: {user_message}

Context Information:
{formatted_context}

Instructions:
- Answer in Thai language
- Be friendly, concise, and helpful
- Use the context information to provide accurate answers
- If the context contains a list (e.g., leads list), show ALL items from the list, don't skip any
- If the context contains contact information (phone numbers, Line ID), include them in your response
- If the context contains data, show ALL available information including phone numbers, names, status, region, etc.
- If the context doesn't contain the answer, use your general knowledge but mention it
- Format the response naturally and conversationally
- When showing lists, include all items mentioned in the context with all available details

Response:"""
```

**ปรับที่นี่:**
- เปลี่ยน tone/style ของ response
- เพิ่ม instructions สำหรับการแสดงข้อมูล
- ปรับ format ของ response

---

### 3. **Tool Response Formatting**
📁 **File:** `backend/app/orchestrator/nodes/generate_response.py`
📍 **Function:** `format_tool_response()`
📍 **Lines:** 139-229

**หน้าที่:**
- Format tool results เป็น text ก่อนส่งให้ LLM
- จัดรูปแบบข้อมูลให้อ่านง่าย

**ปรับที่นี่:**
- เปลี่ยน format ของข้อมูล
- เพิ่ม/ลด fields ที่แสดง
- ปรับ structure ของ formatted text

---

### 4. **RAG Response Formatting**
📁 **File:** `backend/app/orchestrator/nodes/generate_response.py`
📍 **Function:** `format_rag_response()`
📍 **Lines:** 232-250

**หน้าที่:**
- Format RAG results (document search)
- Combine multiple document chunks

---

## 📊 Prompt Flow

```
User Message
    ↓
┌─────────────────────────────────────┐
│ 1. llm_router.py                    │
│    - Analyze intent                 │
│    - Select tools                    │
│    - Extract parameters              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 2. db_query_node.py                 │
│    - Execute selected tools          │
│    - Get data from database          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 3. format_tool_response()            │
│    - Format tool results             │
│    - Convert to readable text        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 4. generate_response_node()          │
│    - Build LLM prompt                │
│    - Include formatted context       │
│    - Generate final response         │
└─────────────────────────────────────┘
    ↓
Final Response
```

---

## 🔧 วิธีปรับ Prompt

### ตัวอย่าง: เปลี่ยน Tone ของ Response

**File:** `backend/app/orchestrator/nodes/generate_response.py`
**Lines:** 83-92

**Before:**
```python
Instructions:
- Answer in Thai language
- Be friendly, concise, and helpful
```

**After:**
```python
Instructions:
- Answer in Thai language
- Be professional, detailed, and comprehensive
- Always include all available data
- Use formal tone
```

---

### ตัวอย่าง: เพิ่ม Tool Description

**File:** `backend/app/orchestrator/llm_router.py`
**Lines:** 50-70

**Before:**
```python
{
    "name": "search_leads",
    "description": "Search or list leads based on query criteria"
}
```

**After:**
```python
{
    "name": "search_leads",
    "description": "Search or list leads based on query criteria. ALWAYS use this when user asks for lists of leads, even if they mention a specific number (e.g., '26 คน'). This tool can return unlimited results."
}
```

---

## 📝 Checklist สำหรับการปรับ Prompt

- [ ] ตรวจสอบ `llm_router.py` - Tool selection logic
- [ ] ตรวจสอบ `generate_response.py` - Response generation prompt
- [ ] ตรวจสอบ `format_tool_response()` - Data formatting
- [ ] ทดสอบ response quality หลังปรับ
- [ ] ตรวจสอบ logs เพื่อดู prompt ที่ส่งไป LLM

---

## 🎯 Quick Reference

| File | Function | Purpose | Priority |
|------|----------|---------|----------|
| `llm_router.py` | `analyze_intent_with_llm()` | Tool selection | ⭐⭐⭐ |
| `generate_response.py` | `generate_response_node()` | Response generation | ⭐⭐⭐ |
| `generate_response.py` | `format_tool_response()` | Data formatting | ⭐⭐ |
| `generate_response.py` | `format_rag_response()` | Document formatting | ⭐ |
