# 🧪 วิธีทดสอบ Tools และดู Process

## 📋 Overview

เอกสารนี้จะอธิบาย:
1. วิธีทดสอบ tools โดยตรง (ไม่ผ่าน LLM workflow)
2. Process ที่ LLM วิเคราะห์และสรุปข้อมูล
3. วิธีใช้ Postman สำหรับทดสอบ

---

## 🔧 วิธีที่ 1: ใช้ Test Tools API (แนะนำ)

### Endpoint
```
POST /api/v1/test-tools
```

### Headers
```
Authorization: Bearer <your-jwt-token>
Content-Type: application/json
```

### ตัวอย่าง Request

#### 1. ทดสอบ search_leads (ลีดวันนี้)
```json
{
  "tool_name": "search_leads",
  "parameters": {
    "query": "today",
    "user_role": "staff"
  }
}
```

#### 2. ทดสอบ get_daily_summary
```json
{
  "tool_name": "get_daily_summary",
  "parameters": {
    "date": "2026-01-17",
    "user_role": "admin"
  }
}
```

#### 3. ทดสอบ get_lead_status
```json
{
  "tool_name": "get_lead_status",
  "parameters": {
    "lead_name": "test lead"
  }
}
```

### ดู Available Tools
```
GET /api/v1/test-tools/list
```

---

## 📮 วิธีที่ 2: ใช้ Postman

### Setup Postman Collection

1. **Create New Request**
   - Method: `POST`
   - URL: `http://localhost:8000/api/v1/test-tools`

2. **Headers**
   ```
   Authorization: Bearer <your-token>
   Content-Type: application/json
   ```

3. **Body (JSON)**
   ```json
   {
     "tool_name": "search_leads",
     "parameters": {
       "query": "today",
       "user_role": "staff"
     }
   }
   ```

### วิธี Get JWT Token

1. Login ผ่าน frontend
2. เปิด Browser DevTools → Application → Local Storage
3. Copy `supabase.auth.token` หรือ `access_token`
4. ใช้ใน Postman Authorization header

---

## 🔄 Process: LLM วิเคราะห์และสรุปข้อมูล

### Flow Diagram

```
┌─────────────────────────────────────────┐
│ 1. Tool Execution (db_query_node)      │
│    - Execute selected tools             │
│    - Get raw data from database         │
│    Output: tool_results = [             │
│      {                                   │
│        "tool": "search_leads",          │
│        "output": {                       │
│          "success": true,                │
│          "data": {                        │
│            "leads": [...]                │
│          }                               │
│        }                                 │
│      }                                   │
│    ]                                     │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 2. Format Tool Results                  │
│    (format_tool_response function)      │
│    - Convert JSON to readable text      │
│    - Format based on tool type          │
│    Output: "พบ 5 leads:\n1. ..."        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 3. Build LLM Prompt                      │
│    - Include user message                │
│    - Include formatted tool results      │
│    - Add instructions                    │
│    Prompt:                                │
│    """                                   │
│    You are a helpful AI assistant...    │
│    User Question: ลีดวันนี้มีใครบ้าง     │
│    Context Information:                  │
│    พบ 5 leads:                           │
│    1. John Doe - โทร: 081-234-5678      │
│    ...                                   │
│    Instructions:                         │
│    - Answer in Thai                      │
│    - Use context information             │
│    """                                   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 4. LLM Response Generation               │
│    (LangChain ChatOpenAI)               │
│    - LLM reads formatted data            │
│    - Generates natural language          │
│    - Synthesizes information             │
│    Output: "วันนี้มี lead ทั้งหมด 5 รายการ:
│            1. John Doe (081-234-5678)   │
│            2. Jane Smith (082-345-6789) │
│            ..."                          │
└─────────────────────────────────────────┘
```

### Code Flow

#### Step 1: Tool Execution (`db_query_node.py`)
```python
# Execute tools selected by LLM
for tool_info in selected_tools:
    tool_name = tool_info.get("name", "")
    params = tool_info.get("parameters", {})
    
    if tool_name == "search_leads":
        result = await search_leads(...)
        tool_results.append({
            "tool": "search_leads",
            "output": result  # Raw database data
        })
```

