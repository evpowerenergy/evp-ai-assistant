"""
Chat History Service
Manages chat history loading, formatting, and saving
"""
from typing import List, Dict, Any, Optional
from app.services.supabase import get_supabase_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


def estimate_tokens(text: str) -> int:
    """
    Rough estimate of token count
    OpenAI: ~1 token ≈ 4 characters (for English/Thai)
    """
    if not text:
        return 0
    return len(text) // 4


async def load_chat_history(
    session_id: str,
    limit: int = 20,
    exclude_current: bool = True
) -> List[Dict[str, Any]]:
    """
    Load chat history from database
    
    Args:
        session_id: Session ID
        limit: Maximum number of messages to load
        exclude_current: If True, exclude the most recent message in DB (use False when
            building context for a new request, so all previous turns are included).
    
    Returns:
        List of messages in chronological order (oldest first)
    """
    try:
        supabase = get_supabase_client()
        
        query = supabase.table("chat_messages")\
            .select("*")\
            .eq("session_id", session_id)\
            .order("created_at", desc=False)  # Oldest first
        
        if exclude_current:
            # Get count first
            count_result = supabase.table("chat_messages")\
                .select("id", count="exact")\
                .eq("session_id", session_id)\
                .execute()
            
            total_count = count_result.count if hasattr(count_result, 'count') else 0
            
            if total_count > 0:
                # Exclude the last message (most recent)
                query = query.limit(limit + 1)
                result = query.execute()
                
                if result.data and len(result.data) > 1:
                    # Remove the last one (most recent)
                    return result.data[:-1]
                return []
        
        result = query.limit(limit).execute()
        
        if result.data:
            logger.info(f"Loaded {len(result.data)} messages from session {session_id}")
            return result.data
        else:
            logger.info(f"No messages found for session {session_id}")
            return []
    
    except Exception as e:
        logger.error(f"Error loading chat history: {e}")
        return []


def format_history_for_llm(
    messages: List[Dict[str, Any]],
    max_tokens: int = 2000
) -> str:
    """
    Format chat history for LLM context
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        max_tokens: Maximum tokens for history (default: 2000)
    
    Returns:
        Formatted history string
    """
    if not messages:
        return ""
    
    # Estimate tokens and trim if necessary
    trimmed_messages = trim_history_by_tokens(messages, max_tokens)
    
    # Format messages
    formatted_parts = []
    for msg in trimmed_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "user":
            formatted_parts.append(f"User: {content}")
        elif role == "assistant":
            formatted_parts.append(f"Assistant: {content}")
        elif role == "system":
            formatted_parts.append(f"System: {content}")
    
    if formatted_parts:
        return "\n\n".join(formatted_parts)
    return ""


def trim_history_by_tokens(
    messages: List[Dict[str, Any]],
    max_tokens: int
) -> List[Dict[str, Any]]:
    """
    Trim history to fit within token limit
    Keeps most recent messages
    
    Args:
        messages: List of messages (oldest first)
        max_tokens: Maximum tokens allowed
    
    Returns:
        Trimmed list of messages (oldest first)
    """
    if not messages:
        return []
    
    total_tokens = 0
    trimmed = []
    
    # Start from most recent (reverse order)
    for msg in reversed(messages):
        content = msg.get("content", "")
        msg_tokens = estimate_tokens(content)
        
        if total_tokens + msg_tokens <= max_tokens:
            trimmed.insert(0, msg)  # Insert at beginning (oldest first)
            total_tokens += msg_tokens
        else:
            # Stop if adding this message would exceed limit
            break
    
    if len(trimmed) < len(messages):
        logger.info(f"Trimmed history: {len(messages)} → {len(trimmed)} messages ({total_tokens} tokens)")
    
    return trimmed


async def get_recent_context(
    session_id: str,
    max_tokens: int = 2000,
    exclude_current: bool = True
) -> str:
    """
    Get recent chat context formatted for LLM
    
    Args:
        session_id: Session ID
        max_tokens: Maximum tokens for context
        exclude_current: Exclude the most recent message
    
    Returns:
        Formatted context string
    """
    messages = await load_chat_history(session_id, limit=50, exclude_current=exclude_current)
    return format_history_for_llm(messages, max_tokens=max_tokens)


async def save_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Save message to database
    
    Args:
        session_id: Session ID
        role: 'user' | 'assistant' | 'system'
        content: Message content
        metadata: Additional metadata (intent, tool_calls, citations, etc.)
    
    Returns:
        Message ID if successful, None otherwise
    """
    try:
        supabase = get_supabase_client()
        
        message_data = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        
        result = supabase.table("chat_messages").insert(message_data).execute()
        
        if result.data:
            message_id = result.data[0].get("id")
            logger.info(f"Saved {role} message to session {session_id}")
            return message_id
        else:
            logger.warning(f"Failed to save message: No data returned")
            return None
    
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        return None


async def update_session_title(
    session_id: str,
    title: str
) -> bool:
    """
    Update session title
    
    Args:
        session_id: Session ID
        title: New title
    
    Returns:
        True if successful, False otherwise
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table("chat_sessions")\
            .update({"title": title, "updated_at": "now()"})\
            .eq("id", session_id)\
            .execute()
        
        if result.data:
            logger.info(f"Updated session title: {session_id} → {title}")
            return True
        else:
            logger.warning(f"Failed to update session title: No data returned")
            return False
    
    except Exception as e:
        logger.error(f"Error updating session title: {e}")
        return False


async def get_session_message_count(session_id: str) -> int:
    """
    Get total message count for a session
    
    Args:
        session_id: Session ID
    
    Returns:
        Message count
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table("chat_messages")\
            .select("id", count="exact")\
            .eq("session_id", session_id)\
            .execute()
        
        return result.count if hasattr(result, 'count') else 0
    
    except Exception as e:
        logger.error(f"Error getting message count: {e}")
        return 0
