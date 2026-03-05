"""
Tool Execution Verifier Node
Verifies tool execution results after running tools (Post-Verification)
Uses LLM to check if the results can answer the user's question
"""
import json
from typing import Dict, Any, Literal
from app.orchestrator.state import AIAssistantState
from app.utils.logger import get_logger
from app.utils.system_prompt import get_tool_execution_verifier_prompt
from openai import AsyncOpenAI
from app.config import settings

logger = get_logger(__name__)


async def verify_tool_execution_with_llm(
    user_message: str,
    selected_tools: list,
    tool_results: list,
    history_context: str = None
) -> tuple[str, str, Dict[str, Any]]:
    """
    Use LLM to verify if tool execution results can answer the user's question
    
    Returns:
        (status, reason, suggested_changes)
        status: "APPROVED", "WRONG_TOOL", "NEEDS_MORE_TOOLS"
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
        
        # Build results summary (limit size to avoid token overflow)
        results_summary = []
        for i, result in enumerate(tool_results, 1):
            tool_name = result.get("tool", "unknown")
            output = result.get("output", {})
            
            # Extract key information from output
            result_info = {
                "tool": tool_name,
                "success": output.get("success", False),
                "has_error": "error" in output or output.get("success") is False,
                "has_data": False
            }
            
            # Check for data structure
            if isinstance(output, dict):
                # Check for common data structures
                if "data" in output:
                    data = output.get("data", {})
                    if isinstance(data, dict):
                        # Check for leads
                        if "leads" in data:
                            leads = data.get("leads", [])
                            result_info["has_data"] = isinstance(leads, list) and len(leads) > 0
                            result_info["data_count"] = len(leads) if isinstance(leads, list) else 0
                        # Check for salesLeads
                        elif "salesLeads" in data:
                            sales_leads = data.get("salesLeads", [])
                            result_info["has_data"] = isinstance(sales_leads, list) and len(sales_leads) > 0
                            result_info["data_count"] = len(sales_leads) if isinstance(sales_leads, list) else 0
                            result_info["total_sales_value"] = data.get("totalSalesValue", 0)
                        # Check for salesTeam
                        elif "salesTeam" in data:
                            sales_team = data.get("salesTeam", [])
                            result_info["has_data"] = isinstance(sales_team, list) and len(sales_team) > 0
                            result_info["data_count"] = len(sales_team) if isinstance(sales_team, list) else 0
                        # Check for stats
                        elif "stats" in data:
                            stats = data.get("stats", {})
                            returned = stats.get("returned", 0)
                            result_info["has_data"] = returned > 0
                            result_info["data_count"] = returned
                    elif isinstance(data, list):
                        result_info["has_data"] = len(data) > 0
                        result_info["data_count"] = len(data)
                # Check for found flag
                elif "found" in output:
                    result_info["has_data"] = output.get("found", False)
                # Check for error
                elif "error" in output:
                    result_info["error_message"] = str(output.get("error", ""))[:200]
            
            results_summary.append(result_info)
        
        # Build context
        context_parts = []
        context_parts.append(f"User Question: {user_message}")
        context_parts.append(f"\nTools Executed ({len(tool_list)}):")
        
        for i, tool_info in enumerate(tool_list, 1):
            tool_name = tool_info.get("name", "")
            params = tool_info.get("parameters", {})
            context_parts.append(f"\n{i}. Tool: {tool_name}")
            if params:
                context_parts.append(f"   Parameters: {json.dumps(params, ensure_ascii=False, indent=2)}")
        
        context_parts.append(f"\nExecution Results:")
        for i, result_info in enumerate(results_summary, 1):
            tool_name = result_info.get("tool", "unknown")
            success = result_info.get("success", False)
            has_data = result_info.get("has_data", False)
            data_count = result_info.get("data_count", 0)
            has_error = result_info.get("has_error", False)
            
            context_parts.append(f"\n{i}. Tool: {tool_name}")
            context_parts.append(f"   Success: {success}")
            context_parts.append(f"   Has Data: {has_data}")
            if data_count > 0:
                context_parts.append(f"   Data Count: {data_count}")
            if has_error:
                error_msg = result_info.get("error_message", "Unknown error")
                context_parts.append(f"   Error: {error_msg}")
            if result_info.get("total_sales_value"):
                context_parts.append(f"   Total Sales Value: {result_info.get('total_sales_value')}")
        
        # Add sample data structure (first 500 chars) for context
        if tool_results:
            first_result = tool_results[0]
            output = first_result.get("output", {})
            try:
                output_str = json.dumps(output, ensure_ascii=False, indent=2)
                if len(output_str) > 500:
                    context_parts.append(f"\n\nSample Output Structure (first 500 chars):")
                    context_parts.append(output_str[:500] + "...")
                else:
                    context_parts.append(f"\n\nSample Output Structure:")
                    context_parts.append(output_str)
            except:
                pass
        
        if history_context:
            context_parts.append(f"\n\n=== Previous Conversation History ===")
            context_parts.append(history_context)
        
        context = "\n".join(context_parts)
        
        # Get system prompt
        system_prompt = get_tool_execution_verifier_prompt()
        
        # Build prompt
        prompt = f"""{system_prompt}

