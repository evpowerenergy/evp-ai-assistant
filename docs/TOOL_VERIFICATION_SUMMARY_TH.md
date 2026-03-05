# สรุป: กระบวนการตรวจสอบการเลือก Tools

## ปัญหาปัจจุบัน

AI Agent เลือก tools/functions ผิด ทำให้:
- ได้ผลลัพธ์ไม่ตรงกับคำถาม
- ต้อง retry หลายครั้ง
- เสียเวลาและ API calls

## Flow ปัจจุบัน (มีปัญหา)

```
คำถามผู้ใช้
    ↓
Router (เลือก tools)
    ↓
DB Query (รัน tools)
    ↓
Result Grader (ตรวจสอบข้อมูล: ว่างเปล่า/มีข้อมูล/error)
    ↓
Generate Response
```

**ปัญหา:** Result Grader ตรวจสอบแค่ข้อมูลมีหรือไม่ ไม่ได้ตรวจสอบว่า tool ที่เลือกถูกต้องหรือไม่

---

## แนวทางแก้ไขที่แนะนำ: Hybrid Approach (ตรวจสอบ 2 ชั้น)

### Flow ใหม่ (แนะนำ)

```
คำถามผู้ใช้
    ↓
Router (เลือก tools)
    ↓
🔍 Tool Selection Verifier (ตรวจสอบก่อนรัน) ⭐ NEW
    ├─ ✅ APPROVED → ไปรัน tools
    └─ ❌ REJECTED/⚠️ NEEDS_ADJUSTMENT → แก้ไข → Router (retry)
    ↓
DB Query (รัน tools)
    ↓
🔍 Tool Execution Verifier (ตรวจสอบหลังรัน) ⭐ NEW
    ├─ ✅ APPROVED → ไป Result Grader
    └─ ❌ WRONG_TOOL/⚠️ NEEDS_MORE_TOOLS → แก้ไข → Router (retry)
    ↓
Result Grader (ตรวจสอบคุณภาพข้อมูล)
    ↓
Generate Response
```

### ข้อดี

1. ✅ **ตรวจสอบ 2 ชั้น** - ก่อนรันและหลังรัน
2. ✅ **ถูกต้องสูงสุด** - ป้องกันการเลือก tool ผิดตั้งแต่ต้น
3. ✅ **มีประสิทธิภาพ** - Pre-verification ประหยัดเวลาและ API calls
4. ✅ **ยืดหยุ่น** - แก้ไขได้ทั้งก่อนและหลังรัน

---

## ตัวอย่างการทำงาน

### ตัวอย่างที่ 1: Tool Selection ผิด

**คำถาม:** "ยอดขายแยกตามเดือน แยกตามแพลตฟอร์มด้วย"

**Router เลือก:** `search_leads` ❌ (ผิด)

**Pre-Verification:**
- ❌ REJECTED: "คำถามเกี่ยวกับยอดขายที่ปิดแล้ว ควรใช้ get_sales_closed ไม่ใช่ search_leads"
- → แก้ไข → Router (retry)

**Router เลือกใหม่:** `get_sales_closed` ✅ (ถูกต้อง)

**Pre-Verification:**
- ✅ APPROVED
- → DB Query

### ตัวอย่างที่ 2: Parameters ไม่ถูกต้อง

**คำถาม:** "ยอดขายแยกตามเดือน"

**Router เลือก:** `get_sales_closed` with `date_from=2026-01-01`, `date_to=2026-02-12` ⚠️ (ควรแยกเป็นหลายเดือน)

**Pre-Verification:**
- ⚠️ NEEDS_ADJUSTMENT: "คำถามต้องการแยกรายเดือน ควรเรียก get_sales_closed หลายครั้ง ครั้งละ 1 เดือน"
- → แก้ไข → Router (retry)

**Router เลือกใหม่:** `get_sales_closed` 3 ครั้ง (แต่ละเดือน) ✅

**Pre-Verification:**
- ✅ APPROVED
- → DB Query

### ตัวอย่างที่ 3: ผลลัพธ์ไม่ตอบคำถาม

**คำถาม:** "ยอดขายแยกตามแพลตฟอร์ม"

**Router เลือก:** `get_sales_closed` ✅ (ถูกต้อง)

**Pre-Verification:**
- ✅ APPROVED
- → DB Query

**Post-Verification:**
- ✅ APPROVED: "ผลลัพธ์มี platform ครบแล้ว สามารถคำนวณแยกตามแพลตฟอร์มได้"
- → Result Grader → Generate Response

---

## Implementation Plan

### Phase 1: Pre-Verification (Quick Win) ⭐

**สร้าง Tool Selection Verifier:**
- ตรวจสอบ tool selection ก่อนรัน
- ประหยัดเวลาและ API calls
- ป้องกันการเลือก tool ผิดตั้งแต่ต้น

**File:** `backend/app/orchestrator/nodes/tool_selection_verifier.py`

### Phase 2: Post-Verification (Enhancement)

**สร้าง Tool Execution Verifier:**
- ตรวจสอบผลลัพธ์หลังรัน
- รับประกันว่าผลลัพธ์ตอบคำถามได้
- สามารถเพิ่ม tools เพิ่มเติมได้

**File:** `backend/app/orchestrator/nodes/tool_execution_verifier.py`

### Phase 3: Tool Selection Refiner

**สร้าง Tool Selection Refiner:**
- รับ feedback จาก Verifiers
- ปรับปรุง tool selection และ parameters
- ส่งกลับไปที่ Router เพื่อ retry

**File:** `backend/app/orchestrator/nodes/tool_selection_refiner.py`

---

## เปรียบเทียบแนวทาง

| แนวทาง | ความถูกต้อง | ประสิทธิภาพ | LLM Calls เพิ่ม |
|--------|------------|------------|----------------|
| Pre-Verification เท่านั้น | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | +1 |
| Post-Verification เท่านั้น | ⭐⭐⭐⭐ | ⭐⭐⭐ | +1 |
| **Hybrid (แนะนำ)** | **⭐⭐⭐⭐⭐** | **⭐⭐⭐⭐** | **+2** |
| Enhanced Grader | ⭐⭐⭐ | ⭐⭐⭐ | +0.5 |

---

## สรุป

### แนะนำ: Hybrid Approach (ตรวจสอบ 2 ชั้น)

**เหตุผล:**
1. ✅ ถูกต้องสูงสุด - ตรวจสอบทั้งก่อนและหลังรัน
2. ✅ มีประสิทธิภาพ - Pre-verification ประหยัดเวลา
3. ✅ ยืดหยุ่น - แก้ไขได้ทั้งก่อนและหลังรัน

### ขั้นตอนการทำ

1. **Phase 1:** สร้าง Tool Selection Verifier (Pre-Verification) - Quick Win
2. **Phase 2:** สร้าง Tool Execution Verifier (Post-Verification) - Enhancement
3. **Phase 3:** สร้าง Tool Selection Refiner - Optimization

---

*ดูรายละเอียดเพิ่มเติมใน: `TOOL_SELECTION_VERIFICATION_ANALYSIS.md`*
