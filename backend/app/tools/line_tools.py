"""
LINE Notification Tools
"""
from typing import Optional
from app.services.line import send_line_notification
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def notify_new_lead(
    user_id: str,
    lead_name: str,
    lead_id: str,
    web_url: Optional[str] = None
) -> bool:
    """
    Send LINE notification for new lead
    """
    try:
        title = "🆕 Lead ใหม่"
        message = f"มี lead ใหม่: {lead_name}"
        
        return await send_line_notification(
            user_id=user_id,
            title=title,
            message=message,
            link_url=web_url
        )
    
    except Exception as e:
        logger.error(f"LINE notification error: {e}")
        return False


async def notify_exception(
    user_id: str,
    exception_type: str,
    message: str,
    web_url: Optional[str] = None
) -> bool:
    """
    Send LINE notification for exception/alert
    """
    try:
        title = f"⚠️ {exception_type}"
        
        return await send_line_notification(
            user_id=user_id,
            title=title,
            message=message,
            link_url=web_url
        )
    
    except Exception as e:
        logger.error(f"LINE notification error: {e}")
        return False
