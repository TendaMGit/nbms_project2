#!/usr/bin/env bash
set -euo pipefail

: "${PGBACKREST_STANZA:?PGBACKREST_STANZA is required}"
: "${PGDATA_RESTORE_DIR:?PGDATA_RESTORE_DIR is required}"
: "${PITR_TARGET_TIME:?PITR_TARGET_TIME is required (RFC3339, UTC)}"

pgbackrest \
  --stanza="${PGBACKREST_STANZA}" \
  --type=time \
  --target="${PITR_TARGET_TIME}" \
  --delta \
  --pg1-path="${PGDATA_RESTORE_DIR}" \
  restore

pg_controldata "${PGDATA_RESTORE_DIR}" | sed -n '1,12p'
