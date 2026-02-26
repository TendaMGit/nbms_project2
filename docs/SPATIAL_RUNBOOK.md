# Spatial Runbook

## Purpose

Operational guide for NBMS Spatial Registry, OGC APIs, vector tiles, ingestion, and GeoServer publication.

## Prerequisites

- Docker + Docker Compose
- PostGIS profile running
- Backend image includes GDAL/GEOS/PROJ and `ogr2ogr`

## Start Runtime

```powershell
docker compose --profile spatial up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py sync_spatial_sources
docker compose exec backend python manage.py run_programme --programme-code NBMS-SPATIAL-BASELINES
docker compose exec backend python manage.py seed_geoserver_layers
docker compose exec backend python manage.py verify_geoserver_smoke
```

## Health and Smoke

```powershell
curl http://127.0.0.1:8000/health/
curl http://127.0.0.1:8000/api/ogc
curl http://127.0.0.1:8000/api/ogc/collections
curl http://127.0.0.1:8000/api/tiles/ZA_PROVINCES_NE/tilejson
curl http://127.0.0.1:8000/api/tiles/ZA_PROVINCES_NE/0/0/0.pbf --output tile.pbf
```

## Source Sync (Real Open Data)

```powershell
docker compose exec backend python manage.py sync_spatial_sources
```

Optional flags:

- `--source-code NE_ADMIN1_ZA`
- `--include-optional` (token-gated sources only)
- `--force`
- `--dry-run`

Default auto-synced sources:

- `NE_ADMIN1_ZA` -> `ZA_PROVINCES_NE`
- `NE_PROTECTED_LANDS_ZA` -> `ZA_PROTECTED_AREAS_NE` (DFFE SAPAD public feed)
- `NE_GEOREGIONS_ZA` -> `ZA_ECOSYSTEM_PROXY_NE`

Restricted optional source:

- `WDPA_OPTIONAL` (requires `WDPA_API_TOKEN`, disabled by default)

## Ingestion (Management Command)

```powershell
docker compose exec backend python manage.py ingest_spatial_layer --layer-code CUSTOM_LAYER --file /tmp/data.geojson --title "Custom Layer"
```

Supported inputs:

- `.geojson`
- `.gpkg`
- `.shp` or zipped shapefile (`.zip`)

Pipeline behavior:

- imports through `ogr2ogr` into temp PostGIS table,
- validates geometry (`ST_IsValid`),
- attempts repair (`ST_MakeValid`),
- upserts into `SpatialFeature`,
- records `SpatialIngestionRun` + audit event.
- converts ArcGIS feature JSON feeds to GeoJSON when required before ingest.
- if source refresh fails but a prior snapshot exists, sync degrades to `skipped` and retains last valid layer snapshot.

## Ingestion (API)

Endpoint:

- `POST /api/spatial/layers/upload`

Required multipart fields:

- `file`
- `layer_code`

Optional:

- `title`
- `source_layer_name` (for multi-layer sources)

## OGC and Tile Endpoints

- `GET /api/ogc`
- `GET /api/ogc/collections`
- `GET /api/ogc/collections/{layer_code}/items?bbox=&datetime=&limit=&offset=&filter=`
- `GET /api/tiles/{layer_code}/tilejson`
- `GET /api/tiles/{layer_code}/{z}/{x}/{y}.pbf`

Controls:

- bbox-size guardrails,
- feature limits and offsets,
- tile zoom cap,
- ETag + cache headers on vector tile responses.

## GeoServer Publishing

```powershell
docker compose exec backend python manage.py seed_geoserver_layers
docker compose exec backend python manage.py verify_geoserver_smoke
```

Required env:

- `GEOSERVER_URL`
- `GEOSERVER_USER`
- `GEOSERVER_PASSWORD`
- optional: `GEOSERVER_WORKSPACE`, `GEOSERVER_DATASTORE`

Default docker runtime values (set in `compose.yml` backend service):
- `GEOSERVER_URL=http://geoserver:8080/geoserver`
- `GEOSERVER_USER=admin`

Behavior:

- ensures workspace + PostGIS datastore,
- creates per-layer SQL views for `SpatialFeature`,
- publishes feature types for WMS/WFS.
- publishes only layers where `publish_to_geoserver=true`.

## ABAC + Consent

- Layer visibility is filtered by sensitivity/org/role.
- Consent-gated layers are hidden unless consent is granted.
- Sensitive layers are generalized in feature output for non-system-admin users.

## Map Workspace

Primary UI route:

- `/map`

Capabilities:

- layer catalog grouped by theme,
- vector-tile rendering,
- optional GeoServer WMS rendering per layer toggle,
- property/AOI filtering,
- feature inspection,
- GeoJSON export,
- add-to-report-product workflow hook.

## Programme Ops Integration

`NBMS-SPATIAL-BASELINES` runs ingest/validate/publish as an operational pipeline:

- ingest step executes `sync_spatial_sources`,
- run artefacts and QA results are persisted per step,
- overlay compute step writes province-disaggregated outputs for protected area coverage indicators,
- API exposes run report JSON:
  - `GET /api/programmes/runs/{run_uuid}/report`
