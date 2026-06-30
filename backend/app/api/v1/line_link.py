"""
LINE account linking API (JWT required).
"""
from fastapi import APIRouter, Depends

from app.core.auth import require_ai_assistant_access
from app.services.line_link import (
    generate_link_code,
    get_line_link_status,
    unlink_line_account,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/line/link-code")
async def create_link_code(current_user: dict = Depends(require_ai_assistant_access)):
    """Generate a 6-digit verification code for LINE linking."""
    user_id = current_user.get("id")
    result = await generate_link_code(user_id)
    return {"success": True, **result}


@router.get("/line/status")
async def line_status(current_user: dict = Depends(require_ai_assistant_access)):
    """Get LINE link status for current user."""
    user_id = current_user.get("id")
    status = await get_line_link_status(user_id)
    return {"success": True, **status}


@router.delete("/line/unlink")
async def line_unlink(current_user: dict = Depends(require_ai_assistant_access)):
    """Unlink LINE account for current user."""
    user_id = current_user.get("id")
    await unlink_line_account(user_id)
    return {"success": True, "message": "LINE account unlinked"}
