"""
Chat API Endpoint
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
import time
import json
from app.core.auth import require_ai_assistant_access
from app.orchestrator.graph import process_message_stream
from app.orchestrator.state import AIAssistantState
from app.services.active_session import get_active_session, set_active_session
from app.services.chat_mode import get_chat_mode, set_chat_mode
from app.services.chat_processor import run_chat_turn
from app.services.chat_history import load_chat_history, format_history_for_llm, save_message
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    session_id: Optional[str] = None
    context: Optional[dict] = None
    chat_mode: Optional[Literal["crm", "kb"]] = None


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    session_id: str
    chat_mode: str = "crm"
    citations: Optional[List[str]] = None
    tool_calls: Optional[List[dict]] = None
    tool_results: Optional[List[dict]] = None  # NEW: Tool results with input/output
    intent: Optional[str] = None
    process_steps: Optional[List[Dict[str, Any]]] = None  # NEW: Process steps
    runtime: Optional[float] = None  # NEW: Total runtime in seconds
    debug_precompute: Optional[Dict[str, Any]] = None  # NEW: Pre-computed summaries for UI debug


class ActiveSessionRequest(BaseModel):
    """Set active session for shared web/LINE history"""
    session_id: str


class ChatModeRequest(BaseModel):
    """Update shared chat mode preference"""
    chat_mode: Literal["crm", "kb"]


@router.get("/chat/mode")
async def get_chat_mode_endpoint(
    current_user: dict = Depends(require_ai_assistant_access),
):
    """Get the user's shared chat mode (web + LINE)."""
    user_id = current_user.get("id")
    mode = await get_chat_mode(user_id)
    return {"chat_mode": mode}


@router.patch("/chat/mode")
async def patch_chat_mode_endpoint(
    body: ChatModeRequest,
    current_user: dict = Depends(require_ai_assistant_access),
):
    """Set shared chat mode preference."""
    user_id = current_user.get("id")
    mode = await set_chat_mode(user_id, body.chat_mode)
    return {"chat_mode": mode}


@router.get("/chat/active-session")
async def get_active_chat_session(
    current_user: dict = Depends(require_ai_assistant_access),
):
    """Get the user's active chat session id (shared with LINE)."""
    user_id = current_user.get("id")
    session_id = await get_active_session(user_id, first_message=None)
    return {"success": True, "session_id": session_id}


