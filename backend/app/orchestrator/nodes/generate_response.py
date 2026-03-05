"""
Generate Response Node
Generates final response using LLM
Receives state (user_message, tool_results, rag_results, etc.) and sends formatted context to LLM.
"""
import json
from typing import Dict, Any
from app.orchestrator.state import AIAssistantState
from app.orchestrator.formatters import format_tool_response, format_rag_response
from app.services.llm import get_llm
from app.utils.logger import get_logger
from app.utils.system_prompt import get_response_generator_prompt

logger = get_logger(__name__)


async def generate_response_node(state: AIAssistantState) -> AIAssistantState:
    """
    Node that generates final response using LLM.
    Receives: user_message, tool_results, rag_results, citations, history_context, data_quality, etc.
    Formats raw data (Input + Output for each tool) and sends to LLM.
    """
    try:
        user_message = state.get("user_message", "")
        tool_results = state.get("tool_results", [])
        rag_results = state.get("rag_results", [])
        citations = state.get("citations", [])
        history_context = state.get("history_context", "")

        logger.info(f"{'='*60}")
        logger.info(f"💬 [STEP 4/4] Generate Response Node: Creating LLM response")
        logger.info(f"   User message: {user_message}")
        logger.info(f"   Tool results: {len(tool_results)} items")
        logger.info(f"   RAG results: {len(rag_results)} items")
        if tool_results:
            raw_data_size = sum(len(json.dumps(r.get("output", {}), ensure_ascii=False)) for r in tool_results)
            logger.info(f"   Raw data size: ~{raw_data_size:,} characters (will be sent to LLM)")
        logger.info(f"{'='*60}")

        # Build context for LLM
        context_parts = []
        if tool_results:
            context_parts.append("Database Query Results:")
            for result in tool_results:
                context_parts.append(f"- {result.get('tool')}: {result.get('output')}")
        if rag_results:
            context_parts.append("\nRelevant Documents:")
            for i, result in enumerate(rag_results, 1):
                content = result.get("content", "")
                context_parts.append(f"{i}. {content}")

        context = "\n".join(context_parts)

        # Build prompt (fallback when no formatted/raw context)
        prompt = f"""You are an AI assistant for EV Power Energy. Answer the user's question based on the provided context.

User Question: {user_message}

Context:
{context if context else "No specific context available. Use your general knowledge."}

Instructions:
- Answer in Thai language
- Be concise and helpful
- If you used database results, mention them naturally
- If you used documents, include citations: {', '.join(citations) if citations else 'None'}
- If information is not available, say so politely

Response:"""

        llm = get_llm(temperature=1.0)

        formatted_context = ""
        raw_data_context = ""
        debug_precompute: Dict[str, Any] = {}

        if tool_results:
            formatted_context = format_tool_response(tool_results, user_message, debug_out=debug_precompute)

            raw_data_parts = []
            for result in tool_results:
                tool_name = result.get("tool", "unknown")
                inp = result.get("input", {})
                output = result.get("output", {})
                part = f"Tool: {tool_name}\n"
                if inp:
                    part += f"📥 Parameters (Input):\n{json.dumps(inp, ensure_ascii=False, indent=2)}\n"
                part += f"📤 Output (JSON):\n{json.dumps(output, ensure_ascii=False, indent=2)}"
                raw_data_parts.append(part)

            raw_data_context = "\n\n".join(raw_data_parts)
        elif rag_results:
            formatted_context = format_rag_response(rag_results, citations, user_message)

        base_system_prompt = get_response_generator_prompt(include_context=True)

        data_quality = state.get("data_quality")
        quality_reason = state.get("quality_reason")
        retry_count = state.get("retry_count", 0)

        quality_context = ""
        if data_quality and data_quality != "sufficient":
            quality_context = f"\n\nNote: Data quality is '{data_quality}'. {quality_reason or ''}"
            if retry_count > 0:
                quality_context += f" (Retried {retry_count} time(s))"

        history_section = ""
        if history_context:
            history_section = f"""

=== Previous Conversation History ===
{history_context}

"""

        if tool_results and raw_data_context:
            prompt = f"""{base_system_prompt}{history_section}
User Question: {user_message}

=== FORMATTED SUMMARY (ตัวเลขที่ระบบคำนวณแล้ว — ใช้ตัวเลขนี้เป็นหลัก) ===
{formatted_context}{quality_context}

=== RAW DATA (รวม Parameters/Input ทุกฟังก์ชัน — ใช้เข้าใจบริบท เช่น date_from/date_to ที่ใช้กรอง) ===
{raw_data_context}

⚠️ กฎสูงสุด — ตอบตรงคำถาม + ห้ามมั่ว:
- **ตอบตรงคำถามเท่านั้น:** ตอบเฉพาะสิ่งที่ผู้ใช้ถาม (User Question ด้านบน) ไม่เพิ่มหัวข้ออื่น ไม่พูดนอกเรื่อง
- **ห้ามมั่ว/สร้างข้อมูล:** ใช้เฉพาะข้อมูลที่มีใน FORMATTED SUMMARY หรือ RAW DATA ด้านบนเท่านั้น ห้ามสมมติ ห้ามคาดเดา ห้ามสร้างตัวเลขหรือข้อความที่ไม่มีใน context ถ้าไม่มีข้อมูลที่ตอบคำถามได้ ให้ตอบว่า "ไม่มีข้อมูลในระบบที่ตอบคำถามนี้ได้" — ห้ามตอบโดยมั่วหรือเติมข้อมูลเอง

⚠️ กฎตัวเลข (ลำดับความสำคัญสูงสุด — ต้องทำตาม):
- เมื่อ FORMATTED SUMMARY ด้านบนมีข้อความ "สรุปตามหน้า /reports/sales-closed" หรือ "สรุปแยกตามแพลตฟอร์ม" หรือ "ช่วงข้อมูลที่ขอ" → **ต้องใช้เฉพาะตัวเลขจาก FORMATTED SUMMARY เท่านั้น** ในการตอบ
- **ห้ามคำนวณตัวเลขใหม่จาก RAW DATA** — จำนวน QT และจำนวนบาท (฿) ที่แสดงต้อง **copy ตรงจาก FORMATTED SUMMARY** ทุกหลัก
- **ห้ามปัดเศษ ห้ามประมาณ ห้ามเปลี่ยนตัวเลข** — ถ้าสรุปเขียน ฿1,666,346.12 ต้องเขียน ฿1,666,346.12 (ไม่ใช่ 1.67 ล้าน หรือ 1666346)
- **ห้ามปรับแต่งตัวเลข** - ห้ามปัดเศษ, ห้ามสร้างตัวเลขใหม่, ห้ามใช้ตัวเลขจากแหล่งอื่น
- **ถ้าข้อมูลว่างเปล่า (empty array/null)** - บอกว่าว่างเปล่าตามความเป็นจริง ไม่ต้องเสริมหรือสรุปว่ามีข้อมูล

📝 RESPONSE STYLE (สไตล์การตอบ):
- **สั้น กระชับ** - ตอบให้สั้น เข้าใจง่าย ไม่ยาวเกินไป
- **ใช้ภาษาง่ายๆ** - ใช้คำที่เข้าใจง่าย ไม่ใช้คำศัพท์เทคนิคที่ซับซ้อน
- **แสดงข้อมูลตอบคำถามผู้ใช้ให้ตรง** - แสดงข้อมูลที่ตอบคำถามผู้ใช้โดยตรง ไม่ต้องแสดงข้อมูลที่ไม่เกี่ยวข้อง

📋 FORMATTING GUIDELINES:
- **ใช้ bullet points (-) หรือ numbering (1. 2. 3.)** สำหรับรายการข้อมูล
- **จำกัดจำนวนรายการ** - ถ้ามีข้อมูลเยอะ (>10 items), แสดงเฉพาะรายการสำคัญ แล้วบอกว่ามีทั้งหมดกี่รายการ
- **ใช้ตารางหรือการจัดรูปแบบ** เมื่อมีข้อมูลหลายรายการ
- **แสดงตัวเลขให้อ่านง่าย** - ใช้ comma สำหรับตัวเลขใหญ่ และจัดรูปแบบวันที่ให้ชัดเจน

Instructions:
- **ตัวเลข (QT, จำนวนบาท):** ถ้า FORMATTED SUMMARY มี "สรุปตามหน้า /reports/sales-closed" หรือ "สรุปแยกตามแพลตฟอร์ม" → ใช้**เฉพาะตัวเลขจาก FORMATTED SUMMARY** (copy ตรงทุกหลัก) ห้ามคำนวณจาก RAW DATA
- **ข้อมูลอื่น (ชื่อ, รายการ):** ใช้ RAW DATA เป็นแหล่งอ้างอิงสำหรับรายละเอียด (ชื่อลูกค้า, QT numbers ฯลฯ)
- Extract information from raw data exactly as provided — **แต่สำหรับจำนวน QT และยอดบาท (sales closed) ใช้จาก FORMATTED SUMMARY เท่านั้น**
- ⚠️ **สำคัญสำหรับ Sales Closed:** ใช้ totalQuotationAmount จาก salesLeads เท่านั้น, ใช้ lastActivityDate สำหรับแยกตามเดือน, จัดการ platform/category ที่เป็น null → 'ไม่ระบุ'
- **Parameters (Input)** บอกเงื่อนไขที่ใช้ดึงข้อมูล (date_from, date_to) — ใช้ตีความ Output ให้ถูกต้อง
- **IMPORTANT**: Do not say information is missing if it exists in the raw data
- Answer in Thai language, keep response short and concise
- **ตอบตรงคำถาม:** ตอบเฉพาะสิ่งที่ User Question ถาม
- **ห้ามมั่ว:** ถ้าข้อมูลที่ตอบคำถามไม่มีใน context ให้บอกว่า "ไม่มีข้อมูลในระบบที่ตอบคำถามนี้ได้"

Response:"""
        elif formatted_context:
            prompt = f"""{base_system_prompt}{history_section}
User Question: {user_message}

Context Information:
{formatted_context}{quality_context}

⚠️ กฎสูงสุด — ตอบตรงคำถาม + ห้ามมั่ว
⚠️ CRITICAL: REPORT DATA TRUTHFULLY - NO EMBELLISHMENT
📝 RESPONSE STYLE: สั้น กระชับ ใช้ภาษาง่ายๆ
Instructions:
- คำนวณ/สรุปจาก RAW DATA ได้เมื่อข้อมูลครบ
- Answer in Thai language
- **ตอบตรงคำถาม** และ **ห้ามมั่ว**

Response:"""
        else:
            prompt = f"""{base_system_prompt}{history_section}
User: {user_message}{quality_context}

Instructions:
- Use the conversation history to understand context
- Answer in Thai language naturally
- Reference previous conversation if relevant

Response:"""

        try:
            llm_response = await llm.ainvoke(prompt)
            response = llm_response.content if hasattr(llm_response, "content") else str(llm_response)
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            if formatted_context:
                response = formatted_context
            else:
                response = "สวัสดีครับ! ผมพร้อมช่วยเหลือคุณแล้วครับ มีอะไรให้ช่วยไหมครับ?"

        state["response"] = response
        if debug_precompute:
            state["debug_precompute"] = debug_precompute

        logger.info(f"{'='*60}")
        logger.info(f"✅ Response Generated Successfully")
        logger.info(f"   Length: {len(response)} characters")
        logger.info(f"{'='*60}\n")

        return state

    except Exception as e:
        logger.error(f"Generate Response Node error: {e}")
        state["error"] = str(e)
        state["response"] = "ขออภัยครับ เกิดข้อผิดพลาดในการสร้างคำตอบ กรุณาลองใหม่อีกครั้ง"
        return state
