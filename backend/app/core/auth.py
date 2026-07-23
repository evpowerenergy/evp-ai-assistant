"""
Authentication and Authorization
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import httpx
from jwt import PyJWKClient
from app.utils.exceptions import AuthenticationError, PermissionDeniedError
from app.utils.logger import get_logger
from app.config import settings
from app.core.roles import is_ai_assistant_role, resolve_role_from_db

logger = get_logger(__name__)
security = HTTPBearer()
_jwks_client: Optional[PyJWKClient] = None


async def _verify_with_supabase_auth(token: str) -> dict:
    """Validate a legacy HS256 access token with the issuing Auth service.

    New Supabase projects expose asymmetric JWKS. Legacy projects do not, and
    local developers may not have the project's JWT secret. Calling /auth/v1/user
    still performs authoritative server-side token validation without weakening
    signature checks or trusting unverified claims locally.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {token}",
                },
            )
        if response.status_code != 200:
            raise AuthenticationError("Invalid token")
        user = response.json()
    except AuthenticationError:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Supabase Auth token verification failed: %s", type(exc).__name__)
        raise AuthenticationError("Token verification failed") from exc

    user_id = user.get("id")
    if not user_id:
        raise AuthenticationError("User ID not found in token")
    return {
        "sub": user_id,
        "email": user.get("email", ""),
        "user_metadata": user.get("user_metadata") or {},
        "aud": user.get("aud", settings.SUPABASE_JWT_AUDIENCE),
    }


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            settings.supabase_jwt_jwks_url,
            cache_keys=True,
            lifespan=300,
        )
    return _jwks_client


async def verify_jwt_token(token: str) -> dict:
    """
    Verify JWT token from Supabase
    Returns decoded token payload
    Signature verification is mandatory. Asymmetric tokens use Supabase JWKS;
    legacy HS256 tokens require SUPABASE_JWT_SECRET.
    """
    try:
        header = jwt.get_unverified_header(token)
        algorithm = str(header.get("alg") or "")
        if algorithm == "HS256":
            if not settings.SUPABASE_JWT_SECRET:
                logger.info("Verifying legacy HS256 token with Supabase Auth")
                return await _verify_with_supabase_auth(token)
            signing_key = settings.SUPABASE_JWT_SECRET
        elif algorithm in {"RS256", "ES256"}:
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token).key
        else:
            raise AuthenticationError("Unsupported JWT algorithm")

        unverified = jwt.decode(
            token,
            signing_key,
            algorithms=[algorithm],
            audience=settings.SUPABASE_JWT_AUDIENCE,
            options={"require": ["exp", "sub"]},
        )
        
        user_id = unverified.get("sub")
        if not user_id:
            raise AuthenticationError("User ID not found in token")
        
        exp = unverified.get("exp")
        
        # Note: auth.users table cannot be queried via REST API
        # We rely on JWT token payload which already contains user info from Supabase Auth
        # Token is validated by Supabase Auth service before being issued
        
        # Return token payload
        return {
            "sub": user_id,
            "email": unverified.get("email", ""),
            "user_metadata": unverified.get("user_metadata", {}),
            "aud": unverified.get("aud", "authenticated"),
            "exp": exp,
            "iat": unverified.get("iat"),
        }
    
    except AuthenticationError:
        raise
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise AuthenticationError("Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise AuthenticationError("Invalid token")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"JWT verification error: {error_msg}")
        raise AuthenticationError("Token verification failed")


async def get_user_from_token(token_payload: dict) -> dict:
    """
    Get user information: role from DB (users/employees) first, then JWT metadata.
    """
    try:
        user_id = token_payload.get("sub")
        if not user_id:
            raise AuthenticationError("User ID not found in token")
        
        user_metadata = token_payload.get("user_metadata", {}) or {}
        role_from_metadata = user_metadata.get("role") or "staff"
        
        # Resolve role from DB so API auth matches frontend (super_admin etc.)
        role_from_db = resolve_role_from_db(user_id)
        role = (role_from_db or role_from_metadata) if role_from_db else role_from_metadata
        
        return {
            "id": user_id,
            "email": token_payload.get("email", ""),
            "role": role if isinstance(role, str) else "staff",
            "metadata": user_metadata
        }
    
    except Exception as e:
        logger.error(f"Error getting user from token: {e}")
        user_id = token_payload.get("sub", "")
        return {
            "id": user_id,
            "email": token_payload.get("email", ""),
            "role": resolve_role_from_db(user_id) or (token_payload.get("user_metadata") or {}).get("role", "staff")
        }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get current user from JWT token
    Validates token with Supabase Auth
    """
    try:
        token = credentials.credentials
        
        # Verify JWT token
        token_payload = await verify_jwt_token(token)
        
        # Get user information
        user = await get_user_from_token(token_payload)
        
        logger.debug(f"Authenticated user: {user.get('id')}, role: {user.get('role')}")
        
        return user
    
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise AuthenticationError("Failed to authenticate")


async def require_ai_assistant_access(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Only users whose role is in AI_ASSISTANT_ALLOWED_ROLES may use authenticated AI APIs.
    """
    user_role = current_user.get("role")
    if not is_ai_assistant_role(user_role):
        allowed_str = ", ".join(settings.ai_assistant_allowed_roles_list)
        logger.warning(
            "AI Assistant access denied for user %s with role %s",
            current_user.get("id"),
            current_user.get("role"),
        )
        raise PermissionDeniedError(
            f"AI Assistant access requires one of these roles: {allowed_str}"
        )
    return current_user


def require_role(allowed_roles: list[str]):
    """
    Dependency factory to require specific role (case-insensitive).
    Usage: user = Depends(require_role(["admin", "manager", "super_admin"]))
    """
    _allowed = [r.lower() for r in (allowed_roles or [])]

    async def role_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        user_role = (current_user.get("role") or "").strip().lower()

        if not _allowed or user_role in _allowed:
            return current_user

        logger.warning(
            f"Permission denied: user {current_user.get('id')} "
            f"with role '{current_user.get('role')}' tried to access resource requiring {allowed_roles}"
        )
        raise PermissionDeniedError(
            f"Required role: {', '.join(allowed_roles)}, got: {current_user.get('role')}"
        )

    return role_checker


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """
    Get current user (optional - for endpoints that work with or without auth)
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except Exception:
        return None
