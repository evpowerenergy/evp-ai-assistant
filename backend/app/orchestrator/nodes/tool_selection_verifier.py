"""
Tool Selection Verifier Node
Verifies tool selection before execution (Pre-Verification)
Uses LLM to check if selected tools are appropriate for the user's question
"""
import json
from typing import Dict, Any, Literal
from app.orchestrator.state import AIAssistantState
from app.utils.logger import get_logger
from app.utils.system_prompt import get_tool_selection_verifier_prompt
from openai import AsyncOpenAI
from app.config import settings

logger = get_logger(__name__)


async def verify_tool_selection_with_llm(
    user_message: str,
    selected_tools: list,
    tool_parameters: Dict[str, Dict[str, Any]],
    history_context: str = None
) -> tuple[str, str, Dict[str, Any]]:
    """
    Use LLM to verify tool selection appropriateness
    
    Returns:
        (status, reason, suggested_changes)
        status: "APPROVED", "REJECTED", "NEEDS_ADJUSTMENT"
        reason: Explanation
        suggested_changes: Suggested tools/parameters changes
    """
    try:
        # Build tool list for LLM
        tool_list = []
        for tool_info in selected_tools:
            tool_name = tool_info.get("name", "")
            params = tool_info.get("parameters", {})
            tool_list.append({
                "name": tool_name,
                "parameters": params
            })
        
        # Build context
        context_parts = []
        context_parts.append(f"User Question: {user_message}")
        context_parts.append(f"\nSelected Tools ({len(tool_list)}):")
        
        for i, tool_info in enumerate(tool_list, 1):
            tool_name = tool_info.get("name", "")
            params = tool_info.get("parameters", {})
            context_parts.append(f"\n{i}. Tool: {tool_name}")
            if params:
                context_parts.append(f"   Parameters: {json.dumps(params, ensure_ascii=False, indent=2)}")
            else:
                context_parts.append(f"   Parameters: (none)")
        
        if history_context:
            context_parts.append(f"\n=== Previous Conversation History ===")
            context_parts.append(history_context)
        
        context = "\n".join(context_parts)
        
        # Get system prompt
        system_prompt = get_tool_selection_verifier_prompt()
        
        # Build prompt
        prompt = f"""{system_prompt}

{context}

ตรวจสอบและตอบในรูปแบบ JSON เท่านั้น:
{{
    "status": "APPROVED|REJECTED|NEEDS_ADJUSTMENT",
    "reason": "คำอธิบายสั้นๆ",
    "suggested_tools": [
        {{
            "name": "tool_name",
            "parameters": {{}}
        }}
    ],
    "suggested_parameters": {{
        "tool_name": {{
            "param_name": "value"
        }}
    }}
}}

Response (JSON only):"""
        
        # Call LLM
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a tool selection verifier. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3  # Lower temperature for more consistent verification
        )
        
        # Parse response
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON
        if content.startswith("```"):
            # Remove markdown code blocks
            content = content.replace("```json", "").replace("```", "").strip()
        
        try:
            result = json.loads(content)
            status = result.get("status", "APPROVED")
            reason = result.get("reason", "No reason provided")
            suggested_tools = result.get("suggested_tools", [])
            suggested_parameters = result.get("suggested_parameters", {})
            
            return status, reason, {
                "suggested_tools": suggested_tools,
                "suggested_parameters": suggested_parameters
            }
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response as JSON: {content}")
            # Fallback: approve if we can't parse (to avoid blocking)
            return "APPROVED", "Could not parse verification response, proceeding", {}
    
    except Exception as e:
        logger.error(f"Error in LLM tool selection verification: {e}")
        # Fallback: approve on error (to avoid blocking)
        return "APPROVED", f"Verification error: {str(e)}, proceeding", {}


async def tool_selection_verifier_node(state: AIAssistantState) -> AIAssistantState:
    """
    Node that verifies tool selection before execution
    """
    try:
        user_message = state.get("user_message", "")
        selected_tools = state.get("selected_tools", [])
        tool_parameters = state.get("tool_parameters", {})
        history_context = state.get("history_context")
        verification_retry_count = state.get("verification_retry_count", 0)
        max_verification_retries = state.get("max_verification_retries", 2)
        
        logger.info(f"{'='*60}")
        logger.info(f"🔍 [TOOL SELECTION VERIFIER] Pre-Verification")
        logger.info(f"   User message: {user_message[:100]}...")
        logger.info(f"   Selected tools: {[t.get('name') for t in selected_tools]}")
        logger.info(f"   Verification retry count: {verification_retry_count}")
        logger.info(f"{'='*60}")
        
        # If no tools selected, skip verification (will be handled by router)
        if not selected_tools:
            logger.info("   ⚠️  No tools selected, skipping verification")
            state["verification_status"] = "APPROVED"
            state["verification_reason"] = "No tools selected"
            return state
        
        # Check if we've exceeded max verification retries
        if verification_retry_count >= max_verification_retries:
            logger.warning(f"   ⚠️  Max verification retries reached, approving")
            state["verification_status"] = "APPROVED"
            state["verification_reason"] = "Max verification retries reached"
            return state
        
        # Verify tool selection
        status, reason, suggested_changes = await verify_tool_selection_with_llm(
            user_message=user_message,
            selected_tools=selected_tools,
            tool_parameters=tool_parameters,
            history_context=history_context
        )
        
        # Update state
        state["verification_status"] = status
        state["verification_reason"] = reason
        state["verification_suggested_changes"] = suggested_changes
        
        logger.info(f"✅ Verification Result:")
        logger.info(f"   Status: {status}")
        logger.info(f"   Reason: {reason}")
        if suggested_changes.get("suggested_tools"):
            logger.info(f"   Suggested tools: {[t.get('name') for t in suggested_changes.get('suggested_tools', [])]}")
        if suggested_changes.get("suggested_parameters"):
            logger.info(f"   Suggested parameters: {suggested_changes.get('suggested_parameters')}")
        logger.info(f"{'='*60}\n")
        
        return state
    
    except Exception as e:
        logger.error(f"Tool Selection Verifier Node error: {e}")
        # On error, approve to avoid blocking
        state["verification_status"] = "APPROVED"
        state["verification_reason"] = f"Verification error: {str(e)}"
        return state


def should_proceed_to_db_query(state: AIAssistantState) -> Literal["db_query", "tool_selection_refiner"]:
    """
    Determine if we should proceed to DB Query or refine tool selection
    """
    verification_status = state.get("verification_status", "APPROVED")
    
    if verification_status == "APPROVED":
        return "db_query"
    else:
        # REJECTED or NEEDS_ADJUSTMENT -> refine
        return "tool_selection_refiner"