@router.patch("/chat/active-session")
async def patch_active_chat_session(
    body: ActiveSessionRequest,
    current_user: dict = Depends(require_ai_assistant_access),
):
    """Set active chat session (web sidebar switch syncs with LINE)."""
    user_id = current_user.get("id")
    await set_active_session(user_id, body.session_id)
    return {"success": True, "session_id": body.session_id}


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(require_ai_assistant_access)
):
    """
    Main chat endpoint
    Processes user message and returns AI response
    """
    try:
        user_id = current_user.get("id")
        logger.info(f"Chat request from user {user_id}: {request.message[:50]}...")
        
        user_role = current_user.get("role", "staff")
        session_id = request.session_id
        if not session_id:
            session_id = await get_active_session(user_id, first_message=request.message)
        else:
            await set_active_session(user_id, session_id)
        
        start_time = time.time()
        turn = await run_chat_turn(
            user_id=user_id,
            user_role=user_role,
            message=request.message,
            session_id=session_id,
            source="web",
            chat_mode=request.chat_mode,
        )
        runtime = turn.get("runtime") or (time.time() - start_time)
        
        process_steps = build_process_steps_from_turn(turn, runtime)
        
        response = ChatResponse(
            response=turn.get("response", "ขออภัยครับ ไม่สามารถสร้างคำตอบได้"),
            session_id=session_id,
            chat_mode=turn.get("chat_mode", "crm"),
            citations=turn.get("citations"),
            tool_calls=turn.get("tool_calls"),
            tool_results=turn.get("tool_results", []),
            intent=turn.get("intent"),
            process_steps=process_steps,
            runtime=runtime,
            debug_precompute=turn.get("debug_precompute"),
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(require_ai_assistant_access)
):
    """
    Streaming chat endpoint
    Streams process steps in real-time using Server-Sent Events (SSE)
    """
    async def generate():
        try:
            user_id = current_user.get("id")
            logger.info(f"Streaming chat request from user {user_id}: {request.message[:50]}...")
            
            # Get or create session
            session_id = request.session_id
            if not session_id:
                session_id = await get_active_session(user_id, first_message=request.message)
            else:
                await set_active_session(user_id, session_id)
            
            # Load chat history for context (exclude_current=False so we include all previous turns)
            chat_history = await load_chat_history(session_id, limit=20, exclude_current=False)
            history_context = format_history_for_llm(chat_history, max_tokens=2000) if chat_history else ""
            
            logger.info(f"Streaming: Loaded {len(chat_history)} messages from history for session {session_id}")
            
            # Start timing
            start_time = time.time()
            
            # Create initial state
            user_role = current_user.get("role", "staff")
            resolved_mode = (
                request.chat_mode
                if request.chat_mode
                else await get_chat_mode(user_id)
            )
            initial_state: AIAssistantState = {
                "user_message": request.message,
                "user_id": user_id,
                "user_role": user_role,
                "session_id": session_id,
                "chat_mode": resolved_mode,
                "chat_history": chat_history,  # NEW: Chat history for context
                "history_context": history_context,  # NEW: Formatted history context
                "intent": None,
                "confidence": 0.0,
                "tool_calls": [],
                "tool_results": [],
                "rag_results": [],
                "citations": [],
                "retry_count": 0,
                "max_retries": 0,  # Disabled: Retry mechanism causes incorrect parameters
                "previous_attempts": [],
                "data_quality": None,
                "quality_reason": None,
                "suggested_retry_params": None,
                "alternative_queries": [],
                "response": None,
                "error": None
            }
            
            # Node name mapping for display
            node_display_names = {
                "mode_gate": "เลือกโหมดแชท",
                "kb_guard": "ตรวจสอบโหมดเอกสาร",
                "router": "วิเคราะห์ Intent",
                "db_query": "ดึงข้อมูลจาก Database",
                "rag_query": "ค้นหาเอกสาร",
                "result_grader": "ตรวจสอบคุณภาพข้อมูล",
                "rpc_planner": "ปรับ Parameters",
                "generate_response": "สร้างคำตอบ",
                "clarify": "ถามซ้ำ"
            }
            
            final_state = None
            
            # Stream workflow execution
            async for event in process_message_stream(initial_state):
                node_name = event.get("node", "")
                node_state = event.get("state", {})
                elapsed = time.time() - start_time
                
                # Build step info
                step_info = {
                    "node": node_name,
                    "display_name": node_display_names.get(node_name, node_name),
                    "status": "processing",
                    "elapsed_time": elapsed,
                    "timestamp": event.get("timestamp", time.time())
                }
                
                # Extract preview based on node
                if node_name == "mode_gate":
                    mode = node_state.get("chat_mode", "crm")
                    step_info["preview"] = f"โหมด: {'CRM' if mode == 'crm' else 'เอกสารบริษัท'}"
                    step_info["status"] = "completed"

                elif node_name == "kb_guard":
                    if node_state.get("intent") == "kb_blocked":
                        step_info["preview"] = "คำถาม CRM — ให้สลับโหมด"
                    else:
                        step_info["preview"] = "เข้าสู่การค้นหาเอกสาร"
                    step_info["status"] = "completed"

                elif node_name == "router":
                    intent = node_state.get("intent", "unknown")
                    step_info["preview"] = f"Intent: {intent}"
                    step_info["status"] = "completed"
                
                elif node_name == "db_query":
                    tool_results = node_state.get("tool_results", [])
                    if tool_results:
                        first_tool = tool_results[0]
                        tool_name = first_tool.get("tool", "")
                        output = first_tool.get("output", {})
                        
                        if tool_name == "search_leads":
                            if isinstance(output, dict) and "data" in output:
                                data = output.get("data", {})
                                leads = data.get("leads", [])
                                count = len(leads) if isinstance(leads, list) else 0
                                step_info["preview"] = f"พบ {count} leads" if count > 0 else "ไม่พบข้อมูล"
                            else:
                                step_info["preview"] = "กำลังดึงข้อมูล..."
                        else:
                            step_info["preview"] = f"เรียกใช้ {tool_name}"
                    else:
                        step_info["preview"] = "กำลังประมวลผล..."
                    step_info["status"] = "completed"
                    step_info["tool_results"] = tool_results
                
                elif node_name == "result_grader":
                    data_quality = node_state.get("data_quality", "unknown")
                    quality_display = {
                        "sufficient": "ข้อมูลเพียงพอ",
                        "insufficient": "ข้อมูลไม่เพียงพอ",
                        "empty": "ไม่พบข้อมูล",
                        "error": "เกิดข้อผิดพลาด"
                    }.get(data_quality, "ตรวจสอบข้อมูล")
                    step_info["preview"] = quality_display
                    step_info["status"] = "completed"
                
                elif node_name == "rpc_planner":
                    retry_count = node_state.get("retry_count", 0)
                    step_info["preview"] = f"Retry #{retry_count}: ปรับ parameters"
                    step_info["status"] = "completed"
                
                elif node_name == "generate_response":
                    response = node_state.get("response", "")
                    step_info["preview"] = "สร้างคำตอบสำเร็จ" if response else "กำลังสร้างคำตอบ..."
                    step_info["status"] = "completed" if response else "processing"
                
                elif node_name == "rag_query":
                    rag_results = node_state.get("rag_results", [])
                    rag_meta = node_state.get("rag_retrieval_meta") or {}
                    count = len(rag_results) if isinstance(rag_results, list) else 0
                    ms = rag_meta.get("retrieval_ms")
                    step_info["preview"] = (
                        f"พบ {count} เอกสาร ({ms}ms)" if count > 0 and ms else
                        (f"พบ {count} เอกสาร" if count > 0 else "ไม่พบเอกสาร")
                    )
                    step_info["data"] = rag_meta
                    step_info["status"] = "completed"
                
                # Send SSE event
                yield f"data: {json.dumps(step_info)}\n\n"
                
                final_state = node_state
            
            # Send final response
            if final_state:
                runtime = time.time() - start_time
                final_response = {
                    "type": "final",
                    "response": final_state.get("response", ""),
                    "session_id": session_id,
                    "chat_mode": final_state.get("chat_mode", resolved_mode),
                    "citations": final_state.get("citations"),
                    "tool_calls": final_state.get("tool_calls"),
                    "tool_results": final_state.get("tool_results", []),  # NEW: Include tool_results
                    "intent": final_state.get("intent"),
                    "runtime": runtime,
                    "debug_precompute": final_state.get("debug_precompute"),
                    "rag_retrieval_meta": final_state.get("rag_retrieval_meta"),
                }
                yield f"data: {json.dumps(final_response)}\n\n"
                
                # Save messages to database (using new chat_history service)
                await save_message(
                    session_id=session_id,
                    role="user",
                    content=request.message,
                    metadata={"source": "web", "chat_mode": resolved_mode},
                )
                await save_message(
                    session_id=session_id,
                    role="assistant",
                    content=final_state.get("response", ""),
                    metadata={
                        "source": "web",
                        "chat_mode": final_state.get("chat_mode", resolved_mode),
                        "intent": final_state.get("intent"),
                        "citations": final_state.get("citations", []),
                        "tool_calls": final_state.get("tool_calls", []),
                        "rag": final_state.get("rag_retrieval_meta"),
                    },
                )
                from app.services.active_session import touch_session
                await touch_session(session_id)
        
        except Exception as e:
            logger.error(f"Streaming chat error: {e}")
            error_response = {
                "type": "error",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_response)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


