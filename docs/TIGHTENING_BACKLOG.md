# TIGHTENING_BACKLOG

## Priority Model
- P0: must-fix before significant new feature expansion.
- P1: high-value hardening and conformance after P0.
- P2: structural improvements that can follow once safety baseline is stable.

## Completed in This Review Pass
- PR1 (DevEx + reproducibility): completed
  - `.env.example` expanded
  - `scripts/bootstrap.ps1`, `scripts/test.ps1`, `scripts/smoke.ps1`, `scripts/smoke.sh`
  - `README.md` updates
- PR2 (Security guardrails): completed (baseline)
  - `src/config/settings/prod.py` secure defaults tightened
  - `src/nbms_app/views_metrics.py` token handling tightened
  - `src/config/settings/base.py` metrics query-token toggle
  - tests: `test_metrics.py`, `test_prod_settings.py`
- PR3 (Authorization/consent correctness): completed (first gap)
  - Block single approve of non-published objects: `src/nbms_app/views.py`
  - tests: `test_reporting_approvals_ui.py`, `test_reporting_freeze.py`
- PR4 (Export correctness scaffolding): completed (initial)
  - `src/nbms_app/services/export_contracts.py`
  - integrated in `src/nbms_app/exports/ort_nr7_v2.py`
  - tests + fixture: `test_export_contracts.py`, `fixtures/exports/ort_indicator_tabular_submission_minimal.json`
- PR5 (seeding defect fix): completed
  - Fixed question-seeding loop in `src/nbms_app/management/commands/seed_binary_indicator_questions.py`
  - added test: `src/nbms_app/tests/test_seed_binary_indicator_questions_command.py`
- PR6 (Windows test-stability fix): completed
  - Added Windows/Python 3.13-safe `tmp_path` compatibility fixture: `src/nbms_app/tests/conftest.py`
  - Full local suite now green: `308 passed`

## P0 Backlog

### P0-1: ORT Section I/II/V field-level conformance uplift
- Rationale: current templates are narrative-only and not ORT granular enough for full submission parity.
- Affected files:
  - `src/nbms_app/management/commands/seed_report_templates.py`
  - `src/nbms_app/exports/ort_nr7_narrative.py`
  - `src/nbms_app/exports/ort_nr7_v2.py`
  - section forms/templates in `src/nbms_app/forms.py`, `templates/nbms_app/reporting/`
- Acceptance criteria:
  - Required ORT-aligned fields exist for Section I/II/V.
  - Export payload includes mapped keys (backward-compatible for existing content).
  - Regression tests added for new fields and export shape.
- Suggested PR boundary:
  - PR-A: schema/template seed + form render
  - PR-B: export mapping + tests

### P0-2: Authorization policy normalization for staff-only routes
- Rationale: mixed use of staff decorators and object scoping increases drift risk.
- Affected files: `src/nbms_app/views.py`, `src/nbms_app/services/authorization.py`, targeted tests.
- Acceptance criteria:
  - Every mutating/reporting-sensitive route has explicit policy path (role + object scope + consent impact).
  - Add endpoint authorization matrix tests for review/snapshot/approval/consent routes.
- Suggested PR boundary:
  - PR-A: introduce reusable policy helper/decorator
  - PR-B: route-by-route migration + tests
- Current status:
  - Baseline complete for staff-protected routes via `src/nbms_app/services/policy_registry.py`.
  - Regression guard tests added in `src/nbms_app/tests/test_policy_registry.py`.
  - Remaining: extend the same explicit policy metadata/enforcement to all non-staff role-gated endpoints.

### P0-3: Minimal CI hardening baseline beyond migration verify
- Rationale: current workflow is good but single-track.
- Affected files: `.github/workflows/`.
- Acceptance criteria:
  - Add separate CI jobs for lint/check, fast tests, and migration verify.
  - Add dependency vulnerability scan and secret scan.
- Suggested PR boundary:
  - PR-A: split pipeline + cache + deterministic test command
  - PR-B: security scan jobs
- Current status:
  - Implemented in `.github/workflows/ci.yml` with `quality-fast`, `tests-linux-full`, `tests-windows-smoke`, and `security-baseline`.
  - Remaining: add dedicated SAST job and calibrate vulnerability audit policy thresholds.

## P1 Backlog

### P1-0: Retire temporary Windows `tmp_path` compatibility shim
- Rationale: `src/nbms_app/tests/conftest.py` restores local stability but should not become permanent technical debt.
- Affected files: `src/nbms_app/tests/conftest.py`, CI matrix/python pinning.
- Acceptance criteria:
  - Upgrade path identified (pytest/Python behavior resolved or pinned).
  - Compatibility shim removed with no Windows regressions.

