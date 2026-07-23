#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
HERMES_DATA_DIR="${PROJECT_DIR}/tmp/hermes-local"
CONTAINER_NAME="evp-hermes-dashboard-local"
IMAGE_NAME="${HERMES_DASHBOARD_IMAGE:-evp-hermes-runtime:test}"

mkdir -p "${HERMES_DATA_DIR}"

if docker container inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
  echo "A dashboard container named ${CONTAINER_NAME} already exists."
  echo "Stop it first with: docker stop ${CONTAINER_NAME}"
  exit 1
fi

DASHBOARD_USERNAME=""
read -r -p "Dashboard username [admin]: " DASHBOARD_USERNAME
DASHBOARD_USERNAME="${DASHBOARD_USERNAME:-admin}"

while true; do
  read -r -s -p "Dashboard password: " DASHBOARD_PASSWORD
  printf '\n'

  if [[ -z "${DASHBOARD_PASSWORD}" ]]; then
    echo "Password cannot be empty."
    continue
  fi

  read -r -s -p "Confirm password: " DASHBOARD_PASSWORD_CONFIRM
  printf '\n'

  if [[ "${DASHBOARD_PASSWORD}" == "${DASHBOARD_PASSWORD_CONFIRM}" ]]; then
    break
  fi

  echo "Passwords do not match. Please try again."
done

DASHBOARD_SECRET="$(openssl rand -hex 32)"

echo "Starting Hermes Dashboard at http://localhost:9119/login"
echo "Use /login directly because this Hermes image incorrectly auto-redirects"
echo "a single Basic Auth provider through its OAuth-only /auth/login route."
echo "Press Ctrl+C to stop it. The main Hermes runtime will remain running."

exec docker run --rm -it \
  --name "${CONTAINER_NAME}" \
  -p 127.0.0.1:9119:9119 \
  -v "${HERMES_DATA_DIR}:/opt/data" \
  -e API_SERVER_ENABLED=false \
  -e HERMES_DASHBOARD_BASIC_AUTH_USERNAME="${DASHBOARD_USERNAME}" \
  -e HERMES_DASHBOARD_BASIC_AUTH_PASSWORD="${DASHBOARD_PASSWORD}" \
  -e HERMES_DASHBOARD_BASIC_AUTH_SECRET="${DASHBOARD_SECRET}" \
  "${IMAGE_NAME}" \
  dashboard --host 0.0.0.0 --port 9119 --no-open --skip-build --isolated
