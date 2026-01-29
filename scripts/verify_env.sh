#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=${1:-.env}
COMPOSE_FILE=${2:-docker/docker-compose.yml}

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing .env file. Run: copy .env.example .env" >&2
  exit 2
fi

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "Compose file not found: $COMPOSE_FILE" >&2
  exit 2
fi

python scripts/verify_env.py --env-file "$ENV_FILE" --compose "$COMPOSE_FILE"
