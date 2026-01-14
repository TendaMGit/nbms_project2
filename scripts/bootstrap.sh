#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

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
