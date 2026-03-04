# Superset Local Overlay

Superset is an optional stakeholder-facing dashboard layer for NBMS. Django + Angular remain the operational system of record for workflow, approvals, governance, and data entry.

The local overlay in this repo is designed to attach to an already running `nbms_dev` stack without taking it down. Superset only connects to the `analytics` schema through the `superset_ro` role, so draft and operational tables remain outside the query boundary.

Pinned image:
- `apache/superset:6.0.0-dev`

Why the `-dev` tag:
- Apache Superset's Docker guidance notes that `-dev` images are the right fit for compose-based Postgres setups because the Postgres dependencies are included.

## Preconditions

- NBMS is already running:
  - `docker compose --profile minimal up -d --build`
- Backend migrations are applied:
  - `docker compose exec backend python manage.py migrate`
- Pilot/demo data is present if you want dashboards with real content:
  - `docker compose exec backend python manage.py seed_indicator_workflow_v2`

## Environment

Copy `.env.example` to `.env` if you have not already, then set the Superset-specific variables locally.

Minimum required values:
- `SUPERSET_SECRET_KEY`
- `SUPERSET_META_DB_PASSWORD`
- `SUPERSET_ADMIN_USERNAME`
- `SUPERSET_ADMIN_PASSWORD`
- `SUPERSET_ADMIN_EMAIL`
- `SUPERSET_NBMS_RO_PASSWORD`

Important:
- Keep `SUPERSET_SECRET_KEY` stable after the first successful `superset_init`.
- If you deliberately rotate it in local development, remove the Superset overlay volumes and reattach so the encrypted metadata can be recreated cleanly.

If you want Superset admin login to match your Django operator account, set:

```powershell
$env:SUPERSET_ADMIN_USERNAME = $env:NBMS_ADMIN_USERNAME
$env:SUPERSET_ADMIN_PASSWORD = $env:NBMS_ADMIN_PASSWORD
```

For this local stack, using your existing Django operator credentials is fine. The Superset admin account is separate from the Django auth database, but the login can be kept aligned for convenience.

## Step 1: Create The Analytics Boundary

Run the backend commands against the live Docker backend:

```powershell
docker compose exec backend python manage.py create_analytics_views
docker compose exec backend python manage.py ensure_superset_ro
```

This does two things:
- creates the `analytics` schema views that expose only published, export-approved indicator outputs and safe metadata
- creates or updates `superset_ro` so it can only `CONNECT` and `SELECT` from `analytics`

Analytics views created:
- `analytics.indicator_registry`
- `analytics.indicator_latest_value`
- `analytics.indicator_timeseries`
- `analytics.framework_target_indicator_links`
- `analytics.indicator_readiness_summary`
- `analytics.spatial_units_geojson`
- `analytics.indicator_spatial_features_geojson`

Spatial publishing note:
- GeoJSON is exposed with `ST_AsGeoJSON(geom, 6)` in the analytics views.
- For large stakeholder map layers, prefer aggregated geometries or precomputed tiles rather than dumping very large GeoJSON payloads into Superset.

## Step 2: Attach Superset Without Downtime

Attach the overlay to the existing Compose project:

```powershell
.\scripts\superset-attach.ps1
```

This starts:
- `superset_db`
- `superset_redis`
- `superset_init`
- `superset`
- `superset_worker`
- `superset_beat`

Useful helpers:

```powershell
.\scripts\superset-logs.ps1
.\scripts\superset-detach.ps1
```

The scripts only target the Superset services. They do not run `down` against the rest of `nbms_dev`.

Open:
- `http://localhost:8088`

## Step 3: Register The NBMS Analytics Database In Superset

Manual UI path:
1. Log into Superset.
2. Go to `Settings -> Database Connections`.
3. Add a new database.
4. Use:

```text
postgresql+psycopg2://superset_ro:${SUPERSET_NBMS_RO_PASSWORD}@postgis:5432/${NBMS_DB_NAME}
```

Recommended settings:
- Database name: `NBMS Analytics`
- Default schema: `analytics`
- `Allow DML`: off
- `Allow CREATE TABLE AS`: off
- `Allow CREATE VIEW AS`: off

Optional automated bootstrap:

```powershell
.\scripts\superset-register-nbms-db.ps1
```

That script runs inside the Superset container and registers or updates `NBMS Analytics` using the read-only `superset_ro` credential.

## Step 4: Security Defaults

The init job ensures:
- Superset admin user from `SUPERSET_ADMIN_*`
- `Publisher` role cloned from Superset `Alpha`
- `Stakeholder Viewer` role cloned from Superset `Gamma`

Default publishing model:
- Publishers build and curate charts/dashboards.
- Stakeholder viewers get dashboard access only through assigned grants.
- Guest-token embedding uses the configured guest role model, with `Stakeholder Viewer` as the intended restricted viewer baseline.

If you need stakeholder-specific slicing:
- add Superset row-level security rules on the dataset
- keep the database-side boundary unchanged; Superset should still only see `analytics`

## Step 5: Build The First Dashboard

Good starter datasets from the pilot indicator work:
- `analytics.indicator_latest_value`
- `analytics.indicator_timeseries`
- `analytics.framework_target_indicator_links`

Suggested first dashboard:
1. Use `analytics.indicator_registry` for indicator inventory cards.
2. Use `analytics.indicator_latest_value` for current RLE/EPL/SPI summary charts.
3. Use `analytics.indicator_timeseries` for TEPI and protected-area timeseries.
4. Use `analytics.framework_target_indicator_links` to facet by GBF target.

Good pilot indicators to filter for:
- `NBA_ECO_RLE_TERR`
- `NBA_ECO_RLE_EPL_TERR_MATRIX`
- `NBA_ECO_EPL_TERR`
- `NBA_TEPI_TERR`
- `NBA_PLANT_SPI`

## Sharing Dashboards

Internal sharing:
- use normal Superset users and dashboard grants

Embedding:
- enable guest-token flows against `/api/v1/security/guest_token/`
- keep the embedded role restricted
- never use an operational NBMS database credential for embedding

High-level guest-token example:

```javascript
const response = await fetch("/api/v1/security/guest_token/", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${accessToken}`,
  },
  body: JSON.stringify({
    resources: [{ type: "dashboard", id: "YOUR_DASHBOARD_ID" }],
    rls: [],
    user: {
      username: "guest-viewer",
      first_name: "Guest",
      last_name: "Viewer",
    },
  }),
});
```

## Verification Checklist

1. `docker compose exec backend python manage.py create_analytics_views`
2. `docker compose exec backend python manage.py ensure_superset_ro`
3. `.\scripts\superset-attach.ps1`
4. Open `http://localhost:8088`
5. Confirm the Superset admin user can sign in
6. Register `NBMS Analytics`
7. Build a simple chart from `analytics.indicator_latest_value`
8. Confirm draft or non-export-approved releases do not appear in Superset datasets

## Troubleshooting

- If `superset` or `superset_worker` loops on startup, run `.\scripts\superset-logs.ps1` and confirm `superset_init` completed.
- If `superset_init` fails with `Invalid decryption key`, your metadata volume was created with a different `SUPERSET_SECRET_KEY`. Restore the old key or delete the Superset overlay volumes and reattach.
- If database registration fails, verify:
  - `docker compose exec backend python manage.py create_analytics_views`
  - `docker compose exec backend python manage.py ensure_superset_ro`
  - `SUPERSET_NBMS_RO_PASSWORD` matches the password used for the role
- If map datasets feel too large, use the GeoJSON views only for small or aggregated layers and prefer existing NBMS vector-tile endpoints for heavy map rendering.
