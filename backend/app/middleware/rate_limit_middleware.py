"""
Rate Limiting Middleware
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.rate_limit import check_rate_limit
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get user ID from request state (if authenticated)
        user_id = getattr(request.state, "user_id", None)
        
        # Determine endpoint type
        endpoint = "chat" if "/chat" in str(request.url) else "default"
        
        # Check rate limit
        is_allowed, remaining = await check_rate_limit(
            user_id=user_id,
            ip_address=client_ip,
            endpoint=endpoint
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"X-RateLimit-Remaining": "0"}
            )
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
