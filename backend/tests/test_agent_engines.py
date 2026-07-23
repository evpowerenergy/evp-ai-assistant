from unittest.mock import AsyncMock

import pytest

from app.engines.base import ActorContext, AgentRequest, AgentResult, RetryableEngineError
from app.engines.service import AgentService


def context() -> ActorContext:
    return ActorContext(
        user_id="user-1",
        user_role="manager_sale",
        session_id="session-1",
        source="test",
        request_id="request-1",
    )


@pytest.mark.asyncio
async def test_agent_service_uses_primary(monkeypatch):
    service = AgentService()
    primary = AsyncMock()
    primary.name = "hermes"
    primary.run.return_value = AgentResult(response="ok", engine="hermes")
    service.engines["hermes"] = primary
    monkeypatch.setattr("app.engines.service.settings.AI_PRIMARY_ENGINE", "hermes")

    result = await service.run(AgentRequest(message="hello"), context())

    assert result.engine == "hermes"
    assert result.fallback_used is False


@pytest.mark.asyncio
async def test_agent_service_falls_back_only_for_retryable_error(monkeypatch):
    service = AgentService()
    primary = AsyncMock()
    primary.name = "hermes"
    primary.run.side_effect = RetryableEngineError("offline")
    fallback = AsyncMock()
    fallback.name = "langgraph"
    fallback.run.return_value = AgentResult(response="safe", engine="langgraph")
    service.engines.update({"hermes": primary, "langgraph": fallback})
    monkeypatch.setattr("app.engines.service.settings.AI_PRIMARY_ENGINE", "hermes")
    monkeypatch.setattr("app.engines.service.settings.AI_FALLBACK_ENGINE", "langgraph")
    monkeypatch.setattr("app.engines.service.settings.AI_FALLBACK_ENABLED", True)

    result = await service.run(AgentRequest(message="hello"), context())

    assert result.engine == "langgraph"
    assert result.fallback_used is True
    assert result.metadata["primary_engine"] == "hermes"


@pytest.mark.asyncio
async def test_agent_service_does_not_hide_programming_errors(monkeypatch):
    service = AgentService()
    primary = AsyncMock()
    primary.name = "hermes"
    primary.run.side_effect = ValueError("bug")
    service.engines["hermes"] = primary
    monkeypatch.setattr("app.engines.service.settings.AI_PRIMARY_ENGINE", "hermes")

    with pytest.raises(ValueError, match="bug"):
        await service.run(AgentRequest(message="hello"), context())


@pytest.mark.asyncio
async def test_web_research_timeout_does_not_use_incapable_fallback(monkeypatch):
    service = AgentService()
    primary = AsyncMock()
    primary.name = "hermes"
    primary.run.side_effect = RetryableEngineError("Hermes request failed: ReadTimeout")
    fallback = AsyncMock()
    fallback.name = "langgraph"
    service.engines.update({"hermes": primary, "langgraph": fallback})
    monkeypatch.setattr("app.engines.service.settings.AI_PRIMARY_ENGINE", "hermes")
    monkeypatch.setattr("app.engines.service.settings.AI_FALLBACK_ENGINE", "langgraph")
    monkeypatch.setattr("app.engines.service.settings.AI_FALLBACK_ENABLED", True)

    with pytest.raises(RetryableEngineError, match="ReadTimeout"):
        await service.run(
            AgentRequest(message="research", request_type="web_research"),
            context(),
        )

    fallback.run.assert_not_awaited()
