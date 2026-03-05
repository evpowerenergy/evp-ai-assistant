# การวิเคราะห์: ตัวเลข Package / Wholesales จาก AI ไม่ตรงกับหน้า /reports/sales-closed

---

## เรื่องวันที่: หน้า /reports/sales-closed ใช้อ้างอิงจาก table ไหน

**คำตอบ:** ใช้อ้างอิงจาก **table `lead_productivity_logs`** และใช้ field **`created_at_thai`** ในการกรองช่วงวันที่

- เอกสารใน CRM: `docs/analysis/SALES_CLOSED_DATE_FIELD_ANALYSIS.md` ระบุชัดว่า หน้า Sales Closed ใช้ `getSalesDataInPeriod()` ซึ่ง query จาก `lead_productivity_logs` โดยกรอง `created_at_thai >= startDate AND created_at_thai <= endDate`
- ใน `src/utils/salesUtils.ts` ใช้ `.gte('created_at_thai', startDate)` และ `.lte('created_at_thai', endDate)` บน `lead_productivity_logs`
- ดังนั้น **ความเข้าใจถูก:** วันที่ที่ใช้ในรายงานยอดปิดการขายให้อ้างอิงจาก **`lead_productivity_logs.created_at_thai`** ตามที่หน้านี้ใช้

---

## เคสจากภาพ: ขอยอดขายเดือน ธค 68 (ธ.ค. 2025)

### ตัวเลขที่เห็นจากภาพ

| | AI สรุป | หน้า /reports/sales-closed (fn) |
|--|--------|----------------------------------|
| **ช่วงวันที่ที่แสดง** | 2025-12-01 ถึง **2025-12-29** | 01 ธ.ค. 2025 – **31** ธ.ค. 2025 |
| **Package (QT)** | 15 QT | **14** QT |
| **Package (บาท)** | 1,578,445.59 | **1,666,346.12** |
| **Wholesales (QT)** | 28 QT | **29** QT |
| **Wholesales (บาท)** | 1,557,887.60 | **1,469,987.07** |
| **รวม QT** | 43 | 43 ✓ |
| **รวมบาท** | 3,136,333.19 | 3,136,333.19 ✓ |

- ฟังก์ชันถูกเรียกด้วย `date_from: "2025-12-01"`, `date_to: "2025-12-31"` (เต็มเดือน) แต่ AI บอกว่า "ข้อมูลช่วง 2025-12-01 ถึง 2025-12-**29**"
- สถานะการทำงานแสดง **"ข้อมูลไม่เพียงพอ"** (Data insufficient) หลังดึงข้อมูล  
  - ค่านี้มาจาก **result_grader** (`grade_result_with_llm`): LLM ประเมิน quality เป็น `"insufficient"` เมื่อคิดว่าข้อมูลมีอยู่แต่ตอบคำถามไม่ครบ (เช่น output ถูก truncate ใน context ให้ grader เห็นแค่ 500 ตัวอักษร, หรือ structure ไม่ตรงที่คาด เช่น มี salesLogs แต่ไม่มี salesLeads)

### ความคลาดเคลื่อนที่สังเกตได้

1. **ช่วงวันที่ในข้อความ (29 vs 31)**  
   - ระบบส่งพารามิเตอร์ `date_to: "2025-12-31"` แต่คำตอบเขียนว่า "2025-12-01 ถึง 2025-12-**29**"  
   - เป็นไปได้ว่า: (ก) RPC/ข้อมูลที่ได้มาจริงมีแค่ถึงวันที่ 29 แล้ว LLM สรุปตามนั้น, (ข) LLM สรุปจากวันที่ล่าสุดใน raw โดยไม่ควร, หรือ (ค) มีการตัด/กรองข้อมูลก่อนถึง LLM  
   - หน้า fn ใช้ช่วง 1–31 ธ.ค. ดังนั้นถ้าจะให้ตรง fn ต้องได้ข้อมูลถึง 31 และข้อความต้องไม่บอกแค่ถึง 29

2. **การแยก Package / Wholesales ยังไม่ตรง fn**  
   - แม้รวม 43 QT และ 3,136,333.19 บาทจะตรง แต่แยก category ผิด: AI ได้ Package 15 QT / 1,578,445.59, Wholesales 28 QT / 1,557,887.60 ขณะที่ fn เป็น Package **14** QT / **1,666,346.12**, Wholesales **29** QT / **1,469,987.07**  
   - แสดงว่าแหล่งที่มาของการแยก category (และ/หรือการนับ QT ต่อ category) ระหว่าง AI กับหน้า /reports/sales-closed ยังไม่เหมือนกัน

