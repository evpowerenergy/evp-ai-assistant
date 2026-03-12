# ลำดับการรันและไฟล์ที่เกี่ยวข้อง — EVP AI Assistant

> คู่มือรันทีละขั้นอย่างละเอียด (ครั้งแรก + รันซ้ำ)

---

## วิธี deploy: เลือกได้ 2 แบบ

| แบบ | ใช้เมื่อ | ต้องมี GitHub Secrets |
|-----|----------|------------------------|
| **แบบสคริปต์บนเครื่อง (เหมือน CRM)** | รัน `./scripts/deploy-backend.sh` และ `./scripts/deploy-frontend.sh` จากเครื่องคุณ ใช้ไฟล์ `.env.cloudrun` | **ไม่ต้อง** |
| **แบบ CI/CD (GitHub Actions)** | Push ไป `main` แล้ว workflow รันให้อัตโนมัติ | **ต้อง** ตั้ง Secrets ใน repo |

**ถ้าใช้แบบสคริปต์ (เหมือน CRM):** ทำตามส่วนที่ 1 ด้านล่างแค่ขั้น 1.1 และ 1.2 (login + สร้าง Artifact Registry) แล้วข้ามไปส่วน **"Deploy แบบสคริปต์บนเครื่อง"** — ไม่ต้องสร้าง Service Account สำหรับ GitHub และไม่ต้องตั้ง GitHub Secrets

---

## ส่วนที่ 1: ครั้งเดียว (One-time setup)

### ขั้น 1.1 เปิดใช้ GCP และเลือก project

| ทำอะไร | คำสั่ง/การกระทำ |
|--------|------------------|
| Login GCP | `gcloud auth login` |
| ตั้ง project (ใช้ project เดียวกับ CRM) | `gcloud config set project ev-power-energy-prod` |
| เปิดใช้ API (ถ้ายังไม่เคย) | `gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com` |

**หมายเหตุ:** ถ้าใช้ **project เดียวกับ CRM** (ev-power-energy-prod) น่าจะเปิด Cloud Build และ Cloud Run ไว้แล้ว — ไม่ต้อง enable ซ้ำ แค่ตรวจสอบว่ามี **Artifact Registry API** (ใช้เก็บ image ของ ai-assistant) ถ้ายังไม่เคยสร้าง repo ใน project นี้ อาจต้องเปิด `artifactregistry.googleapis.com` ครั้งเดียว

**ไฟล์ใน repo ที่ไม่ต้องแก้:** ไม่มี — เป็นการรันบนเครื่องคุณเท่านั้น

---

### ขั้น 1.2 สร้าง Artifact Registry repo

| ทำอะไร | คำสั่ง |
|--------|--------|
| สร้าง repo ชื่อ `ai-assistant` | `gcloud artifacts repositories create ai-assistant --repository-format=docker --location=asia-southeast1 --project=ev-power-energy-prod` |

**หมายเหตุ:** ถ้าใช้ project อื่น เปลี่ยน `--project=...` ให้ตรงกับที่ใช้

**ไฟล์ใน repo:** ไม่มี — สร้าง resource บน GCP

---

### ขั้น 1.3 สร้าง Service Account และ key (สำหรับ GitHub Actions)

| ทำอะไร | คำสั่ง/การกระทำ |
|--------|------------------|
| สร้าง Service Account (หรือใช้ของ CRM ถ้า project เดียว) | ใน GCP Console: IAM → Service Accounts → Create → ตั้งชื่อ เช่น `github-ai-assistant-deploy` |
| ให้สิทธิ SA | บทบาท: **Cloud Run Admin**, **Artifact Registry Writer**, **Service Account User** (หรือใช้ custom role ที่ให้ deploy + push image ได้) |
| สร้าง key (JSON) | ที่ SA → Keys → Add key → JSON → ดาวน์โหลดไฟล์ |

**ไฟล์ใน repo:** ไม่มี

---

### ขั้น 1.4 ตั้ง GitHub Secrets

