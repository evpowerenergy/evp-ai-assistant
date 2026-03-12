# วิธีให้ AI Assistant Frontend เปิดได้แบบ Public (ทุกคนบนอินเทอร์เน็ต)

> คู่มือแบบละเอียดทีละขั้น — ต้องให้ **ผู้ดูแล GCP (Org Admin)** ทำขั้นตอนหนึ่งก่อน แล้วคุณค่อยรันคำสั่ง

---

## สรุปสั้นๆ

0. **(ถ้าคุณเป็น Admin)** ให้สิทธิ์ **Organization Policy Administrator** กับบัญชีที่จะไปแก้ policy ก่อน
1. **Org Admin** ไปแก้ policy **Domain restricted sharing** → ยกเว้นโปรเจกต์ ev-power-energy-prod
2. **คุณ** รันคำสั่ง `gcloud run services add-iam-policy-binding` หนึ่งครั้ง
3. เปิด URL Frontend ในเบราว์เซอร์ → ควรเข้าได้โดยไม่ Forbidden

---

## ขั้นที่ 0: ให้สิทธิ์ Organization Policy Administrator ก่อน (ถ้าคุณเป็น Admin)

ถ้ากด **Manage policy** แล้วขึ้นว่าต้องมีสิทธิ์แก้ organization policies ให้ทำขั้นนี้ก่อน

### วิธีที่ 1: ผ่าน Console (แนะนำ)

