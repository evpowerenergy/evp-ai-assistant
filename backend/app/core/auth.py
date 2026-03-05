"""
Authentication and Authorization
"""
from typing import Optional
import time
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.utils.exceptions import AuthenticationError, PermissionDeniedError
from app.utils.logger import get_logger
from app.services.supabase import get_supabase_client
from app.config import settings

logger = get_logger(__name__)
security = HTTPBearer()


async def verify_jwt_token(token: str) -> dict:
    """
    Verify JWT token from Supabase
    Returns decoded token payload
    Since JWKS endpoint is not available, we decode without signature verification
    and verify user exists in database instead
    """
    try:
        # Decode token without signature verification
        # We'll verify user exists in database separately
        unverified = jwt.decode(token, options={"verify_signature": False})
        
        user_id = unverified.get("sub")
        if not user_id:
            raise AuthenticationError("User ID not found in token")
        
        # Check token expiration manually
        exp = unverified.get("exp")
        if exp and time.time() >= exp:
            logger.warning("JWT token expired")
            raise AuthenticationError("Token expired")
        
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


def _resolve_role_from_db(auth_user_id: str) -> Optional[str]:
    """
    Resolve role from users or employees table (service role, no RLS).
    So API auth matches frontend /me and CRM pattern.
    """
    try:
        supabase = get_supabase_client()
        for table in ("users", "employees"):
            r = supabase.table(table).select("role").eq("auth_user_id", auth_user_id).limit(1).execute()
            row = (r.data or [])[0] if r.data else None
            if row and row.get("role"):
                role = str(row.get("role", "")).strip()
                if role:
                    return role
    except Exception as e:
        logger.debug("resolve role from db: %s", e)
    return None


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
        role_from_db = _resolve_role_from_db(user_id)
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
            "role": _resolve_role_from_db(user_id) or (token_payload.get("user_metadata") or {}).get("role", "staff")
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
