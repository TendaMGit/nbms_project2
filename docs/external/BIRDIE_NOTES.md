# BIRDIE Integration Notes

## Sources
- Swagger UI: https://birdieapp.sanbi.org.za/birdie/swagger-ui/
  - Local snapshot: `birdie-swagger-ui.html`
- OpenAPI spec JSON:
  - https://birdieapp.sanbi.org.za/birdie/swagger-ui/birdie_application.json
  - Local snapshot: `birdie_application.json`
- Project README:
  - https://github.com/AfricaBirdData/BIRDIE
  - Local snapshot: `BIRDIE_README.md`

## OpenAPI Snapshot
- OpenAPI version: `3.0.3`
- Tags include:
  - `Distribution`
  - `Abundance`
  - `Site`
  - `Species`
  - `Variables`
- Endpoint groups observed:
  - Species/guild/site lists
  - State-space model outputs (`/ssm/...`)
  - Occupancy/prediction endpoints (`/psi/...`, `/real_occ/...`)
  - Ancillary geojson parameter/year endpoint (`/rec/geojson/pentad/{parameter}/{year}`)

## NBMS Mapping Direction
- Treat BIRDIE as an external connector module feeding:
  - bronze (raw payload capture),
  - silver (normalized entities),
  - gold (indicator-ready marts).
- Preserve source provenance:
  - endpoint/path used
  - model/version context
  - refresh timestamp and request hash
- Start with API ingestion and method stubs before attempting full R-model parity port.

## Current NBMS Implementation Hook
- BIRDIE integration represented as an operational programme scaffold:
  - `NBMS-BIRDIE-INTEGRATION` seeded by `seed_programme_ops_v1`
