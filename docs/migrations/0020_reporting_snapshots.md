# Migration 0020: Reporting snapshots

## Summary

Adds `ReportingSnapshot` for immutable, governance-grade export snapshots
captured from the v2 ORT payload.

## Rollout steps

1) Apply migrations:
   - `python manage.py migrate nbms_app`
2) Validate snapshot creation from the staff UI or via freeze hook (if wired).

## Rollback strategy

This migration is additive. To roll back:

1) Create a new migration that drops the `ReportingSnapshot` table and indexes.
2) Apply the rollback migration.

## Operational considerations

- Snapshots store full JSON payloads; size depends on export scope.
- Indexes are on instance + created_at and payload_hash for quick lookup and de-duplication.
