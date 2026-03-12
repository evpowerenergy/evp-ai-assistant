#!/usr/bin/env bash
# รัน backend image (ที่ build ไป Cloud Run) บนเครื่อง เพื่อดู error จริงถ้า deploy ไม่ผ่าน
# ใช้: ./scripts/run-backend-local.sh
# ต้องมี .env.cloudrun และต้องเคย build image ไปแล้ว (หรือใช้ image จาก Artifact Registry)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE=".env.cloudrun"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ ไม่พบ $ENV_FILE (สร้างจาก env.cloudrun.example)"
  exit 1
fi
source "$ENV_FILE"

PROJECT_ID="${PROJECT_ID:-ev-power-energy-prod}"
REGION="${REGION:-asia-southeast1}"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/ai-assistant/backend:latest"

echo "🐳 รัน image: $IMAGE"
echo "   ถ้าแอป crash จะเห็น Python error ด้านล่าง"
echo "   ถ้ารันได้ เปิด http://localhost:8080 หรือ http://localhost:8080/api/v1/health"
echo ""

docker run --rm -p 8080:8080 \
  -e PORT=8080 \
  -e SUPABASE_URL="$SUPABASE_URL" \
  -e SUPABASE_SERVICE_ROLE_KEY="$SUPABASE_SERVICE_ROLE_KEY" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e LINE_CHANNEL_SECRET="${LINE_CHANNEL_SECRET:-}" \
  -e LINE_CHANNEL_ACCESS_TOKEN="${LINE_CHANNEL_ACCESS_TOKEN:-}" \
  "$IMAGE"
