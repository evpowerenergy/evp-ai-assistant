"""
LangGraph Workflow
Main orchestration graph for AI Assistant
"""
from typing import Dict, Any, Literal
import time
from langgraph.graph import StateGraph, END
from app.orchestrator.state import AIAssistantState
from app.orchestrator.llm_router import analyze_intent_with_llm
from app.orchestrator.nodes.db_query import db_query_node
from app.orchestrator.nodes.rag_query import rag_query_node
from app.orchestrator.nodes.clarify import clarify_node
from app.orchestrator.nodes.generate_response import generate_response_node
from app.orchestrator.nodes.result_grader import result_grader_node, should_retry
from app.orchestrator.nodes.rpc_planner import rpc_planner_node
from app.orchestrator.nodes.tool_selection_verifier import (
    tool_selection_verifier_node,
    should_proceed_to_db_query,
)
from app.orchestrator.nodes.tool_selection_refiner import tool_selection_refiner_node
from app.orchestrator.nodes.tool_execution_verifier import (
    tool_execution_verifier_node,
    should_proceed_to_result_grader,
)
from app.services.chat_mode import (
    KB_MODE_SWITCH_HINT,
    is_crm_style_question,
    normalize_chat_mode,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def route_by_chat_mode(state: AIAssistantState) -> Literal["crm", "kb"]:
    mode = normalize_chat_mode(state.get("chat_mode"))
    return "kb" if mode == "kb" else "crm"


def route_after_kb_guard(state: AIAssistantState) -> Literal["blocked", "proceed"]:
    if state.get("intent") == "kb_blocked":
        return "blocked"
    return "proceed"


def route_intent(state: AIAssistantState) -> Literal["db_query", "rag_query", "clarify", "general"]:
    """
    Route based on detected intent (CRM mode only).
    """
    intent = state.get("intent", "general")
    confidence = state.get("confidence", 0.0)
    selected_tools = state.get("selected_tools", [])

    if normalize_chat_mode(state.get("chat_mode")) == "crm" and intent == "rag_query":
        intent = "db_query" if selected_tools else "general"

    if confidence < 0.3:
        return "clarify"

    if intent == "general" and not selected_tools:
        return "general"

    if intent == "rag_query":
        return "general"

    return intent  # type: ignore[return-value]


def create_graph() -> StateGraph:
    """Create LangGraph workflow with chat mode gate."""
    graph = StateGraph(AIAssistantState)

    async def mode_gate_node(state: AIAssistantState) -> AIAssistantState:
        state["chat_mode"] = normalize_chat_mode(state.get("chat_mode"))
        logger.info("Mode gate: chat_mode=%s", state["chat_mode"])
        return state

    async def kb_guard_node(state: AIAssistantState) -> AIAssistantState:
        user_message = state.get("user_message", "")
        if is_crm_style_question(user_message):
            state["intent"] = "kb_blocked"
            state["response"] = KB_MODE_SWITCH_HINT
            state["data_quality"] = "empty"
            logger.info("KB guard: blocked CRM-style question")
        else:
            state["intent"] = "rag_query"
            state["confidence"] = 1.0
            state["selected_tools"] = []
            state["tool_parameters"] = {}
        return state

    async def router_node(state: AIAssistantState) -> AIAssistantState:
        """Router node that uses LLM to detect intent and select tools (CRM mode)."""
        user_message = state.get("user_message", "")
        user_id = state.get("user_id", "")
        user_role = state.get("user_role", "staff")
        history_context = state.get("history_context")
        chat_mode = normalize_chat_mode(state.get("chat_mode"))

        analysis = await analyze_intent_with_llm(
            user_message=user_message,
            user_id=user_id,
            user_role=user_role,
            history_context=history_context,
            chat_mode=chat_mode,
        )

        intent = analysis.get("intent", "general")
        if chat_mode == "crm" and intent == "rag_query":
            intent = "db_query" if analysis.get("selected_tools") else "general"

        confidence = analysis.get("confidence", 0.5)
        selected_tools = analysis.get("selected_tools", [])
        tool_parameters = analysis.get("tool_parameters", {})
        entities = analysis.get("entities", {})

        state["intent"] = intent
        state["confidence"] = confidence
        state["entities"] = entities
        state["selected_tools"] = selected_tools
        state["tool_parameters"] = tool_parameters

        state["verification_status"] = None
        state["verification_reason"] = None
        state["verification_suggested_changes"] = None
        state["execution_verification_status"] = None
        state["execution_verification_reason"] = None
        state["execution_verification_suggested_changes"] = None
        if "verification_retry_count" not in state:
            state["verification_retry_count"] = 0
        if "max_verification_retries" not in state:
            state["max_verification_retries"] = 2
        if "execution_verification_retry_count" not in state:
            state["execution_verification_retry_count"] = 0
        if "max_execution_verification_retries" not in state:
            state["max_execution_verification_retries"] = 2

        logger.info("ROUTER (CRM): intent=%s tools=%s", intent, [t["name"] for t in selected_tools])
        return state

    graph.add_node("mode_gate", mode_gate_node)
    graph.add_node("kb_guard", kb_guard_node)
    graph.add_node("router", router_node)
    graph.add_node("tool_selection_verifier", tool_selection_verifier_node)
    graph.add_node("tool_selection_refiner", tool_selection_refiner_node)
    graph.add_node("db_query", db_query_node)
    graph.add_node("tool_execution_verifier", tool_execution_verifier_node)
    graph.add_node("rag_query", rag_query_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("result_grader", result_grader_node)
    graph.add_node("rpc_planner", rpc_planner_node)
    graph.add_node("generate_response", generate_response_node)

    graph.set_entry_point("mode_gate")

    graph.add_conditional_edges(
        "mode_gate",
        route_by_chat_mode,
        {
            "crm": "router",
            "kb": "kb_guard",
        },
    )

    graph.add_conditional_edges(
        "kb_guard",
        route_after_kb_guard,
        {
            "blocked": END,
            "proceed": "rag_query",
        },
    )

    graph.add_conditional_edges(
        "router",
        route_intent,
        {
            "db_query": "tool_selection_verifier",
            "clarify": "clarify",
            "general": "generate_response",
        },
    )

    graph.add_conditional_edges(
        "tool_selection_verifier",
        should_proceed_to_db_query,
        {
            "db_query": "db_query",
            "tool_selection_refiner": "tool_selection_refiner",
        },
    )

    graph.add_edge("tool_selection_refiner", "router")
    graph.add_edge("db_query", "tool_execution_verifier")

    graph.add_conditional_edges(
        "tool_execution_verifier",
        should_proceed_to_result_grader,
        {
            "result_grader": "result_grader",
            "tool_selection_refiner": "tool_selection_refiner",
        },
    )

    graph.add_edge("rag_query", "result_grader")

    graph.add_conditional_edges(
        "result_grader",
        should_retry,
        {
            "retry": "rpc_planner",
            "sufficient": "generate_response",
            "give_up": "generate_response",
        },
    )

    graph.add_edge("rpc_planner", "db_query")
    graph.add_edge("clarify", END)
    graph.add_edge("generate_response", END)

    logger.info("LangGraph workflow created successfully")
    return graph


_graph: StateGraph = None


def get_graph() -> StateGraph:
    global _graph
    if _graph is None:
        _graph = create_graph()
        _graph = _graph.compile()
        logger.info("LangGraph compiled and ready")
    return _graph


async def process_message(state: AIAssistantState) -> AIAssistantState:
    try:
        graph = get_graph()
        state_dict = dict(state)
        result = await graph.ainvoke(state_dict)
        logger.info(
            "WORKFLOW COMPLETED mode=%s intent=%s",
            result.get("chat_mode"),
            result.get("intent"),
        )
        return result
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        state["error"] = str(e)
        state["response"] = "ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง"
        return state


async def process_message_stream(state: AIAssistantState):
    try:
        graph = get_graph()
        state_dict = dict(state)
        async for event in graph.astream(state_dict):
            for node_name, node_state in event.items():
                yield {
                    "node": node_name,
                    "state": node_state,
                    "timestamp": time.time(),
                }
        logger.info("WORKFLOW STREAMING COMPLETED")
    except Exception as e:
        logger.error(f"Workflow streaming error: {e}")
        yield {
            "node": "error",
            "state": {"error": str(e)},
            "timestamp": time.time(),
        }
