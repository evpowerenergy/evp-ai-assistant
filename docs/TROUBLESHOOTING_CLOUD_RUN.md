# แก้ CORS: Frontend เรียก Backend ไม่ได้ (No 'Access-Control-Allow-Origin')

ถ้าเปิด Frontend บน Cloud Run แล้วเบราว์เซอร์ขึ้น error ประมาณ:

- `Access to XMLHttpRequest at 'https://...backend.../api/v1/me' from origin 'https://...frontend...' has been blocked by CORS policy`
- `No 'Access-Control-Allow-Origin' header is present on the requested resource`

**สาเหตุ:** Backend ยังไม่ได้อนุญาต origin ของ Frontend ใน CORS

**วิธีแก้:**

1. **ถ้า deploy ด้วยสคริปต์** (`./scripts/deploy-backend.sh`):
   - ใน `.env.cloudrun` ใส่ `CORS_ORIGINS` ให้เป็น URL ของ Frontend บน Cloud Run (ไม่มี slash ท้าย)
   - ตัวอย่าง: `export CORS_ORIGINS=https://ai-assistant-frontend-1089649909937.asia-southeast1.run.app`
   - แล้วรัน deploy backend อีกครั้ง

2. **ถ้า deploy ผ่าน GitHub Actions:**
   - ใน GitHub repo → **Settings** → **Secrets and variables** → **Actions**
   - สร้าง secret ชื่อ `CORS_ORIGINS` ค่า = URL ของ Frontend (เช่น `https://ai-assistant-frontend-1089649909937.asia-southeast1.run.app`)
   - push ให้ workflow deploy backend รันอีกครั้ง

3. **แก้ผ่าน GCP Console (ไม่ต้อง deploy ใหม่):**
   - ไปที่ Cloud Run → เลือก service **ai-assistant-backend** → แก้ revision / Edit & Deploy New Revision
   - ใน **Variables & Secrets** เพิ่มตัวแปร `CORS_ORIGINS` = `https://ai-assistant-frontend-1089649909937.asia-southeast1.run.app` (ใช้ URL จริงของ frontend คุณ)
   - Deploy

หลังตั้งค่าแล้ว รอ revision ใหม่เสร็จ แล้วลองโหลดหน้า Frontend ใหม่ (หรือ hard refresh)

---

# Error: forbidden from accessing the bucket [PROJECT_cloudbuild]

ถ้ารัน `./scripts/deploy-backend.sh` แล้วขึ้น:

```text
ERROR: (gcloud.builds.submit) The user is forbidden from accessing the bucket [ev-power-energy-prod_cloudbuild].
```

**สาเหตุ:** บัญชีคุณไม่มีสิทธิ์ใช้ Cloud Build หรือเข้าถึง bucket ของ Cloud Build (อาจถูกจำกัดโดย organization policy)

**หมายเหตุ:** โปรเจกต์นี้ใช้รูปแบบ deploy แบบเดียวกับ CRM (config ที่ root, ส่ง source เป็นโฟลเดอร์ปัจจุบัน). ถ้า deploy CRM ได้แต่ AI Assistant ไม่ได้ อาจเป็นคนละโปรเจกต์/บัญชีหรือสิทธิ์เปลี่ยนไป

**ทางเลือก:**

1. **Build บนเครื่องแล้ว push ไป GCP** (ไม่ใช้ Cloud Build):
   ```bash
   ./scripts/deploy-backend.sh --local
   ```
   ต้องมี Docker ติดตั้งบนเครื่อง และบัญชีต้อง push image ไป Artifact Registry กับ deploy Cloud Run ได้ (เช่น roles/run.admin, roles/artifactregistry.writer)

2. **ให้ Admin เพิ่มสิทธิ์** — ให้สิทธิ์ Cloud Build Editor หรือแก้ org policy ที่กันการเข้าถึง bucket `PROJECT_cloudbuild`

3. **ใช้ GitHub Actions แทน** — ถ้า repo ใช้ CI deploy อยู่แล้ว ให้ push ขึ้น repo แล้วให้ workflow ใน GCP ทำ build/deploy (ใช้ service account ที่มีสิทธิ์)

---

# วิเคราะห์ Error: Container failed to start and listen on PORT

## ความหมายของ Error

ข้อความ `The user-provided container failed to start and listen on the port defined provided by the PORT=8080 environment variable within the allocated timeout` หมายความว่า:

- Cloud Run รอให้ **process ใน container เริ่มฟังพอร์ต 8080** ภายในเวลาที่กำหนด (ปกติไม่เกิน 240 วินาที)
- ภายในเวลานั้น **ยังไม่มี process ใด bind กับ 0.0.0.0:8080** เลย
- เลยถือว่า deploy ล้มเหลว

## สาเหตุที่เป็นไปได้ (เรียงจากที่พบบ่อย)

