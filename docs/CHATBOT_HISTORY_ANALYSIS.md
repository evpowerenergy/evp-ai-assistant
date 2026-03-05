# การวิเคราะห์ระบบ Chat History ของ AI Assistant

**สถานะ:** ปรับปรุงตามคำแนะนำแล้ว (โหลดประวัติครบเทิร์น + ใส่ history ใน Direct Answer + โหลดครั้งเดียวแล้ว format ใน memory)

## สรุปผลการวิเคราะห์

ระบบ **มีโครงสร้างรองรับประวัติการแชท (chat history)** อยู่แล้ว แต่มี **จุดที่ทำให้ประวัติไม่ถูกนำไปใช้ครบ** ดังนี้

---

## Flow ปัจจุบัน (ที่ทำงานอยู่แล้ว)

1. **API (`chat.py`)**  
   - โหลดประวัติจาก DB: `load_chat_history(session_id, limit=20, exclude_current=True)`  
   - สร้างข้อความสรุป: `get_recent_context(session_id, max_tokens=2000, exclude_current=True)`  
   - ใส่ใน state: `chat_history`, `history_context`

2. **Graph (`graph.py`)**  
   - ส่ง state (รวม `history_context`) เข้า `router_node`  
   - Router เรียก `analyze_intent_with_llm(..., history_context=history_context)`  
   - State ไหลต่อทุก node (LangGraph merge state)

3. **Router / Intent (`llm_router.py`)**  
   - ใช้ `history_context` ใส่ใน system prompt เป็นส่วน "Previous Conversation History"  
   - ใช้สำหรับวิเคราะห์ intent และเลือก tools

4. **Generate Response (`generate_response.py`)**  
   - ใช้ `history_context` จาก state ใส่ใน prompt เป็น "Previous Conversation History"  
   - ใช้เมื่อตอบจาก db_query / rag_query

---

## ปัญหาที่พบ (ทำไมบอทดูเหมือนไม่มีความจำ)

### 1. ใช้ `exclude_current=True` ตอนโหลดประวัติ (สำคัญที่สุด)

**ที่มา:**  
ใน `chat.py` และ `chat_history.py`:

- โหลดประวัติด้วย `exclude_current=True`
- ใน `load_chat_history`: ถ้า `exclude_current=True` จะดึง `limit+1` รายการ แล้ว **ตัดข้อความล่าสุดใน DB ออก** (`result.data[:-1]`)

**ปัญหา:**  
ตอนที่โหลดประวัติคือ **ต้นทางของ request ใหม่** ยังไม่ได้บันทึกข้อความปัจจุบัน (user message ล่าสุด) ลง DB  
ดังนั้น "ข้อความล่าสุดใน DB" คือ **ข้อความจากเทิร์นก่อนหน้า** (user หรือ assistant)

ผลคือ:

- ประวัติที่ส่งเข้า context **ไม่รวมเทิร์นล่าสุดที่คุยไปแล้ว**
- บอทจะ "ลืม" ว่าคุยอะไรไปในข้อความก่อนหน้า

**แนวทางแก้:**  
เมื่อโหลดประวัติเพื่อใช้เป็น **context ของการตอบใน request นี้** ควรโหลด **ทุกข้อความในห้อง** (เทิร์นก่อนหน้าทั้งหมด)  
→ ใช้ `exclude_current=False` ตอนโหลดประวัติสำหรับ context

---

### 2. โหนด Direct Answer ไม่ใช้ประวัติแชท

**ที่มา:**  
`direct_answer_node` (คำทักทาย, คำถามศัพท์, วันที่/เวลา) **ไม่ได้อ่าน `history_context`** จาก state และไม่ได้ใส่ใน prompt

**ผลกระทบ:**  
เมื่อผู้ใช้ถามแบบ general (สวัสดี, ลีดคืออะไร, วันนี้วันที่เท่าไร) บอทจะตอบโดย **ไม่มีบริบทจากแชทก่อนหน้า** ในห้องนั้น