3. **โครงสร้าง raw ที่เห็นในภาพ**  
   - ในภาพ raw output แสดง `data.salesLogs[]` ที่ข้างในมี `lead`  
   - ฝั่ง evp-ai-assistant อ่าน `data.salesLeads`  
   - ถ้า RPC ส่งแค่ `salesLogs` (ไม่มี `salesLeads`) โค้ดจะได้ `salesLeads = []` แล้วอาจไปใช้ข้อมูลจากที่อื่นหรือ LLM สรุปจาก raw อีกแบบ → ตัวเลขแยก category อาจไม่ตรงกับ fn ที่คำนวณจาก `salesLeads` แบบเดียวกับ `getSalesDataInPeriod()`

### สรุปเคสจากภาพ (ก่อนแก้โค้ด)

- **วันที่:** ควรอ้างอิงจาก `lead_productivity_logs.created_at_thai` และช่วงที่รายงานควรเป็น 1–31 ธ.ค. ตาม fn; ข้อความว่า "ถึง 2025-12-29" จึงคลาดเคลื่อนและน่าตรวจว่าเกิดจากข้อมูลหรือจากข้อความที่ LLM สรุป
- **การแยก Package/Wholesales:** ยังคลาดเคลื่อนจาก fn (ทั้งจำนวน QT และยอดบาท) แม้ยอดรวมจะตรง — น่าจะมาจาก (1) โครงสร้าง/ชุดข้อมูลที่ RPC ส่งมาไม่ตรงกับที่ fn ใช้ (เช่น salesLogs vs salesLeads, หรือการ aggregate ต่อ category ไม่เหมือน getSalesDataInPeriod), หรือ (2) การคำนวณ/สรุปฝั่ง AI ยังไม่ยึด logic เดียวกับหน้า /reports/sales-closed

---

## สาเหตุจากเหตุการณ์นี้ (เคสภาพ ธ.ค. 68) — วิเคราะห์ว่ามาจากอะไรได้บ้าง

จาก flow โค้ดที่ตรวจแล้ว สาเหตุที่เป็นไปได้แยกตามประเด็นดังนี้

### ก. ตัวเลข Package / Wholesales ไม่ตรง fn (15 vs 14, 28 vs 29, ยอดบาทต่างกัน)

| สาเหตุที่เป็นไปได้ | รายละเอียด | วิธีตรวจ |
|-------------------|------------|----------|
| **1) RPC ส่ง `salesLogs` แทน `salesLeads`** | ภาพ raw แสดง `data.salesLogs[]` ข้างในมี `lead`. โค้ด evp-ai-assistant อ่านแค่ `output["data"]["salesLeads"]` → ถ้า RPC ส่งแค่ `salesLogs` จะได้ `salesLeads = []`. ฝั่ง `format_tool_response` จะคำนวณ category summary จาก list ว่าง → ได้ Package 0, Wholesales 0. แต่ LLM ได้ **raw JSON ทั้งก้อน** ใน context จึงอาจไปนับ/รวมจาก `salesLogs` เอง → ถ้า LLM **นับจำนวนแถว** ต่อ category (แทน sum(totalQuotationCount)) จะได้ตัวเลขคนละแบบกับ fn (เช่น 15 vs 14, 28 vs 29). | ดู response จริงของ RPC ว่ามี key `salesLeads` หรือ `salesLogs`; ดูว่า `format_tool_response` ได้ `sales_leads` กี่รายการ. |
| **2) โครงสร้างใน `salesLogs` ไม่ตรงกับ `salesLeads`** | ถ้า RPC ส่ง `salesLogs` เป็น array ของ `{ lead: { ... } }` และไม่มี `totalQuotationCount` / `totalQuotationAmount` / `category` ในระดับที่ LLM หรือ frontend ใช้ การนับ/รวมของ LLM จะผิด. หรือ 1 แถวใน salesLogs = 1 QT ในขณะที่ fn ใช้ 1 แถวต่อ 1 log (อาจมีหลาย QT) → นิยาม "จำนวน QT" ไม่ตรง. | เปรียบเทียบ schema ของ RPC กับที่ `getSalesDataInPeriod()` สร้างใน frontend. |
| **3) RPC ใช้ logic/แหล่งข้อมูลคนละแบบกับ fn** | หน้า fn ใช้ `lead_productivity_logs` + `created_at_thai` และ one row per log พร้อม `totalQuotationCount`, `totalQuotationAmount`, `category`. ถ้า RPC ใช้ table อื่น หรือ aggregate แบบ group by lead / แบบอื่น จำนวนและยอดต่อ category จะไม่ตรง fn แม้ยอดรวมใกล้เคียง. | ตรวจ definition ของ RPC `ai_get_sales_closed` (Supabase/backend CRM) ว่าใช้ table/field/aggregation เดียวกับ `getSalesDataInPeriod()` หรือไม่. |
| **4) Pre-compute ไม่ถูกใช้** | แม้ RPC ส่ง `salesLeads` ครบ ถ้า `output.success` หรือ `output.data` เป็นรูปแบบที่โค้ดอ่านไม่ตรง (เช่น ข้อมูลอยู่ที่ root ไม่ใช่ `output.data`) จะได้ `sales_leads = []` → ไม่มี category_summary_text ที่ถูกต้อง → LLM ต้องสรุปจาก raw เองและอาจนับผิด. | ดูว่าในเคสนี้ `format_tool_response` เข้า branch ที่มี `category_summary_text` หรือไม่ และ `sales_leads` มีกี่รายการ. |

