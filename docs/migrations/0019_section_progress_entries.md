# Migration 0019: Section III/IV progress entries

## Summary

Adds structured progress entry models for NR7:

- `SectionIIINationalTargetProgress`
- `SectionIVFrameworkTargetProgress`

Each model includes narrative fields plus M2M links to indicator data series,
binary indicator responses, evidence, and dataset releases.

## Why

Section III/IV require per-target/per-goal progress records that can be
queried, governed, and exported without relying solely on narrative blobs.

## Rollback strategy

This migration is additive. To roll back:

1) Create a new migration that removes the two progress models and their M2M
   tables.
2) Apply the rollback migration and verify no downstream tables depend on
   these models.

## Rollout steps

1) Apply migrations:
   - `python manage.py migrate nbms_app`
2) Confirm Section III/IV routes render for staff:
   - `/reporting/instances/<uuid>/section-iii/`
   - `/reporting/instances/<uuid>/section-iv/`
3) Validate readiness panel reflects progress entry coverage for scoped targets.

## Operational considerations

- The progress tables are expected to be small (one row per target per
  instance). Indexing is limited to the uniqueness constraints.
- M2M tables can grow with evidence/dataset/indicator references; ensure
  database monitoring accounts for these join tables if evidence linkage is
  heavy.
