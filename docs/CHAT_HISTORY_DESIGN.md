# 🎯 Chat History & Context Management Design

## 📋 Overview

ระบบ Chat History ที่ออกแบบมาเพื่อ:
1. **จำประวัติการสนทนา** - เก็บทุกข้อความที่ผู้ใช้และ AI ส่ง
2. **จำบริบทปัจจุบัน** - ส่งประวัติไปให้ LLM เพื่อให้เข้าใจบริบทการสนทนา
3. **รองรับ Multi-turn Conversation** - สนทนาต่อเนื่องได้หลายรอบ

---

## 🗄️ Database Schema

### ตารางที่มีอยู่แล้ว (จาก `20250116000001_initial_schema.sql`)

#### 1. `chat_sessions`
```sql
- id (UUID, PK)
- user_id (UUID, FK → auth.users)
- title (TEXT) - ชื่อ session
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

#### 2. `chat_messages`
```sql
- id (UUID, PK)
- session_id (UUID, FK → chat_sessions)
- role (TEXT) - 'user' | 'assistant' | 'system'
- content (TEXT) - ข้อความ
- metadata (JSONB) - เก็บข้อมูลเพิ่มเติม (intent, tool_calls, citations)
- created_at (TIMESTAMP)
```

### ✅ Schema ปัจจุบันเพียงพอแล้ว ไม่ต้องสร้างใหม่

---

## 🏗️ Architecture Design

### 1. **Service Layer** (`app/services/chat_history.py`)

**หน้าที่:**
- Load chat history จาก database
- Format history เป็น context สำหรับ LLM
- Save messages ลง database
- จัดการ context window (จำกัดจำนวน messages)

**Functions:**
```python
async def load_chat_history(session_id: str, limit: int = 20) -> List[Dict]
async def format_history_for_llm(messages: List[Dict]) -> str
async def save_message(session_id: str, role: str, content: str, metadata: Dict)
async def get_recent_context(session_id: str, max_tokens: int = 2000) -> str
```

### 2. **Context Management Strategy**

#### Strategy 1: **Full History** (สำหรับ session สั้นๆ)
- ส่งประวัติทั้งหมด (จำกัดที่ 20 messages ล่าสุด)
- เหมาะสำหรับ: การสนทนาทั่วไป

#### Strategy 2: **Sliding Window** (สำหรับ session ยาวๆ)
- ส่งเฉพาะ messages ล่าสุดที่พอดีกับ context window
- คำนวณ tokens และตัด messages เก่าออก
- เหมาะสำหรับ: การสนทนาที่ยาวมาก

#### Strategy 3: **Summary + Recent** (สำหรับ session ยาวมาก)
- สรุปประวัติเก่า + ส่ง messages ล่าสุด
- เหมาะสำหรับ: การสนทนาที่ยาวมากๆ (100+ messages)

**Implementation:** เริ่มจาก Strategy 1 (Full History) แล้วปรับเป็น Strategy 2 เมื่อจำเป็น

### 3. **LLM Integration Points**

#### Point 1: **Intent Analysis** (`llm_router.py`)
- ส่ง history context เพื่อให้ LLM เข้าใจบริบท
- ใช้ในการตัดสินใจเลือก tools

#### Point 2: **Response Generation** (`generate_response.py`)
- ส่ง history context เพื่อให้ LLM สร้างคำตอบที่สอดคล้องกับประวัติ
- ใช้ในการอ้างอิงข้อมูลที่เคยพูดถึง

---

## 🔄 Flow Design

### Flow 1: **New Message (with History)**

```
User ส่งข้อความ
    ↓
1. Load Chat History (last N messages)
    ↓
2. Format History → Context String
    ↓
3. ส่ง Context + Current Message → LLM Router
    ↓
4. LLM Router วิเคราะห์ Intent (มี context)
    ↓
5. Execute Tools (ถ้ามี)
    ↓
6. ส่ง Context + Current Message + Tool Results → Generate Response
    ↓
7. Generate Response (มี context)
    ↓
8. Save User Message + AI Response → Database
```

### Flow 2: **Context Format**

**Format สำหรับ LLM:**
```
=== Chat History ===
User: [ข้อความเก่า 1]
Assistant: [คำตอบเก่า 1]

User: [ข้อความเก่า 2]
Assistant: [คำตอบเก่า 2]

...

