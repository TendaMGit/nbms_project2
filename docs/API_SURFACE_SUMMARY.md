# API_SURFACE_SUMMARY

## Scope
This summary covers executable API-like surfaces in code:
- DRF router endpoints in `src/nbms_app/api.py` under `/api/v1/`
- JSON export endpoints in `src/nbms_app/views.py`
- Metrics and health endpoints

## DRF API (`/api/v1/`)
Source: `src/config/urls.py`, `src/nbms_app/api.py`

### Endpoint list (read-only)
- `GET /api/v1/evidence/`, `GET /api/v1/evidence/{uuid}/`
- `GET /api/v1/frameworks/`, `GET /api/v1/frameworks/{uuid}/`
- `GET /api/v1/framework-goals/`, `GET /api/v1/framework-goals/{uuid}/`
- `GET /api/v1/framework-targets/`, `GET /api/v1/framework-targets/{uuid}/`
- `GET /api/v1/framework-indicators/`, `GET /api/v1/framework-indicators/{uuid}/`
- `GET /api/v1/national-targets/`, `GET /api/v1/national-targets/{uuid}/`
- `GET /api/v1/indicators/`, `GET /api/v1/indicators/{uuid}/`
- `GET /api/v1/dataset-catalog/`, `GET /api/v1/dataset-catalog/{uuid}/`
- `GET /api/v1/dataset-releases/`, `GET /api/v1/dataset-releases/{uuid}/`

### Auth and access model
- Authentication classes from settings (`src/config/settings/base.py`):
  - `SessionAuthentication`
  - `BasicAuthentication`
- Authorization:
  - ABAC filtering via `filter_queryset_for_user` or catalog-specific filters.
  - SystemAdmin bypass via `is_system_admin`.
- Audit:
  - API list/detail reads pass through `AuditReadOnlyModelViewSet` and call `audit_sensitive_access`.

### Serializer field exposure (selected)
- Evidence: `uuid`, `title`, `evidence_type`, `source_url`, `status`, `sensitivity`
- Framework: `uuid`, `code`, `title`, `description`, `status`, `sensitivity`
- FrameworkGoal: `uuid`, `framework`, `code`, `title`, `status`, `sensitivity`, `sort_order`
- FrameworkTarget: `uuid`, `framework`, `goal`, `code`, `title`, `status`, `sensitivity`
- FrameworkIndicator: `uuid`, `framework`, `framework_target`, `code`, `title`, `indicator_type`, `status`, `sensitivity`
- NationalTarget: `uuid`, `code`, `title`, `status`, `sensitivity`
- Indicator: `uuid`, `code`, `title`, `national_target`, `indicator_type`, `status`, `sensitivity`
- DatasetCatalog: `uuid`, `dataset_code`, `title`, `description`, `access_level`, `is_active`
- DatasetRelease: `uuid`, `dataset`, `version`, `release_date`, `status`, `sensitivity`

## JSON Export Endpoints (non-DRF)
Source: `src/nbms_app/urls.py`, `src/nbms_app/views.py`

- `GET /exports/instances/{instance_uuid}/ort-nr7-narrative.json`
  - builder: `build_ort_nr7_narrative_payload`
  - schema marker: `nbms.ort.nr7.narrative.v1`
- `GET /exports/instances/{instance_uuid}/ort-nr7-v2.json`
  - builder: `build_ort_nr7_v2_payload`
  - schema marker: `nbms.ort.nr7.v2`
  - contract validator: `src/nbms_app/services/export_contracts.py`
- `GET /exports/{package_uuid}/download/`
  - download of released `ExportPackage.payload`

Auth/authorization:
- These routes are staff/system-admin gated in `views.py`.
- Export generation additionally enforces readiness, approval, consent, and referential integrity through service-layer calls.
- Structured sections I/II/V and enriched III/IV content are exported from structured models when present; narrative templates remain fallback for backward compatibility.

## Health and Metrics Endpoints
- `GET /health/` (`health_db`)
- `GET /health/storage/` (`health_storage`)
- `GET /metrics/` (`views_metrics.metrics`)
  - access via SystemAdmin session or `METRICS_TOKEN` bearer token
  - query token support only when `METRICS_ALLOW_QUERY_TOKEN=true`

## Schema/OpenAPI Notes
- DRF schema class is configured (`drf_spectacular.openapi.AutoSchema`) in `src/config/settings/base.py`.
- No dedicated OpenAPI serving route is currently wired in `src/config/urls.py`.

## Current API Limitations
- API is read-only; no create/update/delete endpoints.
- No token/JWT/OAuth2 API auth profile (session/basic only).
- No explicit API version negotiation beyond URL namespace `/api/v1/`.

