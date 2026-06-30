"""
LINE Webhook API Endpoint
"""
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app.config import settings
from app.core.audit import log_audit
from app.services.line import parse_webhook_events, verify_line_signature
from app.services.line_handler import dispatch_line_event
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/line/webhook")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: str | None = Header(None, alias="X-Line-Signature"),
):
    """
    LINE webhook endpoint.
    Verifies signature, returns 200 immediately, processes events in background.
    """
    body = await request.body()

    if not settings.LINE_CHANNEL_SECRET:
        raise HTTPException(status_code=503, detail="LINE not configured")

    if not verify_line_signature(body, x_line_signature, settings.LINE_CHANNEL_SECRET):
        logger.warning("Invalid LINE webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    events = parse_webhook_events(body)
    for event in events:
        background_tasks.add_task(dispatch_line_event, event)

    if events:
        await log_audit(
            user_id="line-system",
            action="line_webhook",
            resource="line",
            metadata={"event_count": len(events)},
        )

    return {"status": "ok"}
