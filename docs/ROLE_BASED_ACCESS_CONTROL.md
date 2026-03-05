# 🔐 Role-Based Access Control (RBAC) Overview

## 📋 สรุป

ระบบมีการกำหนดสิทธิ์ข้อมูลตาม role ของ user อยู่แล้ว โดยมี 3 roles หลัก:

- **Admin** - เข้าถึงข้อมูลทั้งหมด
- **Manager** - เข้าถึงข้อมูลส่วนใหญ่
- **Staff** - เข้าถึงข้อมูลจำกัด

---

## 🔍 สิทธิ์ข้อมูลตาม Role

### 1. `ai_get_leads` (Search Leads)

**Admin:**
- ✅ เบอร์โทร (`tel`)
- ✅ Line ID (`line_id`)
- ✅ ข้อมูลทั้งหมด

**Staff:**
- ❌ เบอร์โทร → `NULL` (Mask PII)
- ❌ Line ID → `NULL` (Mask PII)
- ✅ ข้อมูลอื่นๆ (ชื่อ, สถานะ, region, etc.)

**Code:**
```sql
'tel', CASE WHEN p_user_role = 'admin' THEN tel ELSE NULL END,  -- Mask PII
'line_id', CASE WHEN p_user_role = 'admin' THEN line_id ELSE NULL END,  -- Mask PII
```

---

### 2. `ai_get_customer_info` (Get Customer Info)

**Admin:**
- ✅ เบอร์โทร (`tel`)
- ✅ Line ID (`line_id`)
- ✅ ข้อมูลทั้งหมด (created_at, updated_at)

**Staff:**
- ❌ เบอร์โทร → ไม่แสดง
- ❌ Line ID → ไม่แสดง
- ❌ created_at, updated_at → ไม่แสดง
- ✅ เฉพาะชื่อ, service_type, status

**Code:**
```sql
IF v_user_role = 'admin' THEN
    -- Return full information including tel, line_id
ELSE
    -- Mask PII - only name, service_type, status
END IF;
```

---

### 3. `ai_get_daily_summary` (Daily Summary)

**Admin/Manager:**
- ✅ Total leads
- ✅ New leads today
- ✅ Total customers

**Staff:**
- ❌ Total leads → ไม่แสดง
- ✅ New leads today
- ❌ Total customers → ไม่แสดง

**Code:**
```sql
IF p_user_role IN ('admin', 'manager') THEN
    -- Return full summary
ELSE
    -- Return limited summary (only new_leads_today)
END IF;
```

---

### 4. `ai_get_team_kpi` (Team KPI)

**Admin/Manager:**
- ✅ Total leads
- ✅ Active leads
- ✅ Performance metrics

**Staff:**
- ❌ Permission denied

**Code:**
```sql
IF v_user_role NOT IN ('admin', 'manager') THEN
    RETURN jsonb_build_object(
        'error', true,
        'message', 'Permission denied. Only admin and manager can view team KPI.'
    );
END IF;
```

---

### 5. `ai_get_lead_status` (Get Lead Status)

**Admin/Manager:**
- ✅ ข้อมูลทั้งหมด
- ✅ sale_owner_id
- ✅ notes
- ✅ created_at, updated_at

**Staff:**
- ✅ ข้อมูลพื้นฐาน (ชื่อ, สถานะ, category, region)
- ❌ sale_owner_id → ไม่แสดง
- ❌ notes → ไม่แสดง

---

## 🔧 Backend Role Checking

### `require_role` Dependency

Backend มี `require_role` dependency สำหรับตรวจสอบ role:

```python
from app.core.auth import require_role

@router.get("/admin-only")
async def admin_endpoint(
    current_user: dict = Depends(require_role(["admin"]))
):
    # Only admin can access
    pass
```

---

## 📊 สรุปสิทธิ์

| Function | Admin | Manager | Staff |
|----------|-------|---------|-------|
| `ai_get_leads` | ✅ All (incl. tel, line_id) | ✅ All (incl. tel, line_id) | ✅ Limited (no tel, line_id) |
| `ai_get_customer_info` | ✅ All (incl. tel, line_id) | ✅ All (incl. tel, line_id) | ✅ Limited (no tel, line_id) |
| `ai_get_daily_summary` | ✅ Full summary | ✅ Full summary | ✅ Limited (new leads only) |
| `ai_get_team_kpi` | ✅ All metrics | ✅ All metrics | ❌ Denied |
| `ai_get_lead_status` | ✅ All info | ✅ All info | ✅ Basic info only |

---

## 🚨 PII (Personally Identifiable Information) Masking

### ข้อมูลที่ถูก Mask สำหรับ Non-Admin:

1. **เบอร์โทรศัพท์** (`tel`)
2. **Line ID** (`line_id`)
3. **Phone Number** (ใน sales docs)
4. **Contact Information** (PII)

### เหตุผล:
- ป้องกันการรั่วไหลของข้อมูลส่วนตัว
- ป้องกันการใช้งานในทางที่ผิด
- ตามมาตรฐาน GDPR/Privacy laws

---

## 🔄 การเปลี่ยนแปลง

### Migration `20250117000005_remove_pii_masking.sql`

Migration นี้จะลบ PII masking ออกจาก `ai_get_leads` เพื่อแสดงข้อมูลทั้งหมด (ตามที่คุณต้องการ)

**Before:**
```sql
'tel', CASE WHEN p_user_role = 'admin' THEN tel ELSE NULL END,  -- Mask PII
```

**After:**
```sql
'tel', tel,  -- Show all data - no masking
```

---

## 💡 คำแนะนำ

### ถ้าต้องการรักษา RBAC:
- ไม่ต้อง run migration `20250117000005_remove_pii_masking.sql`
- เก็บ PII masking ไว้เพื่อความปลอดภัย

### ถ้าต้องการแสดงข้อมูลทั้งหมด:
- Run migration `20250117000005_remove_pii_masking.sql`
- ข้อมูลทั้งหมดจะแสดงให้ทุก role

---

## 📝 หมายเหตุ

1. **Role มาจาก JWT Token** - `user_metadata.role`
2. **Default Role** - `staff` (ถ้าไม่มี role ใน token)
3. **Role Format** - `admin`, `manager`, `staff` (case-sensitive)