{context}

ตรวจสอบและตอบในรูปแบบ JSON เท่านั้น:
{{
    "status": "APPROVED|WRONG_TOOL|NEEDS_MORE_TOOLS",
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
                {"role": "system", "content": "You are a tool execution verifier. Respond only with valid JSON."},
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
        logger.error(f"Error in LLM tool execution verification: {e}")
        # Fallback: approve on error (to avoid blocking)
        return "APPROVED", f"Verification error: {str(e)}, proceeding", {}


async def tool_execution_verifier_node(state: AIAssistantState) -> AIAssistantState:
    """
    Node that verifies tool execution results after running tools
    """
    try:
        user_message = state.get("user_message", "")
        selected_tools = state.get("selected_tools", [])
        tool_results = state.get("tool_results", [])
        history_context = state.get("history_context")
        execution_verification_retry_count = state.get("execution_verification_retry_count", 0)
        max_execution_verification_retries = state.get("max_execution_verification_retries", 2)
        
        logger.info(f"{'='*60}")
        logger.info(f"🔍 [TOOL EXECUTION VERIFIER] Post-Verification")
        logger.info(f"   User message: {user_message[:100]}...")
        logger.info(f"   Executed tools: {[t.get('name') for t in selected_tools]}")
        logger.info(f"   Tool results: {len(tool_results)} items")
        logger.info(f"   Execution verification retry count: {execution_verification_retry_count}")
        logger.info(f"{'='*60}")
        
        # If no tools executed, skip verification
        if not selected_tools or not tool_results:
            logger.info("   ⚠️  No tools executed or no results, skipping verification")
            state["execution_verification_status"] = "APPROVED"
            state["execution_verification_reason"] = "No tools executed or no results"
            return state
        
        # Check if we've exceeded max verification retries
        if execution_verification_retry_count >= max_execution_verification_retries:
            logger.warning(f"   ⚠️  Max execution verification retries reached, approving")
            state["execution_verification_status"] = "APPROVED"
            state["execution_verification_reason"] = "Max execution verification retries reached"
            return state
        
        # Verify tool execution results
        status, reason, suggested_changes = await verify_tool_execution_with_llm(
            user_message=user_message,
            selected_tools=selected_tools,
            tool_results=tool_results,
            history_context=history_context
        )
        
        # Update state
        state["execution_verification_status"] = status
        state["execution_verification_reason"] = reason
        state["execution_verification_suggested_changes"] = suggested_changes
        
        logger.info(f"✅ Execution Verification Result:")
        logger.info(f"   Status: {status}")
        logger.info(f"   Reason: {reason}")
        if suggested_changes.get("suggested_tools"):
            logger.info(f"   Suggested tools: {[t.get('name') for t in suggested_changes.get('suggested_tools', [])]}")
        if suggested_changes.get("suggested_parameters"):
            logger.info(f"   Suggested parameters: {suggested_changes.get('suggested_parameters')}")
        logger.info(f"{'='*60}\n")
        
        return state
    
    except Exception as e:
        logger.error(f"Tool Execution Verifier Node error: {e}")
        # On error, approve to avoid blocking
        state["execution_verification_status"] = "APPROVED"
        state["execution_verification_reason"] = f"Verification error: {str(e)}"
        return state


def should_proceed_to_result_grader(state: AIAssistantState) -> Literal["result_grader", "tool_selection_refiner"]:
    """
    Determine if we should proceed to Result Grader or refine tool selection
    """
    execution_verification_status = state.get("execution_verification_status", "APPROVED")
    
    if execution_verification_status == "APPROVED":
        return "result_grader"
    else:
        # WRONG_TOOL or NEEDS_MORE_TOOLS -> refine
        return "tool_selection_refiner"
