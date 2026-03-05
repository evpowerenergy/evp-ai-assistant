"""
httpx Client Patch - Must be imported FIRST before any httpx usage
Fixes 'proxy' parameter compatibility issue with postgrest/Supabase
"""
import httpx

# Store original __init__
_original_httpx_client_init = httpx.Client.__init__

def _patched_httpx_client_init(self, *args, **kwargs):
    """Patch httpx.Client to remove 'proxy' parameter (not supported in httpx 0.24.x)"""
    # Remove 'proxy' parameter - httpx.Client only accepts 'proxies' (plural)
    kwargs.pop('proxy', None)
    return _original_httpx_client_init(self, *args, **kwargs)

# Apply patch immediately
httpx.Client.__init__ = _patched_httpx_client_init

# Also patch AsyncClient for completeness
_original_async_init = httpx.AsyncClient.__init__

def _patched_async_init(self, *args, **kwargs):
    """Patch httpx.AsyncClient to remove 'proxy' parameter"""
    kwargs.pop('proxy', None)
    return _original_async_init(self, *args, **kwargs)

httpx.AsyncClient.__init__ = _patched_async_init
