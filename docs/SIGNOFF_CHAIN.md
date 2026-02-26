# National Report Sign-Off Chain

Phase 12 introduces a role-gated sign-off chain for CBD national reports (NR7/NR8).

## Workflow Steps
1. `draft`
2. `section_review`
3. `technical_review` (Technical Committee required)
4. `secretariat_consolidation`
5. `publishing_authority_review`
6. `submitted` (final/locked)

## Core Tables
- `ReportWorkflowDefinition`
- `ReportWorkflowInstance`
- `ReportWorkflowAction`
- `ReportWorkflowSectionApproval`
- `ReportTemplatePackResponse` (locked on finalization)

## Evidence Gate
- `technical_approve` requires evidence coverage from Section III progress links (`evidence_items` or `dataset_releases`).

## Integrity
- Every workflow action captures `payload_hash` of report content snapshot.
- Final publish writes `ReportingInstance.final_content_hash` and `finalized_at`.
- Export artifacts and dossier are hash-stamped and audit-logged.

## API
- `GET /api/reports/{uuid}/workflow`
- `POST /api/reports/{uuid}/workflow/action`

Supported actions:
- `submit`
- `section_approve` (requires `section_code`)
- `technical_approve`
- `consolidate`
- `publishing_approve`
- `reject`
- `unlock` (SystemAdmin)
