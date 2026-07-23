from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass(frozen=True)
class ActorContext:
    user_id: str
    user_role: str
    session_id: str
    source: str
    request_id: str
    run_id: Optional[str] = None
    trace_id: Optional[str] = None
    line_user_id: Optional[str] = None


@dataclass(frozen=True)
class AgentRequest:
    message: str
    history: List[Dict[str, Any]] = field(default_factory=list)
    history_context: str = ""
    chat_mode: str = "auto"
    request_type: str = "general"


@dataclass
class AgentResult:
    response: str
    engine: str
    model: Optional[str] = None
    citations: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    intent: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    fallback_used: bool = False


class RetryableEngineError(RuntimeError):
    """Infrastructure/protocol failure for which a safe fallback is allowed."""

    def __init__(self, message: str, *, metadata: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.metadata = metadata or {}


class AgentEngine(Protocol):
    name: str

    async def run(self, request: AgentRequest, context: ActorContext) -> AgentResult:
        ...
