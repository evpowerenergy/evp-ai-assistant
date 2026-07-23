"""
Config API - expose model and agent info for UI
"""
from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/config")
async def get_config():
    """
    Returns current LLM model and which agents use it (for UI display).
    No auth required so the chat UI can show model name even before/without login.
    All agents use the same OPENAI_MODEL from settings (.env or default).
    """
    model = settings.OPENAI_MODEL
    primary_engine = settings.AI_PRIMARY_ENGINE
    primary_model = settings.HERMES_MODEL if primary_engine == "hermes" else model
    agents = [
        {"name": "วิเคราะห์ Intent (Router)", "role": "router", "model": model},
        {"name": "สร้างคำตอบ / ตอบคำถามทั่วไป", "role": "generate_response", "model": model},
        {"name": "ตรวจคุณภาพข้อมูล (Result Grader)", "role": "result_grader", "model": model},
        {"name": "ตรวจการเลือก Tool", "role": "tool_selection_verifier", "model": model},
        {"name": "ตรวจผลการเรียก Tool", "role": "tool_execution_verifier", "model": model},
    ]
    return {
        "openai_model": model,
        "agents": agents,
        "agents_count": len(agents),
        "primary_engine": primary_engine,
        "primary_model": primary_model,
        "fallback_engine": settings.AI_FALLBACK_ENGINE,
        "fallback_model": model,
    }