ไปที่ repo **SupanatPalee/evp-ai-assistant** → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret name | ค่าที่ใส่ | ใช้เมื่อ |
|-------------|----------|----------|
| `GCP_SA_KEY` | เนื้อทั้งหมดของไฟล์ JSON ที่ดาวน์โหลดจากขั้น 1.3 | ทุก deploy (backend + frontend) |
| `GCP_PROJECT_ID` | (ถ้าไม่ใช้ ev-power-energy-prod) เช่น `my-other-project` | ถ้าใช้คนละ project กับ CRM |
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | Deploy backend |
| `SUPABASE_SERVICE_ROLE_KEY` | ค่า service_role key จาก Supabase | Deploy backend |
| `OPENAI_API_KEY` | ค่า API key จาก OpenAI | Deploy backend |
| `LINE_CHANNEL_SECRET` | (Phase 4) ค่าจาก LINE Developer | Deploy backend |
| `LINE_CHANNEL_ACCESS_TOKEN` | (Phase 4) ค่าจาก LINE Developer | Deploy backend |
| `NEXT_PUBLIC_SUPABASE_URL` | เหมือน SUPABASE_URL (เช่น `https://xxxxx.supabase.co`) | Deploy frontend (build time) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ค่า anon key จาก Supabase | Deploy frontend (build time) |
| `NEXT_PUBLIC_API_URL` | **ใส่หลัง deploy backend ครั้งแรก** — URL ของ service ai-assistant-backend เช่น `https://ai-assistant-backend-xxxxx-as.a.run.app` | Deploy frontend (build time) |

**ไฟล์ใน repo:** ไม่มี — ตั้งใน GitHub เท่านั้น

---

### ขั้น 1.5 รัน migrations บน Supabase (ถ้ายังไม่เคย)

| ทำอะไร | วิธี |
|--------|------|
| รัน migrations | ใช้ Supabase Dashboard → SQL Editor รันไฟล์ใน `supabase/migrations/` ตามลำดับ หรือใช้ `supabase db push` ถ้าใช้ Supabase CLI |

**ไฟล์ใน repo ที่เกี่ยวข้อง:**

- `supabase/migrations/20250116000001_initial_schema.sql`
- `supabase/migrations/20250116000002_initial_rpc_functions.sql`
- … ตามลำดับหมายเลขในชื่อไฟล์

---

## ส่วนที่ 2: Deploy ครั้งแรก (ลำดับสำคัญ)

### ขั้น 2.1 Deploy Backend ก่อน

