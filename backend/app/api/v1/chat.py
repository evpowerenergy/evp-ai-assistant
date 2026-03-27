"""
Chat API Endpoint
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import uuid4
import time
import json
from app.core.auth import get_current_user
from app.core.audit import log_chat_request, log_tool_call
from app.orchestrator.graph import process_message, process_message_stream
from app.orchestrator.state import AIAssistantState
from app.services.supabase import get_supabase_client
from app.services.chat_history import load_chat_history, format_history_for_llm, save_message
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    session_id: Optional[str] = None
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    session_id: str
    citations: Optional[List[str]] = None
    tool_calls: Optional[List[dict]] = None
    tool_results: Optional[List[dict]] = None  # NEW: Tool results with input/output
    intent: Optional[str] = None
    process_steps: Optional[List[Dict[str, Any]]] = None  # NEW: Process steps
    runtime: Optional[float] = None  # NEW: Total runtime in seconds
    debug_precompute: Optional[Dict[str, Any]] = None  # NEW: Pre-computed summaries for UI debug


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Main chat endpoint
    Processes user message and returns AI response
    """
    try:
        user_id = current_user.get("id")
        logger.info(f"Chat request from user {user_id}: {request.message[:50]}...")
        
        # Get or create session
        session_id = request.session_id
        if not session_id:
            session_id = await create_or_get_session(user_id, request.message)
        
        # Load chat history for context (exclude_current=False so we include all previous turns)
        chat_history = await load_chat_history(session_id, limit=20, exclude_current=False)
        history_context = format_history_for_llm(chat_history, max_tokens=2000) if chat_history else ""
        
        logger.info(f"Loaded {len(chat_history)} messages from history for session {session_id}")
        
        # Start timing
        start_time = time.time()
        
        # Create initial state
        user_role = current_user.get("role", "staff")
        initial_state: AIAssistantState = {
            "user_message": request.message,
            "user_id": user_id,
            "user_role": user_role,  # Add user role to state
            "session_id": session_id,
            "chat_history": chat_history,  # NEW: Chat history for context
            "history_context": history_context,  # NEW: Formatted history context
            "intent": None,
            "confidence": 0.0,
            "tool_calls": [],
            "tool_results": [],
            "rag_results": [],
            "citations": [],
            # Retry management (NEW)
            "retry_count": 0,
            "max_retries": 0,  # Disabled: Retry mechanism causes incorrect parameters
            "previous_attempts": [],
            # Data quality (NEW)
            "data_quality": None,
            "quality_reason": None,
            "suggested_retry_params": None,
            "alternative_queries": [],
            # Final response
            "response": None,
            "error": None
        }
        
        # Process message through workflow
        result_state = await process_message(initial_state)
        
        # Calculate runtime
        runtime = time.time() - start_time
        
        # Save messages to database (using new chat_history service)
        await save_message(
            session_id=session_id,
            role="user",
            content=request.message,
            metadata={}
        )
        await save_message(
            session_id=session_id,
            role="assistant",
            content=result_state.get("response", ""),
            metadata={
                "intent": result_state.get("intent"),
                "citations": result_state.get("citations", []),
                "tool_calls": result_state.get("tool_calls", [])
            }
        )
        
        # Log tool calls
        for tool_call in result_state.get("tool_calls", []):
            await log_tool_call(
                user_id=user_id,
                tool_name=tool_call.get("tool", "unknown"),
                tool_input=tool_call.get("input", {}),
                tool_output=tool_call.get("output", {})
            )
        
        # Log request
        await log_chat_request(
            user_id=user_id,
            session_id=session_id,
            message=request.message,
            response=result_state.get("response"),
            tool_calls=result_state.get("tool_calls")
        )
        
        # Build process steps from state
        process_steps = build_process_steps(result_state, runtime)
        
        # Build response
        response = ChatResponse(
            response=result_state.get("response", "ขออภัยครับ ไม่สามารถสร้างคำตอบได้"),
            session_id=session_id,
            citations=result_state.get("citations"),
            tool_calls=result_state.get("tool_calls"),
            tool_results=result_state.get("tool_results", []),  # NEW: Include tool_results
            intent=result_state.get("intent"),
            process_steps=process_steps,
            runtime=runtime,
            debug_precompute=result_state.get("debug_precompute"),
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
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
                session_id = await create_or_get_session(user_id, request.message)
            
            # Load chat history for context (exclude_current=False so we include all previous turns)
            chat_history = await load_chat_history(session_id, limit=20, exclude_current=False)
            history_context = format_history_for_llm(chat_history, max_tokens=2000) if chat_history else ""
            
            logger.info(f"Streaming: Loaded {len(chat_history)} messages from history for session {session_id}")
            
            # Start timing
            start_time = time.time()
            
            # Create initial state
            user_role = current_user.get("role", "staff")
            initial_state: AIAssistantState = {
                "user_message": request.message,
                "user_id": user_id,
                "user_role": user_role,
                "session_id": session_id,
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
                if node_name == "router":
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
                    count = len(rag_results) if isinstance(rag_results, list) else 0
                    step_info["preview"] = f"พบ {count} เอกสาร" if count > 0 else "ไม่พบเอกสาร"
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
                    "citations": final_state.get("citations"),
                    "tool_calls": final_state.get("tool_calls"),
                    "tool_results": final_state.get("tool_results", []),  # NEW: Include tool_results
                    "intent": final_state.get("intent"),
                    "runtime": runtime,
                    "debug_precompute": final_state.get("debug_precompute"),
                }
                yield f"data: {json.dumps(final_response)}\n\n"
                
                # Save messages to database (using new chat_history service)
                await save_message(
                    session_id=session_id,
                    role="user",
                    content=request.message,
                    metadata={}
                )
                await save_message(
                    session_id=session_id,
                    role="assistant",
                    content=final_state.get("response", ""),
                    metadata={
                        "intent": final_state.get("intent"),
                        "citations": final_state.get("citations", []),
                        "tool_calls": final_state.get("tool_calls", [])
                    }
                )
        
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
    """Create or get existing session"""
    try:
        supabase = get_supabase_client()
        
        # Create new session
        session_data = {
            "id": str(uuid4()),
            "user_id": user_id,
            "title": first_message[:50] + ("..." if len(first_message) > 50 else "")
        }
        
        result = supabase.table("chat_sessions").insert(session_data).execute()
        
        if result.data:
            return result.data[0].get("id")
        else:
            raise Exception("Failed to create session")
    
    except Exception as e:
        logger.error(f"Session creation error: {e}")
        # Return a temporary session ID
        return str(uuid4())


async def save_messages(session_id: str, user_message: str, state: AIAssistantState):
    """Save user and assistant messages to database"""
    try:
        supabase = get_supabase_client()
        
        # Save user message
        user_msg = {
            "id": str(uuid4()),
            "session_id": session_id,
            "role": "user",
            "content": user_message,
            "metadata": {}
        }
        supabase.table("chat_messages").insert(user_msg).execute()
        
        # Save assistant message
        assistant_msg = {
            "id": str(uuid4()),
            "session_id": session_id,
            "role": "assistant",
            "content": state.get("response", ""),
            "metadata": {
                "intent": state.get("intent"),
                "citations": state.get("citations", []),
                "tool_calls": state.get("tool_calls", [])
            }
        }
        supabase.table("chat_messages").insert(assistant_msg).execute()
    
    except Exception as e:
        logger.error(f"Error saving messages: {e}")


@router.get("/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    current_user: dict = Depends(get_current_user),
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
        steps.append({
            "name": "rag_query",
            "status": "completed",
            "duration": total_runtime * 0.3,
            "preview": f"พบ {len(state.get('rag_results', []))} เอกสาร"
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
