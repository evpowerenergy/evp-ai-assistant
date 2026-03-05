# 🏗️ Final Architecture: LLM-Based Multi-Stage System

## 🎯 Architecture Overview

```
User Message
    ↓
┌─────────────────────────────────────────────┐
│ Stage 1: LLM Intent Analysis & Tool Select │
│ - Analyze intent (structured output)        │
│ - Extract entities (NER)                    │
│ - Select tools (function calling)           │
│ - Build tool parameters                     │
└─────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ Stage 2: Tool Execution                     │
│ - Execute selected tools (parallel if able) │
│ - Handle errors & retries                   │
│ - Collect results                           │
└─────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ Stage 3: LLM Response Generation            │
│ - Format data based on query type           │
│ - Generate natural language response        │
│ - Add context & citations                   │
└─────────────────────────────────────────────┘
                ↓
Response
```

## 🔧 Implementation Details

### Stage 1: LLM Intent Analysis (Function Calling)

**LLM Call #1: Intent + Tool Selection**

```python
# LLM analyzes message and selects tools via function calling
intent_analysis = await llm.analyze_with_functions(
    message=user_message,
    functions=[
        get_lead_status,
        get_daily_summary,
        search_leads,
        get_customer_info,
        get_team_kpi,
        vector_search  # RAG
    ]
)

# Returns:
# {
#     "intent": "db_query",
#     "entities": {"date": "today", "type": "leads"},
#     "selected_tools": [
#         {"name": "search_leads", "parameters": {"date": "today"}}
#     ],
#     "confidence": 0.95
# }
```

### Stage 2: Tool Execution

```python
# Execute tools in parallel if independent
tool_results = await execute_tools_parallel(
    intent_analysis.selected_tools
)
```

### Stage 3: LLM Response Generation

**LLM Call #2: Synthesize Response**

```python
# LLM generates natural language response
response = await llm.generate_response(
    user_message=user_message,
    intent=intent_analysis.intent,
    tool_results=tool_results,
    context=session_context
)
```

## 📊 Benefits

✅ **Flexible**: LLM understands context better than rules  
✅ **Efficient**: Only 2 LLM calls per request  
✅ **Maintainable**: Add new tools easily (just add to function list)  
✅ **Accurate**: Better entity extraction and intent understanding

## 🔄 LangGraph Flow

```
router (LLM Intent Analysis)
    ↓
┌──────────┬──────────┬──────────┐
│ db_query │ rag_query│ clarify  │
└────┬─────┴────┬─────┴────┬─────┘
     │          │          │
     └──────┬───┴───┬──────┘
            ↓
    generate_response (LLM)
            ↓
           END
```
