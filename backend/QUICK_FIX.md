# ⚡ Quick Fix: ใช้ Python 3.10 แทน

ถ้าไม่ต้องการติดตั้ง Python 3.11 (เพราะมีปัญหา apt_pkg) สามารถใช้ Python 3.10 ที่มีอยู่แล้วได้:

## ขั้นตอน

```bash
cd evp-ai-assistant/backend

# 1. ลบ venv เก่า
rm -rf venv

# 2. สร้าง venv ใหม่ด้วย Python 3.10
python3.10 -m venv venv

# 3. Activate venv
source venv/bin/activate

# 4. ตรวจสอบ Python version
python --version
# ควรแสดง: Python 3.10.12

# 5. อัปเกรด pip
pip install --upgrade pip setuptools wheel

# 6. ติดตั้ง dependencies
pip install -r requirements.txt

# 7. Run backend
uvicorn app.main:app --reload
```

## ข้อดี

- ✅ ไม่ต้องติดตั้ง Python ใหม่
- ✅ เร็วกว่า (ไม่ต้อง compile)
- ✅ รองรับ dependencies ทั้งหมด (รวม line-bot-sdk)
- ✅ Stable และทดสอบแล้ว

## หมายเหตุ

Python 3.10 และ 3.11 ต่างกันเล็กน้อย แต่สำหรับ project นี้ใช้งานได้เหมือนกัน

---

**Last Updated:** 2025-01-16
