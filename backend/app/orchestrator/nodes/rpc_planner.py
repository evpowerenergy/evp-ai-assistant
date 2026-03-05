"""
RPC Planner Node
Refines tool parameters for retry attempts based on suggestions from Result Grader
"""
from typing import Dict, Any
from app.orchestrator.state import AIAssistantState
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def rpc_planner_node(state: AIAssistantState) -> AIAssistantState:
    """
    Node that refines RPC parameters for retry attempts
    """
    try:
        user_message = state.get("user_message", "")
        selected_tools = state.get("selected_tools", [])
        tool_parameters = state.get("tool_parameters", {})
        suggested_retry_params = state.get("suggested_retry_params", {})
        retry_count = state.get("retry_count", 0)
        previous_attempts = state.get("previous_attempts", [])
        
        logger.info(f"{'='*60}")
        logger.info(f"🔧 [RPC PLANNER] Refining parameters for retry")
        logger.info(f"   Retry count: {retry_count + 1}")
        logger.info(f"   Suggested params: {suggested_retry_params}")
        logger.info(f"{'='*60}")
        
        # Increment retry count
        state["retry_count"] = retry_count + 1
        
        # Refine tool parameters based on suggestions
        if suggested_retry_params and selected_tools:
            for tool_info in selected_tools:
                tool_name = tool_info.get("name", "")
                params = tool_info.get("parameters", {})
                
                # Apply suggested adjustments
                if "query" in suggested_retry_params:
                    # Update query for search tools
                    if tool_name in ["search_leads", "get_lead_status", "get_customer_info"]:
                        new_query = suggested_retry_params.get("query")
                        if new_query:
                            params["query"] = new_query
                            logger.info(f"   Updated query: {new_query}")
                
                if suggested_retry_params.get("fuzzy"):
                    # Add fuzzy flag if supported
                    params["fuzzy"] = True
                    logger.info(f"   Added fuzzy search flag")
                
                # Update tool parameters in state
                if tool_name in tool_parameters:
                    tool_parameters[tool_name].update(params)
                else:
                    tool_parameters[tool_name] = params
        
        # Update state
        state["tool_parameters"] = tool_parameters
        state["selected_tools"] = selected_tools
        
        logger.info(f"✅ Parameters refined")
        logger.info(f"   Updated tools: {[t.get('name') for t in selected_tools]}")
        logger.info(f"{'='*60}\n")
        
        return state
    
    except Exception as e:
        logger.error(f"RPC Planner Node error: {e}")
        state["error"] = str(e)
        return state