async def create_or_get_session(user_id: str, first_message: str) -> str:
    """Deprecated: use active_session.get_active_session."""
    return await get_active_session(user_id, first_message=first_message)


def build_process_steps_from_turn(turn: dict, total_runtime: float) -> List[Dict[str, Any]]:
    """Build process steps from run_chat_turn result."""
    state = {
        "intent": turn.get("intent"),
        "tool_results": turn.get("tool_results", []),
        "retry_count": 0,
        "data_quality": None,
        "rag_results": [],
    }
    return build_process_steps(state, total_runtime)  # type: ignore[arg-type]


async def save_messages(session_id: str, user_message: str, state: AIAssistantState):
    """Save user and assistant messages to database"""
    try:
        await save_message(
            session_id=session_id,
            role="user",
            content=user_message,
            metadata={"source": "web"},
        )
        await save_message(
            session_id=session_id,
            role="assistant",
            content=state.get("response", ""),
            metadata={
                "source": "web",
                "intent": state.get("intent"),
                "citations": state.get("citations", []),
                "tool_calls": state.get("tool_calls", []),
            },
        )
    except Exception as e:
        logger.error(f"Error saving messages: {e}")


@router.get("/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    current_user: dict = Depends(require_ai_assistant_access),
    limit: int = 100
):
    """
    Get chat history for a session
    """
    try:
        user_id = current_user.get("id")
        logger.info(f"Loading chat history for session {session_id} (user: {user_id})")
        
        # Load messages from database
        messages = await load_chat_history(session_id, limit=limit, exclude_current=False)
        
        # Format messages for frontend
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "id": msg.get("id"),
                "role": msg.get("role"),
                "content": msg.get("content"),
                "citations": msg.get("metadata", {}).get("citations"),
                "tool_calls": msg.get("metadata", {}).get("tool_calls"),
                "source": msg.get("metadata", {}).get("source"),
                "created_at": msg.get("created_at")
            })
        
        return {
            "success": True,
            "session_id": session_id,
            "messages": formatted_messages,
            "count": len(formatted_messages)
        }
    
    except Exception as e:
        logger.error(f"Error loading chat history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def build_process_steps(state: AIAssistantState, total_runtime: float) -> List[Dict[str, Any]]:
    """
    Build process steps from state for frontend display
    """
    steps = []
    intent = state.get("intent", "unknown")
    tool_results = state.get("tool_results", [])
    retry_count = state.get("retry_count", 0)
    data_quality = state.get("data_quality")
    
    # Step 1: Router
    steps.append({
        "name": "router",
        "status": "completed",
        "duration": total_runtime * 0.1,  # Estimate 10% of time
        "preview": f"Intent: {intent}"
    })
    
    # Step 2: Query execution
    if intent == "db_query":
        query_status = "completed"
        if tool_results:
            # Check if any tool had errors
            has_error = any("error" in r.get("output", {}) for r in tool_results)
            if has_error:
                query_status = "error"
        
        tool_preview = ""
        if tool_results:
            first_tool = tool_results[0]
            tool_name = first_tool.get("tool", "")
            output = first_tool.get("output", {})
            
            # Generate preview
            if tool_name == "search_leads":
                leads = output.get("data", {}).get("leads", [])
                count = output.get("data", {}).get("stats", {}).get("returned", len(leads))
                tool_preview = f"พบ {count} leads" if count > 0 else "ไม่พบข้อมูล"
            elif tool_name == "get_daily_summary":
                new_leads = output.get("new_leads_today", 0)
                tool_preview = f"Lead ใหม่: {new_leads} รายการ"
            else:
                tool_preview = f"เรียกใช้ {tool_name}"
        
        steps.append({
            "name": "db_query",
            "status": query_status,
            "duration": total_runtime * 0.4,  # Estimate 40% of time
            "preview": tool_preview,
            "data": tool_results[0].get("output") if tool_results else None
        })
        
        # Step 3: Result Grader (if retry happened)
        if retry_count > 0 or data_quality:
            grader_status = "completed"
            if data_quality == "error":
                grader_status = "error"
            elif data_quality in ["empty", "insufficient"]:
                grader_status = "completed"  # Completed but suggested retry
            
            steps.append({
                "name": "result_grader",
                "status": grader_status,
                "duration": total_runtime * 0.2,
                "preview": f"Quality: {data_quality}" if data_quality else "ตรวจสอบข้อมูล"
            })
            
            # Step 4: Retry (if happened)
            if retry_count > 0:
                steps.append({
                    "name": "rpc_planner",
                    "status": "completed",
                    "duration": total_runtime * 0.1,
                    "preview": f"Retry #{retry_count}: ปรับ parameters"
                })
    
    elif intent == "rag_query":
        rag_meta = state.get("rag_retrieval_meta") or {}
        ms = rag_meta.get("retrieval_ms")
        count = len(state.get("rag_results", []))
        preview = f"พบ {count} เอกสาร"
        if ms:
            preview += f" ({ms}ms)"
        steps.append({
            "name": "rag_query",
            "status": "completed",
            "duration": total_runtime * 0.3,
            "preview": preview,
            "data": rag_meta,
        })
    
    # Removed direct_answer - general queries go through generate_response
    
    # Step: Generate Response
    steps.append({
        "name": "generate_response",
        "status": "completed",
        "duration": total_runtime * 0.3,  # Estimate 30% of time
        "preview": "สร้างคำตอบสำเร็จ"
    })
    
    return steps
