"""
DB Query Node
Executes database RPC tools selected by LLM
"""
from typing import Dict, Any
from app.orchestrator.state import AIAssistantState
from app.tools.db_tools import (
    get_daily_summary,
    search_leads,
    get_sales_closed,
    get_sales_unsuccessful,
    get_lead_detail,
    get_appointments,
    get_sales_team_list,
    get_sales_team_overview,
    get_service_appointments,
    get_sales_performance,
    get_sales_docs,
    get_permit_requests
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def db_query_node(state: AIAssistantState) -> AIAssistantState:
    """
    Node that executes database tools selected by LLM
    """
    try:
        user_message = state.get("user_message", "")
        user_id = state.get("user_id", "")
        user_role = state.get("user_role", "staff")
        selected_tools = state.get("selected_tools", [])
        tool_parameters = state.get("tool_parameters", {})
        
        logger.info(f"{'='*60}")
        logger.info(f"🔍 [STEP 2/4] DB Query Node: Executing tools")
        logger.info(f"   User ID: {user_id}")
        logger.info(f"   Message: {user_message}")
        logger.info(f"   Selected Tools: {[t.get('name') for t in selected_tools]}")
        logger.info(f"{'='*60}")
        
        tool_results = []
        
        # Execute tools selected by LLM
        if selected_tools:
            for tool_info in selected_tools:
                tool_name = tool_info.get("name", "")
                params = tool_info.get("parameters", {})
                
                try:
                    logger.info(f"📋 Executing tool: {tool_name}")
                    logger.info(f"   Parameters: {params}")
                    
                    # Map tool names to actual functions
                    if tool_name == "get_daily_summary":
                        date = params.get("date")
                        result = await get_daily_summary(user_id, date=date, user_role=user_role)
                        tool_results.append({
                            "tool": "get_daily_summary",
                            "input": {"date": date, "user_role": user_role},
                            "output": result
                        })
                    
                    elif tool_name == "search_leads":
                        query = params.get("query", user_message)
                        # IMPORTANT: Keep query as dict if it's a dict (don't convert to string)
                        if not isinstance(query, dict):
                            query = str(query) if query is not None else str(user_message)
                        date_from = params.get("date_from")
                        date_to = params.get("date_to")
                        status = params.get("status")
                        platform = params.get("platform")  # PLATFORM RULE: from message or conversation context
                        result = await search_leads(
                            query=query,
                            user_id=user_id,
                            filters=None,
                            user_role=user_role,
                            date_from=date_from,
                            date_to=date_to,
                            status=status,
                            platform=platform,
                        )
                        tool_results.append({
                            "tool": "search_leads",
                            "input": {"query": query, "status": status, "date_from": date_from, "date_to": date_to, "platform": platform},
                            "output": result
                        })

                    elif tool_name == "get_sales_closed":
                        date_from = params.get("date_from")
                        date_to = params.get("date_to")
                        sales_member_id = params.get("sales_member_id")
                        platform = params.get("platform")
                        result = await get_sales_closed(
                            user_id=user_id,
                            date_from=date_from,
                            date_to=date_to,
                            sales_member_id=sales_member_id,
                            user_role=user_role,
                            platform=platform,
                        )
                        tool_results.append({
                            "tool": "get_sales_closed",
                            "input": {"date_from": date_from, "date_to": date_to, "sales_member_id": sales_member_id, "platform": platform},
                            "output": result
                        })

                    elif tool_name == "get_sales_unsuccessful":
                        date_from = params.get("date_from")
                        date_to = params.get("date_to")
                        sales_member_id = params.get("sales_member_id")
                        platform = params.get("platform")
                        result = await get_sales_unsuccessful(
                            user_id=user_id,
                            date_from=date_from,
                            date_to=date_to,
                            sales_member_id=sales_member_id,
                            user_role=user_role,
                            platform=platform,
                        )
                        tool_results.append({
                            "tool": "get_sales_unsuccessful",
                            "input": {"date_from": date_from, "date_to": date_to, "sales_member_id": sales_member_id, "platform": platform},
                            "output": result
                        })
                    
                    elif tool_name == "get_lead_detail":
                        lead_id = params.get("lead_id")
                        if lead_id:
                            result = await get_lead_detail(lead_id=lead_id, user_id=user_id, include_logs=True)
                            tool_results.append({
                                "tool": "get_lead_detail",
                                "input": {"lead_id": lead_id},
                                "output": result
                            })
                        else:
                            logger.warning(f"   ⚠️  Missing lead_id parameter for get_lead_detail")
                    
                    elif tool_name == "get_appointments":
                        appointment_type = params.get("appointment_type")
                        date_from = params.get("date_from")
                        date_to = params.get("date_to")
                        sales_member_id = params.get("sales_member_id")
                        result = await get_appointments(
                            user_id=user_id,
                            filters=None,
                            user_role=user_role,
                            date_from=date_from,
                            date_to=date_to,
                            appointment_type=appointment_type,
                            sales_member_id=sales_member_id
                        )
                        tool_results.append({
                            "tool": "get_appointments",
                            "input": {"appointment_type": appointment_type, "date_from": date_from, "date_to": date_to, "sales_member_id": sales_member_id},
                            "output": result
                        })
                    
                    elif tool_name == "get_sales_team_list":
                        status = params.get("status", "active")
                        # If status is 'all', pass 'all' to function (it will convert to None)
                        # RPC function now supports p_status = NULL to get all statuses
                        result = await get_sales_team_list(
                            user_id=user_id,
                            category=None,
                            status=status,  # Pass 'all' if requested, function will handle it
                            user_role=user_role
                        )
                        tool_results.append({
                            "tool": "get_sales_team_list",
                            "input": {"status": status},
                            "output": result
                        })
                    
                    elif tool_name == "get_sales_team_overview":
                        date_from = params.get("date_from")
                        date_to = params.get("date_to")
                        sales_id = params.get("sales_id")
                        period = params.get("period", "month")
                        if not date_from or not date_to:
                            try:
                                from app.utils.date_extractor import extract_date_range
                                df, dt = extract_date_range(user_message)
                                if df and dt:
                                    date_from = date_from or df
                                    date_to = date_to or dt
                                    logger.info(f"   📅 Backfill date range for get_sales_team_overview: {date_from} to {date_to}")
                            except Exception as e:
                                logger.warning(f"   ⚠️ Failed to backfill date range for get_sales_team_overview: {e}")
                        result = await get_sales_team_overview(
                            user_id=user_id,
                            user_role=user_role,
                            date_from=date_from,
                            date_to=date_to,
                            sales_id=sales_id,
                            period=period,
                        )
                        tool_results.append({
                            "tool": "get_sales_team_overview",
                            "input": {"date_from": date_from, "date_to": date_to, "sales_id": sales_id, "period": period},
                            "output": result
                        })

                    # Backward compatibility: old tool names map to consolidated overview tool
                    elif tool_name in ["get_team_kpi", "get_sales_team", "get_sales_team_data"]:
                        date_from = params.get("date_from")
                        date_to = params.get("date_to")
                        if not date_from or not date_to:
                            try:
                                from app.utils.date_extractor import extract_date_range
                                df, dt = extract_date_range(user_message)
                                if df and dt:
                                    date_from = date_from or df
                                    date_to = date_to or dt
                                    logger.info(f"   📅 Backfill date range for legacy sales team tool ({tool_name}): {date_from} to {date_to}")
                            except Exception as e:
                                logger.warning(f"   ⚠️ Failed to backfill date range for legacy sales team tool ({tool_name}): {e}")
                        result = await get_sales_team_overview(
                            user_id=user_id,
                            user_role=user_role,
                            date_from=date_from,
                            date_to=date_to,
                        )
                        tool_results.append({
                            "tool": "get_sales_team_overview",
                            "input": {"date_from": date_from, "date_to": date_to, "source_tool": tool_name},
                            "output": result
                        })
                    
                    elif tool_name == "get_service_appointments":
                        appointment_type = params.get("appointment_type", "all")
                        date_from = params.get("date_from")
                        date_to = params.get("date_to")
                        result = await get_service_appointments(
                            user_id=user_id,
                            filters=None,
                            date_from=date_from,
                            date_to=date_to,
                            appointment_type=appointment_type
                        )
                        tool_results.append({
                            "tool": "get_service_appointments",
                            "input": {"appointment_type": appointment_type, "date_from": date_from, "date_to": date_to},
                            "output": result
                        })
                    
                    elif tool_name == "get_sales_performance":
                        sales_id = params.get("sales_id")
                        if sales_id:
                            date_from = params.get("date_from")
                            date_to = params.get("date_to")
                            period = params.get("period", "month")
                            result = await get_sales_performance(
                                sales_id=sales_id,
                                user_id=user_id,
                                user_role=user_role,
                                date_from=date_from,
                                date_to=date_to,
                                period=period
                            )
                            tool_results.append({
                                "tool": "get_sales_performance",
                                "input": {"sales_id": sales_id, "date_from": date_from, "date_to": date_to, "period": period},
                                "output": result
                            })
                        else:
                            logger.warning(f"   ⚠️  Missing sales_id parameter for get_sales_performance")
                    
                    elif tool_name == "get_sales_docs":
                        query = params.get("query")
                        document_number = params.get("document_number")
                        doc_type = params.get("doc_type")
                        if not document_number and query:
                            import re
                            m_doc = re.search(r"([A-Za-z]{2,5}\d{6,})", str(query), flags=re.IGNORECASE)
                            if m_doc:
                                document_number = m_doc.group(1)
                        date_from = params.get("date_from")
                        date_to = params.get("date_to")
                        limit = params.get("limit", 100)
                        result = await get_sales_docs(
                            user_id=user_id,
                            filters=None,
                            query=query,
                            document_number=document_number,
                            doc_type=doc_type,
                            date_from=date_from,
                            date_to=date_to,
                            limit=limit
                        )
                        tool_results.append({
                            "tool": "get_sales_docs",
                            "input": {"query": query, "document_number": document_number, "doc_type": doc_type, "date_from": date_from, "date_to": date_to, "limit": limit},
                            "output": result
                        })

                    # Backward compatibility: old quotations tool -> unified sales docs tool
                    elif tool_name == "get_quotations":
                        query = params.get("query")
                        document_number = params.get("document_number")
                        date_from = params.get("date_from")
                        date_to = params.get("date_to")
                        limit = params.get("limit", 100)
                        result = await get_sales_docs(
                            user_id=user_id,
                            filters=None,
                            query=query,
                            document_number=document_number,
                            doc_type="QT",
                            date_from=date_from,
                            date_to=date_to,
                            limit=limit,
                        )
                        tool_results.append({
                            "tool": "get_sales_docs",
                            "input": {"query": query, "document_number": document_number, "doc_type": "QT", "date_from": date_from, "date_to": date_to, "limit": limit, "source_tool": "get_quotations"},
                            "output": result
                        })
                    
                    elif tool_name == "get_permit_requests":
                        date_from = params.get("date_from")
                        date_to = params.get("date_to")
                        limit = params.get("limit", 100)
                        result = await get_permit_requests(
                            user_id=user_id,
                            filters=None,
                            date_from=date_from,
                            date_to=date_to,
                            limit=limit
                        )
                        tool_results.append({
                            "tool": "get_permit_requests",
                            "input": {"date_from": date_from, "date_to": date_to, "limit": limit},
                            "output": result
                        })
                    
                    else:
                        logger.warning(f"   ⚠️  Unknown tool: {tool_name}")
                    
                    logger.info(f"   ✅ Tool executed successfully")
                    
                except Exception as e:
                    logger.error(f"   ❌ Error executing tool {tool_name}: {e}")
                    tool_results.append({
                        "tool": tool_name,
                        "input": params,
                        "output": {"error": str(e)}
                    })
        else:
            logger.warning(f"   ⚠️  No tools selected by LLM - this shouldn't happen for db_query intent")
        
        # Update state
        state["tool_calls"] = tool_results
        state["tool_results"] = tool_results
        
        logger.info(f"{'='*60}")
        logger.info(f"✅ [STEP 3/4] DB Query Node: Completed")
        logger.info(f"   Tool calls: {len(tool_results)}")
        logger.info(f"   Tools executed: {[t.get('tool') for t in tool_results]}")
        logger.info(f"{'='*60}")
        
        return state
    
    except Exception as e:
        logger.error(f"DB Query Node error: {e}")
        state["error"] = str(e)
        return state
