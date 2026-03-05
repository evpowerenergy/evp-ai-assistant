# 🎯 Quick Reference: LLM Prompt Locations

## 📍 จุดสำคัญที่ต้องปรับ Prompt

### 1. ⭐⭐⭐ **Intent Analysis & Tool Selection** (สำคัญที่สุด!)

**File:** `backend/app/orchestrator/llm_router.py`  
**Function:** `analyze_intent_with_llm()`  
**Lines:** 127-157

**ปรับที่นี่:**
- Tool descriptions
- Instructions สำหรับ LLM ในการเลือก tools
- Logic การ extract parameters

**ตัวอย่าง:**
```python
system_prompt = f"""You are an intelligent intent analyzer...
IMPORTANT: When user asks about data, you MUST use function calling.
Available tools:
1. search_leads: Use this for listing/searching leads...
"""
```

---

### 2. ⭐⭐⭐ **Response Generation** (สำคัญมาก!)

**File:** `backend/app/orchestrator/nodes/generate_response.py`  
**Function:** `generate_response_node()`  
**Lines:** 75-94

**ปรับที่นี่:**
- Tone และ style ของ response
- Instructions สำหรับการแสดงข้อมูล
- Format ของ response

**ตัวอย่าง:**
```python
prompt = f"""You are a helpful AI assistant...
Instructions:
- Answer in Thai language
- Show ALL items from the list, don't skip any
- Include all available information
"""
```

---

### 3. ⭐⭐ **Tool Response Formatting**

**File:** `backend/app/orchestrator/nodes/generate_response.py`  
**Function:** `format_tool_response()`  
**Lines:** 139-229

**ปรับที่นี่:**
- Format ของข้อมูลก่อนส่งให้ LLM
- Fields ที่แสดง
- Structure ของ formatted text

---

## 🚫 Limits ที่แก้ไขแล้ว

### ✅ แก้ไขแล้ว:

1. **Backend Tool Limit**
   - File: `backend/app/tools/db_tools.py`
   - Changed: `p_limit: 100` → `p_limit: None`

2. **RAG Results Limit**
   - File: `backend/app/orchestrator/nodes/generate_response.py`
   - Changed: `rag_results[:3]` → `rag_results` (no limit)
   - Changed: `content[:300]` → `content` (no character limit)

3. **RPC Function Limit**
   - Migration: `20250117000006_remove_all_limits.sql`
   - Changed: `p_limit = 100` → `p_limit = NULL` (default)
   - Changed: `LIMIT 10000` → `LIMIT 100000` (practically unlimited)

---

## 📝 วิธีปรับ Prompt

### ตัวอย่าง 1: เปลี่ยน Tone

**File:** `backend/app/orchestrator/nodes/generate_response.py`  
**Line:** 84

```python
# Before
- Be friendly, concise, and helpful

# After
- Be professional, detailed, and comprehensive
- Always provide complete information
```

### ตัวอย่าง 2: เพิ่ม Tool Description

**File:** `backend/app/orchestrator/llm_router.py`  
**Line:** 52

```python
{
    "name": "search_leads",
    "description": "Search or list leads. Returns ALL matching results, no limit. Use when user asks for lists of leads."
}
```

---

## 🔍 Debug: ดู Prompt ที่ส่งไป LLM

**ดูใน Backend Logs:**
```
💬 [STEP 4/4] Generate Response Node: Creating LLM response
   User message: ...
   Tool results: ...
```

**หรือเพิ่ม logging:**
```python
logger.info(f"📝 LLM Prompt:\n{prompt}")
```

---

## ✅ Checklist

- [ ] ตรวจสอบ `llm_router.py` - Tool selection
- [ ] ตรวจสอบ `generate_response.py` - Response prompt
- [ ] ตรวจสอบ `format_tool_response()` - Data formatting
- [ ] Run migration `20250117000006_remove_all_limits.sql`
- [ ] ทดสอบ response quality
