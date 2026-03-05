# การวิเคราะห์: ยอดรวม 3 เดือนตรง แต่แยกรายเดือนไม่ตรง (Sales Closed Report)

**บริบท:** จากบทสนทนาแชทบอท — ผู้ใช้เช็คยอดขายรวม 3 เดือนตรงกับในระบบ แต่พอแยกเป็นรายเดือนแล้วตัวเลขไม่ตรง

**เอกสารนี้:** วิเคราะห์สาเหตุที่เป็นไปได้จากมุมของ **ระบบ CRM หน้า `/reports/sales-closed`** และ logic การดึงยอดขาย (รวมถึง query / ฟิลด์วันที่ / ขอบเขตเวลา) เพื่อให้แชทบอทหรือทีมใช้เป็น reference ในการไล่จุดที่ทำให้ยอดรายเดือนไม่ตรง

---

## 1. สรุปสั้น ๆ ตามที่แชทบอทวิเคราะห์

- **ยอดรวม 3 เดือนตรง** → ชุดข้อมูลที่นำมานับโดยรวมคือชุดเดียวกัน (จำนวนดีล/QT ในช่วง 3 เดือนตรงกัน)
- **แยกรายเดือนไม่ตรง** → มักมาจากความต่างของ **ฟิลด์วันที่ / ขอบเขตเวลา / สถานะ** ที่ใช้ **แบ่งเดือน** ระหว่าง:
  - วิธีที่แชทบอท (หรือผู้ใช้) คำนวณรายเดือน  
  - วิธีที่ระบบ CRM / DB นับรายเดือน

ส่วนด้านล่างจะลงรายละเอียดว่า **ระบบ CRM หน้า Sales Closed ดึงยอดยังไง** และจุดไหนที่อาจทำให้ “แยกรายเดือน” ไม่ตรงกับที่คาดไว้

---

## 2. ระบบ CRM หน้า `/reports/sales-closed` ดึงยอดขายอย่างไร

### 2.1 แหล่งข้อมูลและฟิลด์วันที่

| รายการ | ค่าในระบบ CRM (Sales Closed) |
|--------|------------------------------|
| **Route** | `/reports/sales-closed` |
| **Component** | `src/pages/reports/SalesClosed.tsx` |
| **ฟังก์ชันดึงยอด** | `getSalesDataInPeriod()` ใน `src/utils/salesUtils.ts` |
| **Table หลัก** | `lead_productivity_logs` |
| **ฟิลด์วันที่ที่ใช้กรอง** | **`created_at_thai`** (ไม่ใช่ `close_date` หรือ `invoice_date`) |
| **เงื่อนไขสถานะ** | `status = 'ปิดการขายแล้ว'` และ `sale_chance_status = 'win'` หรือ `('win + สินเชื่อ' AND credit_approval_status = 'อนุมัติ')` |

เอกสารอ้างอิงในโปรเจกต์ CRM:
- `docs/analysis/SALES_CLOSED_DATE_FIELD_ANALYSIS.md` — ระบุชัดว่าใช้วันที่จาก **`lead_productivity_logs.created_at_thai`**
- `docs/analysis/SALES_CLOSED_CALCULATION_ANALYSIS.md` — อธิบาย logic การคำนวณและ deduplication

**สรุป:** หน้ารายงานยอดขายปิดการขายใน CRM **นับตาม “วันที่สร้าง log ปิดการขาย” (created_at_thai ของ log)** ไม่ใช่วันที่ปิดดีลแยกต่างหาก หรือวันที่ออกใบแจ้งหนี้

### 2.2 การสร้างช่วงวันที่ (ขอบเขตเวลา) ในหน้า Sales Closed

ใน `SalesClosed.tsx` (ประมาณบรรทัด 64–90):

- ใช้ **timezone ไทย (Asia/Bangkok)** ผ่าน `Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Bangkok', ... })`
- รูปแบบวันที่ส่งเข้า `getSalesDataInPeriod`:
  - **วันเริ่ม:** `YYYY-MM-DD` + `T00:00:00.000` (เที่ยงคืนวันแรก เวลาไทย)
  - **วันสิ้นสุด:** `YYYY-MM-DD` + `T23:59:59.999` (สิ้นวันสุดท้าย เวลาไทย)

ตัวอย่างช่วงรายเดือนที่หน้าจออาจส่งไปได้:
- พ.ย.: `2025-11-01T00:00:00.000` ~ `2025-11-30T23:59:59.999`
- ธ.ค.: `2025-12-01T00:00:00.000` ~ `2025-12-31T23:59:59.999`
- ม.ค.: `2026-01-01T00:00:00.000` ~ `2026-01-31T23:59:59.999`

