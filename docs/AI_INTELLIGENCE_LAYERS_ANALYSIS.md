# การวิเคราะห์ชั้นความฉลาดของ Chatbot (AI Intelligence Layers)

## คำถามสำคัญ: มี AI กี่ตัว? ตัวไหนต้องฉลาด?

### สรุปสั้น ๆ

- **ไม่ใช่ AI 2 ตัวแยกกัน** สำหรับ “วิเคราะห์ intent” กับ “เลือก tools”  
  ระบบใช้ **AI ตัวเดียว (Router)** ทำงาน **ครั้งเดียว** โดยใช้ **Function Calling** ให้ LLM ทั้งวิเคราะห์ intent และเลือก tools + ส่ง parameters พร้อมกัน

- **ชั้นที่ต้องฉลาดเพื่อให้ Chatbot ดีขึ้น (เรียงความสำคัญ):**
  1. **Router (Intent + Tool Selection + Parameters)** — ตัวเดียว ทำ 3 อย่าง: วิเคราะห์ intent, เลือก tools, กำหนด parameters
  2. **Result Grader** — ตรวจคุณภาพผล RPC และแนะนำ retry
  3. **Generate Response** — แปลงข้อมูลเป็นคำตอบภาษาไทย
  4. **RPC / Query ฝั่ง Backend** — ถ้า SQL หรือ logic ใน RPC ผิด แม้เลือก tool ถูก คำตอบก็ผิด

---

## 1. โครงสร้าง AI ในระบบ (มีกี่จุดที่เรียก LLM)

| ลำดับ | โหนด / จุดเรียก | ใช้ LLM หรือไม่ | หน้าที่ |
|------|------------------|-----------------|--------|
| 1 | **Router** (`llm_router.analyze_intent_with_llm`) | ✅ ใช่ (1 ครั้ง) | วิเคราะห์ intent + **เลือก tools** + **ส่ง parameters** (ผ่าน Function Calling) |
| 2 | **db_query_node** / **rag_query_node** | ❌ ไม่ใช้ | เรียก RPC / RAG ตามที่ Router เลือก |
| 3 | **Result Grader** (`grade_result_with_llm`) | ✅ ใช่ (1 ครั้ง) | ตรวจว่า result พอตอบคำถามไหม + แนะนำพารามิเตอร์ retry |
| 4 | **RPC Planner** | ❌ ไม่ใช้ LLM | ใช้แค่ logic: นำ `suggested_retry_params` จาก Grader ไปอัปเดต `tool_parameters` แล้ว retry db_query |
| 5 | **Generate Response** | ✅ ใช่ (1 ครั้ง) | รับ tool_results + RAG → สร้างคำตอบภาษาไทย |
| 6 | **Direct Answer** | ✅ ใช่ (1 ครั้ง) | ตอบคำถามที่ไม่ต้องดึงข้อมูล (ทักทาย, วันที่, คำศัพท์) |

ดังนั้น:
- **“AI ตัวแรก”** = Router ตัวเดียว: รับข้อความ user → **ทั้งวิเคราะห์ intent และเลือก tools + parameters** ใน response เดียว (tool_calls)
- **ไม่มี “AI อีกตัวแยก” สำหรับเลือก tools** — การเลือก tools อยู่ใน Router call เดียวกัน

---

## 2. ชั้นที่ 1: Router (Intent + Tool Selection + Parameters)

### 2.1 ทำงานอย่างไร

- ไฟล์: `app/orchestrator/llm_router.py`
- เรียก OpenAI หนึ่งครั้ง โดยส่ง:
  - ข้อความ user
  - System prompt จาก `get_intent_analyzer_prompt()` (คำศัพท์ CRM, ตัวอย่าง intent/tool)
  - **TOOL_SCHEMAS**: รายการ tools แต่ละตัวมี `name`, `description`, `parameters` (type, description, required, enum ฯลฯ)
- ใช้ **Function Calling** (`tool_choice="auto"`): LLM ตอบด้วย `tool_calls` ที่มี `function.name` และ `function.arguments` (JSON)
- โค้ดดึงจาก response:
  - มี `tool_calls` → intent = `db_query`, ใช้ `selected_tools` + `tool_parameters`
  - ไม่มี tool_calls + เป็นคำทักทาย/วันที่/คำศัพท์ → intent = `direct_answer`

ดังนั้น **description และ parameters ใน TOOL_SCHEMAS เป็นตัวกำหนดว่า “AI ตัวแรก” จะเลือก tool ไหนและส่ง parameter อะไร**

### 2.2 สิ่งที่ทำให้ Router ฉลาดขึ้น

