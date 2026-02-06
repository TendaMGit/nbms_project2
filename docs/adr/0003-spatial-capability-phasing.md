# ADR 0003: Spatial Capability Phasing (PostGIS First, GeoServer Optional)

- Status: Accepted
- Date: 2026-02-06

## Context
NBMS must support spatial indicators and map-centric exploration, while preserving Windows-first developer onboarding where GIS dependencies are optional.

## Decision
- Use PostGIS as the authoritative spatial datastore in Docker and production-like environments.
- Keep `ENABLE_GIS=false` path operational for local Windows development where GDAL/GEOS setup is not available.
- Treat GeoServer as an optional spatial profile component for publication/integration scenarios.
- Expose GeoJSON/vector API endpoints from Django/DRF as the first integration surface for Angular map views.

## Consequences
- Supports immediate spatial roadmap without blocking non-spatial contributors.
- Requires dual-path testing (GIS-enabled and GIS-disabled).
- GeoServer-dependent capabilities should remain optional until reproducibility and security hardening are complete.
