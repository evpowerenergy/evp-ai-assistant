# โครงสร้าง Infrastructure และแผน Deploy — EVP AI Assistant

> วิเคราะห์จาก workflows, Dockerfiles และ config ใน repo (อัปเดต: 2025-03-05)

---

## ต้องทำอะไรบ้าง (สรุป)

| ลำดับ | ทำอะไร | หมายเหตุ |
|-------|--------|----------|
| 1 | ใช้ GCP project เดียวกับ CRM | ค่าเริ่มต้น `ev-power-energy-prod` — ต้องการคนละ project ให้ตั้ง Secret `GCP_PROJECT_ID` |
| 2 | สร้าง Artifact Registry repo ชื่อ **ai-assistant** | ครั้งเดียว: `gcloud artifacts repositories create ai-assistant --repository-format=docker --location=asia-southeast1` |
| 3 | ตั้ง GitHub Secrets | `GCP_SA_KEY`, Supabase, OpenAI, NEXT_PUBLIC_* (รวม `NEXT_PUBLIC_API_URL` = URL ของ ai-assistant-backend หลัง deploy backend) |
| 4 | Push ไป `main` | เปลี่ยนใน `backend/**` → deploy backend; เปลี่ยนใน `frontend/**` → deploy frontend |
| 5 | Deploy backend ก่อน แล้วค่อย frontend | หลัง backend ได้ URL แล้ว ไปใส่ใน `NEXT_PUBLIC_API_URL` แล้ว deploy frontend อีกครั้ง |

**Cloud Run services ที่ได้:** `ai-assistant-frontend` และ `ai-assistant-backend` (แยกจาก CRM ชัดเจน)

---

## 1. สรุปภาพรวม

| ส่วน | Deploy ที่ | Region | Trigger |
|------|------------|--------|---------|
| **Frontend** (Next.js) | Google Cloud Run | `asia-southeast1` | Push ไป `main` ที่ path `frontend/**` |
| **Backend** (FastAPI) | Google Cloud Run | `asia-southeast1` | Push ไป `main` ที่ path `backend/**` |
| **Database / Auth / RPC / Vector** | Supabase (managed) | ตามที่ตั้งค่าใน Supabase | ไม่ deploy ผ่าน repo นี้ — ใช้ migrations ใน Supabase |
| **LINE** (Phase 4) | Webhook ไปที่ Backend URL | — | Backend ที่ Cloud Run เป็น webhook endpoint |

---

## 2. แผน Infrastructure แบบภาพ

```
                    Internet
                        │
    ┌───────────────────┼───────────────────┐
    │                   │                   │
    ▼                   ▼                   ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Frontend   │   │   Backend   │   │   LINE      │
│  (Next.js)  │──▶│  (FastAPI)  │◀──│  Webhook    │
│  Cloud Run  │   │  Cloud Run  │   │  (Phase 4)  │
└─────────────┘   └──────┬──────┘   └─────────────┘
                        │
                        │ SUPABASE_URL + SERVICE_ROLE_KEY
                        ▼
              ┌─────────────────────┐
              │      Supabase       │
              │  • Auth (JWT)       │
              │  • PostgreSQL       │
              │  • RPC (15+ fn)     │
              │  • pgvector (RAG)   │
              └─────────────────────┘
                        │
                        │ OPENAI_API_KEY (จาก Backend env)
                        ▼
              ┌─────────────────────┐
              │      OpenAI API      │
              └─────────────────────┘
```

---

## 3. Deploy อยู่ที่ไหนบ้าง

### 3.1 Google Cloud Run (GCP)

- **Project:** ใช้ project เดียวกับ CRM โดยค่าเริ่มต้นคือ **ev-power-energy-prod** (override ได้ด้วย GitHub Secret `GCP_PROJECT_ID`)
- **Region:** `asia-southeast1` (Singapore — ใกล้ไทย)
- **Artifact Registry:** repo ชื่อ **ai-assistant** เก็บ image แยกเป็น `backend` และ `frontend` (ไม่ปนกับ CRM)
- **Services (Cloud Run):**
  - **ai-assistant-frontend** — Next.js, port 8080, image จาก `.../ai-assistant/frontend:sha`
  - **ai-assistant-backend** — FastAPI (uvicorn), port 8080, image จาก `.../ai-assistant/backend:sha`
