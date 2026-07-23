"""Short-lived capability handoff keyed by the authenticated Hermes session."""

from __future__ import annotations

import re
import threading
import time

_LOCK = threading.Lock()
_TOKENS: dict[str, tuple[str, float]] = {}
_TTL_SECONDS = 180.0


def bind_execution_token(session_id: str, token: str) -> bool:
    if not session_id or not token or len(token) > 8192 or re.search(r"[\r\n\x00]", token):
        return False
    now = time.monotonic()
    with _LOCK:
        for key, (_, deadline) in list(_TOKENS.items()):
            if deadline <= now:
                _TOKENS.pop(key, None)
        _TOKENS[session_id] = (token, now + _TTL_SECONDS)
    return True


def get_execution_token(session_id: str) -> str:
    now = time.monotonic()
    with _LOCK:
        value = _TOKENS.get(session_id)
        if not value or value[1] <= now:
            _TOKENS.pop(session_id, None)
            return ""
        return value[0]
