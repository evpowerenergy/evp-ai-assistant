#!/bin/sh
set -e
# ให้เห็นใน Cloud Run logs ว่า container เริ่มและ PORT คืออะไร
echo "Starting backend: PORT=${PORT:-8080}" 1>&2
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
