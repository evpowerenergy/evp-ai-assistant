from __future__ import annotations

import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any, Dict, List

import httpx

from app.config import settings
from app.core.execution_token import create_execution_token
from app.engines.base import (
    ActorContext,
    AgentRequest,
    AgentResult,
    RetryableEngineError,
)


class HermesEngine:
    name = "hermes"

    @staticmethod
    def _log_offset() -> int:
        if not settings.HERMES_LOG_PATH:
            return 0
        try:
            return Path(settings.HERMES_LOG_PATH).stat().st_size
        except OSError:
            return 0

    @staticmethod
    def _runtime_logs(offset: int) -> List[Dict[str, Any]]:
        """Read only sanitized execution events appended during this turn."""
        if not settings.HERMES_LOG_PATH:
            return []
        try:
            with Path(settings.HERMES_LOG_PATH).open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(offset)
                lines = handle.readlines()[-200:]
        except OSError:
            return []

        events: List[Dict[str, Any]] = []
        tool_pattern = re.compile(
            r"^(?P<ts>\S+ \S+) .*agent\.tool_executor: (?:tool|Tool) "
            r"(?P<tool>[A-Za-z0-9_.-]+) (?P<status>completed|returned error)"
            r"(?: \((?P<duration>[0-9.]+)s[^)]*\))?"
        )
        turn_pattern = re.compile(
            r"^(?P<ts>\S+ \S+) .*agent\.conversation_loop: Turn ended:.*"
            r"model=(?P<model>\S+).*api_calls=(?P<calls>\d+/\d+).*tool_turns=(?P<turns>\d+)"
        )
        for line in lines:
            tool_match = tool_pattern.search(line)
            if tool_match:
                item = tool_match.groupdict()
                event_type = "subagent" if item["tool"] == "delegate_task" else "tool"
                events.append({
                    "timestamp": item["ts"],
                    "type": event_type,
                    "name": item["tool"],
                    "status": "completed" if item["status"] == "completed" else "error",
                    "duration": float(item["duration"]) if item.get("duration") else None,
                })
                continue
            turn_match = turn_pattern.search(line)
            if turn_match:
                item = turn_match.groupdict()
                events.append({
                    "timestamp": item["ts"],
                    "type": "summary",
                    "name": "Hermes turn completed",
                    "status": "completed",
                    "model": item["model"],
                    "api_calls": item["calls"],
                    "tool_turns": int(item["turns"]),
                })
        # Keep enough events for long research turns while still bounding the
        # response size and never exposing tool inputs/outputs.
        return events[-120:]

    @staticmethod
    def _skill_usage_snapshot() -> Dict[str, str]:
        """Return non-sensitive skill activity markers from Hermes' registry."""
        if not settings.HERMES_LOG_PATH:
            return {}
        usage_path = Path(settings.HERMES_LOG_PATH).parent.parent / "skills" / ".usage.json"
        try:
            payload = json.loads(usage_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            return {}
        snapshot: Dict[str, str] = {}
        if not isinstance(payload, dict):
            return snapshot
        for name, data in payload.items():
            if not isinstance(name, str) or not isinstance(data, dict):
                continue
            marker = max(
                str(data.get("last_used_at") or ""),
                str(data.get("last_viewed_at") or ""),
                str(data.get("last_patched_at") or ""),
            )
            if marker:
                snapshot[name] = marker
        return snapshot

    @classmethod
    def _skill_runtime_events(cls, baseline: Dict[str, str]) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for skill_name, marker in cls._skill_usage_snapshot().items():
            if marker <= baseline.get(skill_name, ""):
                continue
            events.append({
                "timestamp": marker,
                "type": "skill",
                "name": skill_name,
                "status": "completed",
                "duration": None,
            })
        return events

    @classmethod
    def _turn_runtime_logs(
        cls, log_offset: int, skill_baseline: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        events = cls._runtime_logs(log_offset) + cls._skill_runtime_events(skill_baseline)
        return sorted(events, key=lambda event: str(event.get("timestamp") or ""))[-120:]

    def _session_key(self, user_id: str, session_id: str) -> str:
        # API key is already a deployment secret and provides a stable,
        # non-reversible identifier. A dedicated key can replace it later.
        key = (settings.HERMES_API_KEY or "evp-local-session-key").encode()
        digest = hmac.new(key, f"{user_id}:{session_id}".encode(), hashlib.sha256).hexdigest()
        return f"agent:evp:web:dm:{digest}"

    @staticmethod
    def _messages(request: AgentRequest) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are EV Power Energy's internal assistant. Answer in the "
                    "user's language. Use only authorized EVP tools for company "
                    "facts; never invent CRM figures or expose credentials. "
                    "Use get_sales_team_overview for top seller, sales ranking, "
                    "sales-by-person, or team KPI questions. Its ranking is "
                    "authoritative: do not call get_sales_closed once per employee "
                    "and never show a sales ID when an employee name is available."
                ),
            }
        ]
        for item in request.history:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant", "system"} and isinstance(content, str):
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": request.message})
        return messages

    async def run(self, request: AgentRequest, context: ActorContext) -> AgentResult:
        if not settings.HERMES_API_KEY or not settings.EVP_EXECUTION_PRIVATE_KEY:
            raise RetryableEngineError("Hermes runtime credentials are not configured")
        url = f"{settings.HERMES_BASE_URL.rstrip('/')}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.HERMES_API_KEY}",
            # Do not send X-Hermes-Session-Id: that switches Hermes to its
            # local SQLite transcript and would override Supabase history.
            "X-Hermes-Session-Key": self._session_key(context.user_id, context.session_id),
            "Idempotency-Key": context.request_id,
            "X-EVP-Execution-Token": create_execution_token(context),
        }
        timeout = httpx.Timeout(
            settings.HERMES_TURN_TIMEOUT_SECONDS,
            connect=settings.HERMES_CONNECT_TIMEOUT_SECONDS,
        )
        log_offset = self._log_offset()
        skill_baseline = self._skill_usage_snapshot()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json={
                        "model": settings.HERMES_MODEL,
                        "messages": self._messages(request),
                        "stream": False,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            raise RetryableEngineError(
                f"Hermes request failed: {type(exc).__name__}",
                metadata={"runtime_logs": self._turn_runtime_logs(log_offset, skill_baseline)},
            ) from exc
        except (TypeError, ValueError, KeyError) as exc:
            raise RetryableEngineError(
                "Hermes returned an invalid response",
                metadata={"runtime_logs": self._turn_runtime_logs(log_offset, skill_baseline)},
            ) from exc

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RetryableEngineError(
                "Hermes response did not contain assistant content",
                metadata={"runtime_logs": self._turn_runtime_logs(log_offset, skill_baseline)},
            ) from exc
        return AgentResult(
            response=str(content),
            engine=self.name,
            model=payload.get("model"),
            usage=payload.get("usage") or {},
            metadata={"runtime_logs": self._turn_runtime_logs(log_offset, skill_baseline)},
        )