**แนวทางแก้:**  
- อ่าน `history_context` จาก state ใน `direct_answer_node`  
- ใส่ส่วน "Previous Conversation History" ใน prompt (แบบเดียวกับใน `generate_response_node`)  
- ถ้ามีประวัติ ให้บอกใน prompt ว่าให้ตอบให้สอดคล้องกับบริบทการสนทนาที่ผ่านมา

---

### 3. โหนด Clarify (ถามซ้ำ)

โหนด `clarify` อาจจะยังไม่ใช้ `history_context` — ถ้าต้องการให้การถามซ้ำอ้างอิงจากประวัติได้ ควรเช็กและเพิ่ม history ใน prompt ของโหนดนี้ด้วย (ถ้ามีการใช้ LLM ใน clarify)

---

## สิ่งที่ระบบทำถูกต้องแล้ว

- บันทึกข้อความ user/assistant ลง `chat_messages` หลังตอบเสร็จ  
- มี `chat_history` service: `load_chat_history`, `get_recent_context`, `format_history_for_llm`  
- State มี `chat_history` และ `history_context`  
- Router และ Generate Response ใช้ `history_context` ใน prompt แล้ว  
- การจำกัดความยาวด้วย `max_tokens=2000` ใน `get_recent_context` ช่วยไม่ให้ context ยาวเกินไป  

---

## แนวทางปรับปรุงเพิ่มเติม (ถ้าต้องการให้บอท “ฉลาด” ขึ้น)

1. **ไม่ตัดเทิร์นล่าสุด (แก้ exclude_current)**  
   - ใช้ `exclude_current=False` เมื่อโหลดประวัติสำหรับ context ใน request ปัจจุบัน  
   - หรือลบการใช้ `exclude_current` สำหรับ use case นี้ และโหลดแค่ `limit` รายการล่าสุด (เรียงจากเก่าไปใหม่)

2. **ใส่ประวัติใน Direct Answer**  
   - ส่ง `history_context` เข้า prompt ของ `direct_answer_node`  
   - เพิ่มข้อความใน system/user prompt ว่าให้อ้างอิงบริบทการสนทนาก่อนหน้า (และตอบเป็นภาษาไทยให้สอดคล้อง)

3. **รูปแบบประวัติให้ชัดสำหรับ LLM**  
   - รูปแบบปัจจุบันเป็น "User: ... / Assistant: ..." อยู่แล้ว  
   - อาจเพิ่มคำว่า "Previous Conversation" หรือ "ประวัติในห้องนี้" ใน prompt เพื่อให้โมเดลแยกจากข้อความปัจจุบันชัด

4. **ขยายประวัติได้ (ถ้าต้องการ)**  
   - ปัจจุบัน: limit=20, max_tokens=2000  
   - ถ้าห้องแชทยาวมาก อาจเพิ่ม limit หรือ max_tokens แล้วติดตามต้นทุน token และ latency

5. **Sliding window / สรุปประวัติ (ทางเลือก)**  
   - ถ้าประวัติยาวมาก อาจเก็บเทิร์นล่าสุด N คู่เต็มๆ แล้วสรุปเทิร์นเก่ากว่าเป็น paragraph สั้นๆ แล้วค่อยใส่ใน context (ต้องมีขั้นตอนสรุปด้วย LLM หรือ rule)

---

## สรุปสั้นๆ

- ระบบ **มีโครงสร้าง chat history และใช้ใน Router กับ Generate Response แล้ว**  
- ปัญหาหลักที่ทำให้บอทดูเหมือน **ไม่เอาประวัติมาใช้** คือ  
  1) การใช้ **exclude_current=True** ทำให้เทิร์นล่าสุดใน DB ถูกตัดออกจาก context  
  2) **Direct Answer** ไม่ได้ใส่ประวัติใน prompt  
- แก้สองจุดนี้แล้ว บอทจะสามารถ "เอาข้อมูลเก่าในห้องแชทนั้นๆ มาใช้" ได้ดีขึ้น เปรียบเสมือนมีความจำในระดับห้องแชท (session) ตามที่ต้องการ
