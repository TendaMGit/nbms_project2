# API_SURFACE_SUMMARY

## Scope
- `src/config/urls.py`
- `src/nbms_app/api_urls.py` (`/api/*`, SPA/BFF endpoints)
- `src/nbms_app/api.py` (`/api/v1/*`, read-only DRF catalog endpoints)
- `src/nbms_app/views.py` (`/exports/*`, health, metrics)

## Auth Model
- Primary API auth: Django session cookie + CSRF (`SessionAuthentication`).
- `/api/auth/csrf` issues CSRF token payload and cookie.
- ABAC/object filtering remains server-side via:
  - `filter_queryset_for_user` (`src/nbms_app/services/authorization.py`)
  - `indicator_data_series_for_user` / `indicator_data_points_for_user`
  - `filter_spatial_layers_for_user` / `filter_spatial_features_for_user`

## SPA/BFF Endpoints (`/api/*`)
Source: `src/nbms_app/api_urls.py`, handlers in `src/nbms_app/api_spa.py`.

### Auth + help
- `GET /api/auth/me` (`IsAuthenticated`)
- `GET /api/auth/capabilities` (`IsAuthenticated`)
- `GET /api/auth/csrf` (`AllowAny`)
- `GET /api/help/sections` (`AllowAny`)
- `GET /api/system/health` (`IsAuthenticated`, staff/system-admin only)

### Dashboard
- `GET /api/dashboard/summary` (`IsAuthenticated`)

### Monitoring Programme Operations
- `GET /api/programmes` (`IsAuthenticated`, ABAC-filtered via monitoring programme access policy)
- `GET /api/programmes/{uuid}` (`IsAuthenticated`, ABAC object scope with no-leak 404 behavior)
- `POST /api/programmes/{uuid}/runs` (`IsAuthenticated`, steward/lead/partner/system-admin manage permission required)
- `GET /api/programmes/runs/{uuid}` (`IsAuthenticated`, ABAC-filtered by parent programme)
- `POST /api/programmes/runs/{uuid}` (`IsAuthenticated`, rerun action; steward/lead/partner/system-admin manage permission required)
- `GET /api/programmes/runs/{uuid}/report` (`IsAuthenticated`, ABAC-filtered report JSON download)
- `GET /api/programmes/templates` (`IsAuthenticated`, template catalog for programme-driven setup)
- `GET /api/integrations/birdie/dashboard` (`IsAuthenticated`, BIRDIE programme scope)

### Reporting (NR7 builder)
- `GET /api/reporting/instances` (`IsAuthenticated`, staff/system-admin + instance scope)
- `GET /api/reporting/instances/{uuid}/nr7/summary` (`IsAuthenticated`, instance scope)
- `GET /api/reporting/instances/{uuid}/nr7/export.pdf` (`IsAuthenticated`, instance scope)

### Indicators
- `GET /api/indicators` (`AllowAny`, ABAC-filtered)
- `GET /api/indicators/{uuid}` (`AllowAny`, ABAC-filtered; includes spatial readiness, registry readiness, and used-by graph payloads)
- `GET /api/indicators/{uuid}/datasets` (`AllowAny`, ABAC-filtered)
- `GET /api/indicators/{uuid}/series` (`AllowAny`, ABAC-filtered)
- `GET /api/indicators/{uuid}/map` (`AllowAny`, ABAC-filtered; spatially-joined indicator GeoJSON)
- `GET /api/indicators/{uuid}/validation` (`AllowAny`, ABAC-filtered)
- `GET /api/indicators/{uuid}/methods` (`AllowAny`, ABAC-filtered)
- `POST /api/indicators/{uuid}/methods/{profile_uuid}/run` (`IsAuthenticated`, role-gated)
- `POST /api/indicators/{uuid}/transition` (`IsAuthenticated`, workflow/role-gated)

### Spatial
- `GET /api/spatial/layers` (`AllowAny`, ABAC-filtered)
- `GET /api/spatial/layers/{slug}/features` (`AllowAny`, ABAC-filtered, GeoJSON FeatureCollection)
- `POST /api/spatial/layers/upload` (`IsAuthenticated`, steward/admin/system-admin role-gated; ingestion audit tracked)
- `GET /api/spatial/layers/{layer_code}/export.geojson` (`AllowAny`, ABAC-filtered export with audit event)
- `GET /api/ogc` (`AllowAny`, OGC API landing)
- `GET /api/ogc/collections` (`AllowAny`, ABAC-filtered collection listing)
- `GET /api/ogc/collections/{layer_code}/items` (`AllowAny`, bbox/datetime/filter/limit/offset)
- `GET /api/tiles/{layer_code}/tilejson` (`AllowAny`)
- `GET /api/tiles/{layer_code}/{z}/{x}/{y}.pbf` (`AllowAny`, ABAC + cache headers + ETag)

### Template packs (multi-MEA runtime scaffolding)
- `GET /api/template-packs` (`IsAuthenticated`)
- `GET /api/template-packs/{pack_code}/sections` (`IsAuthenticated`)
- `GET|POST /api/template-packs/{pack_code}/instances/{instance_uuid}/responses` (`IsAuthenticated`, instance-scope check)
- `GET /api/template-packs/{pack_code}/instances/{instance_uuid}/validate` (`IsAuthenticated`, instance-scope check)
- `GET /api/template-packs/{pack_code}/instances/{instance_uuid}/export.pdf` (`IsAuthenticated`, instance-scope check)
- `GET /api/template-packs/{pack_code}/instances/{instance_uuid}/export` (`IsAuthenticated`, exporter registry driven)

