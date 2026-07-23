from __future__ import annotations

from typing import Dict

from app.config import settings
from app.engines.base import ActorContext, AgentEngine, AgentRequest, AgentResult, RetryableEngineError
from app.engines.hermes import HermesEngine
from app.engines.langgraph import LangGraphEngine
from app.utils.logger import get_logger
from app.services.agent_audit import emit_agent_event

logger = get_logger(__name__)


class AgentService:
    def __init__(self) -> None:
        self.engines: Dict[str, AgentEngine] = {
            "langgraph": LangGraphEngine(),
            "hermes": HermesEngine(),
        }

    def _engine(self, name: str) -> AgentEngine:
        normalized = (name or "").strip().lower()
        if normalized not in self.engines:
            raise RuntimeError(f"Unknown AI engine: {normalized}")
        return self.engines[normalized]

    async def run(self, request: AgentRequest, context: ActorContext) -> AgentResult:
        primary = self._engine(settings.AI_PRIMARY_ENGINE)
        await emit_agent_event(
            run_id=context.run_id, request_id=context.request_id,
            event_type="engine", event_name=f"engine.{primary.name}.started",
            status="started", actor_type="engine", actor_id=primary.name,
        )
        try:
            result = await primary.run(request, context)
            await emit_agent_event(
                run_id=context.run_id, request_id=context.request_id,
                event_type="engine", event_name=f"engine.{primary.name}.completed",
                status="completed", actor_type="engine", actor_id=primary.name,
                model=result.model,
            )
            return result
        except RetryableEngineError as exc:
            fallback_name = settings.AI_FALLBACK_ENGINE.strip().lower()
            timed_out = "Timeout" in str(exc)
            # LangGraph has no browser/research capability. Falling back on a
            # research timeout produces a fast but misleading "no data"
            # answer while Hermes may still be completing the real research.
            if request.request_type == "web_research" and timed_out:
                await emit_agent_event(
                    run_id=context.run_id, request_id=context.request_id,
                    event_type="fallback", event_name="fallback.skipped",
                    status="skipped", actor_type="engine", actor_id=fallback_name,
                    metadata={
                        "reason": str(exc),
                        "request_type": request.request_type,
                        "capability_match": False,
                    },
                )
                raise
            if (
                not settings.AI_FALLBACK_ENABLED
                or not fallback_name
                or fallback_name == primary.name
            ):
                raise
            logger.warning(
                "Primary engine failed request_id=%s engine=%s error=%s; using %s",
                context.request_id,
                primary.name,
                exc,
                fallback_name,
            )
            await emit_agent_event(
                run_id=context.run_id, request_id=context.request_id,
                event_type="engine",
                event_name=f"engine.{primary.name}.{'timed_out' if timed_out else 'failed'}",
                status="timed_out" if timed_out else "failed",
                actor_type="engine", actor_id=primary.name,
                metadata={"error": str(exc)},
            )
            await emit_agent_event(
                run_id=context.run_id, request_id=context.request_id,
                event_type="fallback", event_name=f"fallback.{fallback_name}.started",
                status="started", actor_type="engine", actor_id=fallback_name,
                metadata={"reason": str(exc)},
            )
            result = await self._engine(fallback_name).run(request, context)
            result.fallback_used = True
            result.metadata["primary_engine"] = primary.name
            result.metadata["fallback_reason"] = str(exc)
            # Preserve the primary Hermes trace so the UI remains useful when
            # a long-running turn times out and LangGraph handles the reply.
            result.metadata.update(exc.metadata)
            await emit_agent_event(
                run_id=context.run_id, request_id=context.request_id,
                event_type="fallback", event_name=f"fallback.{fallback_name}.completed",
                status="completed", actor_type="engine", actor_id=fallback_name,
                model=result.model,
            )
            return result


_service: AgentService | None = None


def get_agent_service() -> AgentService:
    global _service
    if _service is None:
        _service = AgentService()
    return _service