### ข. ข้อความว่า "ข้อมูลช่วง 2025-12-01 ถึง 2025-12-**29**" (ไม่ใช่ 31)

| สาเหตุที่เป็นไปได้ | รายละเอียด | วิธีตรวจ |
|-------------------|------------|----------|
| **1) ข้อมูลจาก RPC มีแค่ถึงวันที่ 29** | RPC กรองด้วย field วันที่ที่ไม่อิง `created_at_thai` หรือมี bug ทำให้ข้อมูลหลัง 29 ไม่ถูกคืน → วันที่ล่าสุดใน raw = 29 → LLM สรุปตามนั้น. | ดู raw ว่ามี record วันที่ 30–31 หรือไม่; ตรวจ RPC ว่าใช้ `created_at_thai` และช่วง [date_from, date_to] ครบหรือไม่. |
| **2) LLM สรุปช่วงจากวันที่ใน raw** | ข้อมูลครบถึง 31 แต่ไม่มี record ในวันที่ 30–31 (ไม่มีธุรกรรม) → วันที่ล่าสุดใน array = 29 → LLM เข้าใจผิดว่า "ช่วงข้อมูล = ถึง 29" แทนที่จะยึดพารามิเตอร์ `date_to: 2025-12-31`. | กำหนดใน prompt ว่าให้ระบุช่วงจาก **พารามิเตอร์ที่ส่งให้ tool** (date_from / date_to) ไม่ใช่จาก min/max date ใน raw. |

### ค. สถานะ "ข้อมูลไม่เพียงพอ"

| สาเหตุที่เป็นไปได้ | รายละเอียด | วิธีตรวจ |
|-------------------|------------|----------|
| **1) Result grader ได้ context แค่ ~500 ตัวอักษร** | ใน `result_grader.py` สำหรับ tool ที่ไม่ใช่ sales team จะส่ง `str(output)[:500]` → grader เห็นแค่ส่วนต้นของ JSON อาจไม่มี key `salesLeads` หรือเห็นแค่ `salesLogs` แล้วตัดว่า "ข้อมูลไม่ครบ". | ดูว่า get_sales_closed ถูก treat เป็น sales team tool หรือไม่ (ตอนนี้ไม่ใช่) → output ถูก truncate ที่ 500 ตัวอักษร. |
| **2) Grader เห็น structure ไม่ตรง** | ถ้า RPC คืน `salesLogs` โดยไม่มี `salesLeads` grader อาจตอบ "insufficient" เพราะไม่เห็น array ที่คาดไว้. | ดู prompt ของ grader และตัวอย่าง output ที่ได้ quality = insufficient. |

---

