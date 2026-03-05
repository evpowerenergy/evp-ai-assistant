"""
Current user profile API - ดึง role จากตาราง users/employees ผ่าน backend (service role)
แบบเดียวกับ CRM ที่ใช้ additional-auth-user-data
"""
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    คืน role (และ profile) ของ user ปัจจุบันจากตาราง users หรือ employees
    ใช้ service role จึงไม่ติด RLS (แบบเดียวกับ CRM additional-auth-user-data)
    """
    auth_user_id = current_user.get("id") or current_user.get("sub")
    if not auth_user_id:
        return {"role": current_user.get("role"), "first_name": None, "last_name": None}

    try:
        supabase = get_supabase_client()
        for table in ("users", "employees"):
            r = supabase.table(table).select("role, first_name, last_name").eq("auth_user_id", auth_user_id).limit(1).execute()
            row = (r.data or [])[0] if r.data else None
            if row and row.get("role"):
                role = str(row.get("role", "")).strip()
                if role:
                    return {
                        "role": role,
                        "first_name": row.get("first_name"),
                        "last_name": row.get("last_name"),
                    }
    except Exception as e:
        logger.warning("get_me: %s", e)

    return {
        "role": current_user.get("role"),
        "first_name": None,
        "last_name": None,
    }
