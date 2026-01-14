#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

PYTHON_BIN="${PYTHON_BIN:-python}"
VENV_PATH="${VENV_PATH:-$ROOT_DIR/.venv}"
if [ -x "$VENV_PATH/bin/python" ]; then
  PYTHON="$VENV_PATH/bin/python"
else
  PYTHON="$PYTHON_BIN"
fi

TEST_ARGS=("--noinput")
if [ "${KEEPDB:-0}" = "1" ]; then
  TEST_ARGS=("--keepdb")
fi

PYTHONWARNINGS=default "$PYTHON" "$ROOT_DIR/manage.py" test "${TEST_ARGS[@]}"
