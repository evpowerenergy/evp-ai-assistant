# 📦 Backend Installation Guide

## ปัญหาที่พบบ่อย: ModuleNotFoundError

ถ้าพบ error `ModuleNotFoundError: No module named 'fastapi'` แสดงว่า:
1. ยังไม่ได้ติดตั้ง dependencies
2. Virtual environment ไม่ได้ activate
3. ใช้ Python interpreter ผิดตัว

---

## ✅ วิธีติดตั้งที่ถูกต้อง

### 1. ตรวจสอบ Python Version
```bash
python3.12 --version
# ควรแสดง: Python 3.12.x
```

### 2. สร้าง Virtual Environment
```bash
cd evp-ai-assistant/backend

# สร้าง venv
python3.12 -m venv venv

# Activate venv
# สำหรับ Linux/Mac/WSL:
source venv/bin/activate

# สำหรับ Windows:
# venv\Scripts\activate
```

**ตรวจสอบว่า activate แล้ว:**
```bash
which python
# ควรแสดง: .../evp-ai-assistant/backend/venv/bin/python

python --version
# ควรแสดง: Python 3.12.x
```

### 3. อัปเกรด pip
```bash
pip install --upgrade pip
```

### 4. ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```

**ตรวจสอบว่า fastapi ติดตั้งแล้ว:**
```bash
pip list | grep fastapi
# ควรแสดง: fastapi 0.109.0
```

### 5. ทดสอบว่าใช้งานได้
```bash
python -c "import fastapi; print(fastapi.__version__)"
# ควรแสดง: 0.109.0
```

---

## 🚀 เริ่มต้น Backend

### 1. Setup Environment Variables
```bash
cp env.example .env
# แก้ไข .env ด้วย credentials ของคุณ
```

### 2. Run Backend
```bash
# ตรวจสอบว่า venv activate แล้ว
which python

# Run backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**ตรวจสอบ:**
- ✅ http://localhost:8000/api/v1/health
- ✅ http://localhost:8000/docs

---

## 🐛 Troubleshooting

### Error: `ModuleNotFoundError: No module named 'fastapi'`

**สาเหตุ:**
- Virtual environment ไม่ได้ activate
- ติดตั้ง dependencies ใน Python global แทน venv

**แก้ไข:**
```bash
# 1. ตรวจสอบว่า venv activate แล้ว
which python
# ควรแสดง: .../venv/bin/python

# 2. ถ้ายังไม่ได้ activate
source venv/bin/activate

# 3. ติดตั้ง dependencies อีกครั้ง
pip install -r requirements.txt
```

### Error: `python3.12: command not found`

**สาเหตุ:**
- Python 3.12 ยังไม่ได้ติดตั้ง

**แก้ไข:**
```bash
# ตรวจสอบ Python version ที่มี
python3 --version
python --version

# ถ้ามี Python 3.11 หรือ 3.10 ก็ใช้ได้
python3.11 -m venv venv
# หรือ
python3 -m venv venv
```

### Error: `pip: command not found`

**แก้ไข:**
```bash
# ใช้ python -m pip แทน
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Error: `Permission denied`

**แก้ไข:**
```bash
# ใช้ --user flag
pip install --user -r requirements.txt

# หรือใช้ sudo (ไม่แนะนำ)
sudo pip install -r requirements.txt
```

---

## ✅ Checklist

- [ ] Python 3.12 (หรือ 3.11+) ติดตั้งแล้ว
- [ ] Virtual environment สร้างแล้ว
- [ ] Virtual environment activate แล้ว
- [ ] pip อัปเกรดแล้ว
- [ ] Dependencies ติดตั้งแล้ว (`pip list | grep fastapi`)
- [ ] Environment variables ตั้งค่าแล้ว (`.env`)
- [ ] Backend รันได้ (`uvicorn app.main:app --reload`)

---

## 📝 Quick Commands

```bash
# สร้างและ activate venv
python3.12 -m venv venv
source venv/bin/activate

# ติดตั้ง dependencies
pip install -r requirements.txt

# Run backend
uvicorn app.main:app --reload
```

---

**Last Updated:** 2025-01-16
