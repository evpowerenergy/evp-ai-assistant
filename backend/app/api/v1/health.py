"""
Health Check Endpoint
"""
from fastapi import APIRouter
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    Returns API status
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "ai-assistant-backend"
    }
