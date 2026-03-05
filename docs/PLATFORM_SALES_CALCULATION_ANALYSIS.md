# การวิเคราะห์: ยอดขายแยกตาม Platform ไม่ตรง

**วันที่:** 2026-02-11  
**ปัญหา:** ยอดขายแยกตาม platform ที่ AI แสดงผลไม่ตรงกับระบบ

---

## 1. สรุปปัญหา

### 1.1 คำถามผู้ใช้
"ยอดขายแยกตามเดือน แยกตามแพลตฟอร์มด้วย"

### 1.2 สิ่งที่เกิดขึ้น
- AI เรียก `get_sales_closed` 3 ครั้ง (แต่ละเดือน) ✅
- AI คำนวณ SUM(`totalQuotationAmount`) GROUP BY `platform` จาก `salesLeads` ❓
- **ยอดที่ได้ไม่ตรงกับระบบ** ❌

### 1.3 คำถามสำคัญ
- **AI คำนวณ SUM เองใช่ไหม?** → **ใช่** (ตาม prompt ที่อนุญาตให้คำนวณจาก RAW DATA)
- **คำนวณผิดหรือ?** → **อาจจะ** ต้องตรวจสอบ logic

---

## 2. โครงสร้างข้อมูลจาก RPC `ai_get_sales_closed`

### 2.1 Response Structure

```json
{
  "success": true,
  "data": {
    "salesLeads": [
      {
        "leadId": 123,
        "logId": 456,
        "platform": "Facebook",
        "totalQuotationAmount": 100000,
        "totalQuotationCount": 1,
        "quotationDocuments": [
          {
            "document_number": "QT-001",
            "amount": "100000",
            "created_at_thai": "2025-11-15T10:00:00+07:00"
          }
        ],
        "lastActivityDate": "2025-11-15T10:00:00+07:00"
      },
      // ... รายการอื่นๆ
    ],
    "totalSalesValue": 17367151.15,
    "salesCount": 150
  }
}
```

### 2.2 จุดสำคัญ

**แต่ละรายการใน `salesLeads`:**
- = **1 productivity log** (1 log = 1 หรือหลาย QT หลัง deduplication)
- มี `platform` จาก `leads.platform` (platform ของ lead)
- มี `totalQuotationAmount` = SUM ของ QT ใน log นั้น (หลัง deduplication)
- มี `lastActivityDate` = `created_at_thai` ของ log (วันที่สร้าง log ปิดการขาย)

**กรณีที่อาจทำให้ยอดไม่ตรง:**

1. **Lead เดียวกันมีหลาย log (หลาย QT จากหลาย sale)**
   - แต่ละ log = 1 รายการใน `salesLeads`
   - แต่ละ log มี `platform` เดียวกัน (จาก lead เดียวกัน)
   - แต่ละ log มี `totalQuotationAmount` ของตัวเอง
   - ถ้า SUM ตาม platform → ควรถูกต้อง (เพราะแต่ละ log มี amount ของตัวเอง)

2. **Platform เป็น null หรือ 'ไม่ระบุ'**
   - ถ้า platform เป็น null → อาจถูกจัดกลุ่มเป็น 'ไม่ระบุ' หรือถูกข้าม
   - ต้องตรวจสอบว่า AI จัดกลุ่ม platform null อย่างไร

3. **การคำนวณยอดแยกตามเดือน+แพลตฟอร์ม**
   - ต้องใช้ `lastActivityDate` (หรือ `created_at_thai`) เพื่อแยกเดือน
   - ต้องใช้ `platform` เพื่อแยกแพลตฟอร์ม
   - ต้อง SUM `totalQuotationAmount` ตาม month+platform

---

## 3. Logic ที่ถูกต้อง (ตามหน้า /reports/sales-closed)

### 3.1 หน้า Sales Closed ไม่ได้คำนวณยอดแยกตาม Platform

**จากการตรวจสอบ `SalesClosed.tsx`:**
- ไม่มีการคำนวณยอดแยกตาม platform
- แสดงแค่ `totalSalesValue` รวมทั้งหมด
- แสดง `salesLeads` แต่ละรายการ (แสดง platform แต่ละรายการ)

**ดังนั้น:** ถ้าผู้ใช้ถาม "ยอดขายแยกตาม platform" ในระบบจริง (หน้า /reports/sales-closed) **ไม่มีตารางสรุปยอดแยกตาม platform ให้**

### 3.2 Logic ที่ควรใช้ (ถ้าจะคำนวณยอดแยกตาม Platform)

**จากโครงสร้างข้อมูล `salesLeads`:**
- แต่ละรายการ = 1 log = 1 หรือหลาย QT (หลัง deduplication)
- แต่ละรายการมี `platform` และ `totalQuotationAmount` ที่คำนวณแล้ว

**Logic ที่ถูกต้อง:**
```javascript
// GROUP BY platform และ SUM totalQuotationAmount
const platformTotals = {};
salesLeads.forEach(lead => {
  const platform = lead.platform || 'ไม่ระบุ';
  const amount = parseFloat(lead.totalQuotationAmount || 0);
  
  if (!platformTotals[platform]) {
    platformTotals[platform] = 0;
  }
  platformTotals[platform] += amount;
});
```

