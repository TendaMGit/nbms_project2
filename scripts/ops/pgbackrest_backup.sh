#!/usr/bin/env bash
set -euo pipefail

: "${PGBACKREST_STANZA:?PGBACKREST_STANZA is required}"
BACKUP_TYPE="${PGBACKREST_TYPE:-incr}"

pgbackrest --stanza="${PGBACKREST_STANZA}" --type="${BACKUP_TYPE}" backup
pgbackrest --stanza="${PGBACKREST_STANZA}" check
pgbackrest info --stanza="${PGBACKREST_STANZA}"
