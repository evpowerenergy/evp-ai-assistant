# สรุป: การดึงข้อมูลเมื่อ User ถาม และการเลือกเครื่องมือ

## ภาพรวม Flow

```
User ส่งข้อความ
    ↓
[1] Router (LLM Intent Analysis)
    → วิเคราะห์ intent + เลือก tools (function calling)
    ↓
[2] Route ตาม intent
    ├─ db_query   → ดึงข้อมูลจาก Database (RPC)
    ├─ rag_query  → ค้นเอกสาร (RAG / pgvector)
    ├─ clarify    → ขอคำชี้แจง (confidence ต่ำ)
    └─ direct_answer → ตอบตรง (ทักทาย, วันที่/เวลา, คำศัพท์)
    ↓
[3] ถ้า db_query หรือ rag_query
    → result_grader (ตรวจคุณภาพข้อมูล)
    → ถ้าไม่พอ: rpc_planner ปรับพารามิเตอร์ แล้ว retry db_query
    → ถ้าพอ: generate_response
    ↓
[4] generate_response
    → ใช้ LLM สร้างคำตอบจาก tool_results + rag_results
    ↓
ส่งคำตอบกลับ User
```

---

## 1. การเลือกว่าจะดึงข้อมูลยังไง (Router)

**ที่ใช้:** **LLM-based Intent Router** (`llm_router.py`)  
- ใช้ **OpenAI API + Function Calling**  
- ส่งข้อความ User + รายการ tools (schemas) ให้ LLM  
- LLM ตัดสินใจว่า:
  - ต้อง**ดึงข้อมูล**หรือไม่ → ถ้าใช่ จะ **เลือก tools** และ **ส่งพารามิเตอร์** (เช่น วันที่, status, query)
  - หรือให้ **ตอบตรง** (direct_answer) / **ขอชี้แจง** (clarify)

**ผลที่ได้จาก Router:**
- `intent`: `"db_query"` | `"rag_query"` | `"clarify"` | `"direct_answer"` | `"general"`
- `confidence`: 0–1
- `selected_tools`: รายการ tools ที่ LLM เลือก + parameters
- `tool_parameters`: พารามิเตอร์แยกตาม tool

**กฎใน graph (route_intent):**
- `confidence < 0.3` → **clarify** (ขอคำชี้แจง)
- คำทักทาย / วันที่-เวลา / คำศัพท์ (คืออะไร, definition) และไม่มี tools → **direct_answer**
- มี `selected_tools` และ intent เป็น db → **db_query**
- intent เป็น rag → **rag_query**
- นอกนั้น → **direct_answer** หรือ **general → direct_answer**

---

## 2. เครื่องมือ (Tools) ที่ใช้ดึงข้อมูล

### 2.1 Database (RPC) – ใช้เมื่อ intent = `db_query`

**ที่อยู่:** `app/tools/db_tools.py` → เรียก Supabase RPC

| กลุ่ม | Tool | ใช้เมื่อ |
|--------|------|----------|
| **Leads** | `search_leads` | ค้น/รายการลีด, สถิติ, แยก platform/status, วันที่ (เมื่อวาน/สัปดาห์/เดือน) |
| | `get_lead_status` | สถานะลีด**รายชื่อเดียว** (เช่น ลีดชื่อ John) |
| | `get_my_leads` | ลีดของ**ผู้ใช้ปัจจุบัน** (My Leads) |
| | `get_lead_detail` | รายละเอียดลีดเต็ม (ตาม lead_id) |
| | `get_lead_management` | ข้อมูล Lead Management (จัดการลีด, สถิติ assign) |
| **Sales** | `get_sales_closed` | ยอดขายที่ปิดแล้ว (Sales Closed report) |
| | `get_team_kpi` | KPI ทีม, conversion |
| | `get_sales_team` | รายการทีมขาย + สถิติ |
| | `get_sales_team_list` | รายชื่อทีมขายแบบสั้น (dropdown) |
| | `get_sales_team_data` | ทีมขาย + deals, pipeline |
| | `get_sales_performance` | ผลงานของ**คนขายคนเดียว** (ตาม sales_id) |
| **Appointments** | `get_appointments` | นัดหมายขาย (นัดช่าง, นัดติดตาม, นัดชำระเงิน) |
| | `get_service_appointments` | นัดหมายบริการ/ซ่อม |
| **Documents** | `get_sales_docs` | เอกสารขาย (QT, BL, INV) |
| | `get_quotations` | ใบเสนอราคา |
| **Other** | `get_permit_requests` | คำขออนุญาต |
| | `get_user_info` | ข้อมูล user |

