"""
Chat API Endpoint
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
import asyncio
import time
import json
from app.core.auth import require_ai_assistant_access
from app.orchestrator.state import AIAssistantState
from app.services.active_session import assert_session_owner, get_active_session, set_active_session
from app.services.chat_mode import get_chat_mode, set_chat_mode
from app.services.chat_processor import run_chat_turn
from app.services.chat_history import load_chat_history, save_message
from app.engines.hermes import HermesEngine
from app.config import settings
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
    engine: Optional[str] = None
    model: Optional[str] = None
    fallback_used: bool = False
    request_id: Optional[str] = None
    runtime_logs: Optional[List[Dict[str, Any]]] = None


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
            engine=turn.get("engine"),
            model=turn.get("model"),
            fallback_used=bool(turn.get("fallback_used")),
            request_id=turn.get("request_id"),
            runtime_logs=turn.get("runtime_logs", []),
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(require_ai_assistant_access)
):
    """SSE endpoint using the same AgentService path as non-stream chat."""
    async def generate():
        try:
            user_id = current_user.get("id")
            logger.info(f"Streaming chat request from user {user_id}: {request.message[:50]}...")
            session_id = request.session_id
            if not session_id:
                session_id = await get_active_session(user_id, first_message=request.message)
            else:
                await set_active_session(user_id, session_id)
            await assert_session_owner(user_id, session_id)
            start_time = time.time()
            yield f"data: {json.dumps({'type': 'run.started', 'node': 'agent', 'display_name': 'กำลังประมวลผล', 'status': 'processing', 'session_id': session_id})}\n\n"
            # Hermes writes a sanitized local execution log. Poll only the
            # bytes appended after this request starts and forward new events
            # over SSE while the turn is still running.
            log_offset = HermesEngine._log_offset()
            skill_baseline = HermesEngine._skill_usage_snapshot()
            emitted_skills: set[tuple[str, str]] = set()
            turn_task = asyncio.create_task(
                run_chat_turn(
                    user_id=user_id,
                    user_role=current_user.get("role", "staff"),
                    message=request.message,
                    session_id=session_id,
                    source="web",
                    chat_mode=request.chat_mode,
                )
            )
            emitted_logs = 0
            while not turn_task.done():
                await asyncio.sleep(0.75)
                if settings.AI_PRIMARY_ENGINE.strip().lower() != "hermes":
                    continue
                live_logs = HermesEngine._runtime_logs(log_offset)
                for event in live_logs[emitted_logs:]:
                    yield f"data: {json.dumps({'type': 'runtime.log', 'event': event})}\n\n"
                emitted_logs = len(live_logs)
                for skill_name, marker in HermesEngine._skill_usage_snapshot().items():
                    skill_key = (skill_name, marker)
                    if marker <= skill_baseline.get(skill_name, "") or skill_key in emitted_skills:
                        continue
                    emitted_skills.add(skill_key)
                    skill_event = {
                        "timestamp": marker,
                        "type": "skill",
                        "name": skill_name,
                        "status": "completed",
                    }
                    yield f"data: {json.dumps({'type': 'runtime.log', 'event': skill_event})}\n\n"
            turn = await turn_task
            final_response = {
                "type": "final",
                "event": "run.completed",
                **turn,
                "runtime": turn.get("runtime") or (time.time() - start_time),
            }
            yield f"data: {json.dumps(final_response)}\n\n"
        
        except Exception as e:
            logger.error(f"Streaming chat error: {e}")
            error_response = {
                "type": "error",
                "error": "ไม่สามารถประมวลผลคำขอได้ กรุณาลองใหม่อีกครั้ง",
                "error_class": type(e).__name__,
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
        await assert_session_owner(user_id, session_id)
        
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
    
    except HTTPException:
        raise
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