### Report products
- `GET /api/report-products` (`IsAuthenticated`)
- `GET /api/report-products/runs` (`IsAuthenticated`, staff/system-admin broad view; user-scoped fallback)
- `GET /api/report-products/{code}/preview` (`IsAuthenticated`; optional `instance_uuid` scope check)
- `GET /api/report-products/{code}/export.html` (`IsAuthenticated`; optional `instance_uuid` scope check)
- `GET /api/report-products/{code}/export.pdf` (`IsAuthenticated`; optional `instance_uuid` scope check)

### Reference registries
- `GET /api/registries/ecosystems` (`IsAuthenticated`, ABAC-filtered, pageable, filters: biome/bioregion/version/threat/get_efg)
- `GET /api/registries/ecosystems/{uuid}` (`IsAuthenticated`, ABAC object scope)
- `GET /api/registries/taxa` (`IsAuthenticated`, ABAC-filtered, pageable, filters: rank/status/source/has_voucher/native/endemic/search)
- `GET /api/registries/taxa/{uuid}` (`IsAuthenticated`, ABAC object scope; sensitive voucher locality redacted for non-privileged users)
- `GET /api/registries/ias` (`IsAuthenticated`, ABAC-filtered, pageable, filters: stage/pathway/habitat/eicat/seicat/search)
- `GET /api/registries/ias/{uuid}` (`IsAuthenticated`, ABAC object scope)
- `GET /api/registries/gold` (`IsAuthenticated`, ABAC-filtered mart summaries; params: `kind`, `snapshot_date`, `dimension`, `limit`)
- `GET|POST /api/registries/{object_type}/{object_uuid}/evidence` (`IsAuthenticated`; ABAC object scope, role-gated evidence linking)
- `POST /api/registries/{object_type}/{object_uuid}/transition` (`IsAuthenticated`; role-gated lifecycle workflow actions `submit|approve|publish|reject`)

## DRF API (`/api/v1/*`, read-only)
Source: `src/nbms_app/api.py`.

- `GET /api/v1/evidence/`
- `GET /api/v1/frameworks/`
- `GET /api/v1/framework-goals/`
- `GET /api/v1/framework-targets/`
- `GET /api/v1/framework-indicators/`
- `GET /api/v1/national-targets/`
- `GET /api/v1/indicators/`
- `GET /api/v1/dataset-catalog/`
- `GET /api/v1/dataset-releases/`

All are read-only viewsets with ABAC filtering and audit read-tracking.

## Export + Ops Endpoints
- `GET /exports/instances/{instance_uuid}/ort-nr7-narrative.json`
- `GET /exports/instances/{instance_uuid}/ort-nr7-v2.json`
- `GET /exports/{package_uuid}/download/`
- `GET /health/`
- `GET /health/storage/`
- `GET /metrics/` (SystemAdmin session or `METRICS_TOKEN`)

## Notes
- OpenAPI schema class is configured (`drf_spectacular`) but schema-serving routes are not yet exposed in `src/config/urls.py`.
- `/api/*` provides the Angular primary UI data surface.
- Request correlation:
  - All responses include `X-Request-ID` from `src/nbms_app/middleware_request_id.py`.
  - Frontend nginx forwards `X-Request-ID` to backend (`docker/frontend/nginx.conf`).
- Programme operations runtime:
  - Command-based scheduler runner: `python manage.py run_monitoring_programmes`
  - Single-programme run entrypoint: `python manage.py run_programme --programme-code <CODE>`
  - Seeded programme ops baseline: `python manage.py seed_programme_ops_v1`
  - Registry-aligned template seed: `python manage.py seed_programme_templates`
- Demo/auth bootstrap runtime:
  - `python manage.py ensure_system_admin`
  - `python manage.py seed_demo_users`
  - `python manage.py list_demo_users`
  - `python manage.py export_role_visibility_matrix`
  - `python manage.py issue_e2e_sessions --users <U1> <U2> ...`
- BIRDIE connector runtime:
  - `python manage.py seed_birdie_integration`
  - Bronze/silver/gold lineage in `IntegrationDataAsset`
- Spatial runtime:
- `python manage.py seed_demo_spatial`
- `python manage.py seed_spatial_demo_layers` (compatibility alias)
- `python manage.py ingest_spatial_layer --layer-code <CODE> --file <path>`
- `python manage.py sync_spatial_sources`
- `python manage.py seed_geoserver_layers`
- Registry runtime:
  - `python manage.py sync_vegmap_baseline`
  - `python manage.py seed_get_reference`
  - `python manage.py sync_taxon_backbone`
  - `python manage.py sync_specimen_vouchers`
  - `python manage.py sync_griis_za`
  - `python manage.py seed_registry_workflow_rules`
  - `python manage.py refresh_registry_marts`
  - `python manage.py seed_registry_demo`
  - `python manage.py seed_vegmap_demo`
  - `python manage.py seed_taxon_demo`
  - `python manage.py seed_ias_demo`
- Report product runtime:
  - `python manage.py seed_report_products`