| ปัจจัย | ที่อยู่ | ผลถ้าดี / แย่ |
|--------|--------|----------------|
| **Tool description** | `llm_router.py` → `TOOL_SCHEMAS[].function.description` | อธิบายชัดว่า tool ใช้เมื่อไหร่ กับคำถามแบบไหน → เลือก tool ถูก; ถ้าเลือนหรือสั้นเกินไป → เลือกผิดหรือไม่เลือก |
| **Parameter schema** | `TOOL_SCHEMAS[].function.parameters` (properties, required, enum) | ชัดเจน → ส่ง date_from/date_to, status, query ถูก; ถ้า required/enum ไม่ตรงกับ RPC → ส่งค่าผิดหรือขาด |
| **System prompt (Intent)** | `system_prompt.get_intent_analyzer_prompt()` | ตัวอย่างเช่น “ปิดการขายได้กี่ราย” → ใช้ search_leads + status='ปิดการขาย' → intent กับ tool ตรงกับธุรกิจ |
| **คำศัพท์ / บริบท** | `get_system_context()` ใน system prompt | ให้ความหมาย Lead, Platform, Status ฯลฯ → แปลคำพูด user เป็น intent และ parameters ได้ตรง |

สรุป: **การทำให้ Chatbot ฉลาดขึ้นที่ชั้นนี้ = ปรับ description, parameter schema และ system prompt ของ Router ให้ตรงกับคำถามจริงและกับ RPC ที่ backend คาดหวัง**

---

## 3. ชั้นที่ 2: Result Grader (คุณภาพผล RPC + Retry)

### 3.1 ทำงานอย่างไร

- ไฟล์: `app/orchestrator/nodes/result_grader.py`
- หลัง db_query หรือ rag_query ได้ `tool_results` แล้ว เรียก `grade_result_with_llm(user_message, tool_results, previous_attempts)`
- LLM ตอบเป็น JSON: `quality` (sufficient / insufficient / empty / error), `reason`, `suggested_retry_params` (เช่น query ใหม่, fuzzy)
- ถ้า quality ไม่พอ และยังไม่เกิน max_retries → ส่ง state ไป **rpc_planner** (อัปเดต parameters) แล้ว **retry db_query**

### 3.2 สิ่งที่ทำให้ Grader ฉลาดขึ้น

| ปัจจัย | ผลถ้าดี / แย่ |
|--------|----------------|
| **Prompt ใน grade_result_with_llm** | กำหนดเกณฑ์ว่าเมื่อไหร่ถือว่า “พอตอบคำถาม” เมื่อไหร่ “ว่าง/ไม่พอ” → ถ้ากำหนดดี retry เกิดเฉพาะเมื่อจำเป็น |
| **การตัดสิน empty vs insufficient** | ถ้า RPC คืนโครงสร้างถูกแต่ไม่มีข้อมูล (เช่น lead ไม่มีในระบบ) ควรเป็น empty ไม่ใช่ error → retry strategy ต่างกัน |
| **suggested_retry_params** | ถ้าแนะนำ query/parameter สำหรับ retry ได้ตรง (เช่น แก้คำสะกด, ขยายช่วงวันที่) → รอบถัดไปได้ข้อมูลที่ดีขึ้น |

สรุป: **ความฉลาดชั้นนี้ = วิเคราะห์ว่า “ผลจาก RPC ที่ได้ มันเพียงพอจะตอบคำถาม user หรือไม่” และ “ควร retry ด้วย parameter อะไร”** — ไม่ได้วิเคราะห์ว่า SQL ใน RPC ถูกหรือผิด แต่วิเคราะห์ผลที่ได้

---

## 4. ชั้นที่ 3: RPC / Query ฝั่ง Backend (การเขียน query ถูกต้อง)

### 4.1 อยู่ตรงไหน

- **RPC ฝั่ง Supabase**: ฟังก์ชันใน DB เช่น `ai_get_sales_closed`, `ai_get_lead_status`, `ai_search_leads` ฯลฯ — แต่ละตัวมี SQL / PL/pgSQL ข้างใน
- **Python**: `app/tools/db_tools.py` เป็นตัว **map parameters จาก Router** (และจาก state) ไปเป็น argument ของ RPC (เช่น `p_user_id`, `p_date_from`, `p_date_to`, `p_status`)

ดังนั้น “การวิเคราะห์ว่า RPC มีการเขียน query ได้ถูกใช่ไหม” = ตรวจสองชั้น:
1. **การ map parameter** ใน `db_tools.py`: ค่าที่ส่งเข้า RPC ตรงกับที่ฟังก์ชันคาดหวังไหม (ชื่อ, type, หน่วยเวลา ฯลฯ)
2. ** logic / SQL ใน RPC**: filter, join, นับจำนวน, ช่วงวันที่ (timezone, วันไทย) ตรงกับความหมายของคำถามและกับ frontend ไหม

