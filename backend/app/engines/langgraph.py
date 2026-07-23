from __future__ import annotations

from app.engines.base import ActorContext, AgentRequest, AgentResult
from app.orchestrator.graph import process_message
from app.orchestrator.state import AIAssistantState


class LangGraphEngine:
    name = "langgraph"

    async def run(self, request: AgentRequest, context: ActorContext) -> AgentResult:
        # LangGraph currently supports crm/kb. During compatibility rollout,
        # auto maps to crm; Hermes itself has no mode split.
        mode = request.chat_mode if request.chat_mode in {"crm", "kb"} else "crm"
        state: AIAssistantState = {
            "user_message": request.message,
            "user_id": context.user_id,
            "user_role": context.user_role,
            "session_id": context.session_id,
            "chat_mode": mode,
            "chat_history": request.history,
            "history_context": request.history_context,
            "intent": None,
            "confidence": 0.0,
            "tool_calls": [],
            "tool_results": [],
            "rag_results": [],
            "citations": [],
            "rag_retrieval_meta": None,
            "retry_count": 0,
            "max_retries": 0,
            "previous_attempts": [],
            "response": None,
            "error": None,
        }
        result = await process_message(state)
        return AgentResult(
            response=result.get("response") or "ขออภัยครับ ไม่สามารถสร้างคำตอบได้",
            engine=self.name,
            citations=result.get("citations") or [],
            tool_calls=result.get("tool_calls") or [],
            tool_results=result.get("tool_results") or [],
            intent=result.get("intent"),
            metadata={
                "chat_mode": result.get("chat_mode", mode),
                "rag_retrieval_meta": result.get("rag_retrieval_meta"),
                "debug_precompute": result.get("debug_precompute"),
            },
        )
