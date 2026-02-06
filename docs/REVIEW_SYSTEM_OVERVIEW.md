# REVIEW_SYSTEM_OVERVIEW

## As-Built System Map (2026-02-06)

### Runtime layers
- Backend: Django 5.x + DRF (`src/config`, `src/nbms_app`)
- Frontend: Angular standalone app (`frontend/`)
- Container runtime: root `compose.yml` with profiles `minimal`, `full`, `spatial`
- Data services: PostGIS container, Redis, MinIO, optional GeoServer

### Backend module map
- Core domain models: `src/nbms_app/models.py`
- Server UI workflows: `src/nbms_app/views.py`, templates under `templates/nbms_app/`
- SPA/BFF endpoints: `src/nbms_app/api_spa.py`, `src/nbms_app/api_urls.py`
- Read-only catalog APIs: `src/nbms_app/api.py` (`/api/v1/*`)
- Governance services:
  - authorization: `src/nbms_app/services/authorization.py`
  - policy registry: `src/nbms_app/services/policy_registry.py`
  - consent: `src/nbms_app/services/consent.py`
  - audit: `src/nbms_app/services/audit.py`
- Reporting/export services:
  - ORT exports: `src/nbms_app/exports/ort_nr7_v2.py`, `src/nbms_app/exports/ort_nr7_narrative.py`
  - contract checks: `src/nbms_app/services/export_contracts.py`
- Spatial services:
  - layer/feature ABAC filtering: `src/nbms_app/services/spatial_access.py`
- Multi-MEA runtime:
  - pack exporter registry: `src/nbms_app/services/template_pack_registry.py`

### Frontend module map
- App shell + route layout: `frontend/src/app/app.ts`, `frontend/src/app/app.html`
- Pages:
  - dashboard: `frontend/src/app/pages/dashboard-page.component.ts`
  - indicator explorer + detail: `frontend/src/app/pages/indicator-explorer-page.component.ts`, `frontend/src/app/pages/indicator-detail-page.component.ts`
  - spatial viewer: `frontend/src/app/pages/map-viewer-page.component.ts`
  - reporting entry point: `frontend/src/app/pages/reporting-page.component.ts`
  - template packs: `frontend/src/app/pages/template-packs-page.component.ts`
- API services: `frontend/src/app/services/*.ts`

## Main Workflows

### 1) ORT NR7 reporting workflow
- Reporting entities: `ReportingCycle`, `ReportingInstance`, Section I-V structured models.
- Freeze/review/approval/export flows remain in Django server views/services.
- ORT v2 export remains deterministic and contract-validated.

### 2) Indicator workflow v1
- Seeded by `seed_indicator_workflow_v1`:
  - 4 operational GBF/NBA-inspired indicators
  - linked national targets, framework indicators, methodologies/versions
  - datasets/catalog links, releases, evidence, data series/datapoints
  - monitoring programme links as source-of-data structure
- Workflow transitions exposed via `/api/indicators/{uuid}/transition` with server-side role checks and evidence-before-publish rule.

### 3) Spatial workflow v1
- Seeded by `seed_spatial_demo_layers`:
  - provinces, protected areas, ecosystem threat demo layer
- APIs:
  - `/api/spatial/layers`
  - `/api/spatial/layers/{slug}/features` (GeoJSON + bbox/province/indicator/year filters)
- UI:
  - Angular MapLibre page with layer toggles, filters, legend, feature-inspect panel.

### 4) Multi-MEA template workflow
- Generic runtime models:
  - `ReportTemplatePack`, `ReportTemplatePackSection`, `ReportTemplatePackResponse`
- Seeded packs:
  - `cbd_ort_nr7_v2` (primary)
  - `ramsar_v1`, `cites_v1`, `cms_v1` scaffold packs
- Runtime APIs for section retrieval, response save/load, and export handler dispatch.

## Key Tradeoffs
- Chosen now:
  - session+CSRF auth for Angular (no token split-brain)
  - docker-first reproducibility with Windows fallback
  - GeoJSON API-first spatial delivery before full PostGIS geometry API refactor
- Deferred:
  - direct ORT submission adapters
  - full Ramsar/CITES/CMS export schemas
  - automated indicator computation runners per methodology script

## Current Architecture Risks
- Large `views.py` remains a maintenance hotspot despite policy registry progress.
- Spatial storage currently uses JSON geometries with bbox indexing; works for v1 but is not final-scale geometry architecture.
- Some reporting capture remains Django-template based while Angular progressively becomes primary UX.
