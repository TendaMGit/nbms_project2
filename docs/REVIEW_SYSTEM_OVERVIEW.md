# REVIEW_SYSTEM_OVERVIEW

## As-Built System Map (2026-02-07)

Blueprint alignment statement:
- NBMS operates as a registry + ingestion + validation + publication + reporting platform.
- Indicator computation pipelines are contributor-owned and remain outside NBMS runtime.
- Governance scope is ITSC methods approval plus conditional Data Steward review for flagged releases.
- Roadmap language is maintained as `Phase 1 - National MVP` with backlog tiers inside that phase.

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
  - ingestion pipeline: `src/nbms_app/services/spatial_ingest.py`
  - OGC/tile APIs: `src/nbms_app/api_spatial.py`
- Multi-MEA runtime:
  - pack exporter registry: `src/nbms_app/services/template_pack_registry.py`
- Template pack QA/PDF runtime:
  - `src/nbms_app/services/template_packs.py`
- Indicator method runtime:
  - `src/nbms_app/indicator_methods/`
  - `src/nbms_app/services/indicator_method_sdk.py`
- BIRDIE integration:
  - `src/nbms_app/integrations/birdie/`
- Report products:
  - `src/nbms_app/services/report_products.py`

### Frontend module map
- App shell + route layout: `frontend/src/app/app.ts`, `frontend/src/app/app.html`
- Pages:
  - dashboard: `frontend/src/app/pages/dashboard-page.component.ts`
  - indicator explorer + detail: `frontend/src/app/pages/indicator-explorer-page.component.ts`, `frontend/src/app/pages/indicator-detail-page.component.ts`
  - spatial viewer: `frontend/src/app/pages/map-viewer-page.component.ts`
  - reporting entry point: `frontend/src/app/pages/reporting-page.component.ts`
  - template packs editor: `frontend/src/app/pages/template-packs-page.component.ts`
  - BIRDIE dashboard: `frontend/src/app/pages/birdie-programme-page.component.ts`
  - report products: `frontend/src/app/pages/report-products-page.component.ts`
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
- Seeded by `seed_demo_spatial` (with `seed_spatial_demo_layers` compatibility alias):
  - provinces, protected areas, ecosystem threat demo layer
- APIs:
  - `/api/spatial/layers`
  - `/api/spatial/layers/{slug}/features` (GeoJSON + bbox/province/indicator/year filters)
  - `/api/ogc`, `/api/ogc/collections`, `/api/ogc/collections/{layer_code}/items`
  - `/api/tiles/{layer_code}/tilejson`
  - `/api/tiles/{layer_code}/{z}/{x}/{y}.pbf`
  - `/api/spatial/layers/upload` for GeoJSON/GPKG/SHP ingestion
- UI:
  - Angular MapLibre page with layer toggles, filters, legend, feature-inspect panel.
- Ops:
  - `seed_geoserver_layers` publishes NBMS-backed layers to GeoServer WMS/WFS.

### 4) Multi-MEA template workflow
- Generic runtime models:
  - `ReportTemplatePack`, `ReportTemplatePackSection`, `ReportTemplatePackResponse`
- Seeded packs:
  - `cbd_ort_nr7_v2` (primary)
  - `ramsar_v1` (COP14-oriented section schema)
  - `cites_v1`, `cms_v1` scaffold packs
- Runtime APIs for section retrieval, response save/load, validation, JSON export, and PDF export.

### 5) BIRDIE connector workflow
- Integration client and ingestion service persist lineage in:
  - `IntegrationDataAsset` (`bronze`/`silver`/`gold`)
  - `BirdieSpecies`, `BirdieSite`, `BirdieModelOutput`
- Command:
  - `python manage.py seed_birdie_integration`
- Programme integration:
  - `NBMS-BIRDIE-INTEGRATION` run pipeline with ingest/validation/publish hooks in `programme_ops.py`
- API/UI:
  - `/api/integrations/birdie/dashboard`
  - Angular BIRDIE dashboard route `/programmes/birdie`

### 6) Report product workflow
- Runtime models:
  - `ReportProductTemplate`, `ReportProductRun`
- Seeded product templates:
  - `nba_v1`, `gmo_v1`, `invasive_v1`
- APIs:
  - `/api/report-products*` for list/preview/run history and HTML/PDF exports
- UI:
  - Angular report products builder route `/report-products`

## Key Tradeoffs
- Chosen now:
  - session+CSRF auth for Angular (no token split-brain)
  - docker-first reproducibility with Windows fallback
  - PostGIS-first spatial registry with OGC+tile endpoints and GeoServer bridge
- Deferred:
  - direct ORT submission adapters
  - full CITES/CMS question-bank and export schemas
  - high-volume async execution for all indicator methods/connectors

## Current Architecture Risks
- Large `views.py` remains a maintenance hotspot despite policy registry progress.
- Spatial runtime is hybrid for compatibility (geometry fields with JSON fallbacks in non-GIS environments); long-term target is full geometry-only parity across all runtimes.
- Some reporting capture remains Django-template based while Angular progressively becomes primary UX.