=== Current Conversation ===
User: [ข้อความปัจจุบัน]
```

---

## 📝 Implementation Plan

### Phase 1: Service Layer ✅
1. สร้าง `app/services/chat_history.py`
2. Implement `load_chat_history()`
3. Implement `format_history_for_llm()`
4. Implement `save_message()`

### Phase 2: LLM Integration ✅
1. แก้ไข `llm_router.py` → รับ history context
2. แก้ไข `generate_response.py` → รับ history context
3. ส่ง context ใน system prompt หรือ messages

### Phase 3: API Integration ✅
1. แก้ไข `/chat` endpoint → load history ก่อน process
2. แก้ไข `/chat/stream` endpoint → load history ก่อน process
3. Save messages หลัง process เสร็จ

### Phase 4: Frontend Integration ✅
1. Load history เมื่อเปิด session
2. แสดง history ใน UI
3. ส่ง `session_id` ทุกครั้งที่ส่งข้อความ

---

## 🎨 Context Window Management

### Token Limit Strategy

**OpenAI Models:**
- `gpt-4o-mini`: ~128K tokens context window
- `gpt-5-mini`: ~128K tokens context window

**Strategy:**
1. จำกัด history ที่ ~1000 tokens (ประมาณ 10-15 messages)
2. ถ้าเกิน ให้ตัด messages เก่าออก
3. เก็บ system prompt + current message + tool results + recent history

**Implementation:**
```python
def estimate_tokens(text: str) -> int:
    # Rough estimate: 1 token ≈ 4 characters
    return len(text) // 4

def trim_history(messages: List[Dict], max_tokens: int) -> List[Dict]:
    total_tokens = 0
    trimmed = []
    
    # Start from most recent
    for msg in reversed(messages):
        msg_tokens = estimate_tokens(msg['content'])
        if total_tokens + msg_tokens <= max_tokens:
            trimmed.insert(0, msg)
            total_tokens += msg_tokens
        else:
            break
    
    return trimmed
```

---

## 🔒 Security & Privacy

### 1. **RLS (Row Level Security)**
- ✅ มีอยู่แล้วใน schema
- Users เห็นได้เฉพาะ history ของตัวเอง

### 2. **Data Retention**
- เก็บ history ไม่จำกัด (หรือตาม policy)
- สามารถลบ session ได้

### 3. **PII Handling**
- History อาจมีข้อมูลส่วนตัว (ชื่อ, เบอร์โทร)
- ใช้ RLS เพื่อป้องกันการเข้าถึงข้อมูลของผู้อื่น

---

## 📊 Performance Considerations

### 1. **Database Queries**
- ใช้ index `idx_chat_messages_session_id` และ `idx_chat_messages_created_at`
- Query: `SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at DESC LIMIT 20`

### 2. **Caching** (Optional)
- Cache history ใน memory สำหรับ session ที่ active
- Invalidate cache เมื่อมี message ใหม่

### 3. **Pagination**
- สำหรับ session ที่มี messages เยอะมาก
- Load แบบ pagination (20 messages ต่อครั้ง)

---

## 🧪 Testing Strategy

### Test Cases

1. **New Session (No History)**
   - ส่งข้อความแรก → ไม่มี history
   - ตรวจสอบว่า LLM ทำงานปกติ

2. **Existing Session (With History)**
   - ส่งข้อความต่อ → มี history
   - ตรวจสอบว่า LLM ใช้ history context

3. **Context Continuity**
   - ส่งข้อความที่อ้างอิงข้อมูลเก่า
   - ตรวจสอบว่า LLM จำได้

4. **Long Session (Many Messages)**
   - ส่งข้อความหลายรอบ
   - ตรวจสอบว่า context window ทำงานถูกต้อง

---

## 📚 Best Practices

### 1. **Context Format**
- ใช้ format ที่ชัดเจน (User/Assistant labels)
- แยก history กับ current message

### 2. **Token Management**
- ตรวจสอบ token count ก่อนส่ง
- ตัด history ถ้าเกิน limit

### 3. **Error Handling**
- ถ้า load history fail → ทำงานต่อได้ (ไม่มี history)
- Log errors แต่ไม่ block user

### 4. **Performance**
- Load history แบบ async
- Cache history ถ้าเป็นไปได้

---

## ✅ Success Criteria

1. ✅ LLM จำประวัติการสนทนาได้
2. ✅ สามารถสนทนาต่อเนื่องได้หลายรอบ
3. ✅ Context window ไม่เกิน limit
4. ✅ Performance ดี (load history < 100ms)
5. ✅ Security ดี (RLS ทำงานถูกต้อง)

---

## 🚀 Next Steps

1. Implement Service Layer
2. Integrate with LLM Router
3. Integrate with Generate Response
4. Update API Endpoints
5. Update Frontend
6. Test & Optimize
