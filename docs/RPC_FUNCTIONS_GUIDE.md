# 📚 RPC Functions Guide

> **เอกสารอธิบาย:** RPC Functions อยู่ที่ไหน และเรียกใช้ยังไง

---

## 📍 RPC Functions อยู่ที่ไหน?

### 1. **SQL Functions (Database Level)**

**ไฟล์:** `supabase/migrations/20250116000003_ai_rpc_functions.sql`

นี่คือ **Stored Procedures** ที่สร้างบน Supabase PostgreSQL database

```sql
-- ตัวอย่าง: ai_get_lead_status
CREATE OR REPLACE FUNCTION ai_get_lead_status(
    p_lead_name TEXT,
    p_user_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- SQL logic here
    RETURN v_result;
END;
$$;
```

**Location:**
```
evp-ai-assistant/
└── supabase/
    └── migrations/
        └── 20250116000003_ai_rpc_functions.sql  ← อยู่ที่นี่
```

### 2. **Python Wrapper Functions (Application Level)**

**ไฟล์:** `backend/app/tools/db_tools.py`

นี่คือ **Python functions** ที่เรียกใช้ RPC functions จาก database

```python
async def get_lead_status(lead_name: str, user_id: str) -> Dict[str, Any]:
    supabase = get_supabase_client()
    result = supabase.rpc("ai_get_lead_status", {...}).execute()
    return result.data
```

**Location:**
```
evp-ai-assistant/
└── backend/
    └── app/
        └── tools/
            └── db_tools.py  ← อยู่ที่นี่
```

---

## 🔄 Flow การทำงาน

```
User Question
    ↓
AI Orchestrator (LangGraph)
    ↓
db_query_node
    ↓
Python Function (db_tools.py)
    ↓
supabase.rpc("ai_get_lead_status", {...})
    ↓
PostgreSQL RPC Function (migration file)
    ↓
Query CRM Database Tables
    ↓
Return JSONB Result
    ↓
Back to Python → AI → User
```

---

## 📝 รูปแบบการเรียกใช้

### 1. เรียกจาก Python (Backend)

**Pattern:**
```python
from app.services.supabase import get_supabase_client

supabase = get_supabase_client()
result = supabase.rpc(
    "function_name",           # ชื่อ RPC function
    {
        "param1": value1,      # Parameters
        "param2": value2
    }
).execute()

data = result.data  # Get result
```

**ตัวอย่างจริง:**
```python
# จาก: backend/app/tools/db_tools.py

async def get_lead_status(lead_name: str, user_id: str):
    supabase = get_supabase_client()
    
    result = supabase.rpc(
        "ai_get_lead_status",              # ← ชื่อ function ใน database
        {
            "p_lead_name": lead_name,      # ← Parameter 1
            "p_user_id": user_id            # ← Parameter 2
        }
    ).execute()
    
    return result.data if result.data else {}
```

### 2. เรียกจาก TypeScript/JavaScript (Frontend - ถ้าต้องการ)

**Pattern:**
```typescript
const { data, error } = await supabase.rpc('function_name', {
  param1: value1,
  param2: value2
});
```

**ตัวอย่าง:**
```typescript
// จาก CRM project
const { data, error } = await supabase.rpc(
  'safe_insert_lead_with_duplicate_check',
  {
    p_lead_data: leadData
  }
);
```

### 3. เรียกจาก SQL (Direct)

**Pattern:**
```sql
SELECT ai_get_lead_status('lead name', 'user-id-uuid');
```

**ตัวอย่าง:**
```sql
-- เรียกใช้โดยตรงใน SQL
SELECT ai_get_lead_status('John Doe', '123e4567-e89b-12d3-a456-426614174000');
```

---

## 📋 RPC Functions ที่มีอยู่

### 1. `ai_get_lead_status`

**SQL Function:**
```sql
CREATE OR REPLACE FUNCTION ai_get_lead_status(
    p_lead_name TEXT,
    p_user_id UUID
)
RETURNS JSONB
```

**Python Call:**
```python
from app.tools.db_tools import get_lead_status

result = await get_lead_status("John Doe", "user-id")
# Returns: {"found": true, "lead_id": 123, "status": "active", ...}
```

**Parameters:**
- `p_lead_name` (TEXT) - ชื่อ lead ที่ต้องการค้นหา
- `p_user_id` (UUID) - User ID สำหรับ permission check

**Returns:**
```json
{
  "found": true,
  "lead_id": 123,
  "full_name": "John Doe",
  "status": "active",
  "category": "Package",
  ...
}
```

### 2. `ai_get_daily_summary`

**SQL Function:**
```sql
CREATE OR REPLACE FUNCTION ai_get_daily_summary(
    p_user_id UUID,
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS JSONB
```

**Python Call:**
```python
from app.tools.db_tools import get_daily_summary

result = await get_daily_summary("user-id", "2025-01-16")
# Returns: {"date": "2025-01-16", "new_leads_today": 5, ...}
```

### 3. `ai_get_customer_info`

**SQL Function:**
```sql
CREATE OR REPLACE FUNCTION ai_get_customer_info(
    p_customer_name TEXT,
    p_user_id UUID
)
RETURNS JSONB
```

**Python Call:**
```python
from app.tools.db_tools import get_customer_info

result = await get_customer_info("ABC Company", "user-id")
# Returns: {"found": true, "customer_name": "ABC Company", ...}
```

### 4. `ai_get_team_kpi`

