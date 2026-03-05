"""
Clarification Node
Asks user for clarification when intent is unclear
"""
from typing import Dict, Any
from app.orchestrator.state import AIAssistantState
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def clarify_node(state: AIAssistantState) -> AIAssistantState:
    """
    Node that asks for clarification
    """
    try:
        user_message = state.get("user_message", "")
        
        logger.info(f"Clarify Node: asking for clarification")
        
        # Generate clarification question
        clarification_questions = [
            "ขออภัยครับ คำถามของคุณไม่ชัดเจนพอ คุณต้องการถามเกี่ยวกับอะไรครับ?",
            "คุณต้องการข้อมูลเกี่ยวกับอะไรครับ? (เช่น สถานะ lead, เอกสาร, สรุปยอด)",
            "กรุณาระบุรายละเอียดเพิ่มเติมครับ เช่น ชื่อ lead หรือหัวข้อที่ต้องการค้นหา"
        ]
        
        # Simple selection (in production, use LLM)
        response = clarification_questions[0]
        
        # Update state
        state["response"] = response
        state["intent"] = "clarify"
        
        logger.info(f"Clarify Node: generated clarification question")
        
        return state
    
    except Exception as e:
        logger.error(f"Clarify Node error: {e}")
        state["error"] = str(e)
        return state
