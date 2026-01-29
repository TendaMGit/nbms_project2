# 0026 Security + Governance Integrity Pack

## Summary
- Adds audit metadata fields to `AuditEvent` (event_type, content type/object id, request metadata).
- Extends `FrameworkGoal` with lifecycle + governance fields (status, sensitivity, organisation, created_by, review_note).
- Adds metadata fields to `NationalTarget` and `Indicator` (QA status, reporting cadence, provenance, coverage, licensing).
- Adds `is_active` to alignment link tables:
  - `NationalTargetFrameworkTargetLink`
  - `IndicatorFrameworkIndicatorLink`
- Introduces `IndicatorMethodologyVersionLink` (indicator ? methodology version linkage).

## Data Backfills
- `AuditEvent.event_type` backfilled from existing `action` values.
- `FrameworkGoal.status` backfilled to `archived` where `is_active=False`.
- `IndicatorMethodologyVersionLink` backfilled from `MethodologyIndicatorLink` when exactly one active version exists.

## Rollout / Rollback Notes
- Safe to apply forward; no destructive changes.
- Rolling back removes added columns and the new link table; existing data in new fields will be lost on rollback.
- If you rely on the backfilled links, ensure re-creating `IndicatorMethodologyVersionLink` after any rollback.
