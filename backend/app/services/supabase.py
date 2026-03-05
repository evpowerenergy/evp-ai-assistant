"""
Supabase Client Service
"""
# IMPORTANT: Import httpx patch FIRST before any other imports
# This ensures the patch is active when postgrest/Supabase initialize httpx.Client
from app.services import _httpx_patch  # noqa: F401

from supabase import create_client, Client
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global Supabase client instance
_supabase_client: Client = None
_initialization_error = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client
    Uses service role key for backend operations
    """
    global _supabase_client, _initialization_error
    
    # If we've already failed to initialize, return None instead of retrying
    if _initialization_error:
        raise _initialization_error
    
    if _supabase_client is None:
        try:
            # Try positional arguments first (more compatible)
            _supabase_client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
            logger.info("Supabase client initialized successfully")
        except TypeError as e:
            # If positional fails, try keyword arguments
            error_msg = str(e)
            if "proxy" in error_msg.lower():
                logger.warning(f"Proxy-related error detected: {e}")
                logger.warning("This may be due to postgrest version conflict")
                # Try with minimal arguments
                try:
                    import os
                    # Temporarily disable proxy-related env vars if they exist
                    old_proxy = os.environ.pop("HTTP_PROXY", None)
                    old_https_proxy = os.environ.pop("HTTPS_PROXY", None)
                    try:
                        _supabase_client = create_client(
                            settings.SUPABASE_URL,
                            settings.SUPABASE_SERVICE_ROLE_KEY
                        )
                        logger.info("Supabase client initialized (after removing proxy env vars)")
                    finally:
                        # Restore proxy env vars
                        if old_proxy:
                            os.environ["HTTP_PROXY"] = old_proxy
                        if old_https_proxy:
                            os.environ["HTTPS_PROXY"] = old_https_proxy
                except Exception as e3:
                    _initialization_error = RuntimeError(f"Failed to initialize Supabase client: {e3}")
                    logger.error(f"Failed to initialize Supabase client: {e3}")
                    raise _initialization_error
            else:
                # Other TypeError - try keyword arguments
                try:
                    _supabase_client = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY
                    )
                    logger.info("Supabase client initialized (keyword args)")
                except Exception as e2:
                    _initialization_error = RuntimeError(f"Failed to initialize Supabase client: {e2}")
                    logger.error(f"Failed to initialize Supabase client: {e2}")
                    raise _initialization_error
        except Exception as e:
            _initialization_error = RuntimeError(f"Failed to initialize Supabase client: {e}")
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise _initialization_error
    
    return _supabase_client
