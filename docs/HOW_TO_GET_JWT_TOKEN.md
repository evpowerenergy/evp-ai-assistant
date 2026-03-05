# 🔑 วิธี Get JWT Token สำหรับ Postman

## 📋 Overview

JWT Token คือ access token จาก Supabase Auth ที่ใช้สำหรับ authentication ใน API requests

---

## 🎯 วิธีที่ 1: จาก Browser Console (แนะนำ - ง่ายที่สุด!)

### ขั้นตอน (3 ขั้นตอน)

1. **Login ผ่าน Frontend**
   - เปิด `http://localhost:3000` (หรือ frontend URL)
   - Login ด้วย email/password

2. **เปิด Browser Console**
   - กด `F12` หรือ `Right Click → Inspect`
   - ไปที่ tab **Console**

3. **Run Code นี้:**
   ```javascript
   // Get token from Supabase session
   (async () => {
     const { data: { session } } = await window.supabase.auth.getSession();
     if (session) {
       console.log('✅ Access Token:');
       console.log(session.access_token);
       console.log('\n📋 Copy token นี้ไปใช้ใน Postman!');
       
       // Auto copy to clipboard (ถ้า browser อนุญาต)
       try {
         await navigator.clipboard.writeText(session.access_token);
         console.log('✅ Token copied to clipboard!');
       } catch (e) {
         console.log('⚠️  Please copy token manually');
       }
     } else {
       console.log('❌ Not logged in. Please login first.');
     }
   })();
   ```

4. **Copy Token จาก Console Output**
   - Token จะแสดงใน console
   - Copy token ทั้งหมด (เริ่มต้นด้วย `eyJ...`)

5. **ใช้ใน Postman**
   ```
   Authorization: Bearer <paste-token-here>
   ```

---

## 🎯 วิธีที่ 1B: จาก Browser DevTools (ถ้า Console ไม่ได้)

### ขั้นตอน

1. **Login ผ่าน Frontend**

2. **เปิด Browser DevTools**
   - กด `F12` → ไปที่ tab **Application** (Chrome) หรือ **Storage** (Firefox)

3. **Copy Token**
   
   **Option A: จาก Local Storage**
   ```
   Application → Local Storage → http://localhost:3000
   → ค้นหา key: `supabase.auth.token`
   → Copy value (JSON string)
   → Parse JSON และเอา `access_token`
   ```
   
   **Option B: จาก Session Storage**
   ```
   Application → Session Storage → http://localhost:3000
   → ค้นหา key: `sb-<project-ref>-auth-token`
   → Copy access_token
   ```

4. **ใช้ใน Postman**
   ```
   Authorization: Bearer <access_token>
   ```

### ตัวอย่าง Token Format

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "...",
  "user": {...}
}
```

**เอาเฉพาะ `access_token`** ไปใช้ใน Postman

---

## 🎯 วิธีที่ 2: ใช้ Browser Console (JavaScript)

### ขั้นตอน

1. **Login ผ่าน Frontend**

2. **เปิด Browser Console**
   - กด `F12` → Console tab

3. **Run JavaScript Code**
   ```javascript
   // Get Supabase session
   const session = await window.supabase.auth.getSession();
   console.log("Access Token:", session.data.session?.access_token);
   ```

4. **Copy Token จาก Console Output**

---

## 🎯 วิธีที่ 3: ใช้ Supabase Client (Frontend Code)

### สร้าง Test Script

สร้างไฟล์ `get-token.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Get JWT Token</title>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
</head>
<body>
    <h1>Get JWT Token</h1>
    <button onclick="getToken()">Get Token</button>
    <pre id="token"></pre>
    
    <script>
        const SUPABASE_URL = 'https://ttfjapfdzrxmbxbarfbn.supabase.co';
        const SUPABASE_ANON_KEY = 'YOUR_ANON_KEY'; // ใส่ anon key จาก .env
        
        const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        
        async function getToken() {
            const { data: { session }, error } = await supabase.auth.getSession();
            
            if (error) {
                document.getElementById('token').textContent = 'Error: ' + error.message;
                return;
            }
            
            if (session) {
                document.getElementById('token').textContent = session.access_token;
            } else {
                document.getElementById('token').textContent = 'Not logged in. Please login first.';
            }
        }
    </script>
</body>
</html>
```

---

## 🎯 วิธีที่ 4: ใช้ Supabase CLI (ถ้ามี setup)

```bash
# Login to Supabase
supabase login