**สรุปสั้น ๆ:** สาเหตุหลักที่น่าจะทำให้ตัวเลข Package/Wholesales ผิดคือ **(ก.1) RPC ส่ง salesLogs แทน salesLeads** ทำให้ pre-compute ได้ 0/0 และ LLM ไปนับ/รวมจาก raw เอง (และนับแถวแทน sum(totalQuotationCount)). สาเหตุเรื่องวันที่ "ถึง 29" น่าจะเป็น **(ข.1)** ข้อมูลจริงถึงแค่ 29 หรือ **(ข.2)** LLM สรุปจากวันที่ใน raw. สาเหตุ "ข้อมูลไม่เพียงพอ" น่าจะเป็น **(ค.1)** output ถูก truncate ตอนส่งให้ grader.

---

## สรุปปัญหา (เคสเดิม)

**คำถามผู้ใช้:** อยากรู้ว่า package หรือ wholesales ปิดได้กี่ลีด และยอดขายกี่บาท (เดือนมกรา 2026)

**ผลจาก AI:**
- Package: 29 ลีด, ฿5,016,407.13
- Wholesales: 25 ลีด, ฿1,717,407.00
- รวม: 54 ลีด, ฿6,733,814.13

**ผลจากหน้า /reports/sales-closed (ช่วง 01 ม.ค. – 31 ม.ค. 2026):**
- Package: 15 QT, ฿3,321,854.85
- Wholesales: 39 QT, ฿3,411,959.28
- รวม: 54 QT, ฿6,733,814.13

**สิ่งที่ตรง:** ยอดรวม (54 รายการ, ฿6,733,814.13)  
**สิ่งที่ไม่ตรง:** การแยก Package vs Wholesales ทั้งจำนวนและยอดเงิน

---

## สาเหตุที่เป็นไปได้ (วิเคราะห์จากโค้ด)

### 1. นิยาม "จำนวนลีดที่ปิด" ไม่ตรงกับหน้ารายงาน

- **หน้า /reports/sales-closed** นับ **จำนวน QT ที่ปิด** (รายการปิดการขาย) ไม่ใช่นับ "จำนวน lead" หรือ "จำนวนแถว"
  - ใน `SalesClosed.tsx` และ `salesUtils.ts`:  
    `salesCount = sum(lead.totalQuotationCount)` สำหรับทุกแถวใน `salesLeads`  
    และแยกตาม category โดย `summary.salesCount += lead.totalQuotationCount`, `summary.totalSalesValue += lead.totalQuotationAmount`
  - ดังนั้น "54" บนหน้ารายงาน = จำนวน **QT** ที่ปิด ไม่ใช่จำนวน unique lead หรือจำนวนแถวในตาราง
- **AI** ได้ context เป็น raw JSON จาก `get_sales_closed` (มี `salesLeads`, `totalSalesValue`, `salesCount`) และต้องสรุปเอง
- **ความเป็นไปได้สูง:** LLM นับ **จำนวนแถว (rows)** ใน `salesLeads` แยกตาม category แล้วเรียกว่า "จำนวนลีดที่ปิด"
  - ถ้า RPC ส่งมา 54 แถว (แถวละ 1 log) และแบ่งเป็น 29 แถว category=Package, 25 แถว category=Wholesales → จะได้ 29 กับ 25
  - ในขณะที่หน้ารายงานใช้ **sum(totalQuotationCount)** ต่อ category → ได้ 15 (Package) และ 39 (Wholesales)
- **สรุป:** ถ้า AI ใช้ "จำนวนแถว" แทน "sum(totalQuotationCount)" ต่อ category ตัวเลขจะไม่ตรงกับหน้ารายงานโดยเฉพาะเมื่อ 1 log มีหลาย QT (`totalQuotationCount > 1`)

### 2. โครงสร้างข้อมูลจาก RPC กับ Frontend อาจไม่เหมือนกัน

- **Frontend** ใช้ `getSalesDataInPeriod()` ใน `salesUtils.ts`:
  - ดึงจาก `lead_productivity_logs` + `quotation_documents` + dedupe ตาม `document_number`
  - สร้าง **salesLeads = หนึ่งแถวต่อหนึ่ง log** (ไม่ group by leadId)
  - แต่ละแถวมี: `category`, `totalQuotationCount`, `totalQuotationAmount`, `logId`, `leadId`, ...
  - แยกรายงานตาม category โดย **sum(totalQuotationCount)** และ **sum(totalQuotationAmount)**
- **AI** ใช้ RPC `ai_get_sales_closed` (evp-ai-assistant เรียกที่ `db_tools.get_sales_closed` → Supabase RPC)
  - ไม่มี source ของ RPC ใน repo CRM ที่ค้นได้ ดังนั้นไม่ยืนยันได้ว่า logic และ structure เหมือน frontend
