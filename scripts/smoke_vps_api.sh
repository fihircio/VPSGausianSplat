#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
SCENE_ID="${SCENE_ID:-}"

echo "Checking VPS API at ${API_BASE_URL}"
curl -fsS "${API_BASE_URL}/health"
echo

if [[ -n "${SCENE_ID}" ]]; then
  echo "Checking scene ${SCENE_ID}"
  curl -fsS "${API_BASE_URL}/scene/${SCENE_ID}"
  echo
else
  echo "SCENE_ID is not set; skipping scene readiness check."
fi
