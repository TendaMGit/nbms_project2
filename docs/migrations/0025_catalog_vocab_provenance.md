# 0025_catalog_vocab_provenance

## Purpose
Introduce foundational controlled vocabularies and provenance records for the Reference Catalog.

## Changes
- Add `License` reference table (code/title/url/description/is_active).
- Add `SourceDocument` provenance table (source_url, citation, version_date, notes, created_by).
- No changes to existing ABAC, consent gating, or export readiness logic.

## Rollout notes
- Additive migration only; safe to apply without data backfills.
- No existing records are modified.

## Rollback notes
- Reverse the migration to drop `License` and `SourceDocument` tables.
- No dependent data yet, so rollback is safe in Phase 1 P2.1 backlog rollout.