### P1-1: Expand export contract validation to stronger ORT semantics
- Rationale: current validator checks shape but not deeper semantic constraints.
- Affected files: `src/nbms_app/services/export_contracts.py`, `src/nbms_app/tests/test_export_contracts.py`.
- Acceptance criteria:
  - Validate cross-reference consistency (`references` UUIDs must exist in exported arrays).
  - Validate indicator data row constraints against ORT-style minimum contract.

### P1-2: Audit retention and operational controls
- Rationale: event capture exists, retention/governance lifecycle is missing.
- Affected files: new management command + docs.
- Acceptance criteria:
  - Configurable retention period.
  - Dry-run and purge command with auditable summary output.

### P1-3: Observability upgrade path
- Rationale: metrics are process-local and reset on restart.
- Affected files: `src/nbms_app/services/metrics.py`, `src/nbms_app/views_metrics.py`, settings/docs.
- Acceptance criteria:
  - Prometheus-compatible backend mode or durable counters via cache/Redis.
  - Response-time/error-rate metrics exposed per route class.

### P1-4: Consent policy consistency for catalog entities
- Rationale: export-facing entities are strong; catalog access policy can be made more explicit and testable.
- Affected files: `src/nbms_app/services/catalog_access.py`, readiness policy checks.
- Acceptance criteria:
  - Shared policy helper for dataset/programme sensitivity + agreement + consent.
  - Tests for cross-org/internal/restricted permutations.

### P1-5: Angular primary UI foundation (dashboard + indicator explorer)
- Rationale: current Django templates are functional but not sufficient for a modern analyst workflow.
- Affected files: new `/frontend` Angular workspace, backend auth/bootstrap API endpoints, Docker integration.
- Acceptance criteria:
  - Angular app launches in Docker-integrated workflow.
  - Session+CSRF auth works without bypassing backend ABAC.
  - Dashboard and indicator explorer render with deterministic filtered datasets.

### P1-6: Spatial delivery v1 (GeoJSON API + map UI)
- Rationale: GBF/NR7 reporting increasingly needs map-based evidence review.
- Affected files: DRF spatial endpoints, docker profile docs, Angular map module.
- Acceptance criteria:
  - GeoJSON endpoints for at least 3 layers (admin boundaries, protected areas, one indicator layer).
  - UI layer filters (province/realm/indicator) and legend render deterministically.

## P2 Backlog

### P2-1: Refactor `views.py` by bounded context
- Rationale: large file increases policy drift and review complexity.
- Affected files: `src/nbms_app/views.py` split into modules.
- Acceptance criteria:
  - No route changes.
  - Imports + tests updated with no behavior regression.

### P2-2: DaRT-style reusable reporting package workflows
- Rationale: enter-once/reuse-many is only partially supported via snapshots/export packages.
- Affected files: new services/models for reusable package manifests and mapping metadata.
- Acceptance criteria:
  - Reusable package definition per indicator/target set across reporting instances.
  - Deterministic replay/export from package IDs.

### P2-3: Optional geospatial pipeline hardening
- Rationale: GIS remains optional, but operational expectations for spatial indicators will grow.
- Affected files: settings, docs, optional services.
- Acceptance criteria:
  - Explicit non-GIS and GIS operating modes with identical core test path for non-spatial features.

### P2-4: Indicator workflow v1 pack and multi-MEA template packs
- Rationale: NBMS must support first-class GBF workflows now and extensibility for other MEAs later.
- Affected files: seed commands, indicator computation hooks, export mappings, framework/template registries.
- Acceptance criteria:
  - Four headline-style indicator workflows operate end-to-end (metadata, method versions, series/points, approvals, export visibility).
  - Template pack scaffolding exists for Ramsar/CITES/CMS without impacting CBD/GBF behavior.

## Paper Cuts Blocking Contributors
- `PYTHONPATH` must be set for direct `pytest` runs (`$env:PYTHONPATH="$PWD\src"`), otherwise import errors occur.
- Windows/Python 3.13 uses a compatibility fixture for `tmp_path`; keep this monitored until retirement.
- CI matrix is narrow; contributors can merge changes that pass migration verify but still miss broader quality gates.

## Suggested PR Execution Order (next)
1. P0-1 ORT conformance uplift for Sections I/II/V.
2. P0-2 authorization policy normalization + endpoint matrix tests.
3. P0-3 CI split with security scans.
4. P1-0 retire temporary Windows `tmp_path` compatibility shim.
5. P1-1 deeper export semantic contracts.