- **การเข้าถึง:** ทั้งคู่ตั้ง `--allow-unauthenticated` (การควบคุมสิทธิ์ทำที่แอป: Supabase Auth + Backend RBAC)

### 3.2 Supabase (Managed)

- **ใช้ทำ:** Auth, PostgreSQL, RPC functions, pgvector (vector store สำหรับ RAG)
- **ไม่ deploy ผ่าน repo นี้:** รัน migrations ผ่าน Supabase Dashboard หรือ Supabase CLI แยกต่างหาก
- โปรเจกต์มีโฟลเดอร์ `supabase/migrations/` สำหรับ schema และ RPC

### 3.3 บริการภายนอกที่เชื่อมกับ Backend

- **OpenAI API** — เรียกจาก Backend (ใช้ `OPENAI_API_KEY` ใน env)
- **LINE** (Phase 4) — Webhook ชี้ไปที่ URL ของ Backend บน Cloud Run

---

## 4. CI/CD (GitHub Actions)

- **Trigger:** Push ไป branch **main** เท่านั้น (ไม่มี workflow สำหรับ `dev`)
- **แยกตาม path:**
  - เปลี่ยนเฉพาะ `backend/**` หรือ `.github/workflows/deploy-backend.yml` → รัน **Deploy Backend to Cloud Run**
  - เปลี่ยนเฉพาะ `frontend/**` หรือ `.github/workflows/deploy-frontend.yml` → รัน **Deploy Frontend to Cloud Run**
- **Auth กับ GCP:** ใช้ GitHub Secrets `GCP_SA_KEY` (service account JSON)
- **Deploy แบบ image-based (แยก Artifact กับ Cloud Run):**
  1. Build Docker image ด้วย **Cloud Build** (ใช้ `backend/cloudbuild.yaml` หรือ `frontend/cloudbuild.yaml`)
  2. Push image ไป **Artifact Registry** repo `ai-assistant` (image ชื่อ `backend` หรือ `frontend`, tag = git SHA)
  3. Deploy Cloud Run ด้วย `gcloud run deploy ... --image <image_url>`

### 4.1 Backend workflow สรุป

1. Set GCP project (default `ev-power-energy-prod`, override ด้วย Secret `GCP_PROJECT_ID`)
2. Authenticate ด้วย `GCP_SA_KEY`
3. `gcloud builds submit --config=backend/cloudbuild.yaml backend` → push ไป `.../ai-assistant/backend:<sha>`
4. `gcloud run deploy ai-assistant-backend --image <image>` ที่ region `asia-southeast1`
5. ส่ง env ผ่าน `--set-env-vars`: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY, LINE_* (จาก GitHub Secrets)

### 4.2 Frontend workflow สรุป

1. Set GCP project (เหมือน backend)
2. Authenticate ด้วย `GCP_SA_KEY`
3. `gcloud builds submit --config=frontend/cloudbuild.yaml frontend` พร้อม build-arg (NEXT_PUBLIC_*) → push ไป `.../ai-assistant/frontend:<sha>`
4. `gcloud run deploy ai-assistant-frontend --image <image>` ที่ region `asia-southeast1`

---

## 5. Docker และ Cloud Build

- **backend/Dockerfile:** Python 3.12-slim, uvicorn port 8080
- **backend/cloudbuild.yaml:** build image จาก context `backend/`, tag ไป `_IMAGE`
- **frontend/Dockerfile:** Node 18 multi-stage, รับ ARG NEXT_PUBLIC_* ตอน build, Next.js standalone, port 8080
- **frontend/cloudbuild.yaml:** build พร้อม build-arg (NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL), tag ไป `_IMAGE`
- **next.config.js:** `output: 'standalone'` สำหรับ deploy

---

## 6. Secrets / Environment ที่ต้องตั้ง

### 6.1 GitHub Secrets (สำหรับ CI และส่งเข้า Cloud Run)

