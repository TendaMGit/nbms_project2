# Database Backup and PITR Runbook (pgBackRest)

## Objective
Provide a repeatable PostgreSQL/PostGIS backup and point-in-time recovery (PITR) baseline for NBMS production.

## Recommended Tooling
- Primary recommendation: `pgBackRest`
- Backup repository: object storage or dedicated backup volume
- WAL archiving: enabled continuously

## Baseline Strategy
- Weekly full backup
- Daily incremental backup
- Continuous WAL archive
- Quarterly restore drill minimum

## PostgreSQL Configuration (example)
Set in `postgresql.conf`:
```conf
archive_mode = on
archive_command = 'pgbackrest --stanza=nbms archive-push %p'
archive_timeout = 60
wal_level = replica
max_wal_senders = 10
```

## pgBackRest Stanza Configuration (example)
```conf
[global]
repo1-type=s3
repo1-s3-endpoint=<object-storage-endpoint>
repo1-s3-bucket=nbms-pgbackrest
repo1-path=/pgbackrest
repo1-retention-full=4
repo1-retention-diff=8
start-fast=y
compress-type=zst

[nbms]
pg1-path=/var/lib/postgresql/data
```

## Initial Setup
1. Install pgBackRest on DB host.
2. Configure repo and stanza.
3. Create stanza:
```bash
pgbackrest --stanza=nbms stanza-create
```
4. Run first full backup:
```bash
PGBACKREST_STANZA=nbms PGBACKREST_TYPE=full ./scripts/ops/pgbackrest_backup.sh
```

## Scheduled Backups
Use template schedule from:
- `scripts/ops/pgbackrest.cron.example`

Example policy:
- Sunday 01:00 full
- Monday-Saturday 01:00 incremental

## On-Demand Verification
```bash
pgbackrest --stanza=nbms check
pgbackrest info --stanza=nbms
```

## PITR Procedure (Time-Based)
1. Identify recovery target timestamp (UTC).
2. Stop application traffic and database.
3. Restore to target:
```bash
PGBACKREST_STANZA=nbms \
PGDATA_RESTORE_DIR=/var/lib/postgresql/data \
PITR_TARGET_TIME='2026-02-24 10:30:00+00' \
./scripts/ops/pgbackrest_restore_drill.sh
```
4. Start PostgreSQL in recovery mode.
5. Validate data integrity and application readiness.
6. Re-enable app traffic.

## Restore Drill Checklist
- [ ] Latest backup metadata reviewed (`pgbackrest info`)
- [ ] Target PITR timestamp documented
- [ ] Restore executed in isolated environment first
- [ ] Critical tables row counts validated
- [ ] `python manage.py predeploy_check --skip-migrate-check` passes post-restore
- [ ] `/readyz/` returns ready after app restart
- [ ] Incident/operations log updated with outcomes

## Dry-Run Commands for Ops
```bash
# Validate backups are healthy
pgbackrest --stanza=nbms check
pgbackrest info --stanza=nbms

# Trigger incremental backup manually
PGBACKREST_STANZA=nbms PGBACKREST_TYPE=incr ./scripts/ops/pgbackrest_backup.sh

# Validate restore command syntax (planned runbook values)
PGBACKREST_STANZA=nbms PGDATA_RESTORE_DIR=/var/lib/postgresql/data PITR_TARGET_TIME='YYYY-MM-DD HH:MM:SS+00' \
./scripts/ops/pgbackrest_restore_drill.sh
```

## Retention and Governance
- Keep at least 4 full backups and associated WAL.
- Encrypt backup repository at rest.
- Restrict restore credentials to least privilege.
- Track all backup and restore operations in operations/audit logs.