1. เปิด [Google Cloud Console](https://console.cloud.google.com)
2. **ด้านบนซ้าย** คลิกเลือกโปรเจกต์ → เปิด **Resource hierarchy** หรือไปที่ [Admin / IAM](https://console.cloud.google.com/iam-admin)
3. **ต้องอยู่ที่ระดับ Organization** (ไม่ใช่แค่ Project):
   - คลิก dropdown ด้านบนที่แสดง "Project: ev-power-energy-prod"
   - เลือก **Organization** ที่ครอบโปรเจกต์นี้ (ชื่อองค์กรของคุณ)
4. เมนูซ้าย: **IAM & Admin** → **IAM**
5. กด **Grant access** (หรือ **+ ADD** / **Add principal**)
6. ในช่อง **New principals** ใส่อีเมลบัญชีที่จะใช้แก้ policy (เช่น admin@evpowerenergy.com)
7. ใน **Role** เลือก **Organization Policy Administrator**  
   - ถ้าหาไม่เจอ ให้พิมพ์ในช่องค้นหา: `Organization Policy Administrator` หรือ `orgpolicy`
8. กด **Save**

หลังบันทึก รอสักครู่แล้วให้บัญชีนั้น **ออกจาก Console แล้วล็อกอินใหม่** (หรือเปิด incognito ล็อกอินใหม่) แล้วค่อยไป **ขั้นที่ 1** แก้ policy

### วิธีที่ 2: ผ่าน gcloud (ถ้ามีสิทธิ์อยู่แล้ว)

ถ้าคุณมีสิทธิ์จัดการ IAM ที่ระดับ Organization อยู่แล้ว (เช่น เป็น Owner ขององค์กร) รันในเทอร์มินัล:

```bash
# แทน ORG_ID ด้วยหมายเลข Organization (ดูได้จาก Console หน้า Organization settings)
# แทน EMAIL ด้วยอีเมลที่จะให้สิทธิ์ (เช่น admin@evpowerenergy.com)
gcloud organizations add-iam-policy-binding ORG_ID \
  --member="user:EMAIL" \
  --role="roles/orgpolicy.policyAdmin"
```

ดู ORG_ID: ไปที่ **IAM & Admin** → **Settings** (หรือ Organization settings) ที่ระดับ Organization จะเห็น Organization ID

---

## ส่วนที่ 1: แก้ policy "Domain restricted sharing"

### ขั้น 1.1 เปิดหน้า Organization policies

1. เปิดเบราว์เซอร์ → [Google Cloud Console](https://console.cloud.google.com)
2. ด้านบนเลือก **Organization** (ไม่ใช่แค่ Project) — ต้องเป็นองค์กรที่ครอบ project `ev-power-energy-prod`
3. เมนูซ้าย: **IAM & Admin** → **Organization policies**
4. ด้านบนเลือก **Organization** ที่ถูกต้อง (หรือถ้าไม่มีองค์กร ให้ดูที่ Project level ตามขั้นถัดไป)

**ถ้าไม่มีเมนู Organization:** อาจอยู่ที่ระดับ Project  
→ ไปที่ **IAM & Admin** → **Organization policies** โดยอยู่ที่ project `ev-power-energy-prod` แล้วดูว่ามี policy แบบ "inherited" จาก parent หรือไม่

### ขั้น 1.2 หา policy ที่กัน allUsers

ในรายการ policy ให้หา constraint ที่เกี่ยวกับ **การจำกัดสมาชิกในนโยบาย IAM** โดยมักเป็นชื่อประมาณนี้:

- **Allowed policy member domains**  
  หรือ  
- **Domain restricted sharing**  
  หรือ  
- **Restrict shared VPC network users**  
  หรือ constraint ที่มีคำว่า **policy member** / **domain** / **iam**

**วิธีหาเร็ว:** ใช้ช่องค้นหาหรือ filter บนหน้าเดียวกัน (ถ้ามี) พิมพ์ `iam` หรือ `domain` หรือ `policy member`

Constraint ที่มักทำให้เพิ่ม `allUsers` ไม่ได้คือ:

- **Constraint ID:** `constraints/iam.allowedPolicyMemberDomains`  
  หรือชื่อแสดงผลประมาณ **"Allowed policy member domains"**

ถ้าไม่แน่ใจ ให้ลองเปิดดู constraint ที่เกี่ยวกับ IAM / domain ทีละตัว

### ขั้น 1.3 แก้หรือยกเว้น policy

เมื่อเจอ constraint ที่เกี่ยวข้องแล้ว:

**ทางเลือก A — ยกเว้นเฉพาะโปรเจกต์ (แนะนำ)**

1. กดเข้า constraint นั้น
2. ดูว่า **Policy enforcement** เปิดอยู่หรือไม่ (Enforced / Inherited)
3. กด **Manage policy** หรือ **Edit**
4. เพิ่ม **Exception** สำหรับโปรเจกต์ `ev-power-energy-prod`  
   - เลือก type = **Project**  
   - เลือก project = **ev-power-energy-prod**
5. บันทึก (Save)

ผลคือ: โปรเจกต์นี้จะไม่ถูกบังคับโดย constraint นี้ → สามารถเพิ่ม `allUsers` ที่ Cloud Run ในโปรเจกต์นี้ได้

**ทางเลือก B — ปิดการบังคับทั้งองค์กร**

1. กดเข้า constraint นั้น
2. แก้จาก **Enforce** เป็น **Not set** หรือ **Off** (แล้วแต่ UI)
3. บันทึก

ผลคือ: ทุกโปรเจกต์ในองค์กรจะเพิ่ม allUsers ได้ (ใช้ถ้าองค์กรยอมรับได้)

### ขั้น 1.4 แจ้งคุณเมื่อแก้เสร็จ

เมื่อ Admin แก้หรือยกเว้น policy เสร็จแล้ว แจ้งให้คุณทราบ → คุณไปทำ **ส่วนที่ 2** ได้เลย

---

## ส่วนที่ 2: คุณทำหลัง Admin แก้ policy แล้ว

### ขั้น 2.1 เปิดเทอร์มินัล

เปิด Terminal (หรือ PowerShell / CMD) บนเครื่องที่ติดตั้ง `gcloud` และเคย login โปรเจกต์นี้แล้ว

### ขั้น 2.2 ตั้งโปรเจกต์ (ถ้ายังไม่ตั้ง)

```bash
gcloud config set project ev-power-energy-prod
```

### ขั้น 2.3 ให้สิทธิ์ทุกคน (allUsers) เรียก Frontend

รันคำสั่งนี้ **หนึ่งครั้ง**:

```bash
gcloud run services add-iam-policy-binding ai-assistant-frontend \
  --region=asia-southeast1 \
  --member=allUsers \
  --role=roles/run.invoker \
  --project=ev-power-energy-prod
```

- จะมีคำถาม **"Do you want to continue (Y/n)?"** → กด **Y** แล้ว Enter

ถ้าสำเร็จ จะมีข้อความประมาณ  
`Updated IAM policy for service [ai-assistant-frontend].`

### ขั้น 2.4 ทดสอบ

1. เปิดเบราว์เซอร์ (หรือใช้โหมดไม่ล็อกอิน / incognito)
2. ไปที่ URL ของ Frontend เช่น  
   `https://ai-assistant-frontend-1089649909937.asia-southeast1.run.app`
3. ควรเห็นหน้าเว็บ (ไม่ขึ้น Forbidden)
4. จากนั้นใช้ **login ในแอป** ตามปกติ

---

## ถ้ายัง Forbidden หลังรันคำสั่ง

- **ตรวจสอบว่า Admin แก้ policy จริงหรือไม่**  
  ให้ Admin ตรวจอีกครั้งว่าได้ยกเว้นโปรเจกต์ `ev-power-energy-prod` หรือปิด enforcement ของ constraint ที่กัน allUsers แล้ว

- **ตรวจสอบว่าเพิ่ม allUsers ไปที่ service ไหน**  
  ต้องเป็น **ai-assistant-frontend** (ไม่ใช่ backend)

- **ดู IAM ของ service**  
  1. Cloud Console → **Cloud Run** → เลือก **ai-assistant-frontend**  
  2. แท็บ **Permissions** (หรือ **Manage custom roles** / IAM)  
  3. ดูว่ามี principal **"All users"** และ role **Cloud Run Invoker** หรือไม่

---

## สรุปคำสั่ง (สำหรับคุณ หลัง Admin แก้แล้ว)

```bash
gcloud config set project ev-power-energy-prod

gcloud run services add-iam-policy-binding ai-assistant-frontend \
  --region=asia-southeast1 \
  --member=allUsers \
  --role=roles/run.invoker \
  --project=ev-power-energy-prod
```

---

## หมายเหตุ

- การให้ `allUsers` = **ใครก็ได้ที่เปิด URL ได้** แต่การเข้าใช้งานจริงยังควบคุมด้วย **login ในแอป (Supabase Auth)** ตามที่ออกแบบไว้
- หลังตั้งค่าแล้ว **ไม่ต้องรันซ้ำ** เว้นแต่มีคนไปลบสิทธิ์ allUsers ออก
- ถ้า deploy Frontend ใหม่ (revision ใหม่) **ไม่ต้อง** ตั้ง allUsers ใหม่ — IAM อยู่ที่ระดับ service ไม่ใช่ revision
- **ถ้าเปิดหน้า Frontend แล้วเบราว์เซอร์ขึ้น CORS error** (เรียก API ไม่ได้): ต้องตั้งค่า Backend ให้อนุญาต origin ของ Frontend ดูรายละเอียดใน [TROUBLESHOOTING_CLOUD_RUN.md](TROUBLESHOOTING_CLOUD_RUN.md) ส่วน "แก้ CORS"