- **ความเป็นไปได้:** ถ้า RPC ส่งข้อมูลแบบ **group by leadId** (หนึ่งแถวต่อหนึ่ง lead พร้อมยอดรวมของ lead นั้น):
  - จำนวนแถวจะ = จำนวน lead ที่ปิด (เช่น 29 Package leads, 25 Wholesales leads)
  - ยอดเงินต่อแถวจะรวมทุก QT ของ lead นั้น → การ sum ต่อ category อาจให้ผลต่างจาก frontend ที่แยกตาม log
- **ผล:** แม้ยอดรวม 54 และ ฿6.7M จะตรง การแยก Package/Wholesales ทั้งจำนวนและยอดอาจผิดถ้า RPC aggregate คนละแบบกับ frontend

### 3. การ map category (Package / Wholesales)

- Frontend (เช่น `LeadSummary.tsx`) จัด Wholesales เป็น  
  `lead.category === 'Wholesale' || lead.category === 'Wholesales'`
- Prompt ให้ LLM ใช้ `lead.category` และจัดการ 'Package', 'Wholesale', 'Wholesales'
- **ความเป็นไปได้:** ถ้าในข้อมูลมีทั้ง `Wholesale` และ `Wholesales` และ LLM แยกเป็นคนละกลุ่ม หรือ map ผิด จะทำให้สัดส่วน Package/Wholesales ผิด

### 4. Context ที่ส่งให้ LLM และการคำนวณเอง

- ใน `generate_response_node`:
  - ส่ง **raw JSON** ของ tool output (รวม `salesLeads` ทั้งก้อน) ให้ LLM
  - ส่ง **formatted_context** จาก `format_tool_response()` — สำหรับ get_sales_closed ที่ไม่ใช่โหมด "แต่ละคน" จะได้แค่ข้อความสรุปสั้นๆ (จำนวน QT รวม + มูลค่ารวม)
- System prompt บอกให้ "ยอดแยกตาม category = SUM(totalQuotationAmount) GROUP BY category"
- **แต่ไม่ได้ระบุชัดว่า** "จำนวนลีดที่ปิด / กี่ QT ต่อ category = **sum(totalQuotationCount)** ต่อ category ไม่ใช่นับจำนวนแถว"
- ผลคือ LLM อาจตีความ "กี่ลีด" เป็นจำนวนแถวหรือจำนวน lead แล้วนับผิด

---

## สรุปสาเหตุหลัก (ตามความน่าจะเป็น)

1. **การนับหน่วยผิด**
   - หน้ารายงาน: "จำนวนที่ปิด" = **sum(totalQuotationCount)** ต่อ category (หน่วยเป็น QT)
   - AI: อาจนับเป็น **จำนวนแถวใน salesLeads** ต่อ category → ได้ 29 vs 25 แทน 15 vs 39

2. **ความต่างของข้อมูลจาก RPC**
   - ถ้า RPC `ai_get_sales_closed` return structure/aggregation ไม่เหมือน `getSalesDataInPeriod()` (เช่น แถวต่อ lead แทนแถวต่อ log) ทั้งจำนวนและยอดแยก category จะผิดได้แม้ยอดรวมตรง

3. **การสรุปจาก raw JSON โดย LLM**
   - การให้ LLM คำนวณ category summary เองจาก raw มีโอกาสผิด (นับแถว / sum ผิด field / map category ผิด) ถ้าไม่มีกฎที่ชัดและข้อมูลที่ pre-aggregate แล้ว

---

## แนวทางแก้ที่แนะนำ

### 1. คำนวณสรุป Package/Wholesales ที่ backend (evp-ai-assistant) แล้วส่งเป็นข้อความชัดให้ LLM

- ใน `generate_response.py` ตอนประมวลผลผลลัพธ์ `get_sales_closed`:
  - ถ้า user ถามแนว "package หรือ wholesales ปิดได้กี่ลีด/กี่ QT และยอดขายกี่บาท":
    - อ่าน `salesLeads` จาก output
    - แยก category เหมือน frontend: Package = `category === 'Package'`, Wholesales = `category === 'Wholesale' || category === 'Wholesales'`
    - คำนวณต่อ category:
      - **salesCount (จำนวน QT)** = `sum(lead.totalQuotationCount)`
      - **totalSalesValue** = `sum(lead.totalQuotationAmount)`
    - สร้างข้อความสรุปแบบนี้ใส่ใน context ที่ส่งให้ LLM:
      - "สรุปตามหน้า /reports/sales-closed: Package: X QT, ฿Y บาท; Wholesales: Z QT, ฿W บาท; รวม X+Z QT, ฿Y+W บาท"
