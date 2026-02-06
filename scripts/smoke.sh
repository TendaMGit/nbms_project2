#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"

extract_status() {
  python -c 'import json,sys; print((json.load(sys.stdin)).get("status",""))'
}

extract_detail() {
  python -c 'import json,sys; print((json.load(sys.stdin)).get("detail",""))'
}

health_json=$(curl -fsS "${BASE_URL}/health/")
health_status=$(printf '%s' "$health_json" | extract_status)
if [ "$health_status" != "ok" ]; then
  echo "Health check failed: /health/ returned status '$health_status'." >&2
  exit 1
fi

storage_json=$(curl -fsS "${BASE_URL}/health/storage/")
storage_status=$(printf '%s' "$storage_json" | extract_status)
storage_detail=$(printf '%s' "$storage_json" | extract_detail)

echo "health.status=${health_status}"
echo "health_storage.status=${storage_status}"
if [ -n "$storage_detail" ]; then
  echo "health_storage.detail=${storage_detail}"
fi