#### Step 2: Format Results (`generate_response.py`)
```python
def format_tool_response(tool_results, user_message):
    # Convert JSON to readable text
    if tool_name == "search_leads":
        leads = output.get("data", {}).get("leads", [])
        # Format: "พบ 5 leads:\n1. John Doe - โทร: 081-..."
        return formatted_text
```

#### Step 3: LLM Synthesis (`generate_response.py`)
```python
# Build prompt with formatted data
prompt = f"""
User Question: {user_message}

Context Information:
{formatted_context}  # ← Formatted tool results

Instructions:
- Answer in Thai
- Use context information
"""

# Call LLM
llm_response = await llm.ainvoke(prompt)
response = llm_response.content
```

---

## 📊 ตัวอย่าง: "ลีดวันนี้มีใครบ้าง"

### Step 1: Tool Execution
```json
{
  "tool": "search_leads",
  "output": {
    "success": true,
    "data": {
      "leads": [
        {
          "id": 1,
          "full_name": "John Doe",
          "tel": "081-234-5678",
          "status": "active"
        },
        {
          "id": 2,
          "full_name": "Jane Smith",
          "tel": "082-345-6789",
          "status": "active"
        }
      ],
      "stats": {
        "total": 2,
        "returned": 2
      }
    }
  }
}
```

### Step 2: Format (format_tool_response)
```
พบ 2 leads:
1. John Doe - โทร: 081-234-5678 (สถานะ: active)
2. Jane Smith - โทร: 082-345-6789 (สถานะ: active)
```

### Step 3: LLM Prompt
```
User Question: ลีดวันนี้มีใครบ้าง

Context Information:
พบ 2 leads:
1. John Doe - โทร: 081-234-5678 (สถานะ: active)
2. Jane Smith - โทร: 082-345-6789 (สถานะ: active)

Instructions:
- Answer in Thai
- Use context information
- Be friendly and natural
```

### Step 4: LLM Response
```
วันนี้มี lead ทั้งหมด 2 รายการครับ:

1. **John Doe** - เบอร์โทร: 081-234-5678 (สถานะ: active)
2. **Jane Smith** - เบอร์โทร: 082-345-6789 (สถานะ: active)

ต้องการข้อมูลเพิ่มเติมเกี่ยวกับ lead ใดเป็นพิเศษไหมครับ?
```

---

## 🧪 Testing Checklist

### ✅ Test Tools Directly
- [ ] Test `search_leads` with "today"
- [ ] Test `get_daily_summary` with date
- [ ] Test `get_lead_status` with lead name
- [ ] Verify data format

### ✅ Test Full Flow
- [ ] Send message: "ลีดวันนี้มีใครบ้าง"
- [ ] Check logs for tool execution
- [ ] Verify tool results in state
- [ ] Check LLM response format

### ✅ Test LLM Analysis
- [ ] Check formatted context
- [ ] Verify prompt structure
- [ ] Check response quality

---

## 📝 Postman Collection Example

```json
{
  "info": {
    "name": "AI Assistant Tools Test",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Test search_leads",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{token}}"
          },
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"tool_name\": \"search_leads\",\n  \"parameters\": {\n    \"query\": \"today\",\n    \"user_role\": \"staff\"\n  }\n}"
        },
        "url": {
          "raw": "http://localhost:8000/api/v1/test-tools",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "v1", "test-tools"]
        }
      }
    },
    {
      "name": "List Available Tools",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "http://localhost:8000/api/v1/test-tools/list",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "v1", "test-tools", "list"]
        }
      }
    }
  ]
}
```

---

## 🔍 Debug Tips

### 1. ดู Logs
```bash
# Backend logs จะแสดง:
# - Tool execution
# - Tool results
# - Formatted context
# - LLM prompt
# - LLM response
```

### 2. ตรวจสอบ State
- ดู `tool_results` ใน state
- ตรวจสอบ `formatted_context` ก่อนส่ง LLM
- ดู prompt ที่ส่งไป LLM

### 3. Test Individual Components
- Test tools → `/api/v1/test-tools`
- Test LLM → ดู logs ใน `generate_response_node`
- Test full flow → `/api/v1/chat`