การเปรียบเทียบใน Supabase เป็นแบบ **inclusive**:  
`.gte('created_at_thai', startDate)` และ `.lte('created_at_thai', endDate)`  
→ เรคอร์ดที่ `created_at_thai` อยู่ตรงขอบ (เช่น 23:59:59.999) จะถูกรวมในเดือนนั้น

### 2.3 ไม่มี RFC/API แยกสำหรับ “ยอด Sales Closed”

- หน้า **Sales Closed ดึงข้อมูล client-side** ผ่าน Supabase client โดยตรง (ใน `getSalesDataInPeriod`)
- **ไม่มี API/RFC เฉพาะ** สำหรับรายงานยอดปิดการขายในโปรเจกต์ CRM; ข้อมูลมาจาก `lead_productivity_logs` + `quotation_documents` ตาม logic ใน `salesUtils.ts`
- Server มี `server/endpoints/core/sales-team/sales-team-data.ts` แต่เป็นข้อมูล sales team / leads สำหรับ dashboard ไม่ได้ replicate logic ยอดปิดการขายรายเดือนแบบเดียวกับ `getSalesDataInPeriod`

ดังนั้นถ้าผู้ใช้หรือแชทบอท “เช็คใน DB” — สิ่งที่ต้องให้ตรงกับระบบคือ **query ที่ใช้ตารางและฟิลด์เดียวกับที่หน้า Sales Closed ใช้** (ดูหัวข้อ 4)

---

## 3. สาเหตุที่เป็นไปได้ที่ “แยกรายเดือนไม่ตรง”

### 3.1 ใช้คนละฟิลด์วันที่ (สาเหตุที่พบบ่อยที่สุด)

- **ระบบ CRM (Sales Closed):** นับตาม **`lead_productivity_logs.created_at_thai`**
- ถ้าแชทบอทหรือผู้ใช้ query เองด้วย:
  - `leads.created_at_thai` หรือ `leads.created_at`  
  - หรือ `quotation_documents.created_at_thai`  
  - หรือฟิลด์อื่น (เช่น close_date, invoice_date ถ้ามี)

ผลคือ **ดีล/QT เดียวกันอาจถูกจัดเข้าเดือนคนละเดือน** (เช่น log ปิดใน ธ.ค. แต่ใบแจ้งหนี้ใน ม.ค. → ระบบนับธ.ค., query ที่ใช้วันที่ใบแจ้งหนี้นับม.ค.)

**แนวทาง:** ยืนยันกับผู้ใช้/แชทบอทว่า “รายงานในระบบนับตามวันที่อะไร” — ในกรณีนี้คือ **วันที่สร้าง log ปิดการขาย (created_at_thai ของ lead_productivity_logs)** แล้วให้ query ใช้ฟิลด์เดียวกัน

### 3.2 ขอบเขตช่วงเวลาแต่ละเดือนไม่ตรงกัน

- ระบบ CRM ใช้ `[first day 00:00:00.000, last day 23:59:59.999]` ใน **เวลาไทย**
- ถ้าฝั่งที่เปรียบเทียบใช้:
  - เวลา UTC โดยไม่แปลง → เรคอร์ดใกล้เที่ยงคืนอาจข้ามเดือน
  - หรือใช้ `DATE_TRUNC('month', ...)` แล้วเปรียบเทียบแบบไม่ระบุเวลา → อาจได้เซตคนละชุดกับช่วง [00:00, 23:59:59.999]

การเปรียบเทียบแบบ “แยกรายเดือน” ควรใช้ช่วงเวลาแบบเดียวกับหน้า report (วันแรก–วันสุดท้ายของเดือน ใน timezone ไทย) หรือใช้ `created_at_thai` กับ logic เดียวกัน

### 3.3 Timezone

- ใน DB มี trigger อัปเดต `created_at_thai = created_at + 7 hours` (ดู migration `20250819000000_fix_thailand_timestamps_trigger.sql`)
- ฟรอนต์ส่งค่าวันที่เป็นสตริงรูปแบบ `YYYY-MM-DDTHH:mm:ss.sss` (ไม่มี timezone suffix) แต่ตั้งค่าเป็นเวลาไทยแล้ว
- ถ้า Supabase/Postgres แปลสตริงเป็น timestamp แบบ UTC หรือ local ของเซิร์ฟเวอร์ อาจทำให้ขอบวันขยับได้

เพื่อให้รายเดือนตรงกับระบบ ควรยืนยันว่า:
- ค่าที่ใช้กรองเป็น “เวลาไทย” สอดคล้องกับที่ฟรอนต์ส่ง (หรือใช้ `created_at_thai` ที่ DB คำนวณไว้แล้ว)

### 3.4 เงื่อนไขสถานะดีล

- ระบบ Sales Closed กรองเฉพาะ:
  - `status = 'ปิดการขายแล้ว'`
  - `sale_chance_status = 'win'` หรือ `(sale_chance_status = 'win + สินเชื่อ' AND credit_approval_status = 'อนุมัติ')`
