# การวิเคราะห์: AI ใช้หลายฟังก์ชันหรือฟังก์ชันเดียวหลายรอบ

**วันที่:** 2026-02-11  
**บริบท:** จากตัวอย่างคำถาม "ยอดขายแยกตามเดือน แยกตามแพลตฟอร์มด้วย" ที่ AI ใช้หลาย tool calls และคำตอบยาวเกินไป

---

## 1. สรุป: AI สามารถใช้หลายฟังก์ชันได้

### 1.1 ความสามารถของระบบ

**ใช่ AI สามารถใช้หลายฟังก์ชันได้:**

1. **หลายฟังก์ชันพร้อมกัน** - `llm_router.py` เลือกหลาย tools (`selected_tools` เป็น list)
2. **ฟังก์ชันเดียวหลายรอบ** - สามารถเรียกฟังก์ชันเดียวกันหลายครั้งด้วย parameters ต่างกันได้
3. **Flow:** `router` → `db_query` (รันทุก tool) → `result_grader` → `generate_response`

**Code Evidence:**
- `llm_router.py` (บรรทัด 670-744): LLM สามารถเลือกหลาย tools และส่งเป็น list
- `db_query.py` (บรรทัด 53-54): มี loop `for tool_info in selected_tools:` ที่รันทุก tool ที่เลือก
- `generate_response.py` (บรรทัด 21, 41): รับ `tool_results` เป็น list และแสดงผลทั้งหมด

---

## 2. ปัญหาจากตัวอย่าง

### 2.1 คำถาม
"ยอดขายแยกตามเดือน แยกตามแพลตฟอร์มด้วย"

### 2.2 สิ่งที่ AI ทำ
1. เรียก `get_sales_closed` 3 ครั้ง (แต่ละเดือน: พ.ย., ธ.ค., ม.ค.) ✅ **ถูกต้อง**
2. ได้ยอดรวมต่อเดือน (`totalSalesValue`) ✅ **ถูกต้อง**
3. แต่ไม่มียอดแยกตามแพลตฟอร์มต่อเดือน ❌ **ปัญหา**

### 2.3 สาเหตุของปัญหา

1. **RAW DATA ไม่มีตารางสรุป** - `get_sales_closed` ส่ง `salesLeads` (รายการดีลทีละรายการ) พร้อม `platform` และ `totalQuotationAmount` แต่ไม่มีตารางสรุปยอดแยกตามแพลตฟอร์มต่อเดือน
2. **Prompt ห้ามคำนวณ** - Prompt เดิมบอกว่า "ไม่ต้องคำนวณหรือปรับแต่งเพิ่มเติม" ทำให้ AI ไม่สามารถ SUM ตาม platform ได้
3. **คำตอบยาวเกินไป** - AI เรียก tool หลายครั้งและแสดงผลยาวมาก ควรจบแค่ prompt แรก

---

## 3. แนวทางแก้ไข

### 3.1 ปรับ Prompt (✅ ทำแล้ว)

**เพิ่มกฎ:**
- **อนุญาตให้คำนวณ/สรุปจาก RAW DATA** - ถ้า RAW DATA มีข้อมูลครบ (เช่น platform, amount ในแต่ละรายการ) สามารถ SUM, GROUP BY, หรือสรุปตามที่ผู้ใช้ถามได้ โดยใช้ตัวเลขจาก RAW DATA เท่านั้น
- **ห้ามปรับแต่งตัวเลข** - ห้ามปัดเศษ, ห้ามสร้างตัวเลขใหม่, ห้ามใช้ตัวเลขจากแหล่งอื่น
- **ถ้ามีข้อมูลครบแล้วให้ตอบเลย** - ไม่ต้องเรียก tool เพิ่ม ถ้า RAW DATA มีข้อมูลที่ตอบคำถามได้แล้ว

**ผลลัพธ์:**
- AI สามารถคำนวณยอดแยกตามแพลตฟอร์มได้ (SUM ตาม platform จาก `salesLeads`)
- AI สามารถคำนวณยอดแยกตามเดือน+แพลตฟอร์มได้ (GROUP BY month+platform)
- AI จะตอบสั้นลง เพราะไม่ต้องเรียก tool เพิ่มถ้ามีข้อมูลครบแล้ว

### 3.2 ตัวอย่างการทำงานหลังแก้ไข

**คำถาม:** "ยอดขายแยกตามเดือน แยกตามแพลตฟอร์มด้วย"

**Flow:**
1. Router เลือก `get_sales_closed` 3 ครั้ง (แต่ละเดือน)
2. `db_query` รัน 3 ครั้ง → ได้ `salesLeads` พร้อม `platform` และ `totalQuotationAmount`
3. `generate_response` รับ RAW DATA และคำนวณ:
   - SUM `totalQuotationAmount` ตาม `platform` และ `month` (จาก `created_at_thai`)
   - แสดงตารางยอดแยกตามเดือน+แพลตฟอร์ม
4. **ตอบสั้น กระชับ** - ไม่ต้องเรียก tool เพิ่ม

---

## 4. Flow ที่ปรับปรุงแล้ว

```
User Question: "ยอดขายแยกตามเดือน แยกตามแพลตฟอร์มด้วย"
    ↓
Router (llm_router.py)
    ↓
เลือก get_sales_closed 3 ครั้ง (แต่ละเดือน)
    ↓
db_query (db_query.py)
    ↓
รัน get_sales_closed 3 ครั้ง → ได้ salesLeads พร้อม platform, amount
    ↓
result_grader (result_grader.py)
    ↓
ตรวจสอบคุณภาพข้อมูล → sufficient
    ↓
generate_response (generate_response.py)
    ↓
คำนวณจาก RAW DATA:
- GROUP BY month (จาก created_at_thai) + platform
- SUM totalQuotationAmount
    ↓
แสดงตารางยอดแยกตามเดือน+แพลตฟอร์ม
    ↓
ตอบสั้น กระชับ ✅
```

---

## 5. สรุป

### 5.1 ความสามารถของระบบ
- ✅ AI สามารถใช้หลายฟังก์ชันได้
- ✅ AI สามารถเรียกฟังก์ชันเดียวหลายรอบด้วย parameters ต่างกันได้
- ✅ Flow รองรับการรันหลาย tools และรวมผลลัพธ์

### 5.2 ปัญหาที่พบ
- ❌ Prompt ห้ามคำนวณ ทำให้ AI ไม่สามารถ SUM ตาม platform ได้
- ❌ คำตอบยาวเกินไป ใช้หลาย tool calls แม้มีข้อมูลครบแล้ว

### 5.3 การแก้ไข
- ✅ ปรับ prompt ให้อนุญาตคำนวณ/สรุปจาก RAW DATA
- ✅ ปรับ prompt ให้ตอบสั้นลง ถ้ามีข้อมูลครบแล้วไม่ต้องเรียก tool เพิ่ม
- ✅ เน้นให้ใช้ตัวเลขจาก RAW DATA เท่านั้น ห้ามปรับแต่ง

### 5.4 ผลลัพธ์ที่คาดหวัง
- ✅ AI สามารถคำนวณยอดแยกตามแพลตฟอร์ม/เดือน+แพลตฟอร์มได้
- ✅ คำตอบสั้น กระชับ เข้าใจง่าย
- ✅ ใช้ tool calls เท่าที่จำเป็น

---

*อ้างอิง:*
- `backend/app/orchestrator/llm_router.py` - Tool selection
- `backend/app/orchestrator/nodes/db_query.py` - Tool execution
- `backend/app/orchestrator/nodes/generate_response.py` - Response generation
- `backend/app/utils/system_prompt.py` - Prompt definitions
