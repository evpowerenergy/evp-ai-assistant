# 🔧 Python 3.12 Compatibility Guide

## ⚠️ ปัญหาที่พบ

เมื่อใช้ Python 3.12 พบ dependency conflicts:

1. **aiohttp**: เวอร์ชันเก่าไม่รองรับ Python 3.12 (build error)
2. **line-bot-sdk**: ต้องการ `aiohttp==3.8.5` ซึ่งไม่รองรับ Python 3.12
3. **supabase**: ต้องการ `httpx<0.25.0` ซึ่ง conflict กับเวอร์ชันใหม่

---

## ✅ วิธีแก้ไข

### วิธีที่ 1: ใช้ Python 3.11 (แนะนำสำหรับ Production)

Python 3.11 รองรับ dependencies ทั้งหมดได้ดีกว่า:

```bash
# สร้าง venv ใหม่ด้วย Python 3.11
cd evp-ai-assistant/backend
python3.11 -m venv venv
source venv/bin/activate

# ติดตั้ง dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**ข้อดี:**
- ✅ รองรับ dependencies ทั้งหมด
- ✅ Stable และทดสอบแล้ว
- ✅ ไม่มี build errors

### วิธีที่ 2: ใช้ Python 3.12 (Development Only)

ถ้าต้องการใช้ Python 3.12:

```bash
cd evp-ai-assistant/backend
python3.12 -m venv venv
source venv/bin/activate

# ติดตั้ง dependencies (line-bot-sdk จะถูกข้าม)
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**ข้อจำกัด:**
- ❌ `line-bot-sdk` ถูก comment ออก (Phase 4 ยังไม่ได้ทำ)
- ⚠️ อาจมี build issues กับบาง packages

---

## 📝 สิ่งที่แก้ไขใน requirements.txt

### 1. ลบ `aiohttp>=3.9.0`
- ให้ `langchain` จัดการ version เอง (ต้องการ `aiohttp>=3.8.3,<4.0.0`)
- แต่ `aiohttp 3.8.x` ไม่รองรับ Python 3.12

### 2. Comment `line-bot-sdk`
- `line-bot-sdk 3.5.0` ต้องการ `aiohttp==3.8.5` (เฉพาะ version นี้)
- ไม่รองรับ Python 3.12
- Phase 4 ยังไม่ได้ทำ จึง comment ไว้ก่อน

### 3. ให้ dependencies จัดการ versions เอง
- `supabase` จัดการ `httpx` version
- `langchain` จัดการ `aiohttp` version (แต่จะ conflict กับ Python 3.12)

---

## 🚀 การใช้งาน

### Development (Python 3.12)
```bash
# LINE features จะไม่ทำงาน (Phase 4)
# แต่ core features (chat, RAG, DB) ทำงานได้
uvicorn app.main:app --reload
```

### Production (Python 3.11)
```bash
# ทุก features ทำงานได้ รวมถึง LINE (Phase 4)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🔮 Phase 4: LINE Integration

เมื่อถึง Phase 4 และต้องการใช้ LINE:

### Option 1: ใช้ Python 3.11
```bash
# Uncomment line-bot-sdk ใน requirements.txt
line-bot-sdk==3.5.0
```

### Option 2: รอ line-bot-sdk เวอร์ชันใหม่
- รอให้ `line-bot-sdk` อัปเดตรองรับ `aiohttp` เวอร์ชันใหม่
- หรือใช้ alternative LINE SDK

---

## ✅ Checklist

- [ ] เลือก Python version (3.11 หรือ 3.12)
- [ ] สร้าง virtual environment
- [ ] ติดตั้ง dependencies
- [ ] ตรวจสอบว่า backend รันได้
- [ ] ทดสอบ core features (chat, RAG, DB)

---

## 📚 References

- [Python 3.12 Release Notes](https://docs.python.org/3.12/whatsnew/3.12.html)
- [aiohttp Python 3.12 Issue](https://github.com/aio-libs/aiohttp/issues/7739)
- [line-bot-sdk GitHub](https://github.com/line/line-bot-sdk-python)

---

**Last Updated:** 2025-01-16  
**Status:** ✅ Python 3.11 Recommended | ⚠️ Python 3.12 Limited Support
