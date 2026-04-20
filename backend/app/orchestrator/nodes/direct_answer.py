"""
Direct Answer Node
Handles general questions that can be answered directly without DB/RAG
Examples: "วันนี้วันที่อะไร", "สวัสดี", "hello"
"""
from typing import Dict, Any
from app.orchestrator.state import AIAssistantState
from app.services.llm import get_llm
from app.utils.logger import get_logger
from app.utils.system_prompt import get_direct_answer_prompt
from datetime import datetime

logger = get_logger(__name__)


async def direct_answer_node(state: AIAssistantState) -> AIAssistantState:
    """
    Node that answers general questions directly without DB/RAG
    """
    try:
        user_message = state.get("user_message", "")
        history_context = state.get("history_context", "")
        
        logger.info(f"{'='*60}")
        logger.info(f"💬 [DIRECT ANSWER] Processing general question")
        logger.info(f"   Message: {user_message}")
        logger.info(f"{'='*60}")
        
        # Get current date/time for context
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        current_date_thai = now.strftime("%d/%m/%Y")
        day_name_thai = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"][now.weekday()]
        
        # Build context for LLM
        context_info = f"""
Current Date: {current_date} ({current_date_thai})
Current Time: {current_time}
Day of Week: {day_name_thai}
"""
        
        # Build history section for conversation continuity
        history_section = ""
        if history_context:
            history_section = f"""

=== Previous Conversation History ===
{history_context}

"""
        
        # Get base system prompt with vocabulary context
        base_system_prompt = get_direct_answer_prompt(include_context=True)
        
        # Build prompt for direct answer (include chat history for context-aware replies)
        prompt = f"""{base_system_prompt}{history_section}
User Question: {user_message}

Context Information:
{context_info}

Instructions:
- Use the conversation history above to reply in context (e.g. follow-up questions, greetings).
- Answer in Thai language naturally.

Response:"""
        
        # Generate response using LLM
        try:
            # Use temperature=1.0 for mini models (gpt-4o-mini, gpt-5-mini, gpt-5.4-mini) - required by model
            llm = get_llm(temperature=1.0)
            llm_response = await llm.ainvoke(prompt)
            response = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            # Fallback response
            if "วันที่" in user_message or "date" in user_message.lower():
                response = f"วันนี้วันที่ {current_date_thai} ({day_name_thai})"
            elif "เวลา" in user_message or "time" in user_message.lower():
                response = f"เวลาปัจจุบันคือ {current_time}"
            elif any(greeting in user_message.lower() for greeting in ["สวัสดี", "hello", "hi"]):
                response = "สวัสดีครับ! ผมพร้อมช่วยเหลือคุณแล้วครับ มีอะไรให้ช่วยไหมครับ?"
            else:
                response = "สวัสดีครับ! ผมพร้อมช่วยเหลือคุณแล้วครับ มีอะไรให้ช่วยไหมครับ?"
        
        # Update state
        state["response"] = response
        state["intent"] = "direct_answer"
        
        # Log metadata (for audit)
        state["tool_calls"] = [{
            "tool": "direct_answer",
            "input": {"user_message": user_message},
            "output": {"response": response, "context_used": context_info}
        }]
        
        logger.info(f"{'='*60}")
        logger.info(f"✅ Direct Answer Generated")
        logger.info(f"   Response: {response[:100]}..." if len(response) > 100 else f"   Response: {response}")
        logger.info(f"{'='*60}\n")
        
        return state
    
    except Exception as e:
        logger.error(f"Direct Answer Node error: {e}")
        state["error"] = str(e)
        state["response"] = "ขออภัยครับ เกิดข้อผิดพลาดในการสร้างคำตอบ กรุณาลองใหม่อีกครั้ง"
        return state