- ให้ LLM แค่ "พูดตามตัวเลขที่สรุปแล้ว" ไม่ต้องคำนวณจาก raw เอง → ลดโอกาสนับแถวหรือ sum ผิด

### 2. กำหนดนิยามใน system prompt ให้ชัด

- เพิ่มข้อความทำนอง:
  - "สำหรับรายงานยอดปิดการขาย (sales closed): 'จำนวนลีดที่ปิด' หรือ 'กี่ QT' หมายถึง **จำนวนรายการ QT ที่ปิด** = sum(totalQuotationCount) แยกตาม category (Package / Wholesales). **ห้าม** นับเป็นจำนวนแถว (จำนวน row) ใน salesLeads."
- ระบุให้ใช้ `totalQuotationAmount` ต่อแถวเท่านั้น และ Wholesales = category 'Wholesale' หรือ 'Wholesales'

### 3. ให้ RPC กับ Frontend ใช้ logic เดียวกัน

- ตรวจสอบ (หรือเขียน) RPC `ai_get_sales_closed` ให้:
  - ใช้เงื่อนไขเวลาและสถานะเดียวกับ `getSalesDataInPeriod()` (เช่น `created_at_thai`, status ปิดการขายแล้ว, win / win+สินเชื่อ)
  - ส่ง **salesLeads = หนึ่งแถวต่อหนึ่ง log** (ไม่ group by leadId) พร้อม `category`, `totalQuotationCount`, `totalQuotationAmount` ต่อแถว
  - ถ้า RPC อยู่ที่ CRM/Supabase ควรอ้างอิง logic จาก `salesUtils.getSalesDataInPeriod()` และเอกสาร `SALES_CLOSED_CALCULATION_ANALYSIS.md` ให้ผลลัพธ์สอดคล้องกับหน้า /reports/sales-closed

### 4. (ทางเลือก) ส่ง categorySummary จาก RPC

- ถ้า RPC สามารถคำนวณได้ ให้ return เพิ่ม field เช่น `categorySummary: [{ category: 'Package', salesCount, totalSalesValue }, { category: 'Wholesales', ... }]` โดย salesCount = sum(totalQuotationCount), totalSalesValue = sum(totalQuotationAmount) ตาม category
- ฝั่ง evp-ai-assistant ใช้ค่าจาก `categorySummary` นี้เป็นหลักในการตอบ "package หรือ wholesales ปิดได้กี่ลีด และยอดขายกี่บาท" แทนการให้ LLM คำนวณจาก raw

---

## สรุปหนึ่งบรรทัด

ตัวเลขรวมตรงเพราะใช้ชุดข้อมูลช่วงเวลาเดียวกัน แต่การแยก Package/Wholesales ผิดน่าจะมาจาก (1) AI นับจำนวน**แถว**ต่อ category แทน **sum(totalQuotationCount)** ตามที่หน้ารายงานใช้ และ/หรือ (2) โครงสร้างหรือการ aggregate ของ RPC ไม่เหมือน frontend แก้โดย pre-compute สรุป Package/Wholesales (QT count + ยอดเงิน) ใน backend ตาม logic หน้ารายงาน แล้วส่งข้อความสรุปให้ LLM และ/หรือ sync logic ระหว่าง RPC กับ `getSalesDataInPeriod()` พร้อมกำหนดนิยาม "จำนวน QT ที่ปิด" ใน prompt ให้ชัด

---

## การแก้ไขที่ดำเนินการแล้ว

1. **generate_response.py**
   - เพิ่ม `_normalize_category_for_sales_closed()` และ `_compute_sales_closed_category_summary()` เพื่อคำนวณ Package/Wholesales ตาม logic หน้า /reports/sales-closed (sum(totalQuotationCount), sum(totalQuotationAmount), Wholesale/Wholesales รวมเป็น Wholesales)
   - เมื่อ user ถามแนว "package หรือ wholesales ปิดได้กี่ลีด/กี่บาท" จะ pre-compute category summary แล้วใส่ข้อความ "สรุปตามหน้า /reports/sales-closed (แยกตาม category): Package: X QT, ฿Y บาท; Wholesales: Z QT, ฿W บาท; ..." ใน context ให้ LLM ใช้ตัวเลขนี้เป็นหลัก

