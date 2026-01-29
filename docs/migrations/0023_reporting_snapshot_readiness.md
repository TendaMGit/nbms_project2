# 0023_reporting_snapshot_readiness

## Summary
- Add readiness capture fields to reporting snapshots (JSON report + summary flags).

## Rollout
1) Apply migrations:
   ```powershell
   python manage.py migrate
   ```
2) New snapshots will capture readiness report data automatically.

## Rollback
- Create a new migration to remove the three readiness fields from `ReportingSnapshot` if rollback is required.
