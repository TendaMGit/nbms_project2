# NEXT BACKLOG - NBMS Project 2

## Phase 0.5: Developer ergonomics + CI posture (Windows-first)
Acceptance criteria:
- Document a Windows-first "doctor" concept (no code change yet) covering env checks, DB reachability, and migration status.
- CI pytest guidance explicitly uses `ENABLE_GIS=false` and `config.settings.test`.
- /health/ smoke check is called out in docs/runbooks as a standard verification step.

Artifacts:
- Docs-only checklist for a future `scripts/verify_env.ps1` or `scripts/doctor.ps1`.
- CI notes in docs/ops for ENABLE_GIS=false posture.
- /health/ smoke command block.

Risks/Dependencies:
- CI updates will be needed later if the doctor script is implemented.
- Windows pathing differences (PowerShell vs bash) must be kept consistent.

## Phase 1: Reference Catalog normalized registry + CRUD parity
Acceptance criteria:
- Frameworks/Goals/Targets/Indicators and Programmes/Datasets/Methodologies have parity across list/detail/create/edit UI.
- Registry metadata completeness: QA status, provenance, sensitivity, consent-required flags, and source references are captured end-to-end.
- Import/export commands cover all registry entities with documented CSV templates and validation errors.
- ABAC/consent gating is enforced consistently on list/detail and in exports.

Artifacts:
- Screens: list/detail/edit for each registry entity.
- `docs/ops/REGISTRY_PARITY_MATRIX.md` (route coverage + gaps).
- CSV templates + example fixtures for each registry table.
- Updated reference catalog import/export docs and validation examples.

Risks/Dependencies:
- Requires alignment with consent/IPLC policy and sensitivity defaults.
- Backfill/migration constraints must remain forward-safe.

## Phase 2: Alignment UI expansion + readiness/validation
Status:
- Phase 2.1 (coverage UI panels) delivered.
- Phase 2.2 (bulk alignment) in progress.

Acceptance criteria:
- Alignment UI supports bulk add/remove, confidence, and source metadata.
- Readiness diagnostics include alignment coverage metrics and mapping completeness.
- Deterministic ordering of mappings in review pack and ORT NR7 v2 export.

Artifacts:
- Alignment UI screens and coverage/readiness panels.
- Commands or scripts to export mapping coverage (if needed).
- `docs/ops/ALIGNMENT_COVERAGE.md` (coverage semantics + CLI usage).
- Golden files or snapshot diffs showing deterministic ordering.

Risks/Dependencies:
- Requires stable reference catalog data and consistent identifier strategy.
- Potential performance impact for large mapping tables.

## Phase 3: Pilot extraction strategy (from nbms_project)
Acceptance criteria:
- Documented extraction scope and mapping rules (no legacy schema import).
- Identifier mapping for targets/indicators/frameworks, plus provenance notes.
- Consent/IPLC flags and sensitivity rules mapped explicitly.
- Acceptance checklist for each dataset with rollback plan.

Artifacts:
- Extraction mapping document (source field -> destination field).
- Data acceptance checklist and sample validation output.
- Import script plan (docs only; no implementation yet).

Risks/Dependencies:
- Legacy data quality and missing identifiers.
- Legal/consent constraints on IPLC-sensitive data.

## Phase 4: Demo seed plan (end-to-end walkthrough)
Acceptance criteria:
- Deterministic seed plan for cycles, instance, approvals, and review pack v2.
- ORT NR7 v2 export produces a stable, golden payload for demo.
- Documented seed/reset order and expected outcomes.

Artifacts:
- Seed plan outline with commands and expected objects.
- Golden export JSON (planned) and review pack v2 screenshots (planned).
- Demo walkthrough checklist.

Risks/Dependencies:
- Requires finalized reference catalog metadata and mapping completeness.
- Must respect approvals/consent gating and deterministic ordering.