**สำหรับแยกตามเดือน+แพลตฟอร์ม:**
```javascript
// GROUP BY month + platform และ SUM totalQuotationAmount
const monthPlatformTotals = {};
salesLeads.forEach(lead => {
  const date = new Date(lead.lastActivityDate);
  const month = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
  const platform = lead.platform || 'ไม่ระบุ';
  const amount = parseFloat(lead.totalQuotationAmount || 0);
  
  const key = `${month}_${platform}`;
  if (!monthPlatformTotals[key]) {
    monthPlatformTotals[key] = { month, platform, amount: 0 };
  }
  monthPlatformTotals[key].amount += amount;
});
```

---

## 4. ปัญหาที่อาจเกิดขึ้น

### 4.1 AI อาจใช้ `amount` จาก `quotationDocuments` แทน `totalQuotationAmount`

**❌ ผิด:**
```javascript
// นับซ้ำถ้ามีหลาย QT ใน log เดียวกัน
salesLeads.forEach(lead => {
  lead.quotationDocuments.forEach(qt => {
    platformTotals[platform] += parseFloat(qt.amount);
  });
});
```

**✅ ถูกต้อง:**
```javascript
// ใช้ totalQuotationAmount ที่คำนวณแล้ว (หลัง deduplication)
salesLeads.forEach(lead => {
  platformTotals[platform] += parseFloat(lead.totalQuotationAmount);
});
```

### 4.2 AI อาจไม่จัดการ platform ที่เป็น null

**❌ ผิด:**
```javascript
// ข้าม platform ที่เป็น null
if (lead.platform) {
  platformTotals[lead.platform] += amount;
}
```

**✅ ถูกต้อง:**
```javascript
// จัดกลุ่ม platform null เป็น 'ไม่ระบุ'
const platform = lead.platform || 'ไม่ระบุ';
platformTotals[platform] += amount;
```

### 4.3 AI อาจใช้ `created_at_thai` จาก `quotationDocuments` แทน `lastActivityDate`

**สำหรับแยกตามเดือน:**
- ต้องใช้ `lastActivityDate` (หรือ `created_at_thai` ของ log) ไม่ใช่ `created_at_thai` ของ QT
- เพราะระบบนับตามวันที่สร้าง log ปิดการขาย ไม่ใช่วันที่สร้าง QT

---

## 5. แนวทางแก้ไข

### 5.1 ปรับ Prompt ให้ชัดเจนขึ้น

**เพิ่มคำแนะนำใน prompt:**
- **ใช้ `totalQuotationAmount`** จากแต่ละรายการใน `salesLeads` เท่านั้น (ไม่ใช้ `amount` จาก `quotationDocuments`)
- **ใช้ `lastActivityDate`** (หรือ `created_at_thai` ของ log) สำหรับแยกเดือน (ไม่ใช้ `created_at_thai` ของ QT)
- **จัดการ platform null** → จัดกลุ่มเป็น 'ไม่ระบุ'
- **SUM ตาม platform** → `SUM(totalQuotationAmount) GROUP BY platform`
- **SUM ตาม month+platform** → `SUM(totalQuotationAmount) GROUP BY month(lastActivityDate) + platform`

### 5.2 เพิ่มตัวอย่างการคำนวณใน Prompt

**ตัวอย่าง code ที่ถูกต้อง:**
```javascript
// ยอดแยกตาม platform
const platformTotals = {};
salesLeads.forEach(lead => {
  const platform = lead.platform || 'ไม่ระบุ';
  const amount = parseFloat(lead.totalQuotationAmount || 0);
  platformTotals[platform] = (platformTotals[platform] || 0) + amount;
});

// ยอดแยกตามเดือน+platform
const monthPlatformTotals = {};
salesLeads.forEach(lead => {
  const date = new Date(lead.lastActivityDate);
  const month = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
  const platform = lead.platform || 'ไม่ระบุ';
  const amount = parseFloat(lead.totalQuotationAmount || 0);
  const key = `${month}_${platform}`;
  monthPlatformTotals[key] = (monthPlatformTotals[key] || 0) + amount;
});
```

---

## 6. สรุป

### 6.1 คำตอบคำถาม

**Q: มันไม่ได้ดึงข้อมูลมาจาก query แต่เป็น AI คำนวณ SUM เองใช่ไหม?**  
**A: ใช่** - AI คำนวณ SUM จาก RAW DATA (`salesLeads`) ตามที่ prompt อนุญาต

**Q: แสดงว่าคำนวณผิดหรือ?**  
**A: อาจจะ** - ต้องตรวจสอบว่า AI ใช้:
- `totalQuotationAmount` (ถูกต้อง) หรือ `amount` จาก `quotationDocuments` (ผิด - นับซ้ำ)
- `lastActivityDate` (ถูกต้อง) หรือ `created_at_thai` ของ QT (ผิด - อาจผิดเดือน)
- จัดการ platform null ถูกต้องหรือไม่

### 6.2 สิ่งที่ต้องปรับ

1. **ปรับ Prompt** - เพิ่มคำแนะนำให้ใช้ `totalQuotationAmount` และ `lastActivityDate` เท่านั้น
2. **เพิ่มตัวอย่างการคำนวณ** - แสดงตัวอย่าง code ที่ถูกต้องใน prompt
3. **ตรวจสอบผลลัพธ์** - ทดสอบว่ายอดที่ AI คำนวณตรงกับที่ควรจะเป็นหรือไม่

---

*อ้างอิง:*
- `supabase/migrations/20250120000002_create_ai_get_sales_closed.sql` - RPC function structure
- `src/utils/salesUtils.ts` - Frontend calculation logic
- `src/pages/reports/SalesClosed.tsx` - Frontend display logic