| ลำดับ | ทำอะไร | ไฟล์ใน repo ที่เกี่ยวข้อง |
|-------|--------|---------------------------|
| 1 | แก้ไขอะไรก็ได้ใน `backend/` หรือ push workflow ของ backend แล้ว **push ไป branch `main`** | อย่างน้อยหนึ่งไฟล์ภายใต้ `backend/**` หรือ `.github/workflows/deploy-backend.yml` |
| 2 | GitHub Actions จะรัน workflow **Deploy Backend to Cloud Run** อัตโนมัติ | Trigger อยู่ที่ `.github/workflows/deploy-backend.yml` |
| 3 | ใน workflow ระบบจะ (ตามลำดับ): | |
| 3.1 | Checkout code | — |
| 3.2 | Set GCP project (จาก Secret หรือ ev-power-energy-prod) | — |
| 3.3 | Auth ด้วย `GCP_SA_KEY` | — |
| 3.4 | Build image ใช้ **backend/cloudbuild.yaml** โดยส่ง context โฟลเดอร์ **backend/** | `backend/cloudbuild.yaml`, `backend/Dockerfile`, ไฟล์ใน `backend/` |
| 3.5 | Push image ไป Artifact Registry ที่ `asia-southeast1-docker.pkg.dev/<PROJECT_ID>/ai-assistant/backend:<git-sha>` | — |
| 3.6 | Deploy Cloud Run service ชื่อ **ai-assistant-backend** ด้วย image นั้น + env จาก Secrets | — |

**สรุปไฟล์ที่ workflow อ่าน/ใช้:**

- `.github/workflows/deploy-backend.yml` — กำหนดขั้นตอน
- `backend/cloudbuild.yaml` — กำหนดวิธี build
- `backend/Dockerfile` — build backend image
- ไฟล์ทั้งหมดใน `backend/` (รวมใน context ที่ส่งไป Cloud Build)

หลัง deploy backend สำเร็จ ให้ copy **URL ของ service** (เช่น `https://ai-assistant-backend-xxxxx-as.a.run.app`) ไปใส่ใน GitHub Secret ชื่อ **NEXT_PUBLIC_API_URL** (ขั้น 1.4) ถ้ายังไม่ได้ใส่

---

### ขั้น 2.2 Deploy Frontend (หลัง backend ได้ URL แล้ว)

| ลำดับ | ทำอะไร | ไฟล์ใน repo ที่เกี่ยวข้อง |
|-------|--------|---------------------------|
| 1 | ให้แน่ใจว่าได้ใส่ **NEXT_PUBLIC_API_URL** ใน GitHub Secrets แล้ว (URL ของ ai-assistant-backend) | — |
| 2 | แก้ไขอะไรก็ได้ใน `frontend/` หรือ push workflow ของ frontend แล้ว **push ไป branch `main`** | อย่างน้อยหนึ่งไฟล์ภายใต้ `frontend/**` หรือ `.github/workflows/deploy-frontend.yml` |
| 3 | GitHub Actions จะรัน workflow **Deploy Frontend to Cloud Run** อัตโนมัติ | Trigger อยู่ที่ `.github/workflows/deploy-frontend.yml` |
| 4 | ใน workflow ระบบจะ: | |
| 4.1 | Checkout, set project, auth | — |
| 4.2 | Build image ใช้ **frontend/cloudbuild.yaml** ส่ง context โฟลเดอร์ **frontend/** และ build-arg จาก Secrets (NEXT_PUBLIC_*) | `frontend/cloudbuild.yaml`, `frontend/Dockerfile`, ไฟล์ใน `frontend/` |
| 4.3 | Push image ไป `.../ai-assistant/frontend:<git-sha>` | — |
| 4.4 | Deploy Cloud Run service ชื่อ **ai-assistant-frontend** | — |

**สรุปไฟล์ที่ workflow อ่าน/ใช้:**

- `.github/workflows/deploy-frontend.yml`
- `frontend/cloudbuild.yaml`
- `frontend/Dockerfile` (รับ ARG NEXT_PUBLIC_* ใน stage builder)
- ไฟล์ทั้งหมดใน `frontend/` (รวมใน context)

---

## ส่วนที่ 3: รันซ้ำ (Redeploy) — อัตโนมัติเมื่อ push main

คุณ **ไม่ต้องรันคำสั่งบนเครื่อง** — แค่ push ไป `main` แล้วระบบจะ deploy ให้ตาม path ที่เปลี่ยน:

| อยาก deploy อะไร | ต้องมีไฟล์ที่เปลี่ยนใน push นี้ | Workflow ที่รัน | ไฟล์ที่ใช้ใน pipeline |
|-------------------|-----------------------------------|------------------|------------------------|
| **Backend** | อย่างน้อยหนึ่งไฟล์ใน `backend/**` หรือ `.github/workflows/deploy-backend.yml` | deploy-backend.yml | deploy-backend.yml → backend/cloudbuild.yaml → backend/Dockerfile + ทั้งหมดใน backend/ |
| **Frontend** | อย่างน้อยหนึ่งไฟล์ใน `frontend/**` หรือ `.github/workflows/deploy-frontend.yml` | deploy-frontend.yml | deploy-frontend.yml → frontend/cloudbuild.yaml → frontend/Dockerfile + ทั้งหมดใน frontend/ |

**หมายเหตุ:** ถ้า push มีทั้งการเปลี่ยนใน `backend/` และ `frontend/` จะรัน **ทั้งสอง workflow** (backend และ frontend).

---

## สรุปตารางไฟล์ตามหน้าที่

| ไฟล์ | ใช้เมื่อ | ใช้โดย |
|------|----------|--------|
| `.github/workflows/deploy-backend.yml` | Push main + เปลี่ยน backend หรือ workflow นี้ | GitHub Actions — กำหนดขั้นตอน deploy backend |
| `.github/workflows/deploy-frontend.yml` | Push main + เปลี่ยน frontend หรือ workflow นี้ | GitHub Actions — กำหนดขั้นตอน deploy frontend |
| `backend/cloudbuild.yaml` | Build backend image | Cloud Build (เรียกจาก deploy-backend workflow) |
| `backend/Dockerfile` | Build backend image | Cloud Build (จาก cloudbuild.yaml) |
| `frontend/cloudbuild.yaml` | Build frontend image | Cloud Build (เรียกจาก deploy-frontend workflow) |
| `frontend/Dockerfile` | Build frontend image (รับ ARG NEXT_PUBLIC_*) | Cloud Build (จาก cloudbuild.yaml) |
| โฟลเดอร์ `backend/` | ทุกครั้ง build backend | ส่งเป็น context ให้ `gcloud builds submit ... backend` |
| โฟลเดอร์ `frontend/` | ทุกครั้ง build frontend | ส่งเป็น context ให้ `gcloud builds submit ... frontend` |
| `supabase/migrations/*.sql` | ครั้งเดียวหรือเมื่อมี migration ใหม่ | รันบน Supabase แยก (ไม่ผ่าน GitHub Actions) |

---

## สรุปลำดับรันแบบสั้น (ครั้งแรก)

1. รันบนเครื่อง (ครั้งเดียว): `gcloud auth login` → `gcloud config set project ev-power-energy-prod` → เปิด API → สร้าง Artifact Registry repo `ai-assistant` → สร้าง SA + key
2. ตั้ง GitHub Secrets ทั้งหมด (รวม NEXT_PUBLIC_API_URL หลังได้ backend URL)
3. รัน migrations บน Supabase (ถ้ายังไม่เคย)
4. Push ไป `main` ที่มีเปลี่ยนใน `backend/` → รอ deploy backend → copy URL ไปใส่ NEXT_PUBLIC_API_URL
5. Push ไป `main` ที่มีเปลี่ยนใน `frontend/` → รอ deploy frontend

หลังจากนั้น แค่ push ไป `main` (มีเปลี่ยน path ตามตารางด้านบน) ระบบจะ build + push image + deploy Cloud Run ให้เองโดยอัตโนมัติ

---

## Deploy แบบสคริปต์บนเครื่อง (เหมือน CRM) — ไม่ใช้ GitHub Secrets

### ขั้นตอนครั้งแรก

1. **สร้างไฟล์ `.env.cloudrun` ที่ root โปรเจกต์**
   ```bash
   cp env.cloudrun.example .env.cloudrun
   ```
   แก้ค่าใน `.env.cloudrun` ให้ตรงกับโปรเจกต์ (Supabase, OpenAI, NEXT_PUBLIC_* ฯลฯ)

2. **Deploy backend ก่อน**
   ```bash
   ./scripts/deploy-backend.sh
   ```
   ใช้ไฟล์: `scripts/deploy-backend.sh` → โหลด `.env.cloudrun` → ใช้ `backend/cloudbuild.yaml` + โฟลเดอร์ `backend/` → build + deploy **ai-assistant-backend**

3. **ใส่ URL ของ backend ใน `.env.cloudrun`**
   หลัง deploy backend เสร็จ จะมี Service URL — copy ไปใส่ใน `NEXT_PUBLIC_API_URL` ใน `.env.cloudrun`

4. **Deploy frontend**
   ```bash
   ./scripts/deploy-frontend.sh
   ```
   ใช้ไฟล์: `scripts/deploy-frontend.sh` → โหลด `.env.cloudrun` → ใช้ `frontend/cloudbuild.yaml` + โฟลเดอร์ `frontend/` → build + deploy **ai-assistant-frontend**

### รันซ้ำ (redeploy)

- Deploy backend อีกครั้ง: `./scripts/deploy-backend.sh`
- Deploy frontend อีกครั้ง: `./scripts/deploy-frontend.sh`

**ไฟล์ที่เกี่ยวข้อง:** `env.cloudrun.example`, `scripts/deploy-backend.sh`, `scripts/deploy-frontend.sh`, `backend/cloudbuild.yaml`, `frontend/cloudbuild.yaml`, `.env.cloudrun` (ไม่ commit)
