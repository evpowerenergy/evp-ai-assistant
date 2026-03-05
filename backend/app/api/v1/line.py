"""
LINE Webhook API Endpoint
"""
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from app.utils.logger import get_logger
from app.core.audit import log_audit

logger = get_logger(__name__)
router = APIRouter()


@router.post("/line/webhook")
async def line_webhook(
    request: Request,
    x_line_signature: Optional[str] = Header(None)
):
    """
    LINE webhook endpoint
    Receives and processes LINE messages
    """
    try:
        # Get request body
        body = await request.body()
        
        # TODO: Verify LINE signature in Phase 4
        # from linebot import LineBotApi, WebhookHandler
        # handler = WebhookHandler(channel_secret)
        # handler.handle(body, x_line_signature)
        
        # TODO: Process LINE events in Phase 4
        logger.info("LINE webhook received (not yet implemented)")
        
        # Log webhook
        await log_audit(
            user_id="line-system",
            action="line_webhook",
            resource="line",
            request_data={"signature": x_line_signature}
        )
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"LINE webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
