"""
Test Tools API Endpoint
สำหรับทดสอบ tools โดยตรง (ไม่ผ่าน LLM workflow)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.core.auth import require_ai_assistant_access
from app.tools.db_tools import (
    get_daily_summary,
    search_leads,
    get_customer_info,
    get_team_kpi
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class TestToolRequest(BaseModel):
    """Request model for testing tools"""
    tool_name: str
    parameters: Dict[str, Any]


@router.post("/test-tools")
async def test_tools(
    request: TestToolRequest,
    current_user: dict = Depends(require_ai_assistant_access)
):
    """
    Test database tools directly
    
    Example requests:
    
    1. Test search_leads:
    {
        "tool_name": "search_leads",
        "parameters": {
            "query": "today",
            "user_role": "staff"
        }
    }
    
    2. Test get_daily_summary:
    {
        "tool_name": "get_daily_summary",
        "parameters": {
            "date": "2026-01-17",
            "user_role": "admin"
        }
    }
    
    3. Test get_customer_info:
    {
        "tool_name": "get_customer_info",
        "parameters": {
            "customer_name": "test customer"
        }
    }
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role", "staff")
        
        logger.info(f"🧪 Testing tool: {request.tool_name}")
        logger.info(f"   Parameters: {request.parameters}")
        logger.info(f"   User ID: {user_id}, Role: {user_role}")
        
        # Execute tool based on name
        result = None
        
        if request.tool_name == "search_leads":
            query = request.parameters.get("query", "")
            result = await search_leads(
                query=query,
                user_id=user_id,
                filters=None,
                user_role=request.parameters.get("user_role", user_role)
            )
        
        elif request.tool_name == "get_daily_summary":
            date = request.parameters.get("date")
            result = await get_daily_summary(
                user_id=user_id,
                date=date,
                user_role=request.parameters.get("user_role", user_role)
            )
        
        elif request.tool_name == "get_customer_info":
            customer_name = request.parameters.get("customer_name", "")
            if not customer_name:
                raise HTTPException(status_code=400, detail="customer_name is required")
            result = await get_customer_info(customer_name, user_id)
        
        elif request.tool_name == "get_team_kpi":
            team_id = request.parameters.get("team_id")
            result = await get_team_kpi(user_id, team_id)
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown tool: {request.tool_name}. Available: search_leads, get_daily_summary, get_customer_info, get_team_kpi"
            )
        
        logger.info(f"✅ Tool executed successfully")
        logger.info(f"   Result: {result}")
        
        return {
            "success": True,
            "tool_name": request.tool_name,
            "parameters": request.parameters,
            "result": result,
            "user_id": user_id,
            "user_role": user_role
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Tool test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-tools/list")
async def list_available_tools():
    """
    List all available tools with their parameters
    """
    tools = [
        {
            "name": "search_leads",
            "description": "Search or list leads based on query",
            "parameters": {
                "query": "string (required) - Search query (e.g., 'today', 'all leads')",
                "user_role": "string (optional) - User role for access control"
            },
            "example": {
                "tool_name": "search_leads",
                "parameters": {
                    "query": "today",
                    "user_role": "staff"
                }
            }
        },
        {
            "name": "get_daily_summary",
            "description": "Get daily summary statistics",
            "parameters": {
                "date": "string (optional) - Date in YYYY-MM-DD format",
                "user_role": "string (optional) - User role for access control"
            },
            "example": {
                "tool_name": "get_daily_summary",
                "parameters": {
                    "date": "2026-01-17",
                    "user_role": "admin"
                }
            }
        },
        {
            "name": "get_customer_info",
            "description": "Get customer information by name",
            "parameters": {
                "customer_name": "string (required) - Name of the customer"
            },
            "example": {
                "tool_name": "get_customer_info",
                "parameters": {
                    "customer_name": "ABC Company"
                }
            }
        },
        {
            "name": "get_team_kpi",
            "description": "Get team KPI and performance metrics",
            "parameters": {
                "team_id": "integer (optional) - Team ID"
            },
            "example": {
                "tool_name": "get_team_kpi",
                "parameters": {
                    "team_id": 1
                }
            }
        }
    ]
    
    return {
        "available_tools": tools,
        "endpoint": "/api/v1/test-tools",
        "method": "POST"
    }
