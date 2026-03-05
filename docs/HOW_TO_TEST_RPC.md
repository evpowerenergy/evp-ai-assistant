# 🧪 วิธีทดสอบ RPC Functions จากภายนอก

## วิธีที่ 1: ใช้ Python Script (แนะนำ)

```bash
cd /home/film/ev-power-energy/evp-ai-assistant/backend
source venv/bin/activate
python test_rpc_function.py
```

**Script นี้จะทดสอบ:**
- ✅ `ai_get_daily_summary` (with different roles)
- ✅ `ai_get_lead_status`
- ✅ `ai_get_team_kpi`

---

## วิธีที่ 2: ใช้ Supabase SQL Editor

1. ไปที่ **Supabase Dashboard** → **SQL Editor**
2. Run SQL นี้:

```sql
-- Test ai_get_daily_summary
SELECT ai_get_daily_summary(
    '9f39067b-f803-4cb4-b3c6-c0f2e3403fd8'::uuid,
    CURRENT_DATE,
    'staff'::text
);

-- Test with admin role
SELECT ai_get_daily_summary(
    '9f39067b-f803-4cb4-b3c6-c0f2e3403fd8'::uuid,
    CURRENT_DATE,
    'admin'::text
);
```

---

## วิธีที่ 3: ใช้ curl (REST API)

```bash
# Get auth token first (from frontend or Supabase)
TOKEN="your-access-token-here"

# Test RPC function
curl -X POST \
  "https://ttfjapfdzrxmbxbarfbn.supabase.co/rest/v1/rpc/ai_get_daily_summary" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "apikey: YOUR_SUPABASE_ANON_KEY" \
  -d '{
    "p_user_id": "9f39067b-f803-4cb4-b3c6-c0f2e3403fd8",
    "p_date": "2026-01-17",
    "p_user_role": "staff"
  }'
```

---

## วิธีที่ 4: ใช้ Postman / Insomnia

**Request:**
- **Method:** POST
- **URL:** `https://ttfjapfdzrxmbxbarfbn.supabase.co/rest/v1/rpc/ai_get_daily_summary`
- **Headers:**
  - `Authorization: Bearer <your-token>`
  - `Content-Type: application/json`
  - `apikey: <your-anon-key>`
- **Body (JSON):**
```json
{
  "p_user_id": "9f39067b-f803-4cb4-b3c6-c0f2e3403fd8",
  "p_date": "2026-01-17",
  "p_user_role": "staff"
}
```