### 4.2 สิ่งที่ทำให้ชั้นนี้ “ถูกต้อง”

| ชั้น | สิ่งที่ต้องตรวจ |
|------|------------------|
| **db_tools.py** | รับ `date_from`/`date_to` จาก LLM (มักเป็น YYYY-MM-DD) → แปลงเป็น timestamp / timezone ที่ RPC ใช้ (เช่น Thai 00:00–23:59) ได้ตรงไหม; ส่ง `status`, `query` ฯลฯ ตรงกับ signature RPC ไหม |
| **RPC (SQL)** | WHERE, JOIN ตรงกับนิยามธุรกิจไหม (เช่น “ปิดการขาย” = leads.status vs productivity_log.status); นับซ้ำ/หายไปไหม; กรณีไม่มีข้อมูล คืน `success: true` + array ว่าง หรือ error ตรงกับที่ Grader/Generate Response คาดไว้ไหม |

ถ้า RPC หรือ map parameter ผิด แม้ Router เลือก tool ถูกและส่ง parameter ถูกตามที่ user ตั้งใจ ผลลัพธ์ที่ได้ก็ยังผิด ดังนั้น **ความถูกของ RPC และการ map parameter เป็นฐานของความฉลาดที่มองจากผลลัพธ์**

---

## 5. ชั้นที่ 4: Generate Response (แปลข้อมูลเป็นคำตอบ)

### 5.1 ทำงานอย่างไร

- ไฟล์: `app/orchestrator/nodes/generate_response.py`
- รับ `tool_results`, `rag_results`, `user_message` จาก state
- ใช้ system prompt จาก `get_response_generator_prompt()` + context ที่รวมผลจาก tools/RAG
- เรียก LLM สร้างข้อความตอบเป็นภาษาไทย

### 5.2 สิ่งที่ทำให้ชั้นนี้ฉลาดขึ้น

- **System prompt**: บอกให้แสดงข้อมูลครบ (เช่น list ไม่ข้าม, มีเบอร์โทร ถ้ามี), ตอบเป็นภาษาไทย, อ้างอิง citation ถ้ามี
- **การจัดรูปแบบ context** ที่ส่งเข้า LLM: ถ้าตัดหรือย่อผล RPC มากเกินไป คำตอบอาจขาดรายละเอียดหรือผิดบริบท

---

## 6. สรุป: AI กี่ตัว และอะไรที่ต้องฉลาด

### 6.1 จำนวน “AI” ที่เกี่ยวกับการเลือก tools และ intent

- **AI ตัวเดียว** ที่รับผิดชอบ **ทั้ง** การวิเคราะห์ intent **และ** การเลือก tools (และ parameters) คือ **Router** (หนึ่งครั้งเรียก OpenAI พร้อม TOOL_SCHEMAS)
- **ไม่มี AI อีกตัวแยก** ที่เฉพาะ “เลือก tools” — การเลือก tools อยู่ใน response เดียวกับ intent (ผ่าน tool_calls)

### 6.2 สิ่งที่ต้องฉลาด/ถูกต้อง (เรียงตามความสำคัญต่อผลลัพธ์)

1. **Router (AI ตัวแรกและตัวเดียวสำหรับ intent + tools)**  
   - ปรับ: **description ของแต่ละ tool**, **parameter schema** (ชื่อ, type, required, enum), **system prompt** (ตัวอย่างคำถาม–tool–parameter, คำศัพท์ CRM)  
   → เลือก tool ถูก และส่ง parameter ตรงกับที่ RPC ต้องการ

2. **Result Grader (AI ชั้นที่สองใน pipeline)**  
   - ปรับ: **prompt การให้คะแนนคุณภาพ** และ **การแนะนำ retry parameters**  
   → ตัดสินได้ว่าเมื่อไหร่ผลพอตอบคำถาม เมื่อไหร่ควร retry และ retry ด้วยค่าอะไร

3. **RPC และการ map parameter (ไม่ใช่ LLM แต่เป็น logic/SQL)**  
   - ตรวจ: **การ map ใน db_tools.py** กับ **SQL/logic ใน RPC** (filter, join, วันที่, สถานะ)  
   → ถ้า RPC หรือ map ผิด คำตอบจะผิดแม้ Router จะเลือก tool ถูก

4. **Generate Response**  
   - ปรับ: **system prompt** และ **การจัด context**  
   → คำตอบอ่านง่าย ครบ และสอดคล้องกับข้อมูล

ถ้าจะ “ทำให้ Chatbot ฉลาดขึ้น” แนะนำโฟกัสตามลำดับ: (1) Router descriptions + parameters + prompt, (2) Result Grader prompt, (3) ความถูกต้องของ RPC และการ map parameter, (4) Generate Response prompt และ context formatting.
