from __future__ import annotations

from typing import Any, Dict

import jwt

from app.config import settings
from app.utils.exceptions import AuthenticationError, PermissionDeniedError


def verify_execution_token(token: str) -> Dict[str, Any]:
    if not settings.EVP_EXECUTION_PUBLIC_KEY:
        raise AuthenticationError("Execution-token verification is not configured")
    try:
        payload = jwt.decode(
            token,
            settings.EVP_EXECUTION_PUBLIC_KEY.replace("\\n", "\n"),
            algorithms=["EdDSA"],
            audience="evp-mcp",
            issuer="evp-api",
            options={"require": ["exp", "iat", "sub", "jti", "session_id"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid execution token") from exc
    if not isinstance(payload.get("scopes"), list):
        raise PermissionDeniedError("Execution token has no scopes")
    return payload


def require_execution_scope(payload: Dict[str, Any], scope: str) -> None:
    if scope not in set(payload.get("scopes") or []):
        raise PermissionDeniedError(f"Missing execution scope: {scope}")
