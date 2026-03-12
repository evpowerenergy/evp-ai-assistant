#!/usr/bin/env bash
# Deploy AI Assistant Backend ไป GCP Cloud Run (รูปแบบเดียวกับ CRM — config ที่ root, ส่ง source เป็น .)
# ใช้: จาก root โปรเจกต์รัน ./scripts/deploy-backend.sh
#      หรือ ./scripts/deploy-backend.sh --local เพื่อ build ด้วย Docker บนเครื่อง (ไม่ใช้ Cloud Build)

set -e

USE_LOCAL_DOCKER=0
for arg in "$@"; do
  if [[ "$arg" == "--local" ]]; then
    USE_LOCAL_DOCKER=1
    break
  fi
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f backend/Dockerfile ]]; then
  echo "❌ ไม่พบ backend/Dockerfile"
  exit 1
fi
if [[ $USE_LOCAL_DOCKER -eq 0 && ! -f cloudbuild-backend.yaml ]]; then
  echo "❌ ไม่พบ cloudbuild-backend.yaml (หรือใช้ --local เพื่อ build บนเครื่อง)"
  exit 1
fi

ENV_FILE=".env.cloudrun"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ ไม่พบไฟล์ $ENV_FILE"
  echo "   สร้างจากตัวอย่าง: cp env.cloudrun.example .env.cloudrun"
  echo "   แล้วแก้ค่าใน .env.cloudrun (อย่างน้อย SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY)"
  exit 1
fi

source "$ENV_FILE"

PROJECT_ID="${PROJECT_ID:-ev-power-energy-prod}"
REGION="${REGION:-asia-southeast1}"
ARTIFACT_REPO="${ARTIFACT_REPO:-ai-assistant}"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$ARTIFACT_REPO/backend:latest"
SERVICE_NAME="${GCP_RUN_SERVICE_NAME:-ai-assistant-backend}"

if [[ -z "$SUPABASE_URL" || -z "$SUPABASE_SERVICE_ROLE_KEY" || -z "$OPENAI_API_KEY" ]]; then
  echo "❌ ใน $ENV_FILE ต้องมี SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY"
  exit 1
fi

echo "📦 Project: $PROJECT_ID | Region: $REGION"
echo "🖼  Image:  $IMAGE"
echo "🚀 Service: $SERVICE_NAME"
echo ""

gcloud config set project "$PROJECT_ID" --quiet

if [[ $USE_LOCAL_DOCKER -eq 1 ]]; then
  echo "🔨 Building image (local Docker)..."
  if ! command -v docker &>/dev/null; then
    echo "❌ ไม่พบคำสั่ง docker — ติดตั้ง Docker แล้วรันใหม่ หรือไม่ใช้ --local"
    exit 1
  fi
  gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet 2>/dev/null || true
  docker build -t "$IMAGE" backend
  docker push "$IMAGE"
else
  echo "🔨 Building image (Cloud Build — แบบเดียวกับ CRM: config ที่ root, ส่ง .)..."
  gcloud builds submit --config=cloudbuild-backend.yaml \
    --substitutions=_IMAGE="$IMAGE"
fi

# สร้างไฟล์ env ชั่วคราว (YAML, escape ค่าที่มี ' เพื่อไม่ให้ YAML พัง)
ENV_YAML=$(mktemp).yaml
trap "rm -f $ENV_YAML" EXIT
yaml_escape() { echo "$1" | sed "s/'/''/g"; }
{
  echo "SUPABASE_URL: '$(yaml_escape "$SUPABASE_URL")'"
  echo "SUPABASE_SERVICE_ROLE_KEY: '$(yaml_escape "$SUPABASE_SERVICE_ROLE_KEY")'"
  echo "OPENAI_API_KEY: '$(yaml_escape "$OPENAI_API_KEY")'"
  echo "LINE_CHANNEL_SECRET: '$(yaml_escape "${LINE_CHANNEL_SECRET:-}")'"
  echo "LINE_CHANNEL_ACCESS_TOKEN: '$(yaml_escape "${LINE_CHANNEL_ACCESS_TOKEN:-}")'"
  # CORS: ต้องมี origin ของ frontend เพื่อไม่ให้เบราว์เซอร์บล็อก (CORS error)
  if [[ -n "${CORS_ORIGINS:-}" ]]; then
    echo "CORS_ORIGINS: '$(yaml_escape "$CORS_ORIGINS")'"
  fi
} > "$ENV_YAML"

echo ""
echo "🚀 Deploying to Cloud Run..."
# ใช้ --no-allow-unauthenticated ก่อน เพื่อไม่ให้ติดขั้นตอน IAM (เปิด public ทีหลังด้วยคำสั่งแยก)
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --no-allow-unauthenticated \
  --env-vars-file "$ENV_YAML" \
  --timeout 300

echo ""
echo "✅ Deploy backend เสร็จแล้ว"
echo "   ถ้าต้องการให้ใครก็ได้เรียก (public): รันคำสั่งนี้แล้วใส่ URL ด้านบนใน .env.cloudrun (NEXT_PUBLIC_API_URL)"
echo "   gcloud run services add-iam-policy-binding $SERVICE_NAME --region=$REGION --member=allUsers --role=roles/run.invoker"
