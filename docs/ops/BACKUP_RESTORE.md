# Backup and Restore (Docker Stack)

These scripts target the docker-compose runtime used by NBMS (`compose.yml`).

## Prerequisites

- Docker Desktop running
- Stack running with `docker compose --profile minimal up -d`
- Environment variables set in `.env` (`POSTGRES_USER`, `NBMS_DB_NAME`)

## Backup

PowerShell:

```powershell
scripts/backup_stack.ps1 -OutputDir backups
```

POSIX shell:

```bash
scripts/backup_stack.sh backups
```

Artifacts produced:

- `backups/postgis-<timestamp>.sql`
- `backups/minio-<timestamp>.tgz`

## Restore

PowerShell:

```powershell
scripts/restore_stack.ps1 -DbBackup backups/postgis-20260206-101500.sql -MinioBackup backups/minio-20260206-101500.tgz
```

POSIX shell:

```bash
scripts/restore_stack.sh backups/postgis-20260206-101500.sql backups/minio-20260206-101500.tgz
```

## Notes

- Restore operations overwrite the current running data in `postgis` and `minio`.
- For production operations, run restore into a staging environment first and validate `/health/`, `/health/storage/`, and `/api/system/health`.
