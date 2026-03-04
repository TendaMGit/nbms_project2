#!/usr/bin/env bash

set -euo pipefail

/app/docker/docker-bootstrap.sh

echo "[superset-init] applying metadata migrations"
superset db upgrade

echo "[superset-init] syncing built-in roles and permissions"
superset init

echo "[superset-init] ensuring admin user and local stakeholder roles"
/app/.venv/bin/python /app/docker/bootstrap_security.py

echo "[superset-init] complete"
