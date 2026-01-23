# Migration 0021: Review decisions

## Summary

Adds ReviewDecision for immutable, snapshot-linked sign-off records.

## Rollout steps

1) Apply migrations:
   - `python manage.py migrate nbms_app`
2) Verify review decisions appear on the instance review dashboard.

## Rollback strategy

This migration is additive. To roll back:

1) Create a new migration that drops the `ReviewDecision` table and indexes.
2) Apply the rollback migration.

## Operational considerations

- Decisions are append-only; updates are blocked at the model layer.
- Index on (reporting_instance, created_at) supports timeline views.
