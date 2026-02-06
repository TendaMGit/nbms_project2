# REVIEW_SYSTEM_OVERVIEW

## Scope
- Repository: `nbms_project2`
- Review date: 2026-02-06
- Basis: code, tests, settings, scripts, docs in current workspace.
- Intent: as-built truth for NBMS hardening and incremental delivery.

## Top-Level Inventory (as built)
```
.
|- .github/workflows/
|- docker/
|- docs/
|- scripts/
|- src/
|  |- config/
|  |  |- settings/{base,dev,prod,test}.py
|  |  |- urls.py
|  |  |- test_runner.py
|  |- nbms_app/
|     |- models.py
|     |- views.py
|     |- api.py
|     |- services/
|     |- exports/
|     |- management/commands/
|     |- middleware*.py
|     |- signals*.py
|     |- tests/
|- templates/
|- static/
|- requirements.txt
|- requirements-dev.txt
|- README.md
```

## Runtime + Tooling
- Core runtime: Django 5.2, DRF, django-guardian, django-two-factor-auth, django-otp, django-storages, psycopg2.
  - Source: `requirements.txt`
- Test stack: `pytest`, `pytest-django`.
  - Source: `requirements-dev.txt`, `pytest.ini`
- Deployment helpers:
  - Local + Docker infra: `docker/docker-compose.yml`
  - Migration verification stack: `docker-compose.verify.yml`, `.github/workflows/migration-verify.yml`
  - Windows-first scripts: `scripts/bootstrap.ps1`, `scripts/test.ps1`, `scripts/smoke.ps1`

## Module Responsibility Map
- App routing:
  - Project URLs: `src/config/urls.py`
  - UI routes: `src/nbms_app/urls.py`
  - API router: `src/nbms_app/api.py`
- Domain model:
  - Single app model set in `src/nbms_app/models.py` (reporting, catalog, approvals, consent, audit, snapshots).
- Governance services:
  - RBAC/ABAC: `src/nbms_app/services/authorization.py`, `src/nbms_app/services/catalog_access.py`
  - Route-policy matrix: `src/nbms_app/services/policy_registry.py`
  - Consent: `src/nbms_app/services/consent.py`
  - Audit: `src/nbms_app/services/audit.py`, `src/nbms_app/signals_audit.py`, `src/nbms_app/middleware_audit.py`
  - Approvals: `src/nbms_app/services/instance_approvals.py`
- Reporting/export services:
  - Readiness: `src/nbms_app/services/readiness.py`
  - ORT exports: `src/nbms_app/exports/ort_nr7_narrative.py`, `src/nbms_app/exports/ort_nr7_v2.py`
  - Export release workflow: `src/nbms_app/services/exports.py`
  - Snapshot/review decisions: `src/nbms_app/services/snapshots.py`, `src/nbms_app/services/review_decisions.py`
- Ingest/ETL commands:
  - Indicator data CSV import/export: `src/nbms_app/management/commands/import_indicator_data.py`, `src/nbms_app/management/commands/export_indicator_data.py`
  - Reference catalog CSV import/export: `src/nbms_app/management/commands/reference_catalog_import.py`, `src/nbms_app/management/commands/reference_catalog_export.py`
  - Alignment mappings CSV import/export: `src/nbms_app/management/commands/import_alignment_mappings.py`, `src/nbms_app/management/commands/export_alignment_mappings.py`

## Core Workflows Implemented in Code

### 1) Indicator registry + methodology versioning
- Implemented models for indicators and methodology versions:
  - `Indicator`, `Methodology`, `MethodologyVersion`, `IndicatorMethodologyVersionLink` in `src/nbms_app/models.py`
- UI and catalog flows:
  - `methodology_*`, `methodology_version_*`, `indicator_methodology_versions` views in `src/nbms_app/views.py`
- Import/export support for methodology links and versions:
  - `reference_catalog_import.py`, `reference_catalog_export.py`

### 2) Reporting instances (7NR/ORT style)
- Reporting backbone:
  - `ReportingCycle`, `ReportingInstance`, `ReportSectionTemplate`, `ReportSectionResponse`
- Structured sections:
  - Section I/II/V one-to-one models + Section III/IV progress models in `src/nbms_app/models.py`
- Approvals and freeze:
  - UI endpoints in `src/nbms_app/views.py`
  - service logic in `src/nbms_app/services/instance_approvals.py`
- Exports:
  - ORT narrative and v2 routes in `src/nbms_app/urls.py`
  - payload builders in `src/nbms_app/exports/*`
- Validation/readiness:
  - `ValidationRuleSet` + readiness engine in `src/nbms_app/services/readiness.py`

### 3) Consent + sensitivity workflows
- Consent record model: `ConsentRecord` in `src/nbms_app/models.py`
- Decision logic: `requires_consent`, `consent_is_granted`, `set_consent_status` in `src/nbms_app/services/consent.py`
- Consent workspace UI:
  - `reporting_instance_consent`, `reporting_instance_consent_action` in `src/nbms_app/views.py`
- Export block on missing consent:
  - `approve_for_instance` and `release_export` services

### 4) Authorization checks (RBAC + object-level)
- Role constants + role checks in `src/nbms_app/services/authorization.py`
- ABAC queryset filtering in `filter_queryset_for_user`
- Guardian object permissions integrated when `perm` argument is passed
- Catalog-specific access filtering in `src/nbms_app/services/catalog_access.py`
- Route-policy metadata and matrix in `src/nbms_app/services/policy_registry.py`
- Coverage guard tests: `src/nbms_app/tests/test_policy_registry.py`