**SQL Function:**
```sql
CREATE OR REPLACE FUNCTION ai_get_team_kpi(
    p_team_id INTEGER DEFAULT NULL,
    p_user_id UUID
)
RETURNS JSONB
```

**Python Call:**
```python
from app.tools.db_tools import get_team_kpi

result = await get_team_kpi(None, "user-id")
# Returns: {"total_leads": 100, "active_leads": 50, ...}
```

---

## 🔍 ตัวอย่างการใช้งานจริง

### ตัวอย่าง 1: เรียกจาก AI Orchestrator

```python
# จาก: backend/app/orchestrator/nodes/db_query.py

async def db_query_node(state: AIAssistantState):
    user_message = state.get("user_message", "")
    user_id = state.get("user_id", "")
    
    # เรียกใช้ RPC tool
    result = await get_lead_status("John Doe", user_id)
    
    # Update state
    state["tool_results"] = [{
        "tool": "get_lead_status",
        "output": result
    }]
    
    return state
```

### ตัวอย่าง 2: เรียกจาก API Endpoint

```python
# จาก: backend/app/api/v1/chat.py

@router.post("/chat")
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    # AI Orchestrator จะเรียกใช้ RPC tools อัตโนมัติ
    result_state = await process_message(initial_state)
    # RPC calls เกิดขึ้นภายใน workflow
```

### ตัวอย่าง 3: เรียกโดยตรง (Testing)

```python
# Test script
from app.tools.db_tools import get_lead_status

async def test():
    result = await get_lead_status("test lead", "user-id")
    print(result)
```

---

## 🛠️ การสร้าง RPC Function ใหม่

### Step 1: สร้าง SQL Function

**ไฟล์:** `supabase/migrations/YYYYMMDDHHMMSS_new_function.sql`

```sql
CREATE OR REPLACE FUNCTION ai_new_function(
    p_param1 TEXT,
    p_user_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
BEGIN
    -- Your SQL logic here
    v_result := jsonb_build_object(
        'success', true,
        'data', 'your data'
    );
    
    RETURN v_result;
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'error', true,
            'message', SQLERRM
        );
END;
$$;

GRANT EXECUTE ON FUNCTION ai_new_function(TEXT, UUID) TO authenticated;
```

### Step 2: สร้าง Python Wrapper

**ไฟล์:** `backend/app/tools/db_tools.py`

```python
async def new_function(param1: str, user_id: str) -> Dict[str, Any]:
    """
    New function via RPC
    RPC: ai_new_function(param1, user_id)
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.rpc(
            "ai_new_function",
            {
                "p_param1": param1,
                "p_user_id": user_id
            }
        ).execute()
        
        logger.info(f"RPC: ai_new_function, param1={param1}, user={user_id}")
        return result.data if result.data else {}
    
    except Exception as e:
        logger.error(f"RPC error (ai_new_function): {e}")
        return {"error": str(e)}
```

### Step 3: ใช้ใน AI Orchestrator

**ไฟล์:** `backend/app/orchestrator/nodes/db_query.py`

```python
from app.tools.db_tools import new_function

# ใน db_query_node
if condition:
    result = await new_function(param1, user_id)
```

---

## 🔐 Security & Permissions

### 1. SECURITY DEFINER

RPC functions ใช้ `SECURITY DEFINER` ซึ่งหมายความว่า:
- Function รันด้วยสิทธิ์ของ function owner (ไม่ใช่ caller)
- สามารถ bypass RLS ได้ (ถ้าต้องการ)
- ต้องระวัง security implications

### 2. Permission Checks

ทุก RPC function ควร:
- รับ `p_user_id` parameter
- ตรวจสอบ role ของ user
- Filter data ตาม role
- Mask PII สำหรับ non-admin

### 3. Grant Permissions

```sql
GRANT EXECUTE ON FUNCTION ai_get_lead_status(TEXT, UUID) TO authenticated;
```

---

## 📊 เปรียบเทียบ: RPC vs Direct Query

### ❌ ไม่ควรทำ (Direct Query)

```python
# ❌ ไม่ปลอดภัย - AI เขียน SQL เอง
result = supabase.table("leads").select("*").eq("name", name).execute()
```

### ✅ ควรทำ (RPC Function)

```python
# ✅ ปลอดภัย - ผ่าน RPC function ที่มี permission checks
result = supabase.rpc("ai_get_lead_status", {"p_lead_name": name, "p_user_id": user_id}).execute()
```

**ข้อดี:**
- ✅ Security: Permission checks built-in
- ✅ Predictable: Output schema ชัดเจน
- ✅ Audit: Log ได้ง่าย
- ✅ Maintainable: Logic อยู่ที่เดียว

---

## 🧪 Testing RPC Functions

### Test SQL Function โดยตรง

```sql
-- ใน Supabase SQL Editor
SELECT ai_get_lead_status('John Doe', '123e4567-e89b-12d3-a456-426614174000');
```

### Test Python Wrapper

```python
# ใน Python shell หรือ test file
from app.tools.db_tools import get_lead_status
import asyncio

async def test():
    result = await get_lead_status("test", "user-id")
    print(result)

asyncio.run(test())
```

---

## 📚 References

- **SQL Functions:** `supabase/migrations/20250116000003_ai_rpc_functions.sql`
- **Python Wrappers:** `backend/app/tools/db_tools.py`
- **Usage:** `backend/app/orchestrator/nodes/db_query.py`
- **CRM Examples:** `ev-power-energy-crm/supabase/functions/`

---

**Last Updated:** 2025-01-16
