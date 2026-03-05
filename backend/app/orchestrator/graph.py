"""
LangGraph Workflow
Main orchestration graph for AI Assistant
"""
from typing import Dict, Any, Literal, AsyncIterator
import time
from langgraph.graph import StateGraph, END
from app.orchestrator.state import AIAssistantState
from app.orchestrator.llm_router import analyze_intent_with_llm
from app.orchestrator.nodes.db_query import db_query_node
from app.orchestrator.nodes.rag_query import rag_query_node
from app.orchestrator.nodes.clarify import clarify_node
from app.orchestrator.nodes.generate_response import generate_response_node
# Removed direct_answer_node - all queries go through generate_response
from app.orchestrator.nodes.result_grader import result_grader_node, should_retry
from app.orchestrator.nodes.rpc_planner import rpc_planner_node
from app.orchestrator.nodes.tool_selection_verifier import (
    tool_selection_verifier_node,
    should_proceed_to_db_query
)
from app.orchestrator.nodes.tool_selection_refiner import tool_selection_refiner_node
from app.orchestrator.nodes.tool_execution_verifier import (
    tool_execution_verifier_node,
    should_proceed_to_result_grader
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def route_intent(state: AIAssistantState) -> Literal["db_query", "rag_query", "clarify", "general"]:
    """
    Route based on detected intent.
    general = only when no system data is requested (greetings, date/time, definitions);
    data requests are routed to db_query (router + data-keyword fallback ensure tools are selected).
    """
    intent = state.get("intent", "general")
    confidence = state.get("confidence", 0.0)
    selected_tools = state.get("selected_tools", [])
    user_message = state.get("user_message", "").lower()
    
    # If confidence is too low, ask for clarification
    if confidence < 0.3:
        return "clarify"
    
    # general + no tools → generate_response (no DB fetch). Data requests get db_query + tools.
    if intent == "general" and not selected_tools:
        return "general"
    
    return intent


def create_graph() -> StateGraph:
    """
    Create LangGraph workflow
    """
    graph = StateGraph(AIAssistantState)
    
    # Define router node first (must be defined before adding)
    async def router_node(state: AIAssistantState) -> AIAssistantState:
        """Router node that uses LLM to detect intent and select tools"""
        user_message = state.get("user_message", "")
        user_id = state.get("user_id", "")
        user_role = state.get("user_role", "staff")
        
        # Get history context from state
        history_context = state.get("history_context")
        
        # Use LLM-based intent analysis
        analysis = await analyze_intent_with_llm(
            user_message=user_message,
            user_id=user_id,
            user_role=user_role,
            history_context=history_context
        )
        
        intent = analysis.get("intent", "general")
        confidence = analysis.get("confidence", 0.5)
        selected_tools = analysis.get("selected_tools", [])
        tool_parameters = analysis.get("tool_parameters", {})
        entities = analysis.get("entities", {})
        
        # Store analysis results in state
        state["intent"] = intent
        state["confidence"] = confidence
        state["entities"] = entities
        state["selected_tools"] = selected_tools  # Store for db_query_node to use
        state["tool_parameters"] = tool_parameters
        
        # Reset verification fields when router runs (new analysis)
        # This ensures fresh verification for each router run
        state["verification_status"] = None
        state["verification_reason"] = None
        state["verification_suggested_changes"] = None
        state["execution_verification_status"] = None
        state["execution_verification_reason"] = None
        state["execution_verification_suggested_changes"] = None
        # Only reset retry count if this is a new user message (not a retry from refiner)
        # Check if verification_retry_count exists - if not, initialize it
        if "verification_retry_count" not in state:
            state["verification_retry_count"] = 0
        if "max_verification_retries" not in state:
            state["max_verification_retries"] = 2
        if "execution_verification_retry_count" not in state:
            state["execution_verification_retry_count"] = 0
        if "max_execution_verification_retries" not in state:
            state["max_execution_verification_retries"] = 2
        
        logger.info(f"{'='*60}")
        logger.info(f"🎯 ROUTER: LLM Intent Analysis")
        logger.info(f"   Message: {user_message[:50]}...")
        logger.info(f"   Detected Intent: {intent}")
        logger.info(f"   Confidence: {confidence:.2%}")
        logger.info(f"   Selected Tools: {[t['name'] for t in selected_tools]}")
        logger.info(f"   Entities: {entities}")
        logger.info(f"{'='*60}")
        
        return state
    
    # Add all nodes FIRST (including router)
    graph.add_node("router", router_node)
    graph.add_node("tool_selection_verifier", tool_selection_verifier_node)  # Pre-verification
    graph.add_node("tool_selection_refiner", tool_selection_refiner_node)  # Tool refinement
    graph.add_node("db_query", db_query_node)
    graph.add_node("tool_execution_verifier", tool_execution_verifier_node)  # NEW: Post-verification
    graph.add_node("rag_query", rag_query_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("result_grader", result_grader_node)  # Result quality checker
    graph.add_node("rpc_planner", rpc_planner_node)  # Parameter refiner for retry
    graph.add_node("generate_response", generate_response_node)
    
    # Set entry point AFTER adding router node
    graph.set_entry_point("router")
    
    # Add conditional edges from router
    graph.add_conditional_edges(
        "router",
        route_intent,
        {
            "db_query": "tool_selection_verifier",  # NEW: Verify before executing
            "rag_query": "rag_query",  # RAG queries skip verification
            "clarify": "clarify",
            "general": "generate_response"  # General queries go to generate_response
        }
    )
    
    # Tool Selection Verifier decides: proceed to DB Query or refine selection
    graph.add_conditional_edges(
        "tool_selection_verifier",
        should_proceed_to_db_query,
        {
            "db_query": "db_query",  # Approved, proceed to execution
            "tool_selection_refiner": "tool_selection_refiner"  # Rejected/Needs adjustment
        }
    )
    
    # Tool Selection Refiner goes back to router to retry with refined tools
    graph.add_edge("tool_selection_refiner", "router")
    
    # Tool Execution Verifier checks results after DB Query (Post-Verification)
    graph.add_edge("db_query", "tool_execution_verifier")
    
    # Tool Execution Verifier decides: proceed to Result Grader or refine selection
    graph.add_conditional_edges(
        "tool_execution_verifier",
        should_proceed_to_result_grader,
        {
            "result_grader": "result_grader",  # Approved, proceed to result grader
            "tool_selection_refiner": "tool_selection_refiner"  # Wrong tool/Needs more tools
        }
    )
    
    # RAG queries go directly to result_grader (skip execution verification)
    graph.add_edge("rag_query", "result_grader")
    
    # Result grader decides: retry, sufficient, or give_up
    graph.add_conditional_edges(
        "result_grader",
        should_retry,
        {
            "retry": "rpc_planner",  # Retry with adjusted parameters
            "sufficient": "generate_response",  # Data is good, generate response
            "give_up": "generate_response"  # Max retries reached, generate response anyway
        }
    )
    
    # RPC planner refines parameters and goes back to db_query
    graph.add_edge("rpc_planner", "db_query")
    
    # Clarify goes directly to END
    graph.add_edge("clarify", END)
    
    # Generate response goes to END
    graph.add_edge("generate_response", END)
    
    logger.info("LangGraph workflow created successfully")
    
    return graph


# Global graph instance
_graph: StateGraph = None


def get_graph() -> StateGraph:
    """Get or create graph instance"""
    global _graph
    
    if _graph is None:
        _graph = create_graph()
        _graph = _graph.compile()
        logger.info("LangGraph compiled and ready")
    
    return _graph


async def process_message(state: AIAssistantState) -> AIAssistantState:
    """
    Process user message through workflow
    """
    try:
        graph = get_graph()
        
        # Convert to dict to avoid TypedDict validation issues with extra fields
        state_dict = dict(state)
        
        # Run graph
        result = await graph.ainvoke(state_dict)
        
        logger.info(f"{'='*60}")
        logger.info(f"✅ WORKFLOW COMPLETED")
        logger.info(f"   Final Intent: {result.get('intent')}")
        logger.info(f"   Has Response: {bool(result.get('response'))}")
        logger.info(f"   Response Length: {len(result.get('response', ''))} chars")
        logger.info(f"{'='*60}\n")
        
        return result
    
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        state["error"] = str(e)
        state["response"] = "ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง"
        return state


async def process_message_stream(state: AIAssistantState):
    """
    Process user message through workflow with streaming
    Yields state updates for each node execution
    """
    try:
        graph = get_graph()
        
        # Convert to dict to avoid TypedDict validation issues with extra fields
        state_dict = dict(state)
        
        # Stream graph execution
        async for event in graph.astream(state_dict):
            # event is a dict with node names as keys
            for node_name, node_state in event.items():
                yield {
                    "node": node_name,
                    "state": node_state,
                    "timestamp": time.time()
                }
        
        logger.info(f"{'='*60}")
        logger.info(f"✅ WORKFLOW STREAMING COMPLETED")
        logger.info(f"{'='*60}\n")
    
    except Exception as e:
        logger.error(f"Workflow streaming error: {e}")
        yield {
            "node": "error",
            "state": {"error": str(e)},
            "timestamp": time.time()
        }
