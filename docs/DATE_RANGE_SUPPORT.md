# 📅 Date Range Support - รองรับช่วงเวลา

## 🎯 Overview

ระบบตอนนี้รองรับการดึงข้อมูลตามช่วงเวลา (date range) จาก natural language queries แล้ว

---

## ✅ สิ่งที่รองรับ

### 1. **Natural Language Date Extraction**

ระบบจะ extract วันที่จากคำถามภาษาไทยและอังกฤษ:

| คำถาม | date_from | date_to |
|-------|-----------|---------|
| "เมื่อวาน" / "yesterday" | yesterday | yesterday |
| "วันนี้" / "today" | today | today |
| "พรุ่งนี้" / "tomorrow" | tomorrow | tomorrow |
| "สัปดาห์นี้" / "this week" | Monday | today |
| "สัปดาห์ที่แล้ว" / "last week" | Last Monday | Last Sunday |
| "เดือนนี้" / "this month" | 1st of month | today |
| "เดือนที่แล้ว" / "last month" | 1st of last month | Last day of last month |
| "ปีนี้" / "this year" | Jan 1 | today |
| "วันที่ 15 มกราคม" | 2026-01-15 | 2026-01-15 |
| "ระหว่าง 1-5 มกราคม" | 2026-01-01 | 2026-01-05 |
| "2026-01-15" | 2026-01-15 | 2026-01-15 |

---

## 🔧 Files ที่แก้ไข

### 1. **Date Extractor Utility** (ใหม่!)
📁 `backend/app/utils/date_extractor.py`

**หน้าที่:**
- Extract date range จาก natural language
- รองรับภาษาไทยและอังกฤษ
- รองรับรูปแบบวันที่หลายแบบ

**Functions:**
- `extract_date_range(query)` - Extract date range จาก query
- `extract_date_from_llm_params(params)` - Extract จาก LLM parameters

---

### 2. **Search Leads Function**
📁 `backend/app/tools/db_tools.py`

**เปลี่ยนแปลง:**
- เพิ่ม `date_from` และ `date_to` parameters
- เรียกใช้ `extract_date_range()` เพื่อ extract วันที่จาก query
- ส่ง `date_from` และ `date_to` ไปยัง RPC function

**Before:**
```python
async def search_leads(query: str, user_id: str, ...)
    # Only checked for "today"
```

**After:**
```python
async def search_leads(query: str, user_id: str, ..., date_from: Optional[str] = None, date_to: Optional[str] = None)
    # Extract date range from query or use provided dates
    if date_from is None and date_to is None:
        date_from, date_to = extract_date_range(query)
```

---

### 3. **LLM Router - Tool Schema**
📁 `backend/app/orchestrator/llm_router.py`

**เปลี่ยนแปลง:**
- เพิ่ม `date_from` และ `date_to` parameters ใน `search_leads` tool schema
- อัพเดท description ให้ชัดเจนว่า support date range
- เพิ่ม instructions สำหรับ LLM ในการ extract dates

**Before:**
```python
{
    "name": "search_leads",
    "parameters": {
        "query": "...",
        "date": "..."  # Single date only
    }
}
```

**After:**
```python
{
    "name": "search_leads",
    "parameters": {
        "query": "...",
        "date_from": "...",  # Start date
        "date_to": "..."     # End date
    }
}
```

---

### 4. **DB Query Node**
📁 `backend/app/orchestrator/nodes/db_query.py`

**เปลี่ยนแปลง:**
- ส่ง `date_from` และ `date_to` ไปยัง `search_leads` function

---

### 5. **RPC Function**
📁 `supabase/migrations/20250117000006_remove_all_limits.sql`

**รองรับแล้ว:**
- `p_date_from` และ `p_date_to` parameters
- ใช้ `created_at_thai` ในการ filter
- รองรับ date range queries

---

## 📝 ตัวอย่างการใช้งาน

### ตัวอย่าง 1: "ลูกค้าที่ได้มาเมื่อวาน"

**User Query:** "ขอรายชื่อลูกค้าที่ได้มาเมื่อวานหน่อย"