2. **system_prompt.py**
   - กำหนดชัดว่า "จำนวนลีดที่ปิด/กี่ QT" = **sum(totalQuotationCount)** ต่อ category ห้ามนับจำนวนแถว
   - กำหนด Wholesales = category 'Wholesale' หรือ 'Wholesales' (รวมกลุ่มเดียวกัน)
   - เพิ่มตัวอย่างการคำนวณ category stats (salesCount + totalSalesValue) จาก salesLeads
   - กำหนดว่าเมื่อ context มี "สรุปตามหน้า /reports/sales-closed (แยกตาม category): ..." ต้องใช้ตัวเลขนั้นเป็นหลัก ห้ามคำนวณใหม่จาก raw

3. **ช่วงหลายเดือน (พ.ย. 2025 ถึง ม.ค. 2026) — ไม่ดึงข้อมูลครบ**
   - **db_tools.py:** เมื่อ date_from และ date_to กินหลายเดือน จะแยกเป็นเดือนต่อเดือน เรียก RPC ครั้งละ 1 เดือน แล้ว merge salesLeads, totalSalesValue, salesCount ให้เป็นชุดเดียว ดังนั้นการเรียก get_sales_closed ครั้งเดียวด้วย date_from=2025-11-01, date_to=2026-01-31 จะได้ข้อมูล พ.ย., ธ.ค., ม.ค. ครบ
   - **system_prompt.py / llm_router.py:** อัปเดตให้เมื่อผู้ใช้ถามช่วงหลายเดือน (เช่น พย 2025 ถึง มค 2026) ให้เรียก get_sales_closed **ครั้งเดียว** โดยส่ง date_from = วันแรกของช่วง, date_to = วันสุดท้ายของช่วง — ระบบจะดึงแต่ละเดือนและรวมให้อัตโนมัติ

4. **จำนวน QT และยอดเงินยังไม่ตรง**
   - ตัวเลขที่แสดงมาจากการ pre-compute ใน generate_response (sum(totalQuotationCount), sum(totalQuotationAmount) ต่อ category) และข้อความ "สรุปตามหน้า /reports/sales-closed (แยกตาม category): ..." ใน context
   - ถ้ายังไม่ตรงกับหน้า /reports/sales-closed ควรตรวจว่า RPC `ai_get_sales_closed` ส่ง structure เดียวกับ frontend (หนึ่งแถวต่อหนึ่ง log, มี category, totalQuotationCount, totalQuotationAmount) และ logic การนับ/รวมใน RPC ตรงกับ `getSalesDataInPeriod()` หรือไม่

5. **ถาม 3 เดือนย้อนหลัง — ตัวเลขธันวาคมไม่ตรงกับตอนถามเดือนเดียว**
   - **สาเหตุ:** เมื่อ merge 3 เดือน เรา concat salesLeads จาก Nov, Dec, Jan โดยไม่ได้ใส่ "เดือน" ให้แต่ละแถว → LLM ต้องแยกเดือนเองจาก date (เช่น lastActivityDate) และอาจตีความผิด (timezone, format, ขอบเดือน) ทำให้ธันวาคมในคำตอบ 3 เดือนไม่ตรงกับตอนถามเดือนธันวาเดียว
   - **การแก้:** (1) ใน db_tools ตอน merge ให้ใส่ `period_start`, `period_end` ให้ทุกแถว (แถวจาก RPC ธ.ค. = 2025-12-01 ถึง 2025-12-31) (2) ใน generate_response เมื่อ salesLeads มี period_start ให้คำนวณสรุปแยกตามเดือนจาก period (group by period_start แล้ว sum ต่อ category) แล้วใส่ข้อความ "สรุปแยกตามเดือน (จาก period ...)" ใน context ให้ LLM ใช้ตัวเลขนี้เป็นหลัก — ตัวเลขต่อเดือนจะตรงกับตอนถามเดือนเดียวเพราะมาจากชุด RPC เดียวกัน

