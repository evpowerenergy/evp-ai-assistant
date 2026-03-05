# 🐍 ติดตั้ง Python 3.11 บน WSL Ubuntu 22.04

## วิธีที่ 1: ใช้ Script (แนะนำ)

### ขั้นตอนที่ 1: ติดตั้ง Python 3.11

```bash
cd evp-ai-assistant/backend
bash install_python311.sh
```

### ขั้นตอนที่ 2: สร้าง Virtual Environment

```bash
bash setup_venv.sh
```

---

## วิธีที่ 2: รันคำสั่งเอง (Manual)

### ขั้นตอนที่ 1: Update และติดตั้ง Prerequisites

```bash
sudo apt update
sudo apt install -y software-properties-common
```

### ขั้นตอนที่ 2: เพิ่ม deadsnakes PPA

```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
```

### ขั้นตอนที่ 3: ติดตั้ง Python 3.11

```bash
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

### ขั้นตอนที่ 4: ตรวจสอบการติดตั้ง

```bash
python3.11 --version
# ควรแสดง: Python 3.11.x
```

### ขั้นตอนที่ 5: สร้าง Virtual Environment

```bash
cd evp-ai-assistant/backend

# ลบ venv เก่า (ถ้ามี)
rm -rf venv

# สร้าง venv ใหม่ด้วย Python 3.11
python3.11 -m venv venv

# Activate venv
source venv/bin/activate

# ตรวจสอบ Python version
python --version
# ควรแสดง: Python 3.11.x
```

### ขั้นตอนที่ 6: ติดตั้ง Dependencies

```bash
# อัปเกรด pip, setuptools, wheel
pip install --upgrade pip setuptools wheel

# ติดตั้ง dependencies
pip install -r requirements.txt
```

---

## ✅ ตรวจสอบ

```bash
# ตรวจสอบ Python version
python --version
# ควรแสดง: Python 3.11.x

# ตรวจสอบ packages
pip list | grep fastapi
pip list | grep supabase
```

---

## 🚀 เริ่มต้น Backend

```bash
# ตรวจสอบว่า venv activate แล้ว
which python
# ควรแสดง: .../venv/bin/python

# Run backend
uvicorn app.main:app --reload
```

---

## 🐛 Troubleshooting

### Error: `python3.11: command not found`

**แก้ไข:**
```bash
# ตรวจสอบว่า Python 3.11 ติดตั้งแล้วหรือยัง
which python3.11

# ถ้ายังไม่มี ให้ติดตั้งตามวิธีที่ 1 หรือ 2
```

### Error: `The virtual environment was not created successfully`

**แก้ไข:**
```bash
# ติดตั้ง python3.11-venv
sudo apt install -y python3.11-venv
```

### Error: `Permission denied`

**แก้ไข:**
```bash
# ใช้ sudo สำหรับคำสั่งที่ต้องการสิทธิ์
sudo apt install -y python3.11 python3.11-venv
```

---

## 📝 สรุปคำสั่งทั้งหมด

```bash
# 1. ติดตั้ง Python 3.11
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 2. สร้าง venv
cd evp-ai-assistant/backend
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate

# 3. ติดตั้ง dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 4. Run backend
uvicorn app.main:app --reload
```

---

**Last Updated:** 2025-01-16
