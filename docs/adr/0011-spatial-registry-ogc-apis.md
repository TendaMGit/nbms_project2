# ADR 0011: Spatial Registry + OGC APIs

## Status

Accepted (2026-02-07)

## Context

NBMS requires production-grade spatial capability for GBF/CBD reporting, Ramsar and other MEA workflows, and map-rich report products. Prior implementation used JSON geometry payloads only, which limited interoperability, standards compliance, and scalable query performance.

## Decision

1. Introduce a first-class Spatial Registry:
   - `SpatialUnitType`
   - `SpatialUnit`
   - extended `SpatialLayer`
   - extended `SpatialFeature`
   - `SpatialIngestionRun`
2. Implement OGC-style APIs:
   - `/api/ogc`
   - `/api/ogc/collections`
   - `/api/ogc/collections/{layer_code}/items`
3. Implement vector-tile endpoints:
   - `/api/tiles/{layer_code}/tilejson`
   - `/api/tiles/{layer_code}/{z}/{x}/{y}.pbf`
4. Standardize ingestion through GDAL/ogr2ogr into PostGIS with validity repair and provenance/audit capture.
5. Keep non-GIS fallback runtime support for Windows/non-Docker paths via `nbms_app.spatial_fields`, while Docker/PostGIS (`ENABLE_GIS=true`) is canonical.

## Consequences

Positive:

- standards-aligned map/service interoperability,
- scalable vector serving (MVT),
- better governance (audit + consent + ABAC on spatial data),
- direct support for spatial indicator methods and reporting products.

Trade-offs:

- GIS stack adds operational complexity (GDAL/GEOS/PROJ),
- migration/test paths must differentiate GIS and non-GIS environments,
- GeoServer publishing introduces another integration surface to monitor.