6. **Follow-up "แยก Package/Wholesales" ได้ Intent general ไม่ดึงข้อมูล**
   - **สาเหตุ:** ข้อความสั้นแบบ "แยก Package / Wholesales" ไม่มีคำที่เคยอยู่ใน data keywords (เช่น ยอดขาย, ลีด, นัด) จึงไม่ trigger `_message_has_data_keyword` → tool_choice ยังเป็น "auto" และ LLM เลือกไม่เรียก tool แล้วตอบจากความจำ/แชทก่อนหน้า
   - **การแก้:** (1) เพิ่มคำว่า package, wholesales, แพ็กเกจ, โฮลเซล, แยก package, แยก wholesales, แยกรายการ ใน DATA_KEYWORDS_SALES_CLOSED เพื่อให้ข้อความแบบนี้ถือเป็น data request และใช้ tool_choice="required" (2) ใน system prompt และใน router prompt กำหนดชัดว่า follow-up แบบ "แยก Package/Wholesales", "แยกรายการ", "อยากได้รายชื่อ" ต้องเรียก get_sales_closed **ทุกครั้ง** โดยใช้ช่วงวันที่จากข้อความก่อนหน้า (เช่น ธันวา → 2025-12-01 ถึง 2025-12-31) — ห้ามตอบจากความจำ
   - **ทางเลือก "บังคับดึงข้อมูลทุกครั้ง":** สำหรับคำถามที่เกี่ยวกับข้อมูล เราใช้วิธี (ก) บังคับใช้ tool เมื่อข้อความมี data keyword (tool_choice=required) และ (ข) กำหนดใน prompt ว่า follow-up ต้องเรียก tool พร้อมช่วงวันที่จากแชท — ไม่ได้บังคับให้ทุกข้อความทุกข้อต้องเรียก tool (เช่น ทักทายยังเป็น general ได้)

7. **เคสจากภาพ ธ.ค. 68 — ตัวเลข Package/Wholesales ผิด, ข้อความ "ถึง 29", "ข้อมูลไม่เพียงพอ"**
   - **สาเหตุที่วิเคราะห์:** (ก) RPC อาจส่ง `salesLogs` แทน `salesLeads` → โค้ดได้ salesLeads = [] → pre-compute ได้ 0/0 → LLM นับจาก raw เองและนับแถวแทน sum(totalQuotationCount); (ข) LLM สรุปช่วงวันที่จาก raw แทนพารามิเตอร์ date_to; (ค) result_grader ได้ output แค่ 500 ตัวอักษร → ประเมิน insufficient
   - **การแก้ที่ทำแล้ว (evp-ai-assistant):**
     1. **db_tools.py:** เพิ่ม `_map_sales_logs_to_leads()` และ `_normalize_sales_closed_response()` — ถ้า RPC ส่ง `data.salesLogs` (หรือ root.salesLogs) จะ map เป็น `data.salesLeads` ให้ครบ และ return รูปแบบเดียวกับที่ frontend ใช้ (salesLeads, totalSalesValue, salesCount) เพื่อให้ pre-compute ใน generate_response ทำงานได้
     2. **db_tools.py:** คืนค่า `request_date_from` และ `request_date_to` ใน `data` ของ get_sales_closed เพื่อให้ LLM ระบุช่วงตามที่ขอ ไม่สรุปจากวันที่ใน raw
     3. **result_grader.py:** เพิ่ม `get_sales_closed` ในรายการ tool ที่ส่ง context มากกว่า 500 ตัวอักษร (แบบเดียวกับ sales team tools) และแสดง salesLeads count ถ้ามี — ลดโอกาส grader ให้ "ข้อมูลไม่เพียงพอ" เพราะ truncate
     4. **generate_response.py:** ถ้า `salesLeads` ว่างแต่มี `salesLogs` ใน output จะ map `salesLogs` → salesLeads ด้วย `_map_sales_logs_to_leads()` แล้วคำนวณ category summary ต่อ; และเมื่อมี request_date_from/request_date_to จะใส่ข้อความ "ช่วงข้อมูลที่ขอ: ... — ให้ระบุช่วงตามนี้ในคำตอบ (ไม่สรุปจากวันที่ใน raw)" ใน context
   - **หมายเหตุ:** ถ้า RPC ฝั่ง CRM/Supabase ยังใช้ logic หรือ table คนละแบบกับ `getSalesDataInPeriod()` (เช่น ไม่ใช้ `lead_productivity_logs.created_at_thai`) ควร sync ให้ตรงเพื่อให้ตัวเลขและช่วงวันที่ตรงกับหน้า /reports/sales-closed
