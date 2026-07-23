#!/usr/bin/env bash
# Start the local FastAPI gateway with the local Hermes execution keys.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
HERMES_DIR="$PROJECT_DIR/tmp/hermes-local"

for required_file in \
  "$BACKEND_DIR/.env" \
  "$BACKEND_DIR/.venv-runtime/bin/python" \
  "$HERMES_DIR/hermes-api-key" \
  "$HERMES_DIR/evp-execution-private.pem" \
  "$HERMES_DIR/evp-execution-public.pem"; do
  if [[ ! -f "$required_file" ]]; then
    echo "Missing required local runtime file: $required_file" >&2
    exit 1
  fi
done

cd "$BACKEND_DIR"
set -a
source .env
set +a

export AI_PRIMARY_ENGINE="hermes"
export AI_FALLBACK_ENGINE="langgraph"
export AI_FALLBACK_ENABLED="true"
export HERMES_BASE_URL="http://127.0.0.1:8642"
export HERMES_API_KEY="$(tr -d '\r\n' < "$HERMES_DIR/hermes-api-key")"
export HERMES_MODEL="gpt-5.6-luna"
export HERMES_TURN_TIMEOUT_SECONDS="900"
export EVP_EXECUTION_TOKEN_TTL_SECONDS="900"
export HERMES_LOG_PATH="$HERMES_DIR/logs/agent.log"
export EVP_EXECUTION_PRIVATE_KEY="$(<"$HERMES_DIR/evp-execution-private.pem")"
export EVP_EXECUTION_PUBLIC_KEY="$(<"$HERMES_DIR/evp-execution-public.pem")"

exec .venv-runtime/bin/python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${API_PORT:-8000}"
