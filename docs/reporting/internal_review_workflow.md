# Internal Review Workflow (NR7)

This workflow provides a governance-safe internal review path for SANBI/DFFE
before any ORT submission transforms are applied.

## Roles

- Secretariat/Data Steward: complete content and resolve readiness blockers.
- IPLC/CARE consent reviewer: resolve consent for sensitive items.
- Technical reviewer: verify indicator data series, binary responses, and mappings.

## Steps

1) Populate narrative sections (I–V + Annex).
2) Capture structured Section III/IV progress entries with references to:
   - Indicator data series + points
   - Binary indicator responses
   - Evidence and dataset releases
3) Resolve instance approvals for published items in scope.
4) Resolve consent for any IPLC-sensitive content.
5) Open the Review Dashboard:
   - Check readiness score and blockers.
   - Fix missing Section III/IV coverage.
   - Verify mapping coverage (national↔framework).
6) Open the Review Pack v2:
   - Validate narrative text, progress entries, and embedded indicator tables.
   - Confirm binary responses and evidence links.
7) Export v2 JSON (review artifact) and freeze the instance if ready.
8) Create a reporting snapshot (immutable v2 export record).
9) Use snapshot diff vs the last snapshot to confirm changes before sign-off.
10) Record a review decision tied to the latest snapshot (approved or changes requested).

## Why this comes before ORT ingestion

The v2 export is the canonical internal review artifact that is strictly gated
by approvals and consent. ORT transforms and schema validation should be applied
only after the content is complete, reviewed, and governance-approved.
