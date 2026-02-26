# TIGHTENING_BACKLOG

## Status Snapshot
- Completed in this increment:
  - Angular primary app scaffold with dashboard/indicator explorer/map/template-pack pages.
  - SPA/BFF API layer under `/api/*` with auth/help/indicator/spatial/template-pack endpoints.
  - Spatial layer registry + feature store + GeoJSON APIs + ABAC tests.
  - Initial indicator workflow seed pack (4 end-to-end indicators) with methodology/data/evidence/programme links.
  - Multi-MEA template pack runtime scaffolding (CBD primary; Ramsar/CITES/CMS scaffolds).
  - Ramsar pack hardening with QA + PDF export endpoints and interactive Angular editor.
  - BIRDIE connector module with bronze/silver/gold lineage persistence and dashboard API/UI.
  - Report product framework (NBA/GMO/Invasive templates with HTML/PDF exports).
  - Playwright smoke e2e in CI docker-minimal job.
  - Docker-first root compose profile with backend+frontend+core services.
  - CI expansion with frontend and Docker smoke jobs.

## P0 (must-fix before major feature expansion)

### P0-1: Policy registry enforcement for all `/api/*` mutating endpoints
- Rationale: policy metadata exists for server views, but API endpoints still mix direct checks and service-level enforcement.
- Affected files:
  - `src/nbms_app/api_spa.py`
  - `src/nbms_app/services/policy_registry.py`
  - `src/nbms_app/tests/test_policy_registry.py`
- Acceptance criteria:
  - Every mutating API route maps to explicit policy entry.
  - Unauthorized access returns non-leaking responses consistently.
- Suggested PR slice:
  - PR-A: policy map expansion
  - PR-B: endpoint-by-endpoint enforcement + matrix tests

### P0-2: Indicator workflow import API (CSV upload) with strict validation
- Rationale: management command exists, but UI/API-driven import path is still missing.
- Affected files:
  - `src/nbms_app/api_spa.py`
  - `src/nbms_app/services/indicator_data.py` (or dedicated parser service)
  - `src/nbms_app/tests/test_api_indicator_explorer.py`
- Acceptance criteria:
  - CSV upload endpoint validates schema and writes datapoints deterministically.
  - ABAC + role checks enforced; audit event recorded.
- Suggested PR slice:
  - PR-A: parser service + tests
  - PR-B: endpoint + UI hookup

### P0-3: Export contract uplift for multi-MEA packs
- Rationale: Ramsar now has structured runtime export; CITES/CMS remain scaffold-level.
- Affected files:
  - `src/nbms_app/services/template_pack_registry.py`
  - pack-specific contract validators (new)
  - `src/nbms_app/tests/test_api_template_packs.py`
- Acceptance criteria:
  - CITES/CMS packs have explicit minimal contracts and validation tests (Ramsar complete).
- Suggested PR slice:
  - PR-A: contract schemas
  - PR-B: validation integration

## P1 (high value after P0)

### P1-1: PostGIS-native geometry migration path
- Rationale: current spatial features are JSON + bbox fields; v1 works but is not long-term geometry architecture.
- Affected files:
  - `src/nbms_app/models.py`
  - new migrations
  - spatial APIs/services and tests
- Acceptance criteria:
  - Geometry storage supports native spatial indexing and robust spatial filters.

### P1-2: Angular reporting section capture parity (I-V)
- Rationale: reporting editing still mostly Django-template driven.
- Affected files:
  - `frontend/src/app/pages/*`
  - `src/nbms_app/api_spa.py` (response save/load APIs)
- Acceptance criteria:
  - Angular can edit/save all Section I-V structured responses with existing export parity.

### P1-3: Frontend test depth
- Rationale: frontend baseline improved (component tests + smoke e2e) but still lacks deep workflow interaction coverage.
- Affected files:
  - `frontend/src/app/**/*.spec.ts`
  - CI workflow thresholds
- Acceptance criteria:
  - functional tests for dashboard, explorer filters, map interactions, template-pack response flow.

## P2 (next-wave hardening)

### P2-1: DaRT-style reusable package manifests
- Rationale: snapshots/exports exist; reusable package lifecycle is still partial.
- Affected files:
  - new models/services around package manifests and mapping registries
- Acceptance criteria:
  - create once, reuse across cycles/MEAs with deterministic replay.

### P2-2: SAST and supply-chain policy in CI
- Status: largely complete (Bandit + Trivy + gitleaks in CI); remaining work is policy tuning and gate strictness.
- Affected files:
  - `.github/workflows/ci.yml`
- Acceptance criteria:
  - SAST job added, tuned, and gating policy defined.

### P2-3: Contributor paper-cut reduction
- Rationale: Docker build context and local env drift can still slow contributors.
- Affected files:
  - `.dockerignore`, `README.md`, scripts
- Acceptance criteria:
  - sub-5-minute minimal profile rebuild on clean cache (documented benchmark).