### 5) Audit logging
- Event model: `AuditEvent` (`src/nbms_app/models.py`)
- Domain event recording and metadata sanitization: `src/nbms_app/services/audit.py`
- Automatic CRUD event coverage via signals: `src/nbms_app/signals_audit.py`
- Request context capture: `src/nbms_app/middleware_audit.py`, `src/nbms_app/services/request_context.py`

## Capability Truth Table

| Area | Status | Evidence (as-built) | Primary Risk |
|---|---|---|---|
| AuthN/AuthZ (RBAC + object-level) | Partial | `authorization.py`, `catalog_access.py`, guardian in `filter_queryset_for_user`, route decorators in `views.py`, policy matrix in `policy_registry.py` | Drift risk is reduced by route policy coverage tests, but non-staff role-gated routes still rely on view-level checks. |
| Consent + sensitivity gating | Partial | `ConsentRecord`, `consent.py`, approval/export checks in `instance_approvals.py` and `exports.py` | Consent semantics are strong for exportable items, but scope is not uniformly enforced across every data surface. |
| Audit events + traceability | Implemented | `AuditEvent`, `record_event`, request metadata capture, model signals | No tamper-evident storage/retention controls defined in code. |
| Indicator computation pipeline (raw -> validated -> computed -> published) | Partial | `IndicatorDataSeries`, `IndicatorDataPoint`, `reporting_readiness.py`, readiness diagnostics | No explicit computation orchestration/job pipeline or publish pipeline distinct from workflow status. |
| Dataset catalog + provenance | Implemented | `DatasetCatalog`, `MonitoringProgramme`, `Methodology*`, provenance fields (`source_system`, `source_ref`), CSV IO commands | Provenance quality depends on operator discipline; no hard completeness enforcement at publish. |
| Import/export formats (ORT/GBF, CSV/Excel/API) | Partial | ORT JSON export routes + builders, CSV import/export commands | No first-class Excel pipeline; no push/pull integration adapters for partner systems; API is read-only. |
| Validation framework (rulesets/scopes) | Partial | `ValidationRuleSet`, `seed_validation_rules.py`, readiness consumption in `readiness.py` | Rules primarily gate readiness/export, not universal model-level validation. |
| Observability (health/logging/metrics) | Partial | `/health/`, `/health/storage/`, `/metrics`, `metrics.py`, logging settings | Metrics are in-process/in-memory only; no durable metrics backend/tracing. |
| Security basics (secrets/headers/CSRF/CORS/rate limit) | Partial | Prod security defaults in `config/settings/prod.py`, CSRF, rate-limit middleware | No CSP policy, no CORS policy module, no automated secret scanning in CI workflow. |
| Testing + CI + migrations integrity | Partial | 80+ test modules; migration verification workflow + split CI workflow exist; local suite validated at `308 passed` with Windows `tmp_path` compatibility fixture in `src/nbms_app/tests/conftest.py` | Compatibility shim should be retired once upstream temp-path behavior is stable; SAST still missing from CI baseline. |
| Documentation quality (Windows-first + ops runbook) | Partial | Strong runbook material (`README.md`, `docs/ops/STATE_OF_REPO.md`) | Multiple docs overlap; no single “current hardening backlog + execution status” doc before this review. |

## As-Built Architecture and Tradeoffs
- Architecture style: Django monolith with explicit service layer for governance-sensitive behavior.
- Strengths:
  - Governance-critical logic is centralized in services (`authorization`, `consent`, `instance_approvals`, `exports`, `readiness`).
  - Reporting export gating is explicit and test-covered.
  - Rich domain model for catalog + reporting + audit.
- Tradeoffs:
  - `src/nbms_app/views.py` is very large and mixes orchestration + policy checks + rendering.
  - API surface is intentionally read-only; external integrations currently rely on files/commands rather than service APIs.
  - Observability and security hardening are functional but still baseline.

## NBMS Requirement Delta (high-level)
- GBF/CBD ORT alignment: partial implemented; structured Section III/IV is strong, but ORT field-level conformance for sections I/II/V remains incomplete.
- DaRT-style "enter once, reuse many": partial; snapshots/review packs/export packages support reuse, but cross-cycle reusable package workflows and integration contracts are still minimal.
- Governance posture: strong baseline with audit/RBAC/consent, but still needs tighter object-level consistency, CI guardrails, and security policy depth before scale-up.

## External Standards Alignment Notes
- CBD COP Decision 16/31 confirms use of headline and binary indicators for monitoring and reporting; NBMS models now explicitly support both via structured progress + binary group/question response models.
  - Source: https://www.cbd.int/decisions/cop/16/31
- CBD ORT NR7 guidance/templates define structured Section II fields and Section III/IV progress semantics; Section I/II/V structured models and ORT v2 mapping in code follow this direction.
  - Sources:
    - https://www.cbd.int/doc/decisions/cop-15/cop-15-dec-06-en.pdf
    - https://www.cbd.int/doc/online-reporting/31/Guidance_English.pdf
    - https://www.cbd.int/doc/online-reporting/31/Template_Section_III_Progress_in_national_targets_English.pdf
- GBF indicator methods emphasize disaggregation by geography, taxon, ecosystem, and socioeconomic variables; NBMS indicator series schema retains optional disaggregation payloads and export ordering.
  - Source: https://www.gbf-indicators.org/resources/indicator-factsheets/
- DaRT "enter once, reuse many" pattern is partially covered via `ReportingSnapshot`, review packs, and export packages; cross-cycle reusable package manifests remain backlog work.
  - Source: https://www.unep.org/explore-topics/environmental-rights-and-governance/what-we-do/meeting-international-environmental-agreements


