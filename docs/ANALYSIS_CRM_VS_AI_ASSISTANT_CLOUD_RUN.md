# วิเคราะห์: ทำไม CRM เปิดได้ แต่ AI Assistant Frontend ขึ้น Forbidden (โปรเจกต์เดียวกัน แยก Service)

## สถานการณ์

- **โปรเจกต์ GCP:** เดียวกัน — `ev-power-energy-prod`
- **Cloud Run services:** แยกคนละตัว
  - CRM: `ev-power-crm-frontend`
  - AI Assistant: `ai-assistant-frontend` (และ `ai-assistant-backend`)
- **ปัญหา:** เปิด Frontend AI Assistant ได้ Forbidden, อยากให้เปิดได้แบบ public (มี login ในแอปอยู่แล้ว)

---

## 1. ความแตกต่างของคำสั่ง deploy

### CRM (`ev-power-energy-crm/scripts/deploy-gcp.sh`)

```bash
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --port 8080 \
  --no-invoker-iam-check
```

- **ไม่มี** `--allow-unauthenticated`
- มีแค่ `--no-invoker-iam-check` (ข้ามการเช็คสิทธิ์ผู้รันคำสั่ง ไม่เกี่ยวกับการให้สิทธิ์ผู้เรียก)
- ดังนั้นตอน deploy CRM **gcloud จะไม่พยายามเพิ่ม principal `allUsers`** ให้ service นี้

### AI Assistant Frontend (`evp-ai-assistant/scripts/deploy-frontend.sh`)

```bash
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --port 8080 \
  --allow-unauthenticated
```

- **มี** `--allow-unauthenticated`
- ตอน deploy จะพยายาม **เพิ่ม IAM binding `allUsers` + role `roles/run.invoker`** ให้ service นี้
- เลยไปชน **Organization policy** ที่ห้ามเพิ่ม principal แบบ “ทุกคนบนอินเทอร์เน็ต” → error และไม่มีสิทธิ์ public

---

## 2. ทำไม CRM ถึง “ไม่มีปัญหา” (เปิดได้)

ได้หลายกรณี แยกตามความเป็นไปได้ดังนี้

### กรณี A: CRM ได้ allUsers ไปก่อน (โดยวิธีอื่น หรือก่อนมี policy)

- สคริปต์ CRM **ไม่เคยส่ง** `--allow-unauthenticated` ดังนั้นตอน deploy ตามสคริปต์จะไม่มีการเพิ่ม `allUsers`
- ถ้าวันนี้ CRM เปิดจากเน็ตได้จริง แปลว่า **allUsers ต้องถูกเพิ่มด้วยวิธีอื่น** เช่น
  - มีคนไปกด “Allow unauthenticated invocations” ใน Console ของ service `ev-power-crm-frontend`
  - หรือรัน `gcloud run services add-iam-policy-binding ... --member=allUsers` ไว้เมื่อก่อน
- ถ้าการเพิ่มนั้นเกิด **ก่อน** ที่องค์กรเปิดใช้ policy “ห้าม allUsers” → การตั้งค่าเก่าจะยังอยู่ ไม่ถูกลบ
- Policy มักจะ **กันแค่การเพิ่ม allUsers ครั้งใหม่** ไม่ได้ไปลบ binding เดิมของ CRM

→ **สรุป:** CRM “ไม่มีปัญหา” เพราะ **มี allUsers อยู่แล้วจากอดีต** และไม่ได้ถูก deploy ใหม่ด้วย `--allow-unauthenticated` ที่ต้องไปชน policy

### กรณี B: CRM จริงๆ ไม่ได้ public (ไม่มี allUsers)

- ถ้า service CRM **ไม่มี** principal `allUsers` เลย
- แล้วคุณเปิด CRM ได้ อาจเป็นเพราะคุณเปิดจากเครื่อง/บัญชีที่ **มีสิทธิ์ GCP** อยู่แล้ว (เช่น โปรเจกต์นี้ให้ role ที่มี `run.invoker` กับบัญชีคุณ)
- ในทาง IAM ถ้าไม่มี allUsers คนที่ไม่มีสิทธิ์ (เช่น เปิดใน incognito / คนนอกองค์กร) จะต้อง Forbidden เหมือนกัน

