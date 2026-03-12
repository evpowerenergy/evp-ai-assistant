#!/usr/bin/env bash
# Deploy AI Assistant Frontend ไป GCP Cloud Run (แบบเดียวกับ CRM — รันบนเครื่อง + ใช้ .env.cloudrun)
# ใช้: จาก root โปรเจกต์รัน ./scripts/deploy-frontend.sh
# ควร deploy backend ก่อน แล้วใส่ NEXT_PUBLIC_API_URL ใน .env.cloudrun ให้ชี้ไป backend URL

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f frontend/cloudbuild.yaml || ! -f frontend/Dockerfile ]]; then
  echo "❌ ไม่พบ frontend/cloudbuild.yaml หรือ frontend/Dockerfile"
  exit 1
fi

ENV_FILE=".env.cloudrun"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ ไม่พบไฟล์ $ENV_FILE"
  echo "   สร้างจากตัวอย่าง: cp env.cloudrun.example .env.cloudrun"
  echo "   แล้วแก้ค่า (อย่างน้อย NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL)"
  exit 1
fi

source "$ENV_FILE"

PROJECT_ID="${PROJECT_ID:-ev-power-energy-prod}"
REGION="${REGION:-asia-southeast1}"
ARTIFACT_REPO="${ARTIFACT_REPO:-ai-assistant}"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$ARTIFACT_REPO/frontend:latest"
SERVICE_NAME="${GCP_RUN_SERVICE_NAME:-ai-assistant-frontend}"

if [[ -z "$NEXT_PUBLIC_SUPABASE_URL" || -z "$NEXT_PUBLIC_SUPABASE_ANON_KEY" || -z "$NEXT_PUBLIC_API_URL" ]]; then
  echo "❌ ใน $ENV_FILE ต้องมี NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL"
  echo "   (NEXT_PUBLIC_API_URL = URL ของ service ai-assistant-backend บน Cloud Run)"
  exit 1
fi

echo "📦 Project: $PROJECT_ID | Region: $REGION"
echo "🖼  Image:  $IMAGE"
echo "🚀 Service: $SERVICE_NAME"
echo ""

gcloud config set project "$PROJECT_ID" --quiet

echo "🔨 Building image (Cloud Build)..."
gcloud builds submit \
  --config=frontend/cloudbuild.yaml \
  --substitutions=_IMAGE="$IMAGE",_NEXT_PUBLIC_SUPABASE_URL="$NEXT_PUBLIC_SUPABASE_URL",_NEXT_PUBLIC_SUPABASE_ANON_KEY="$NEXT_PUBLIC_SUPABASE_ANON_KEY",_NEXT_PUBLIC_API_URL="$NEXT_PUBLIC_API_URL" \
  frontend

echo ""
echo "🚀 Deploying to Cloud Run..."
# ไม่ใช้ --allow-unauthenticated เพื่อไม่ให้ deploy ติด org policy
# ถ้าต้องการให้ทุกคนเข้า: ให้ admin ปลด policy แล้วรันคำสั่งด้านล่าง
# หรือให้เฉพาะทีม: รัน add-iam-policy-binding ด้วย user/group แทน allUsers
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --port 8080 \
  --no-allow-unauthenticated

echo ""
echo "✅ Deploy frontend เสร็จแล้ว"
echo "   ถ้าเปิด URL แล้ว Forbidden: ให้สิทธิ์ invoker (เลือกอย่างใดอย่างหนึ่ง):"
echo "   • ทุกคน: gcloud run services add-iam-policy-binding $SERVICE_NAME --region=$REGION --member=allUsers --role=roles/run.invoker"
echo "   • เฉพาะคุณ: gcloud run services add-iam-policy-binding $SERVICE_NAME --region=$REGION --member=user:YOUR_EMAIL --role=roles/run.invoker"