- ถ้า query ที่ใช้เช็ครวม status อื่น (เช่น “ติดตามหลังการขาย”) หรือไม่เช็ค `credit_approval_status` สำหรับ win + สินเชื่อ ยอดรายเดือนอาจไม่ตรง

---

## 4. Query ที่สอดคล้องกับระบบ (สำหรับเช็ค/เปรียบเทียบ)

ถ้าจะให้ตัวเลข **รายเดือน** ตรงกับหน้ารายงาน Sales Closed ต้องใช้ **ตาราง + ฟิลด์วันที่ + เงื่อนไขสถานะ** เดียวกับที่ระบบใช้

### 4.1 เงื่อนไขที่ต้องตรงกับระบบ

- ตาราง: **`lead_productivity_logs`**
- ฟิลด์วันที่: **`created_at_thai`**
- สถานะ:
  - `status = 'ปิดการขายแล้ว'`
  - `sale_chance_status = 'win'` หรือ (`sale_chance_status = 'win + สินเชื่อ'` และ `credit_approval_status = 'อนุมัติ'`)

ยอดเงินจริงระบบคำนวณจาก **`quotation_documents`** ที่ผูกกับ log เหล่านั้น หลัง deduplication ตาม document number (ดู `salesUtils.ts`) — ถ้าต้องการแค่ “จำนวนรายการปิดการขายต่อเดือน” การนับจาก log ตามด้านล่างก็สอดคล้องกับช่วงวันที่และเดือนที่ระบบใช้

### 4.2 ตัวอย่าง SQL แยกรายเดือน (ให้ตรงกับระบบ)

```sql
-- ยอดรายเดือน (นับจำนวน log ที่ปิดการขายแล้ว) ตรงกับ logic หน้า Sales Closed
-- ใช้ created_at_thai จาก lead_productivity_logs และเงื่อนไข status เหมือนระบบ

SELECT 
  date_trunc('month', created_at_thai AT TIME ZONE 'Asia/Bangkok')::date AS month_start,
  COUNT(*) AS closed_logs_count
FROM lead_productivity_logs
WHERE 
  status = 'ปิดการขายแล้ว'
  AND (
    sale_chance_status = 'win' 
    OR (sale_chance_status = 'win + สินเชื่อ' AND credit_approval_status = 'อนุมัติ')
  )
  AND created_at_thai >= :start_of_three_months   -- e.g. 2025-11-01 00:00:00+07
  AND created_at_thai <= :end_of_three_months     -- e.g. 2026-01-31 23:59:59.999+07
GROUP BY date_trunc('month', created_at_thai AT TIME ZONE 'Asia/Bangkok')
ORDER BY month_start;
```

หมายเหตุ:
- ถ้า `created_at_thai` เก็บเป็น `timestamptz` อยู่แล้ว การใช้ `AT TIME ZONE 'Asia/Bangkok'` จะช่วยให้การตัดเดือนสอดคล้องกับ “เดือนในเวลาไทย”
- ช่วง `:start_of_three_months` และ `:end_of_three_months` ควรตรงกับที่หน้า report เลือก (วันแรก 00:00:00 และวันสุดท้าย 23:59:59.999 เวลาไทย)

### 4.3 ตัวอย่างกรองเป็นช่วงเดือนเดียว (ให้ตรงกับที่ผู้ใช้เลือกใน UI)

```sql
-- ตัวอย่าง: เฉพาะเดือน พ.ย. 2025 (ให้ตรงกับช่วงที่หน้า Sales Closed ส่งไป)
SELECT COUNT(*), COALESCE(SUM(...), 0) AS total_amount
FROM lead_productivity_logs lpl
JOIN quotation_documents qd ON qd.productivity_log_id = lpl.id AND qd.document_type = 'quotation'
WHERE 
  lpl.status = 'ปิดการขายแล้ว'
  AND (
    lpl.sale_chance_status = 'win' 
    OR (lpl.sale_chance_status = 'win + สินเชื่อ' AND lpl.credit_approval_status = 'อนุมัติ')
  )
  AND lpl.created_at_thai >= '2025-11-01T00:00:00.000'
  AND lpl.created_at_thai <= '2025-11-30T23:59:59.999';
```

การรวมยอดเงินจาก `quotation_documents` ต้องทำ deduplication ตาม document number เหมือนใน `salesUtils.ts` จึงจะได้ตัวเลขเท่ากับหน้าจอพอดี — ตัวอย่างด้านบนเน้น “ช่วงเวลา + ฟิลด์วันที่ + สถานะ” ให้ตรงกับระบบ

---

## 5. สิ่งที่ควรยืนยันกับผู้ใช้ (สำหรับแชทบอท)

