#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

require_env() {
  local var="$1"
  if [ -z "${!var:-}" ]; then
    echo "Missing required env var: $var" >&2
    exit 1
  fi
}

is_true() {
  case "${1,,}" in
    1|true|yes) return 0 ;;
    *) return 1 ;;
  esac
}

require_env "POSTGRES_PASSWORD"
require_env "NBMS_DB_PASSWORD"

USE_S3="${USE_S3:-0}"
if is_true "$USE_S3"; then
  require_env "S3_ACCESS_KEY"
  require_env "S3_SECRET_KEY"
fi

ENABLE_GEOSERVER="${ENABLE_GEOSERVER:-0}"
if is_true "$ENABLE_GEOSERVER"; then
  require_env "GEOSERVER_PASSWORD"
fi

PYTHON_BIN="${PYTHON_BIN:-python}"
VENV_PATH="${VENV_PATH:-$ROOT_DIR/.venv}"
CREATE_VENV="${CREATE_VENV:-0}"

if [ "$CREATE_VENV" = "1" ] && [ ! -d "$VENV_PATH" ]; then
  "$PYTHON_BIN" -m venv "$VENV_PATH"
fi

if [ -x "$VENV_PATH/bin/python" ]; then
  PYTHON="$VENV_PATH/bin/python"
else
  PYTHON="$PYTHON_BIN"
fi

"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r "$ROOT_DIR/requirements.txt"

"$PYTHON" "$ROOT_DIR/manage.py" migrate --noinput

if [ "${CREATE_SUPERUSER:-0}" = "1" ]; then
  "$PYTHON" "$ROOT_DIR/manage.py" createsuperuser
fi
