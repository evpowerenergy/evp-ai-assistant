# 🔍 Error Analysis - Supabase Proxy & Graph Issues

## 📋 สรุปปัญหา

### ❌ Error 1: Supabase Client Proxy Parameter
```
Client.__init__() got an unexpected keyword argument 'proxy'
```

**Root Cause:**
- `postgrest==0.13.2` (ที่ Supabase 2.3.0 ใช้) **ไม่รองรับ `proxy` parameter** ใน `Client.__init__()`
- แต่ Supabase SDK อาจพยายามส่ง `proxy` parameter ไปยัง postgrest Client
- **ไม่มี environment variables `HTTP_PROXY`/`HTTPS_PROXY`** อยู่ในระบบ (ตรวจสอบแล้ว)

**ผลกระทบ:**
- ❌ Supabase client initialize ไม่ได้
- ❌ Auth, Save Chat, Audit Log **พังหมด**
- ❌ Frontend ได้ 401 → redirect ไป login

---

### ❌ Error 2: LangGraph Workflow
```
Workflow error: Need to add_node `router` first
```

**Root Cause:**
- `graph.set_entry_point("router")` ถูกเรียก **ก่อน** `graph.add_node("router")`
- LangGraph **ไม่อนุญาต** ให้ set entry point ก่อน add node

**สถานะ:** ✅ **แก้ไขแล้ว** - ย้าย `add_node("router")` ไปก่อน `set_entry_point("router")`

---

## 🔧 วิธีแก้ไข

### ✅ Graph Error - แก้แล้ว

**ไฟล์:** `app/orchestrator/graph.py`

**แก้ไข:**
- ย้าย `add_node("router")` ไปก่อน `set_entry_point("router")`

---

### 🔧 Supabase Proxy Error - ยังต้องแก้

**ปัญหา:** `postgrest==0.13.2` ที่ Supabase ติดตั้งมา ไม่รองรับ proxy parameter

**วิธีแก้ (เลือก 1 อย่าง):**

#### วิธีที่ 1: Downgrade postgrest (แนะนำ)

```bash
cd evp-ai-assistant/backend
python3 -m pip install "postgrest>=0.10.8,<0.13.0" --force-reinstall
```

#### วิธีที่ 2: Patch Supabase Client

สร้าง wrapper ที่ patch postgrest client:

```python
# app/services/supabase.py
from supabase import create_client, Client
from postgrest import SyncPostgrestClient

# Monkey patch to remove proxy parameter
_original_init = SyncPostgrestClient.__init__

def _patched_init(self, *args, **kwargs):
    # Remove proxy if it exists
    kwargs.pop('proxy', None)
    return _original_init(self, *args, **kwargs)

SyncPostgrestClient.__init__ = _patched_init
```

#### วิธีที่ 3: ใช้ Supabase Version ที่ต่ำกว่า

```bash
pip install "supabase==1.2.0" --force-reinstall
```

---

## 📊 Dependencies ปัจจุบัน

```
supabase==2.3.0          ✅ ถูกต้อง
postgrest==0.13.2        ⚠️ อาจมีปัญหา proxy
httpx==0.24.1            ✅ Compatible
httpcore==0.17.3         ✅ Compatible
packaging==23.2          ✅ Compatible (แก้แล้ว)
```

---

## 🎯 Checklist หลังแก้

- [ ] Restart backend server
- [ ] ตรวจสอบ log: `Supabase client initialized successfully`
- [ ] ตรวจสอบ log: **ไม่มี** `proxy` error
- [ ] ตรวจสอบ log: **ไม่มี** `Need to add_node router` error
- [ ] ทดสอบ chat: ส่งข้อความสำเร็จ
- [ ] ทดสอบ auth: ไม่ redirect ไป login

---

## 🔍 Debug Commands

```bash
# ตรวจสอบ dependencies
pip freeze | grep -E "supabase|postgrest|httpx"

# ทดสอบ Supabase client
python3 -c "from app.services.supabase import get_supabase_client; get_supabase_client()"

# ตรวจสอบ proxy env vars
env | grep -i proxy
```