1. **รายงาน “ในระบบ” ที่ผู้ใช้เทียบอยู่คืออะไร**
   - ถ้าเป็นหน้า **Sales Closed** (`/reports/sales-closed`) → ระบบใช้วันที่ **`created_at_thai` ของ log (วันที่สร้าง log ปิดการขาย)** ไม่ใช่วันที่ออกใบแจ้งหนี้หรือวันที่สร้าง lead

2. **ตอนเช็คใน DB / แยกรายเดือน ผู้ใช้ใช้ฟิลด์อะไร**
   - ถ้าใช้คนละฟิลด์ (เช่น `leads.created_at`, `quotation_documents.created_at_thai`) ให้ปรับมาใช้ **`lead_productivity_logs.created_at_thai`** และเงื่อนไข status ตามหัวข้อ 4

3. **ช่วงเวลาแต่ละเดือน**
   - ใช้แบบ “วันแรก 00:00:00 – วันสุดท้าย 23:59:59” ในเวลาไทย และใช้ฟิลด์ `created_at_thai` จะได้ขอบเขตเดียวกับหน้า report

4. **สถานะ**
   - ใช้เฉพาะปิดการขายสำเร็จ: `status = 'ปิดการขายแล้ว'` และ (win หรือ win+สินเชื่อที่อนุมัติแล้ว) ตามที่ระบบกำหนด

---

## 6. สรุป

| ประเด็น | สรุปสำหรับระบบ CRM Sales Closed |
|--------|-----------------------------------|
| **ฟิลด์วันที่** | `lead_productivity_logs.created_at_thai` |
| **ขอบเขตเดือน** | วันแรก 00:00:00.000 – วันสุดท้าย 23:59:59.999 (เวลาไทย) |
| **Timezone** | ไทย (Asia/Bangkok); DB มี `created_at_thai` จาก trigger +7 ชม. |
| **สถานะ** | ปิดการขายแล้ว + (win หรือ win+สินเชื่อที่อนุมัติ) |
| **ที่มาข้อมูล** | Client-side ผ่าน Supabase ใน `getSalesDataInPeriod()` ไม่มี RFC/API แยกสำหรับยอด Sales Closed |

**ยอดรวม 3 เดือนตรง แต่แยกรายเดือนไม่ตรง** — น่าจะมาจากการที่ฝั่งที่เปรียบเทียบใช้ **ฟิลด์วันที่หรือขอบเขตเวลาแยกรายเดือนไม่ตรงกับระบบ** (หรือเงื่อนไขสถานะไม่ตรง) จึงควรยืนยันและปรับ query ให้ใช้ `created_at_thai` ของ `lead_productivity_logs` พร้อมช่วงเวลาและสถานะตามที่ระบุในเอกสารนี้

---

## 7. การปรับแชทบอทให้ยึดความถูกต้องตามหน้า /reports/sales-closed

แชทบอท (evp-ai-assistant) ปรับแล้วดังนี้:

1. **Tool `get_sales_closed` (llm_router.py)**  
   - คำอธิบาย tool ชัดเจนว่า: ตัวเลขยึดตามหน้า /reports/sales-closed, นับตาม `lead_productivity_logs.created_at_thai`  
   - เมื่อผู้ใช้ถามยอดแยกรายเดือน ให้เรียก get_sales_closed ครั้งละ 1 เดือน โดยส่ง `date_from` = วันแรกของเดือน, `date_to` = วันสุดท้ายของเดือน (YYYY-MM-DD)

2. **Intent analyzer (system_prompt.py)**  
   - เพิ่มกฎ SALES CLOSED: ยอดขายยึดตาม /reports/sales-closed; สำหรับยอดแยกรายเดือน เรียก get_sales_closed ครั้งละเดือน ด้วยช่วงวันแรก–วันสุดท้ายของเดือน

3. **การแสดงผล (generate_response.py)**  
   - ตอนแสดงผล get_sales_closed เพิ่มข้อความว่า "ตัวเลขยึดตามหน้า /reports/sales-closed" ใน summary

4. **Backend (db_tools.py)**  
   - ใช้อยู่แล้ว: ส่งวันที่เป็น `YYYY-MM-DDT00:00:00.000+07:00` และ `YYYY-MM-DDT23:59:59.999+07:00` ตรงกับฟรอนต์  
   - RPC `ai_get_sales_closed` ใน Supabase ใช้ `lpl.created_at_thai` สำหรับ date filter ตรงกับ logic หน้ารายงาน

---

*อ้างอิง:*
- CRM: `src/pages/reports/SalesClosed.tsx`, `src/utils/salesUtils.ts` (getSalesDataInPeriod)
- CRM: `docs/analysis/SALES_CLOSED_DATE_FIELD_ANALYSIS.md`, `docs/analysis/SALES_CLOSED_CALCULATION_ANALYSIS.md`
- DB: `supabase/migrations/20250819000000_fix_thailand_timestamps_trigger.sql`
