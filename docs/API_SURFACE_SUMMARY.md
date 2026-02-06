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
- `GET /api/auth/csrf` (`AllowAny`)
- `GET /api/help/sections` (`AllowAny`)
- `GET /api/system/health` (`IsAuthenticated`, staff/system-admin only)

### Dashboard
- `GET /api/dashboard/summary` (`IsAuthenticated`)

### Indicators
- `GET /api/indicators` (`AllowAny`, ABAC-filtered)
- `GET /api/indicators/{uuid}` (`AllowAny`, ABAC-filtered)
- `GET /api/indicators/{uuid}/datasets` (`AllowAny`, ABAC-filtered)
- `GET /api/indicators/{uuid}/series` (`AllowAny`, ABAC-filtered)
- `GET /api/indicators/{uuid}/validation` (`AllowAny`, ABAC-filtered)
- `POST /api/indicators/{uuid}/transition` (`IsAuthenticated`, workflow/role-gated)

### Spatial
- `GET /api/spatial/layers` (`AllowAny`, ABAC-filtered)
- `GET /api/spatial/layers/{slug}/features` (`AllowAny`, ABAC-filtered, GeoJSON FeatureCollection)

### Template packs (multi-MEA runtime scaffolding)
- `GET /api/template-packs` (`IsAuthenticated`)
- `GET /api/template-packs/{pack_code}/sections` (`IsAuthenticated`)
- `GET|POST /api/template-packs/{pack_code}/instances/{instance_uuid}/responses` (`IsAuthenticated`, instance-scope check)
- `GET /api/template-packs/{pack_code}/instances/{instance_uuid}/export` (`IsAuthenticated`, exporter registry driven)

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
