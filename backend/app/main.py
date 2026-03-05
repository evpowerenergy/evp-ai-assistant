"""
FastAPI Application Entry Point
"""
# IMPORTANT: Import httpx patch FIRST to fix proxy parameter compatibility
# This must be imported before any module that uses httpx (supabase, postgrest, etc.)
from app.services import _httpx_patch  # noqa: F401

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.utils.logger import setup_logging, get_logger
from app.api.v1 import chat, line, ingest, health, test_tools, config as config_router, prompt_tests, me as me_router
from app.middleware.rate_limit_middleware import RateLimitMiddleware

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting AI Assistant API...")
    yield
    # Shutdown
    logger.info("Shutting down AI Assistant API...")


app = FastAPI(
    title="AI Assistant API",
    description="Internal AI Assistant & Knowledge Chatbot API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # Use property to get list
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Include API routes
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(line.router, prefix="/api/v1", tags=["line"])
app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])
app.include_router(test_tools.router, prefix="/api/v1", tags=["test-tools"])
app.include_router(config_router.router, prefix="/api/v1", tags=["config"])
app.include_router(prompt_tests.router, prefix="/api/v1", tags=["prompt-tests"])
app.include_router(me_router.router, prefix="/api/v1", tags=["me"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Assistant API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