**Process:**
1. LLM Router → Extract: `date_from="2026-01-16"`, `date_to="2026-01-16"`
2. DB Query Node → Call `search_leads(query="...", date_from="2026-01-16", date_to="2026-01-16")`
3. Date Extractor → Confirm dates (if not provided by LLM)
4. RPC Function → Query with date filter: `created_at_thai BETWEEN '2026-01-16' AND '2026-01-16'`
5. Response → แสดงเฉพาะ leads ที่ created เมื่อวาน

---

### ตัวอย่าง 2: "ลีดสัปดาห์นี้"

**User Query:** "ลีดสัปดาห์นี้มีใครบ้าง"

**Process:**
1. LLM Router → Extract: `date_from="2026-01-13"` (Monday), `date_to="2026-01-17"` (today)
2. RPC Function → Query: `created_at_thai BETWEEN '2026-01-13' AND '2026-01-17'`
3. Response → แสดง leads ทั้งหมดที่ created ในสัปดาห์นี้

---

### ตัวอย่าง 3: "ระหว่าง 1-5 มกราคม"

**User Query:** "ขอรายชื่อลูกค้าระหว่าง 1-5 มกราคม"

**Process:**
1. Date Extractor → Extract: `date_from="2026-01-01"`, `date_to="2026-01-05"`
2. RPC Function → Query: `created_at_thai BETWEEN '2026-01-01' AND '2026-01-05'`
3. Response → แสดง leads ที่ created ในช่วงวันที่ 1-5 มกราคม

---

## 🔍 RPC Function Date Filter

RPC function `ai_get_leads` ใช้ `created_at_thai` ในการ filter:

```sql
AND (
    -- Date filter - cast created_at_thai to date for comparison
    (p_date_from IS NULL AND p_date_to IS NULL)
    OR (
        created_at_thai IS NOT NULL 
        AND (created_at_thai::text::timestamp)::date BETWEEN 
            COALESCE(p_date_from, '1900-01-01'::date) AND 
            COALESCE(p_date_to, '2100-12-31'::date)
    )
)
```

**หมายเหตุ:** ใช้ `created_at_thai` (วันที่สร้าง) ไม่ใช่ `updated_at_thai`

---

## 🎯 ถ้าต้องการใช้ `updated_at_thai` แทน

ถ้าต้องการ filter ตาม `updated_at_thai` (วันที่อัพเดทล่าสุด) แทน `created_at_thai`:

1. แก้ RPC function → เปลี่ยน `created_at_thai` เป็น `updated_at_thai`
2. หรือเพิ่ม parameter `p_use_updated_at` เพื่อเลือก field ที่จะใช้

---

## 📋 Checklist

- [x] สร้าง `date_extractor.py` utility
- [x] แก้ `search_leads` function → รองรับ date_from, date_to
- [x] แก้ LLM router → เพิ่ม date_from, date_to ใน tool schema
- [x] แก้ db_query_node → ส่ง date_from, date_to
- [x] RPC function → รองรับ date range แล้ว (ใช้ created_at_thai)

---

## 🚀 ทดสอบ

### Test Cases:

1. **"ลูกค้าที่ได้มาเมื่อวาน"**
   - Expected: แสดงเฉพาะ leads ที่ created เมื่อวาน

2. **"ลีดสัปดาห์นี้"**
   - Expected: แสดง leads ที่ created ในสัปดาห์นี้ (Monday - today)

3. **"ลีดเดือนนี้"**
   - Expected: แสดง leads ที่ created ในเดือนนี้ (1st - today)

4. **"ระหว่าง 1-5 มกราคม"**
   - Expected: แสดง leads ที่ created ระหว่าง 1-5 มกราคม

---

## 💡 Tips

1. **ถ้า LLM ไม่ extract dates:**
   - `date_extractor.py` จะ extract จาก query อัตโนมัติ
   - ทำงานเป็น fallback

2. **ถ้าต้องการ filter ตาม `updated_at_thai`:**
   - ต้องแก้ RPC function
   - หรือเพิ่ม parameter เพื่อเลือก field

3. **Performance:**
   - Date range queries จะเร็วกว่า full table scan
   - ใช้ index บน `created_at_thai` (ถ้ามี)