→ **สรุป:** ในกรณีนี้ CRM ก็ “มีปัญหา” แบบเดียวกัน แค่คุณไม่เจอเพราะคุณมีสิทธิ์อยู่แล้ว

### กรณี C: โปรเจกต์ / โฟลเดอร์ต่างกัน (ถ้าไม่ใช้โปรเจกต์เดียวกันจริงๆ)

- ถ้า CRM อยู่คนละ **project** หรือคนละ **folder** ที่ถูกยกเว้นจาก policy
- การเพิ่ม allUsers อาจทำได้ที่ CRM แต่ทำไม่ได้ที่ AI Assistant

จากที่คุณบอกว่า “โปรเจกต์เดียวกัน แยก deploy คนละ Service” จึงสมมติว่าเป็นโปรเจกต์เดียวกัน และความต่างอยู่ที่ **การมี/ไม่มี allUsers ในแต่ละ service** กับ **เวลา/วิธีที่เพิ่ม allUsers**

---

## 3. สิ่งที่ควรตรวจ (เพื่อให้วิเคราะห์ตรงจริง)

ในโปรเจกต์ `ev-power-energy-prod`:

1. **ดู IAM ของแต่ละ service ว่าใครมีสิทธิ์ invoke**
   - Cloud Run → เลือก **ev-power-crm-frontend** → แท็บ **Permissions** (หรือ IAM) → ดูว่ามี principal **“All users”** (allUsers) หรือไม่
   - ทำเหมือนกันกับ **ai-assistant-frontend**
2. **ทดสอบว่า CRM จริงๆ public หรือไม่**
   - เปิด URL ของ CRM ใน **โหมดไม่ล็อกอิน** (incognito / browser อื่นที่ไม่ได้ล็อกอิน Google ที่มีสิทธิ์)
   - ถ้าเปิดได้ = CRM มี allUsers จริง → สอดคล้องกับกรณี A
   - ถ้าเปิดไม่ได้ = CRM ก็ private → สอดคล้องกับกรณี B

---

## 4. สรุปความต่างและทางออก

| หัวข้อ | CRM | AI Assistant Frontend |
|--------|-----|------------------------|
| สคริปต์ deploy | **ไม่มี** `--allow-unauthenticated` | **มี** `--allow-unauthenticated` |
| ผลตอน deploy | ไม่พยายามเพิ่ม allUsers → ไม่ชน org policy | พยายามเพิ่ม allUsers → ชน org policy |
| สาเหตุที่ CRM “ไม่มีปัญหา” | (ถ้าเปิดได้จากเน็ต) น่าจะได้ allUsers ไปก่อนแล้วโดยวิธีอื่น/ก่อนมี policy | ต้องการ allUsers แต่ถูก policy กันไว้ |

**ทางออกสำหรับ AI Assistant Frontend:**

- **ถ้าองค์กรอนุญาต:** ให้ admin ปลด/ยกเว้น policy ที่ห้าม allUsers (หรือยกเว้นโปรเจกต์นี้) แล้วค่อยรัน `gcloud run services add-iam-policy-binding ai-assistant-frontend ... --member=allUsers --role=roles/run.invoker` อีกครั้ง
- **ถ้าองค์กรไม่ให้ใช้ allUsers:** ใช้แบบ “ให้เฉพาะ user/group เรียกได้” (เพิ่ม member เป็น user/group แทน allUsers) แล้วให้คนที่ใช้ล็อกอิน Google ที่อยู่ในรายการนั้น

ถ้าต้องการให้สคริปต์ AI Assistant **ไม่ไปชน policy** (ไม่ให้ gcloud พยายามเพิ่ม allUsers ตอน deploy) สามารถเอา `--allow-unauthenticated` ออกจาก `deploy-frontend.sh` ได้ แล้วค่อยไปเพิ่ม allUsers (หรือ user/group) ผ่าน Console / gcloud แยกต่างหาก หลัง admin ปลด policy หรือเมื่อตัดสินใจแล้วว่าจะให้ใคร invoke
