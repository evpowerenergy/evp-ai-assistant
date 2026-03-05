# 🔐 JWT Authentication ในโปรเจ็กต์ evp-ai-assistant

## ❓ คำถาม: ต้องสร้าง JWT บน Supabase หรือไม่?

**คำตอบ: ไม่ต้อง!** Supabase จัดการ JWT ให้อัตโนมัติแล้ว

---

## 🔄 Flow การทำงานของ JWT

### 1. **User Login (Frontend)**
```
User → Frontend → Supabase Auth → JWT Token
```
- เมื่อ user login ผ่าน Supabase Auth
- Supabase สร้าง JWT token อัตโนมัติ
- Frontend ได้รับ JWT token และเก็บไว้ใน session

### 2. **ส่ง Request (Frontend → Backend)**
```typescript
// Frontend ส่ง JWT token ใน Authorization header
Authorization: Bearer <jwt_token>
```

### 3. **Verify Token (Backend)**
```python
# Backend verify JWT token
token = credentials.credentials  # จาก Authorization header
token_payload = await verify_jwt_token(token)  # Verify token
user = await get_user_from_token(token_payload)  # Get user info
```

---

## 📍 JWT ถูกใช้ในโปรเจ็กต์ที่ไหนบ้าง?

### **Frontend (Next.js)**
1. **`src/contexts/AuthContext.tsx`**
   - เก็บ JWT token ใน session
   - Auto refresh token เมื่อใกล้หมดอายุ

2. **`src/hooks/useChat.ts`**
   - ส่ง JWT token ไปยัง backend API
   ```typescript
   Authorization: `Bearer ${session.access_token}`
   ```

3. **`src/lib/supabase/client.ts`**
   - Supabase client ที่จัดการ JWT อัตโนมัติ

### **Backend (FastAPI)**
1. **`app/core/auth.py`**
   - **`verify_jwt_token()`** - Verify JWT token จาก frontend
   - **`get_user_from_token()`** - Get user info จาก token
   - **`get_current_user()`** - Dependency สำหรับ protect endpoints

2. **`app/api/v1/chat.py`**
   - ใช้ `get_current_user` เพื่อ protect chat endpoint
   ```python
   async def chat(
       request: ChatRequest,
       current_user: dict = Depends(get_current_user)  # ← JWT verification ตรงนี้
   )
   ```

---

## 🛠️ การ Verify JWT Token (Backend)

ปัจจุบันโปรเจ็กต์ใช้วิธีนี้:

### **วิธีปัจจุบัน:**
1. **Decode JWT token** (ไม่ verify signature - เพราะไม่มี JWKS endpoint)
2. **Check token expiration**
3. **Verify user** โดย query database (optional)
4. **Return token payload**

### **Code Location:**
```python
# app/core/auth.py
async def verify_jwt_token(token: str) -> dict:
    # 1. Decode token (no signature verification)
    unverified = jwt.decode(token, options={"verify_signature": False})
    
    # 2. Check expiration
    if exp and time.time() >= exp:
        raise AuthenticationError("Token expired")
    
    # 3. Verify user exists (optional)
    # ... database query ...
    
    # 4. Return payload
    return token_payload
```

---

## ⚙️ Configuration

### **Frontend (.env.local)**
```env
NEXT_PUBLIC_SUPABASE_URL=https://ttfjapfdzrxmbxbarfbn.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...  # Anon key สำหรับ frontend
```

### **Backend (.env)**
```env
SUPABASE_URL=https://ttfjapfdzrxmbxbarfbn.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...  # Service role key สำหรับ backend
```

---

## 🔑 Keys ที่ใช้

1. **Anon Key (Frontend)**
   - ใช้สำหรับ frontend → Supabase requests
   - มี RLS (Row Level Security) enforce
   - ไม่สามารถ bypass RLS ได้

2. **Service Role Key (Backend)**
   - ใช้สำหรับ backend operations
   - **Bypass RLS** - สามารถเข้าถึงข้อมูลทั้งหมดได้
   - ⚠️ **ห้าม expose ใน frontend!**

3. **JWT Token (User)**
   - สร้างโดย Supabase เมื่อ user login
   - ใช้สำหรับ authenticate user
   - มี expiration time (ปกติ 1 hour)

---

## 🔍 Debug JWT Issues

### **1. Token หมดอายุ**
```
Error: "Token expired"
Fix: Frontend auto refresh หรือ login ใหม่
```

### **2. Token ไม่ valid**
```
Error: "Invalid token"
Fix: ตรวจสอบว่า token ถูกส่งไปถูกต้องหรือไม่
```

### **3. User ไม่พบ**
```
Error: "User not found"
Fix: ตรวจสอบว่า user มีใน database หรือไม่
```

---

## 📝 สรุป

✅ **ไม่ต้องสร้าง JWT เอง** - Supabase จัดการให้หมดแล้ว  
✅ **JWT ถูกใช้ทุกที่ที่ต้องการ authentication**  
✅ **Frontend:** ส่ง JWT token ใน Authorization header  
✅ **Backend:** Verify JWT token และ get user info  
✅ **Supabase:** สร้างและจัดการ JWT tokens อัตโนมัติ

---

## 🔗 References

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [JWT.io](https://jwt.io/) - JWT Debugger
- [Supabase JWT Guide](https://supabase.com/docs/guides/auth/jwts)
