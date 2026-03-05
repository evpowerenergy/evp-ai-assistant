"""
Result Grader Node
Evaluates data quality from RPC results and decides if retry is needed
"""
from typing import Dict, Any, Literal
from app.orchestrator.state import AIAssistantState
from app.utils.logger import get_logger
from openai import AsyncOpenAI
from app.config import settings

logger = get_logger(__name__)


def is_empty_result(output: Dict[str, Any]) -> bool:
    """
    Check if RPC result is empty
    """
    if not output:
        return True
    
    # Check for error
    if "error" in output:
        return False  # Error is not empty, it's an error
    
    # Check for success flag
    if output.get("success") is False:
        return True
    
    # Check for data structure
    if "data" in output:
        data = output.get("data", {})
        # Check for leads
        if "leads" in data:
            leads = data.get("leads", [])
            if not leads or len(leads) == 0:
                return True
        # Check for salesTeam (for get_sales_team_list)
        if "salesTeam" in data:
            sales_team = data.get("salesTeam", [])
            if not sales_team or len(sales_team) == 0:
                return True
        # Check for stats
        if "stats" in data:
            stats = data.get("stats", {})
            returned = stats.get("returned", 0)
            if returned == 0:
                return True
    
    # Check for salesTeam at root level (some RPC functions return it directly)
    if "salesTeam" in output:
        sales_team = output.get("salesTeam", [])
        if not sales_team or len(sales_team) == 0:
            return True
    
    # Check for found flag
    if "found" in output:
        return not output.get("found", False)
    
    # Check if output is empty dict
    if isinstance(output, dict) and len(output) == 0:
        return True
    
    return False


def has_error(output: Dict[str, Any]) -> bool:
    """
    Check if RPC result has error
    """
    if not output:
        return False
    
    if "error" in output:
        return True
    
    if output.get("success") is False and "error" in str(output):
        return True
    
    return False


async def grade_result_with_llm(
    user_message: str,
    tool_results: list,
    previous_attempts: list
) -> tuple[str, str, Dict[str, Any]]:
    """
    Use LLM to grade result quality and suggest retry parameters
    
    Returns:
        (quality, reason, suggested_params)
        quality: "sufficient", "insufficient", "empty", "error"
        reason: Explanation
        suggested_params: Suggested parameters for retry
    """
    try:
        # Build context for LLM
        context_parts = []
        context_parts.append(f"User Question: {user_message}")
        context_parts.append("\nTool Results:")
        
        for i, result in enumerate(tool_results, 1):
            tool_name = result.get("tool", "unknown")
            output = result.get("output", {})
            context_parts.append(f"\n{i}. Tool: {tool_name}")
            
            # For certain tools, show full output structure without truncation
            # For others, limit to avoid token overflow
            if tool_name in ["get_sales_team_list", "get_sales_team", "get_team_kpi", "get_sales_closed"]:
                # Show more context for sales/report tools so grader doesn't mark insufficient due to truncation
                import json
                try:
                    output_str = json.dumps(output, indent=2, ensure_ascii=False)
                    # Still limit but show more (2000 chars)
                    if len(output_str) > 2000:
                        context_parts.append(f"   Output (first 2000 chars): {output_str[:2000]}...")
                        context_parts.append(f"   Output length: {len(output_str)} characters")
                        # Show key info
                        if isinstance(output, dict):
                            data = output.get("data", {})
                            if isinstance(data, dict):
                                if "salesTeam" in data:
                                    sales_team = data["salesTeam"]
                                    context_parts.append(f"   salesTeam count: {len(sales_team) if isinstance(sales_team, list) else 'N/A'}")
                                if "salesLeads" in data:
                                    sales_leads = data["salesLeads"]
                                    context_parts.append(f"   salesLeads count: {len(sales_leads) if isinstance(sales_leads, list) else 'N/A'}")
                    else:
                        context_parts.append(f"   Output: {output_str}")
                except:
                    context_parts.append(f"   Output: {str(output)[:1000]}...")
            else:
                context_parts.append(f"   Output: {str(output)[:500]}...")  # Limit length
        
        if previous_attempts:
            context_parts.append(f"\nPrevious Attempts: {len(previous_attempts)}")
        
        context = "\n".join(context_parts)
        
        # Build prompt
        prompt = f"""You are a data quality evaluator for EV Power Energy CRM system.
Evaluate the tool results and determine if they are sufficient to answer the user's question.

{context}

Evaluate the results and determine:
1. **Quality**: Is the data sufficient to answer the question?
   - "sufficient": Data is complete and can answer the question (even if output is truncated in log, if data structure shows success and has data, it's sufficient)
   - "insufficient": Data exists but may not fully answer the question
   - "empty": No data found (empty results, empty arrays, or success=false)
   - "error": Error occurred during query

2. **Reason**: Brief explanation of your assessment
   - IMPORTANT: If output shows "..." at the end, it's just log truncation for display, NOT actual data truncation
   - Check the actual data structure: if "success": true and data arrays exist with items, it's sufficient
   - Only mark as "insufficient" if data is genuinely incomplete (e.g., pagination needed, missing fields)

3. **Retry Suggestion**: If quality is "empty" or "insufficient", suggest:
   - Alternative query terms (if user misspelled something)
   - Different search parameters
   - Fuzzy search options

Respond in JSON format:
{{
    "quality": "sufficient|insufficient|empty|error",
    "reason": "brief explanation",
    "suggested_retry_params": {{
        "query": "alternative query if applicable",
        "fuzzy": true/false,
        "adjustments": "what to adjust"
    }}
}}

Response (JSON only):"""
        
        # Call LLM
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a data quality evaluator. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse response
        import json
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON
        if content.startswith("```"):
            # Remove markdown code blocks
            content = content.replace("```json", "").replace("```", "").strip()
        
        try:
            result = json.loads(content)
            quality = result.get("quality", "sufficient")
            reason = result.get("reason", "No reason provided")
            suggested_params = result.get("suggested_retry_params", {})
            return quality, reason, suggested_params
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response as JSON: {content}")
            # Fallback to rule-based
            return grade_result_rule_based(user_message, tool_results)
    
    except Exception as e:
        logger.error(f"Error in LLM grading: {e}")
        # Fallback to rule-based
        return grade_result_rule_based(user_message, tool_results)


