# 🔧 แก้ปัญหา apt_pkg Module Error

## ปัญหา

```
ModuleNotFoundError: No module named 'apt_pkg'
```

## วิธีแก้ไข

### วิธีที่ 1: Reinstall python3-apt (แนะนำ)

```bash
# แก้ไข apt_pkg module
sudo apt install --reinstall python3-apt python3-distutils

# ลองรัน script อีกครั้ง
bash install_python311.sh
```

### วิธีที่ 2: ใช้ Manual Installation (ถ้าวิธีที่ 1 ไม่ได้)

```bash
# ใช้ script ที่ compile จาก source
bash install_python311_manual.sh
```

**หมายเหตุ:** วิธีนี้จะใช้เวลานาน (10-20 นาที) เพราะต้อง compile Python

### วิธีที่ 3: ใช้ Python 3.10 แทน (เร็วที่สุด)

ถ้าไม่ต้องการรอ compile Python 3.11:

```bash
cd evp-ai-assistant/backend

# ลบ venv เก่า
rm -rf venv

# สร้าง venv ด้วย Python 3.10 (มีอยู่แล้ว)
python3.10 -m venv venv
source venv/bin/activate

# ติดตั้ง dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

---

## สาเหตุของปัญหา

- Python version เปลี่ยนทำให้ `apt_pkg` module ไม่ match
- `python3-apt` package ไม่ sync กับ Python version ปัจจุบัน

---

## ตรวจสอบ

```bash
# ตรวจสอบ python3-apt
python3 -c "import apt_pkg; print('OK')"

# ตรวจสอบ Python 3.11
python3.11 --version
```

---

**Last Updated:** 2025-01-16