**การเลือก tool จริง:**  
LLM ได้รับ **TOOL_SCHEMAS** (ชื่อ + description + parameters) ใน `llm_router.py` แล้วใช้ **function calling** เลือก tool และส่ง arguments (เช่น `query`, `date_from`, `date_to`, `status`).  
โหนด **db_query_node** รับ `selected_tools` + `tool_parameters` จาก state แล้วไป map เรียกฟังก์ชันใน `db_tools.py` ตามชื่อ tool。

---

### 2.2 เอกสาร (RAG) – ใช้เมื่อ intent = `rag_query`

**ที่อยู่:** `app/tools/rag_tools.py` → `app/services/vector_store.py`  
- **search_documents(query, limit=5)**  
  - ค้นจาก **pgvector** (embedding + similarity)  
  - ได้ chunks เอกสารที่เกี่ยวข้อง + source  
- **format_citations**  
  - แปลงเป็นข้อความ citation ให้แสดงในคำตอบ

ใช้เมื่อคำถามเกี่ยวกับ ขั้นตอน, วิธีทำ, นโยบาย, คู่มือ, SOP, เอกสาร

---

### 2.3 ตอบตรง (ไม่ดึงข้อมูล) – direct_answer

**ที่อยู่:** `app/orchestrator/nodes/direct_answer.py`  
- ไม่เรียก DB หรือ RAG  
- ใช้ **LLM** + context วันที่/เวลาปัจจุบัน  
- ใช้กับ: ทักทาย, ถามวันที่/เวลา, คำศัพท์ (คืออะไร, definition)

---

## 3. การ retry เมื่อข้อมูลไม่พอ (คุณภาพผลลัพธ์)

หลัง **db_query** หรือ **rag_query** จะไม่ส่งตรงไป generate_response ทันที แต่จะผ่าน:

1. **result_grader_node**  
   - ตรวจว่า result ว่าง/ผิดพลาดหรือไม่  
   - ถ้า **ไม่พอ** → ส่งไป **rpc_planner**

2. **rpc_planner_node**  
   - ปรับ/เติม **tool_parameters** (เช่น วันที่, query)  
   - จากนั้นส่งกลับไป **db_query** อีกครั้ง

3. วนได้จนครบ **max_retries** แล้วจะไป **generate_response** ต่อ (แม้ข้อมูลจะยังไม่สมบูรณ์)

ดังนั้น “การดึงข้อมูล” อาจเกิดหลายรอบเมื่อระบบตัดสินใจว่าผลลัพธ์ยังไม่ดีพอ

---

## 4. สรุปสั้น ๆ

| คำถาม | คำตอบ |
|--------|--------|
| **เลือกยังไงว่าจะดึงข้อมูลจากไหน?** | ใช้ **LLM (OpenAI)** วิเคราะห์ intent และ **function calling** เลือก tools จาก TOOL_SCHEMAS |
| **เครื่องมือดึงข้อมูลมีอะไรบ้าง?** | **(1) DB:** RPC ผ่าน `db_tools.py` (search_leads, get_team_kpi, get_appointments ฯลฯ) **(2) เอกสาร:** RAG ผ่าน `rag_tools.py` (vector search) **(3) ไม่ดึง:** direct_answer (LLM + วันที่/เวลา) |
| **พารามิเตอร์ของ tool (วันที่, status ฯลฯ) มาจากไหน?** | LLM ส่งมาจากข้อความ User ผ่าน **tool_parameters** ใน function call |
| **ถ้าผลลัพธ์ว่างหรือไม่พอ?** | **result_grader** ส่งให้ **rpc_planner** ปรับพารามิเตอร์ แล้ว **retry db_query** |

ถ้าอยากให้ลงรายละเอียดส่วนใดเพิ่ม (เช่น แต่ละ tool รับพารามิเตอร์อะไร, หรือ flow retry แบบ step-by-step) บอกได้เลยครับ
