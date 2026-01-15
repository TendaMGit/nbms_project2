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

PYTEST_ARGS=()
if [ "${KEEPDB:-0}" = "1" ]; then
  PYTEST_ARGS=("--reuse-db")
fi

PYTHONWARNINGS=default "$PYTHON" -m pytest "${PYTEST_ARGS[@]}"