| Secret | ใช้โดย |
|--------|--------|
| `GCP_SA_KEY` | ทุก workflow — auth กับ GCP, build image, deploy Cloud Run |
| `GCP_PROJECT_ID` | (ถ้าต้องการ) override project — ไม่ตั้งจะใช้ `ev-power-energy-prod` |
| `SUPABASE_URL` | Backend deploy (env ใน Cloud Run) |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend deploy |
| `OPENAI_API_KEY` | Backend deploy |
| `LINE_CHANNEL_SECRET` | Backend deploy (Phase 4) |
| `LINE_CHANNEL_ACCESS_TOKEN` | Backend deploy (Phase 4) |
| `NEXT_PUBLIC_SUPABASE_URL` | Frontend build (build-arg ใน Cloud Build) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Frontend build (build-arg ใน Cloud Build) |
| `NEXT_PUBLIC_API_URL` | Frontend build (build-arg) — ชี้ไป URL ของ **ai-assistant-backend** บน Cloud Run |

### 6.2 สิ่งที่ต้องทำก่อน deploy จริง

1. **GCP project**  
   ใช้ project เดียวกับ CRM (default **ev-power-energy-prod**). ถ้าใช้คนละ project ให้ตั้ง GitHub Secret ชื่อ `GCP_PROJECT_ID`.

2. **สร้าง Artifact Registry repo** (ครั้งเดียวต่อ project)  
   ใน project นั้นสร้าง repo ชื่อ **ai-assistant** (format Docker, region ตาม Cloud Run เช่น asia-southeast1):
   ```bash
   gcloud artifacts repositories create ai-assistant \
     --repository-format=docker \
     --location=asia-southeast1 \
     --project=ev-power-energy-prod
   ```
   **ถ้าใช้ project เดียวกับ CRM:** Cloud Build และ Cloud Run น่าจะเปิดไว้แล้ว แค่ตรวจสอบว่ามี Artifact Registry API (ถ้าสร้าง repo ไม่ได้ ให้รัน `gcloud services enable artifactregistry.googleapis.com`)

3. **Service Account**  
   สร้าง SA ที่มีสิทธิ deploy Cloud Run + push image ไป Artifact Registry (หรือใช้ SA เดียวกับ CRM ถ้าใช้ project เดียว). สร้าง key เป็น JSON แล้วใส่ใน GitHub Secret ชื่อ `GCP_SA_KEY`.

4. **GitHub Secrets**  
   ตั้งค่าตามตารางใน repo `SupanatPalee/evp-ai-assistant` (รวมถึง `NEXT_PUBLIC_API_URL` = URL ของ service **ai-assistant-backend** บน Cloud Run หลัง deploy backend ครั้งแรก).

5. **Supabase**  
   รัน migrations ใน `supabase/migrations/` ให้ครบ.

6. **ลำดับ deploy**  
   Deploy backend ก่อน → copy URL ของ ai-assistant-backend ไปใส่ใน `NEXT_PUBLIC_API_URL` (และใน GitHub Secret) → deploy frontend.

---

## 7. สรุปคำตอบคำถาม

- **โปรเจกต์วางแผน infra ยังไง?**  
  แยก Frontend กับ Backend เป็นคนละ service บน **Google Cloud Run** (region asia-southeast1), ใช้ **Supabase** เป็นที่เก็บข้อมูล/Auth/RPC/vector, ใช้ **GitHub Actions** deploy อัตโนมัติเมื่อ push ไป `main` แยกตาม path (backend/** หรือ frontend/**).

- **Deploy ไว้ที่ไหนบ้าง?**  
  - **Frontend:** Google Cloud Run service ชื่อ `ai-assistant-frontend`  
  - **Backend:** Google Cloud Run service ชื่อ `ai-assistant-backend`  
  - **Database / Auth / RPC / Vector:** Supabase (managed, ไม่ได้ “deploy” จาก repo นี้ แค่รัน migrations)  
  - **LINE:** ใช้ Backend URL บน Cloud Run เป็น webhook (Phase 4)

---

## 8. หมายเหตุเพิ่มเติม

- ตอนนี้มี branch **dev** แต่ workflow deploy ยัง trigger แค่จาก **main** — ถ้าอยากให้ push ไป dev ไม่ deploy production ให้ใช้แบบนี้ได้เลย
- ถ้าอยากให้มี “staging” แยก (เช่น deploy จาก branch `dev` ไปอีก project หรืออีก service บน Cloud Run) ต้องเพิ่ม workflow ใหม่และอาจแยก GCP project หรือ service name
