# 📮 Postman Setup Guide

## 🔑 Step 1: Get JWT Token

### วิธีที่ง่ายที่สุด: จาก Browser

1. **Login ผ่าน Frontend**
   ```
   http://localhost:3000 (หรือ frontend URL ของคุณ)
   ```

2. **เปิด Browser DevTools**
   - กด `F12` หรือ `Right Click → Inspect`

3. **ไปที่ Console Tab**
   - พิมพ์ code นี้:
   ```javascript
   // Get Supabase session
   (async () => {
     const { data: { session } } = await window.supabase.auth.getSession();
     if (session) {
       console.log('Access Token:', session.access_token);
       console.log('Copy this token to Postman!');
       // Auto copy to clipboard (if browser allows)
       navigator.clipboard.writeText(session.access_token).then(() => {
         console.log('✅ Token copied to clipboard!');
       });
     } else {
       console.log('❌ Not logged in. Please login first.');
     }
   })();
   ```

4. **Copy Token จาก Console**

---

## 📮 Step 2: Setup Postman

### 1. Create New Collection

1. สร้าง Collection ชื่อ "AI Assistant API"
2. Add Environment Variables:
   - `base_url`: `http://localhost:8000`
   - `jwt_token`: `<paste-your-token-here>`

### 2. Create Request: Test Tools

**Request 1: List Available Tools**
- Method: `GET`
- URL: `{{base_url}}/api/v1/test-tools/list`
- Headers: (ไม่ต้องมี Authorization)

**Request 2: Test search_leads**
- Method: `POST`
- URL: `{{base_url}}/api/v1/test-tools`
- Headers:
  ```
  Authorization: Bearer {{jwt_token}}
  Content-Type: application/json
  ```
- Body (raw JSON):
  ```json
  {
    "tool_name": "search_leads",
    "parameters": {
      "query": "today",
      "user_role": "staff"
    }
  }
  ```

**Request 3: Test get_daily_summary**
- Method: `POST`
- URL: `{{base_url}}/api/v1/test-tools`
- Headers: Same as above
- Body:
  ```json
  {
    "tool_name": "get_daily_summary",
    "parameters": {
      "date": "2026-01-17",
      "user_role": "admin"
    }
  }
  ```

**Request 4: Chat (Full Flow)**
- Method: `POST`
- URL: `{{base_url}}/api/v1/chat`
- Headers: Same as above
- Body:
  ```json
  {
    "message": "ลีดวันนี้มีใครบ้างขอเบอร์โทรและชื่อ"
  }
  ```

---

## 🔄 Step 3: Auto-Refresh Token (Optional)

### Setup Pre-request Script

ใน Postman Collection → Pre-request Script:

```javascript
// Auto refresh token if expired
// Note: This requires Supabase client setup
// For now, manually update token when expired
```

---

## 📋 Postman Collection JSON

Import collection นี้ใน Postman:

```json
{
  "info": {
    "name": "AI Assistant API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000",
      "type": "string"
    },
    {
      "key": "jwt_token",
      "value": "",
      "type": "string"
    }
  ],
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/api/v1/health",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "health"]
        }
      }
    },
    {
      "name": "List Available Tools",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/api/v1/test-tools/list",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "test-tools", "list"]
        }
      }
    },
    {
      "name": "Test search_leads",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{jwt_token}}",
            "type": "text"
          },
          {
            "key": "Content-Type",
            "value": "application/json",
            "type": "text"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"tool_name\": \"search_leads\",\n  \"parameters\": {\n    \"query\": \"today\",\n    \"user_role\": \"staff\"\n  }\n}"
        },
        "url": {
          "raw": "{{base_url}}/api/v1/test-tools",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "test-tools"]
        }
      }
    },
    {
      "name": "Test get_daily_summary",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{jwt_token}}",
            "type": "text"
          },
          {
            "key": "Content-Type",
            "value": "application/json",
            "type": "text"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"tool_name\": \"get_daily_summary\",\n  \"parameters\": {\n    \"date\": \"2026-01-17\",\n    \"user_role\": \"admin\"\n  }\n}"
        },
        "url": {
          "raw": "{{base_url}}/api/v1/test-tools",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "test-tools"]
        }
      }
    },
    {
      "name": "Chat - Full Flow",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{jwt_token}}",
            "type": "text"
          },
          {
            "key": "Content-Type",
            "value": "application/json",
            "type": "text"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"message\": \"ลีดวันนี้มีใครบ้างขอเบอร์โทรและชื่อ\"\n}"
        },
        "url": {
          "raw": "{{base_url}}/api/v1/chat",
          "host": ["{{base_url}}"],
          "path": ["api", "v1", "chat"]
        }
      }
    }
  ]
}
```

---

## 🎯 Quick Start

1. **Get Token**: ใช้ Browser Console (ดูวิธีที่ 1)
2. **Import Collection**: Copy JSON ด้านบน → Postman → Import
3. **Set Token**: Collection → Variables → `jwt_token` → Paste token
4. **Test**: Run request "Test search_leads"

---

## 🔍 Verify Token Works

### Test Request
```bash
curl -X GET http://localhost:8000/api/v1/health \
  -H "Authorization: Bearer YOUR_TOKEN"
```

ถ้าได้ response แสดงว่า token ถูกต้อง!
