# 🚫 Remove All Limits - ให้ดึงข้อมูลตามที่ user ขอ

## 📋 สรุป Limits ที่พบ

### 1. **RPC Function Limits**

#### `ai_get_leads` - มี 2 limits:
- **Default limit:** `p_limit = 100` (เมื่อไม่มี date filter)
- **Date filter limit:** `LIMIT 10000` (เมื่อมี date filter)

**Location:** 
- `backend/app/tools/db_tools.py` line 155: `"p_limit": 100`
- `supabase/migrations/20250117000005_remove_pii_masking.sql` line 95: `LIMIT CASE WHEN ... THEN p_limit ELSE 10000 END`

---

### 2. **Format Function Limits**

#### `format_rag_response()` - มี 2 limits:
- **Document limit:** `rag_results[:3]` - แสดงแค่ 3 documents
- **Content limit:** `content[:300]` - แสดงแค่ 300 characters

**Location:** `backend/app/orchestrator/nodes/generate_response.py` lines 239-242

---

### 3. **Context Building Limits**

#### `generate_response_node()` - มี limit:
- **RAG results:** `rag_results[:3]` - แสดงแค่ 3 results

**Location:** `backend/app/orchestrator/nodes/generate_response.py` line 42

---

## ✅ วิธีแก้ไข: Remove All Limits

### Step 1: แก้ RPC Function Limit

**File:** `supabase/migrations/20250117000006_remove_all_limits.sql`

```sql
-- Remove limit from ai_get_leads
-- Show all results based on user query, not hardcoded limit

CREATE OR REPLACE FUNCTION ai_get_leads(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_limit INTEGER DEFAULT NULL,  -- Changed: NULL = no limit
    p_user_role TEXT DEFAULT 'staff'
)
...
LIMIT CASE 
    WHEN p_limit IS NULL THEN NULL  -- No limit
    WHEN p_limit > 0 THEN p_limit
    ELSE NULL  -- No limit
END
```

---

### Step 2: แก้ Backend Tool Limit

**File:** `backend/app/tools/db_tools.py`

**Before:**
```python
"p_limit": 100,  # Hardcoded limit
```

**After:**
```python
"p_limit": None,  # No limit - get all results
# หรือ
"p_limit": 10000,  # Very high limit (practically unlimited)
```

---

### Step 3: แก้ Format Function Limits

**File:** `backend/app/orchestrator/nodes/generate_response.py`

**Before:**
```python
for i, result in enumerate(rag_results[:3], 1):  # Limit to 3
    content_parts.append(content[:300])  # Limit to 300 chars
```

**After:**
```python
for i, result in enumerate(rag_results, 1):  # No limit
    content_parts.append(content)  # No character limit
```

---

### Step 4: แก้ Context Building Limits

**File:** `backend/app/orchestrator/nodes/generate_response.py`

**Before:**
```python
for i, result in enumerate(rag_results[:3], 1):  # Limit to 3
```

**After:**
```python
for i, result in enumerate(rag_results, 1):  # No limit
```

---

## 🎯 Recommended Changes

### Option 1: Remove Limits Completely (แนะนำ)

- RPC: `p_limit = NULL` (no limit)
- Backend: `p_limit = None`
- Format: Remove all `[:N]` slices

### Option 2: Very High Limits (ถ้า database ใหญ่มาก)

- RPC: `p_limit = 10000` (practically unlimited)
- Backend: `p_limit = 10000`
- Format: Keep some limits for performance

---

## 📝 Files to Modify

1. ✅ `backend/app/tools/db_tools.py` - Remove `p_limit: 100`
2. ✅ `backend/app/orchestrator/nodes/generate_response.py` - Remove `[:3]` and `[:300]` limits
3. ✅ `supabase/migrations/20250117000006_remove_all_limits.sql` - New migration to remove RPC limits

---

## ⚠️ Performance Considerations

**ถ้า database ใหญ่มาก:**
- อาจใช้ `p_limit = 10000` แทน `NULL`
- เก็บ RAG limit `[:10]` สำหรับ performance
- ใช้ pagination สำหรับ very large datasets

**ถ้า database ไม่ใหญ่มาก:**
- Remove all limits - ให้ดึงข้อมูลทั้งหมดตามที่ user ขอ
