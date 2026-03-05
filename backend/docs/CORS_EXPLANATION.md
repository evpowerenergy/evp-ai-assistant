# 🌐 CORS (Cross-Origin Resource Sharing) อธิบาย

## 🤔 CORS คืออะไร?

**CORS (Cross-Origin Resource Sharing)** เป็นกลไกความปลอดภัยของเบราว์เซอร์ที่ป้องกันไม่ให้เว็บไซต์เรียก API จาก domain อื่นโดยไม่ได้รับอนุญาต

### ตัวอย่างปัญหา

```
Frontend: http://localhost:3000 (Next.js)
Backend:  http://localhost:8000 (FastAPI)
```

เมื่อ Frontend พยายามเรียก Backend API:
- ❌ **ไม่มี CORS:** เบราว์เซอร์จะบล็อก request (CORS error)
- ✅ **มี CORS:** เบราว์เซอร์อนุญาตให้เรียกได้

---

## 🔧 ทำไมต้องตั้งค่า CORS_ORIGINS?

### ในระบบนี้:

```
Frontend (Next.js)  →  Backend API (FastAPI)
http://localhost:3000  →  http://localhost:8000
```

**Frontend ต้องเรียก Backend API** แต่:
- Frontend อยู่ที่ `localhost:3000`
- Backend อยู่ที่ `localhost:8000`
- **เป็นคนละ origin** (port ต่างกัน)

**ถ้าไม่ตั้งค่า CORS:**
```
Access to fetch at 'http://localhost:8000/api/v1/chat' from origin 
'http://localhost:3000' has been blocked by CORS policy
```

---

## 📝 CORS_ORIGINS คืออะไร?

`CORS_ORIGINS` คือรายการของ **origin ที่อนุญาต** ให้เรียก Backend API ได้

### ตัวอย่าง:

```env
# Development: อนุญาต localhost:3000 และ localhost:3001
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Production: อนุญาต domain จริง
CORS_ORIGINS=https://ai-assistant.example.com,https://www.example.com
```

---

## 🎯 ทำไมต้องเป็น localhost:3000 และ localhost:3001?

### `localhost:3000`
- **Frontend (Next.js)** รันที่ port 3000
- ใช้สำหรับ development
- ต้องอนุญาตให้เรียก Backend API

### `localhost:3001`
- **Alternative port** สำหรับ development
- บางครั้งอาจรัน Frontend ที่ port อื่น (ถ้า 3000 ถูกใช้)
- หรือสำหรับทดสอบหลาย instance

---

## 🔍 ดูในโค้ด

### `backend/app/main.py`:

```python
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # ← ใช้ค่าจาก .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### `backend/app/config.py`:

```python
CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
```

---

## 🚀 การใช้งานจริง

### Development (Local)

```env
# .env
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

**หมายความว่า:**
- ✅ `http://localhost:3000` เรียก Backend API ได้
- ✅ `http://localhost:3001` เรียก Backend API ได้
- ❌ `http://localhost:3002` เรียก Backend API **ไม่ได้**

### Production

```env
# .env (Production)
CORS_ORIGINS=https://ai-assistant.yourcompany.com
```

**หมายความว่า:**
- ✅ `https://ai-assistant.yourcompany.com` เรียก Backend API ได้
- ❌ Domain อื่นเรียก Backend API **ไม่ได้**

---

## ⚠️ ความปลอดภัย

### ❌ ไม่ควรทำ:

```env
# อนุญาตทุก origin (อันตราย!)
CORS_ORIGINS=*
```

**ทำไมอันตราย?**
- ใครก็เรียก API ได้
- เสี่ยงถูกโจมตี (CSRF, XSS)
- ข้อมูลรั่วไหล

### ✅ ควรทำ:

```env
# ระบุ origin ที่ต้องการเท่านั้น
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

---

## 📊 Flow การทำงาน

```
1. Frontend (localhost:3000) ส่ง request ไป Backend (localhost:8000)
   ↓
2. Backend ตรวจสอบ Origin header
   ↓
3. ถ้า Origin อยู่ใน CORS_ORIGINS → อนุญาต ✅
   ถ้า Origin ไม่อยู่ใน CORS_ORIGINS → ปฏิเสธ ❌
   ↓
4. เบราว์เซอร์ตรวจสอบ CORS headers
   ↓
5. ถ้าผ่าน → แสดงผล
   ถ้าไม่ผ่าน → แสดง CORS error
```

---

## 🛠️ วิธีตั้งค่า

### 1. Development

```env
# .env
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### 2. Production

```env
# .env (Production)
CORS_ORIGINS=https://ai-assistant.yourcompany.com
```

### 3. Multiple Environments

```env
# Development
CORS_ORIGINS=http://localhost:3000

# Staging
CORS_ORIGINS=https://staging.yourcompany.com

# Production
CORS_ORIGINS=https://yourcompany.com
```

---

## ✅ สรุป

1. **CORS** = กลไกความปลอดภัยของเบราว์เซอร์
2. **CORS_ORIGINS** = รายการ origin ที่อนุญาตให้เรียก API
3. **localhost:3000** = Frontend (Next.js) development port
4. **localhost:3001** = Alternative port สำหรับ development
5. **ต้องตั้งค่า** = เพื่อให้ Frontend เรียก Backend API ได้

---

**Last Updated:** 2025-01-16
