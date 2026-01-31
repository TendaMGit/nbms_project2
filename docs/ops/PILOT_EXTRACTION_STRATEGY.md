# Pilot Extraction Strategy (Phase 3)

## A. Executive summary
This document defines how we will extract a limited, safe subset of data from the legacy `nbms_project` into `nbms_project2` without importing the legacy schema. The goal is to bootstrap the normalized registries, alignment mappings, and indicator data needed for a pilot, while preserving ABAC/consent rules and deterministic identifiers. We explicitly do **not** migrate legacy workflow states, approvals, or audit logs unless explicitly approved later.

## B. In-scope vs out-of-scope datasets

### In-scope (default)
- Registry entities (normalized):
  - Framework registry: Framework, FrameworkGoal, FrameworkTarget, FrameworkIndicator
  - NationalTarget
  - Indicator
  - MonitoringProgramme
  - DatasetCatalog + DatasetRelease
  - Methodology + MethodologyVersion (where possible)
  - Evidence (where it can be mapped safely)
  - SensitivityClass, DataAgreement, SourceDocument (if present)
- Alignment mappings:
  - NationalTargetFrameworkTargetLink
  - IndicatorFrameworkIndicatorLink
- Indicator data:
  - IndicatorDataSeries
  - IndicatorDataPoint
- Seeded reference data (not extracted):
  - BinaryIndicatorQuestion (seed via `seed_binary_indicator_questions`)

### Out-of-scope (default)
- Legacy workflow state machines and legacy approvals (draft/approved/rejected flags) that do not map 1:1 to NBMS2 workflows.
- Legacy audit logs and governance histories.
- Instance-scoped progress/approvals/section responses (unless explicitly approved for Mode 2).
- Any entity that cannot be mapped safely to NBMS2 fields without bypassing ABAC/consent.

## C. Extraction modes

### Mode 1 (recommended): "Bootstrap registry + mappings + indicator data"
- Imports registries, mappings, and indicator data only.
- Uses deterministic identifier mapping and strict validation.
- Leaves instance-specific workflows and approvals untouched.
- Safest for Phase 4 demo and avoids importing legacy governance states.

### Mode 2 (optional later): "Include instance data"
- Adds ReportingInstance, approvals, and Section III/IV progress artifacts.
- Pros: closer to a full pilot dataset; can demo review/approval flows with migrated content.
- Cons: risk of importing stale approval states, consent gaps, and non-deterministic workflows.
- Requires explicit decision and separate validation plan.

## D. Source-of-truth stance
- `nbms_project2` is the future source of truth.
- `nbms_project` is a **donor of selected data only**, with explicit transformation rules.
- Import scripts must never mutate `nbms_project` data and must be idempotent on `nbms_project2`.

## E. Consent/IPLC + ABAC safety rules
- **Never assume public**. If a source record lacks explicit visibility/sensitivity, treat it as restricted.
- If IPLC-sensitive flags exist, map to `SensitivityLevel.IPLC_SENSITIVE` and require consent gating in NBMS2.
- If consent signals are missing, import the object as restricted and require manual consent in NBMS2.
- Mapping must not create or reveal relationships between objects the user cannot access.

## F. Deterministic identifiers and ordering
- Prefer source UUIDs when present.
- If source UUIDs are absent, generate UUIDv5 from a namespace + stable key (e.g., `framework_code + ':' + target_code`).
- If no stable key exists, generate UUIDv4 and record it in the **ID mapping ledger**.
- All exported CSVs and CLI output must be sorted deterministically by `(code, title, uuid)`.

## G. Constraints and risks
- Missing identifiers or inconsistent codes may cause collisions or duplicates.
- Some `nbms_project` entities are modeled differently (e.g., `IndicatorData` vs `IndicatorDataSeries/Point`).
- Consent/IPLC signals may be incomplete or stored in governance tables; those must be reconciled.
- OneDrive file locks can disrupt large exports; recommend running extraction from `C:\dev\...`.

## H. Deliverables from Phase 3
- `docs/ops/PILOT_EXTRACTION_STRATEGY.md` (this file)
- `docs/ops/PILOT_EXTRACTION_MAPPING.md` (field-by-field mapping rules)
- `docs/ops/PILOT_EXTRACTION_ACCEPTANCE_CHECKLIST.md`
- `docs/ops/PILOT_IMPORT_SCRIPT_PLAN.md`