def grade_result_rule_based(
    user_message: str,
    tool_results: list
) -> tuple[str, str, Dict[str, Any]]:
    """
    Rule-based result grading (fallback)
    """
    if not tool_results:
        return "empty", "No tool results", {}
    
    for result in tool_results:
        output = result.get("output", {})
        tool_name = result.get("tool", "")
        
        # Check for error
        if has_error(output):
            return "error", "RPC error occurred", {}
        
        # Check for empty
        if is_empty_result(output):
            # Suggest fuzzy search for name-based queries
            suggested_params = {}
            if tool_name in ["get_lead_status", "get_customer_info"]:
                # Extract name from user message
                import re
                # Try to find name patterns
                name_patterns = re.findall(r'ชื่อ\s+([^\s]+)', user_message)
                if name_patterns:
                    suggested_params = {
                        "query": name_patterns[0],
                        "fuzzy": True,
                        "adjustments": "Try fuzzy search for name"
                    }
            
            return "empty", "No data found", suggested_params
    
    # If we get here, results exist
    return "sufficient", "Data found", {}


async def result_grader_node(state: AIAssistantState) -> AIAssistantState:
    """
    Node that grades the quality of RPC results
    """
    try:
        user_message = state.get("user_message", "")
        tool_results = state.get("tool_results", [])
        previous_attempts = state.get("previous_attempts", [])
        retry_count = state.get("retry_count", 0)
        
        logger.info(f"{'='*60}")
        logger.info(f"📊 [RESULT GRADER] Evaluating data quality")
        logger.info(f"   Tool results: {len(tool_results)} items")
        logger.info(f"   Retry count: {retry_count}")
        logger.info(f"{'='*60}")
        
        # Grade results
        quality, reason, suggested_params = await grade_result_with_llm(
            user_message=user_message,
            tool_results=tool_results,
            previous_attempts=previous_attempts
        )
        
        # Update state
        state["data_quality"] = quality
        state["quality_reason"] = reason
        state["suggested_retry_params"] = suggested_params
        
        # Store current attempt in history
        if tool_results:
            attempt = {
                "retry_count": retry_count,
                "tool_results": tool_results,
                "quality": quality,
                "reason": reason
            }
            if "previous_attempts" not in state:
                state["previous_attempts"] = []
            state["previous_attempts"].append(attempt)
        
        logger.info(f"✅ Quality Assessment:")
        logger.info(f"   Quality: {quality}")
        logger.info(f"   Reason: {reason}")
        if suggested_params:
            logger.info(f"   Suggested Retry: {suggested_params}")
        logger.info(f"{'='*60}\n")
        
        return state
    
    except Exception as e:
        logger.error(f"Result Grader Node error: {e}")
        # Default to sufficient to avoid blocking
        state["data_quality"] = "sufficient"
        state["quality_reason"] = f"Error in grading: {str(e)}"
        return state


def should_retry(state: AIAssistantState) -> Literal["retry", "sufficient", "give_up"]:
    """
    Determine if we should retry based on data quality and retry count
    """
    quality = state.get("data_quality", "sufficient")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    
    # If quality is sufficient, no need to retry
    if quality == "sufficient":
        return "sufficient"
    
    # If we've exceeded max retries, give up
    if retry_count >= max_retries:
        return "give_up"
    
    # If quality is empty or insufficient, try retry
    if quality in ["empty", "insufficient"]:
        return "retry"
    
    # For errors, also try retry (but with different strategy)
    if quality == "error":
        return "retry"
    
    # Default: sufficient
    return "sufficient"
