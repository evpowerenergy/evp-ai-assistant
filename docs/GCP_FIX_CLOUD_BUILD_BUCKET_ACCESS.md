# แก้สิทธิ์ให้ deploy ผ่าน Cloud Build ได้ (bucket ev-power-energy-prod_cloudbuild)

ใช้เอกสารนี้เมื่อ **ทั้ง AI Assistant และ CRM** deploy ไม่ผ่าน ด้วย error:

```text
The user is forbidden from accessing the bucket [ev-power-energy-prod_cloudbuild].
Please check your organization's policy or if the user has the "serviceusage.services.use" permission.
```

โปรเจกต์ที่เกี่ยวข้อง: **ev-power-energy-prod** (ใช้ร่วมกันทั้ง CRM และ AI Assistant)

---

## สรุปสาเหตุ

บัญชีที่รัน `./scripts/deploy-backend.sh` หรือ `./scripts/deploy-gcp.sh` (เช่น **admin@evpowerenergy.com**) ไม่มีสิทธิ์ **เขียน** bucket เริ่มต้นของ Cloud Build (`ev-power-energy-prod_cloudbuild`) จึงอัปโหลด source ไม่ได้

---

## ขั้นตอนสำหรับคนรัน deploy (ตรวจก่อน)

1. **ตรวจใช้บัญชีและโปรเจกต์ถูก**
   ```bash
   gcloud auth list
   gcloud config get-value project
   ```
   - บัญชีที่ active ต้องเป็นบัญชีที่ Admin จะให้สิทธิ์ (เช่น admin@evpowerenergy.com)
   - โปรเจกต์ต้องเป็น `ev-power-energy-prod`

2. **ถ้ายัง deploy ไม่ได้** → ส่งเอกสารส่วน "ขั้นตอนสำหรับ GCP Admin" ด้านล่างให้คนดูแลโปรเจกต์

---

## ขั้นตอนสำหรับ GCP Admin (แก้สิทธิ์)

ให้บัญชีที่ใช้รัน deploy (เช่น **admin@evpowerenergy.com**) มีสิทธิ์ดังนี้ในโปรเจกต์ **ev-power-energy-prod**:

### วิธีที่ 1: ให้ role ที่ครอบครำ (แนะนำ)

1. เปิด **Google Cloud Console** → เลือกโปรเจกต์ **ev-power-energy-prod**
2. ไปที่ **IAM & Admin** → **IAM**
3. หา principal (เช่น admin@evpowerenergy.com):
   - ถ้ามีอยู่แล้ว → กดแก้ (ดินสอ) แล้ว **เพิ่ม role**: **Cloud Build Editor**
   - ถ้าไม่มี → กด **Grant access** → ใส่ principal → เลือก role **Cloud Build Editor** (และถ้าต้อง deploy Cloud Run ด้วย ให้มี **Cloud Run Admin** ด้วย)
4. Save

**Cloud Build Editor** มีสิทธิ์ใช้ Cloud Build และเขียน object ใน bucket ที่ Cloud Build ใช้ (รวม default bucket)

### วิธีที่ 2: ให้สิทธิ์ที่ bucket โดยตรง (ถ้าวิธีที่ 1 ไม่พอ หรือ bucket ถูกจำกัดแยก)

1. เปิด **Cloud Storage** → **Buckets**
2. เลือก bucket **ev-power-energy-prod_cloudbuild**
3. ไปที่แท็บ **Permissions**
4. กด **Grant access**
5. **New principals:** ใส่อีเมลบัญชีที่รัน deploy (เช่น admin@evpowerenergy.com)
6. **Role:** เลือก **Storage Object Admin** หรือ **Cloud Build Editor**
7. Save

### สิทธิ์ที่ต้องมี (สรุป)

บัญชีที่รัน deploy ต้องมีอย่างน้อยหนึ่งในนี้ในโปรเจกต์ **ev-power-energy-prod**:

| ทางเลือก | Role |
|----------|------|
| แนะนำ | **Cloud Build Editor** (และ **Cloud Run Admin** ถ้าต้อง deploy ขึ้น Cloud Run) |
| หรือ | **Editor** หรือ **Owner** ของโปรเจกต์ |

และต้องมีสิทธิ์ใช้บริการ (quota):

- **Service Usage Consumer** (มักมีอยู่แล้วถ้ามี Cloud Build Editor / Editor)

ถ้ามี **Organization policy** จำกัดการเข้าถึง default Cloud Build bucket ต้องไปแก้ที่ **IAM & Admin** → **Organization policies** ระดับองค์กร

---

## หลังแก้สิทธิ์แล้ว

ให้คนที่รัน deploy ลองอีกครั้ง (จาก repo AI Assistant หรือ CRM):

```bash
# AI Assistant
cd /path/to/evp-ai-assistant
./scripts/deploy-backend.sh

# CRM
cd /path/to/ev-power-energy-crm
./scripts/deploy-gcp.sh
```

ถ้ายังไม่ผ่าน ให้ลอง **build บนเครื่อง** (ไม่ใช้ Cloud Build):

```bash
# AI Assistant เท่านั้น (สคริปต์ CRM ยังไม่มีโหมด --local)
./scripts/deploy-backend.sh --local
```