# Get project access token
supabase projects list
```

---

## 🎯 วิธีที่ 5: สร้าง Test User และ Get Token (Backend Script)

สร้างไฟล์ `backend/get_test_token.py`:

```python
"""
Script to get JWT token for testing
"""
import asyncio
from supabase import create_client
from app.config import settings

async def get_test_token():
    """Get JWT token for testing"""
    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY
    )
    
    # Login (replace with your test credentials)
    email = "test@example.com"
    password = "testpassword123"
    
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            token = response.session.access_token
            print(f"\n✅ Token obtained:")
            print(f"{token}\n")
            print(f"Use in Postman:")
            print(f"Authorization: Bearer {token}\n")
            return token
        else:
            print("❌ Login failed")
            return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(get_test_token())
```

---

## 🎯 วิธีที่ 6: ใช้ curl (Quick Test)

```bash
# Login และ get token
curl -X POST 'https://ttfjapfdzrxmbxbarfbn.supabase.co/auth/v1/token?grant_type=password' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'

# Response จะมี access_token
```

---

## 📝 Postman Setup

### Step 1: Get Token (ใช้วิธีที่ 1 - จาก Browser)

1. Login ผ่าน frontend
2. Copy `access_token` จาก Local Storage
3. ไปที่ Postman

### Step 2: Setup Postman Request

1. **Create New Request**
   - Method: `POST`
   - URL: `http://localhost:8000/api/v1/test-tools`

2. **Headers Tab**
   ```
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   Content-Type: application/json
   ```

3. **Body Tab (raw JSON)**
   ```json
   {
     "tool_name": "search_leads",
     "parameters": {
       "query": "today",
       "user_role": "staff"
     }
   }
   ```

4. **Send Request**

---

## 🔍 ตรวจสอบ Token

### ตรวจสอบว่า Token ถูกต้อง

```bash
# Decode JWT (ไม่ต้อง verify signature)
# ใช้ https://jwt.io หรือ Python:

python3 -c "
import jwt
import json
token = 'YOUR_TOKEN_HERE'
decoded = jwt.decode(token, options={'verify_signature': False})
print(json.dumps(decoded, indent=2))
"
```

### ตรวจสอบ Token Expiry

Token มักจะ expire ใน 1 hour (3600 seconds)

ถ้า token หมดอายุ:
- ใช้ refresh token เพื่อ get token ใหม่
- หรือ login ใหม่

---

## 🚨 Troubleshooting

### Error: 401 Unauthorized

**สาเหตุ:**
- Token หมดอายุ
- Token ไม่ถูกต้อง
- Token format ผิด

**แก้ไข:**
1. ตรวจสอบ token format: ต้องเริ่มด้วย `eyJ...`
2. Login ใหม่และ copy token ใหม่
3. ตรวจสอบว่า copy token ครบ (ไม่ขาด)

### Error: Token not found

**สาเหตุ:**
- ยังไม่ได้ login
- Token ถูก clear จาก browser

**แก้ไข:**
1. Login ผ่าน frontend อีกครั้ง
2. Copy token ใหม่

---

## 💡 Tips

1. **ใช้ Postman Environment Variables**
   - สร้าง variable: `{{jwt_token}}`
   - ใช้ใน Authorization: `Bearer {{jwt_token}}`
   - Update token เมื่อหมดอายุ

2. **Token Expiry**
   - Token หมดอายุใน 1 hour
   - ควร refresh หรือ login ใหม่เมื่อหมดอายุ

3. **Security**
   - ❌ อย่า commit token ลง git
   - ❌ อย่า share token กับคนอื่น
   - ✅ ใช้ test user สำหรับ development

---

## 📚 Quick Reference

### Token Location (Browser)
- **Chrome/Edge**: DevTools → Application → Local Storage → `supabase.auth.token`
- **Firefox**: DevTools → Storage → Local Storage → `supabase.auth.token`

### Token Format
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzA1NDk2MDAwLCJzdWIiOiI5ZjM5MDY3Yi1mODAzLTRjYjQtYjNjNi1jMGYyZTM0MDNmZDgiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiYXV0aF9wcm92aWRlciI6ImVtYWlsIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3MDU0OTI0MDB9XSwic2Vzc2lvbl9pZCI6IjEyMzQ1Njc4LTEyMzQtMTIzNC0xMjM0LTEyMzQ1Njc4OTAxMiJ9.signature
```

### Postman Authorization Header
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
