"""
Rate Limiting
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from app.utils.logger import get_logger

logger = get_logger(__name__)

# In-memory rate limit store (use Redis in production)
_rate_limit_store: Dict[str, Dict[str, any]] = defaultdict(dict)


class RateLimiter:
    """Simple rate limiter (in-memory)"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def is_allowed(self, key: str) -> tuple[bool, int]:
        """
        Check if request is allowed
        Returns: (is_allowed, remaining_requests)
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Get or create rate limit entry
        entry = _rate_limit_store.get(key, {})
        
        # Clean old requests
        requests = [
            req_time for req_time in entry.get("requests", [])
            if req_time > window_start
        ]
        
        # Check limit
        if len(requests) >= self.max_requests:
            remaining = 0
            return False, remaining
        
        # Add current request
        requests.append(now)
        _rate_limit_store[key] = {
            "requests": requests,
            "last_reset": now
        }
        
        remaining = self.max_requests - len(requests)
        return True, remaining
    
    def reset(self, key: str):
        """Reset rate limit for a key"""
        if key in _rate_limit_store:
            del _rate_limit_store[key]


# Global rate limiters
user_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)  # 100 req/min per user
ip_rate_limiter = RateLimiter(max_requests=200, window_seconds=60)  # 200 req/min per IP
chat_rate_limiter = RateLimiter(max_requests=20, window_seconds=60)  # 20 chat req/min per user


async def check_rate_limit(
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    endpoint: str = "default"
) -> tuple[bool, int]:
    """
    Check rate limit for user and IP
    Returns: (is_allowed, remaining_requests)
    """
    is_allowed = True
    remaining = 0
    
    # Check user rate limit
    if user_id:
        if endpoint == "chat":
            allowed, remaining = chat_rate_limiter.is_allowed(f"user:{user_id}:chat")
        else:
            allowed, remaining = user_rate_limiter.is_allowed(f"user:{user_id}")
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for user: {user_id}, endpoint: {endpoint}")
            return False, remaining
    
    # Check IP rate limit
    if ip_address:
        allowed, _ = ip_rate_limiter.is_allowed(f"ip:{ip_address}")
        if not allowed:
            logger.warning(f"Rate limit exceeded for IP: {ip_address}")
            return False, remaining
    
    return is_allowed, remaining
