"""
Tool Selection Refiner Node
Refines tool selection based on verification feedback
Updates selected_tools and tool_parameters based on suggestions from Tool Selection Verifier
"""
from typing import Dict, Any
from app.orchestrator.state import AIAssistantState
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def tool_selection_refiner_node(state: AIAssistantState) -> AIAssistantState:
    """
    Node that refines tool selection based on verification feedback
    """
    try:
        user_message = state.get("user_message", "")
        selected_tools = state.get("selected_tools", [])
        tool_parameters = state.get("tool_parameters", {})
        
        # Check both selection and execution verification
        verification_status = state.get("verification_status")
        execution_verification_status = state.get("execution_verification_status")
        
        # Use execution verification if available, otherwise use selection verification
        if execution_verification_status:
            verification_status = execution_verification_status
            verification_reason = state.get("execution_verification_reason", "")
            verification_suggested_changes = state.get("execution_verification_suggested_changes", {})
            verification_retry_count = state.get("execution_verification_retry_count", 0)
            state["execution_verification_retry_count"] = verification_retry_count + 1
        else:
            verification_status = verification_status or "APPROVED"
            verification_reason = state.get("verification_reason", "")
            verification_suggested_changes = state.get("verification_suggested_changes", {})
            verification_retry_count = state.get("verification_retry_count", 0)
            state["verification_retry_count"] = verification_retry_count + 1
        
        logger.info(f"{'='*60}")
        logger.info(f"🔧 [TOOL SELECTION REFINER] Refining tool selection")
        logger.info(f"   Verification status: {verification_status}")
        logger.info(f"   Verification reason: {verification_reason}")
        logger.info(f"   Current tools: {[t.get('name') for t in selected_tools]}")
        logger.info(f"{'='*60}")
        
        # Get suggested changes
        suggested_tools = verification_suggested_changes.get("suggested_tools", [])
        suggested_parameters = verification_suggested_changes.get("suggested_parameters", {})
        
        # Refine based on verification status
        if verification_status == "REJECTED" or verification_status == "WRONG_TOOL":
            # Replace tools completely
            if suggested_tools:
                logger.info(f"   🔄 Replacing tools with suggested tools")
                selected_tools = suggested_tools
                # Update tool_parameters based on suggested tools
                tool_parameters = {}
                for tool_info in suggested_tools:
                    tool_name = tool_info.get("name", "")
                    params = tool_info.get("parameters", {})
                    tool_parameters[tool_name] = params
                    logger.info(f"      - {tool_name}: {params}")
            else:
                logger.warning(f"   ⚠️  REJECTED but no suggested_tools provided, keeping current tools")
        
        elif verification_status == "NEEDS_ADJUSTMENT" or verification_status == "NEEDS_MORE_TOOLS":
            # Adjust existing tools
            logger.info(f"   🔧 Adjusting tool parameters")
            
            # Apply suggested parameters
            if suggested_parameters:
                for tool_name, params in suggested_parameters.items():
                    # Find tool in selected_tools
                    for tool_info in selected_tools:
                        if tool_info.get("name") == tool_name:
                            # Update parameters
                            current_params = tool_info.get("parameters", {})
                            current_params.update(params)
                            tool_info["parameters"] = current_params
                            tool_parameters[tool_name] = current_params
                            logger.info(f"      - Updated {tool_name}: {current_params}")
                            break
            
            # Add suggested tools if provided
            if suggested_tools:
                logger.info(f"   ➕ Adding suggested tools")
                for suggested_tool in suggested_tools:
                    suggested_name = suggested_tool.get("name", "")
                    # Check if tool already exists
                    exists = any(t.get("name") == suggested_name for t in selected_tools)
                    if not exists:
                        selected_tools.append(suggested_tool)
                        tool_parameters[suggested_name] = suggested_tool.get("parameters", {})
                        logger.info(f"      - Added {suggested_name}")
        
        # Update state
        state["selected_tools"] = selected_tools
        state["tool_parameters"] = tool_parameters
        
        # Clear verification fields to allow router to re-analyze
        # Clear both selection and execution verification fields
        state["verification_status"] = None
        state["verification_reason"] = None
        state["verification_suggested_changes"] = None
        state["execution_verification_status"] = None
        state["execution_verification_reason"] = None
        state["execution_verification_suggested_changes"] = None
        
        logger.info(f"✅ Tool selection refined")
        logger.info(f"   Updated tools: {[t.get('name') for t in selected_tools]}")
        logger.info(f"   Updated parameters: {list(tool_parameters.keys())}")
        logger.info(f"{'='*60}\n")
        
        return state
    
    except Exception as e:
        logger.error(f"Tool Selection Refiner Node error: {e}")
        state["error"] = str(e)
        # On error, keep current tools and proceed
        return state
