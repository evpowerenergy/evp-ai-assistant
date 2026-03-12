# วิธีดู Container Logs บน Cloud Run (ให้เห็น error จริง)

## สิ่งที่คุณเห็นก่อนหน้านี้

Log ที่คุณส่งมาคือ **Cloud Run audit / health check** — เป็นข้อความว่า "health check ไม่ผ่าน" **ไม่ใช่** output จาก process ใน container (ไม่เห็น Python traceback หรือข้อความจาก entrypoint)

## วิธีดู log ที่ออกจาก container จริง

### วิธีที่ 1: Logs Explorer (ใน GCP Console)

1. ไปที่ **Google Cloud Console** → **Logging** → **Logs Explorer**
2. ใส่ **query** ด้านล่าง (แก้ revision name ถ้าไม่ใช่ 00005-r9d):

```
resource.type="cloud_run_revision"
resource.labels.service_name="ai-assistant-backend"
resource.labels.revision_name="ai-assistant-backend-00005-r9d"
```

3. กด **Run query**
4. ดู log ที่ **ไม่ใช่** `cloudaudit.googleapis.com/system_event` — หา log ที่เป็น **stdout/stderr จาก container** (มักเป็น `textPayload` หรือ `jsonPayload.message`)
5. ถ้ามีข้อความ **"Starting backend: PORT=8080"** แปลว่า entrypoint รันแล้ว ดูบรรทัดถัดไปว่ามี **Python traceback** หรือ error อะไร

### วิธีที่ 2: หน้า Cloud Run → Logs

1. ไปที่ **Cloud Run** → เลือก service **ai-assistant-backend**
2. แท็บ **Logs** (หรือ **LOGS**)
3. ใช้ filter หรือเลือก **revision** ที่ deploy ไม่ผ่าน (เช่น 00005-r9d)
4. ดู log จาก **container** (ไม่ใช่ "Service revision ..." หรือ system event) — ควรเห็นข้อความจาก process ของเราและ Python ถ้ามี crash

### วิธีที่ 3: รัน container บนเครื่อง (เห็น error ชัดที่สุด)

รัน image เดียวกับบน Cloud Run ด้วย env เดียวกัน แล้วดู error บนเทอร์มินัล:

```bash
cd /path/to/evp-ai-assistant
./scripts/run-backend-local.sh
```

(ต้องมี `.env.cloudrun` และเคย `gcloud auth configure-docker asia-southeast1-docker.pkg.dev` แล้ว)

- ถ้าแอป **crash** จะมี **Python traceback โผล่บนเทอร์มินัล** — ใช้ข้อความนี้เป็นหลักในการแก้
- ถ้าแอป **รันได้** แปลว่าปัญหาอาจเป็นเฉพาะบน Cloud Run (เวลา/ทรัพยากร/network)

## สรุป

- Log ที่คุณส่งมา = **ผลลัพธ์** (health check ไม่ผ่าน) ไม่ใช่ **สาเหตุ** (ข้อความจาก container)
- ต้องไปดู **container logs** (วิธี 1 หรือ 2) หรือ **รัน container บนเครื่อง** (วิธี 3) จึงจะเห็น Python error / traceback จริง