| สาเหตุ | อธิบาย | วิธีตรวจ |
|--------|--------|----------|
| **1. แอป crash ก่อนฟังพอร์ต** | Python แคชหรือ exception ตอนโหลด (import config, routers, LangChain ฯลฯ) ทำให้ process จบก่อน uvicorn bind พอร์ต | ดู **Cloud Run Logs** หรือรัน container บนเครื่อง (ด้านล่าง) |
| **2. โหลดช้า (cold start)** | โหลด dependencies หนัก (LangChain, LangGraph ฯลฯ) นานกว่าเวลาที่ Cloud Run รอ | เห็นใน logs ว่ามี "Starting backend: PORT=8080" แต่ไม่มี "Uvicorn running" |
| **3. พอร์ต/โฮสต์ผิด** | แอปฟังที่ localhost หรือพอร์ตอื่น ไม่ใช่ 0.0.0.0:PORT | เราใช้ `--host 0.0.0.0 --port $PORT` ใน entrypoint แล้ว น่าจะถูก |
| **4. env ไม่ถึง container** | ค่า SUPABASE_* / OPENAI_* ไม่ถูกส่งหรือผิดรูปแบบ → แอป crash ตอนโหลด config | ดู logs ว่ามี ValidationError หรือข้อความจาก pydantic หรือไม่ |

## ขั้นตอนที่ควรทำ (เพื่อวิเคราะห์ต่อ)

### 1. ดู Cloud Run Logs (สำคัญที่สุด)

1. เปิดลิงก์ **Logs** ที่แสดงใน error (หรือไปที่ GCP Console → Cloud Run → ai-assistant-backend → Logs)
2. เลือก revision ล่าสุดที่ deploy ไม่ผ่าน (เช่น ai-assistant-backend-00005-r9d)
3. ดูว่ามีข้อความใดบ้าง โดยเฉพาะ:
   - **"Starting backend: PORT=8080"** → แปลว่า entrypoint รันแล้ว แต่อาจ crash หลังบรรทัดนี้
   - **Python traceback / ValidationError / ModuleNotFoundError** → นี่คือสาเหตุจริง ให้ copy ข้อความทั้งหมดมา

ถ้าไม่เห็น "Starting backend" เลย แปลว่าอาจมีปัญหาเรื่อง image หรือ entrypoint (เช่น line ending ของ script)

### 2. รัน container บนเครื่อง (เห็น error ชัดที่สุด)

รัน container ด้วย env เดียวกับ Cloud Run แล้วดู error บนเทอร์มินัล:

```bash
cd /path/to/evp-ai-assistant
source .env.cloudrun

docker run --rm -p 8080:8080 \
  -e PORT=8080 \
  -e SUPABASE_URL="$SUPABASE_URL" \
  -e SUPABASE_SERVICE_ROLE_KEY="$SUPABASE_SERVICE_ROLE_KEY" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e LINE_CHANNEL_SECRET="${LINE_CHANNEL_SECRET:-}" \
  -e LINE_CHANNEL_ACCESS_TOKEN="${LINE_CHANNEL_ACCESS_TOKEN:-}" \
  asia-southeast1-docker.pkg.dev/ev-power-energy-prod/ai-assistant/backend:latest
```

- ถ้าแอป **crash** จะมี Python traceback โผล่บนเทอร์มินัล → ใช้ข้อความนี้เป็นหลักในการแก้
- ถ้าแอป **รันได้** (เห็น "Uvicorn running" และเรียก http://localhost:8080 ได้) แปลว่าปัญหาอาจเป็นเรื่อง env บน Cloud Run หรือเวลาโหลดเกิน timeout

(ถ้าไม่ได้ login Docker กับ GCP: `gcloud auth configure-docker asia-southeast1-docker.pkg.dev --quiet`)

### 3. ตรวจ env ใน .env.cloudrun

- มี `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY` ครบและไม่เว้นวรรกหรือใส่ผิดบรรทัด
- ค่าไม่มี comma กลาง string (เราใช้ env file แล้ว ไม่น่าพังจาก comma)
- ถ้า copy จากที่อื่น ตรวจว่าไม่มีตัวอักษรพิเศษหรือ BOM ที่ทำให้อ่านผิด

## สรุป

- Error นี้แปลว่า **ยังไม่มี process ฟัง 0.0.0.0:8080 ภายในเวลาที่ Cloud Run รอ**
- สาเหตุที่พบบ่อย: **แอป crash ตอนโหลด** (config/import) หรือ **โหลดช้าเกิน timeout**
- ขั้นต่อไป: **ดู Logs ใน Cloud Run** และ/หรือ **รัน container บนเครื่องด้วยคำสั่งด้านบน** แล้วนำข้อความ error (โดยเฉพาะ Python traceback) มาวิเคราะห์ต่อ
