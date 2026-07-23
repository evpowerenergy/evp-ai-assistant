from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

import jwt

from app.config import settings
from app.engines.base import ActorContext


ROLE_SCOPES = {
    "super_admin": ["crm.read", "sales.read", "marketing.read", "knowledge.read"],
    "manager_sale": ["crm.read", "sales.read", "knowledge.read"],
    "manager_marketing": ["marketing.read", "knowledge.read"],
    "manager_hr": ["knowledge.read"],
}


def scopes_for_role(role: str) -> List[str]:
    return list(ROLE_SCOPES.get((role or "").strip().lower(), []))


def create_execution_token(context: ActorContext) -> str:
    """Create the short-lived capability consumed only by the EVP MCP gateway."""
    if not settings.EVP_EXECUTION_PRIVATE_KEY:
        raise RuntimeError("EVP_EXECUTION_PRIVATE_KEY is not configured")
    now = datetime.now(timezone.utc)
    private_key = settings.EVP_EXECUTION_PRIVATE_KEY.replace("\\n", "\n")
    return jwt.encode(
        {
            "iss": "evp-api",
            "aud": "evp-mcp",
            "sub": context.user_id,
            "role": context.user_role,
            "scopes": scopes_for_role(context.user_role),
            "session_id": context.session_id,
            "request_id": context.request_id,
            "jti": context.request_id,
            "source": context.source,
            "iat": now,
            "exp": now + timedelta(seconds=settings.EVP_EXECUTION_TOKEN_TTL_SECONDS),
        },
        private_key,
        algorithm="EdDSA",
        headers={"kid": settings.EVP_EXECUTION_KEY_ID},
    )
