# NBMS API (Read-Only)

Base path: `/api/v1/`

## Read-only endpoints
- `GET /api/v1/frameworks/`
- `GET /api/v1/frameworks/{uuid}/`
- `GET /api/v1/framework-goals/`
- `GET /api/v1/framework-goals/{uuid}/`
- `GET /api/v1/framework-targets/`
- `GET /api/v1/framework-targets/{uuid}/`
- `GET /api/v1/framework-indicators/`
- `GET /api/v1/framework-indicators/{uuid}/`
- `GET /api/v1/national-targets/`
- `GET /api/v1/national-targets/{uuid}/`
- `GET /api/v1/indicators/`
- `GET /api/v1/indicators/{uuid}/`
- `GET /api/v1/dataset-catalog/`
- `GET /api/v1/dataset-catalog/{uuid}/`
- `GET /api/v1/dataset-releases/`
- `GET /api/v1/dataset-releases/{uuid}/`
- `GET /api/v1/evidence/`
- `GET /api/v1/evidence/{uuid}/`

## Access rules
- All endpoints are read-only and enforce ABAC filtering for non-SystemAdmin users.
- SystemAdmin has unrestricted access (superuser or `SystemAdmin` group/permission).
- Read access is audited on detail and list endpoints (sensitive objects are always audited).

## Notes
- API responses are intended for registry/reference lookups and internal integrations.
- Write endpoints are intentionally omitted in this phase.
