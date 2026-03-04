# UI Indicator Database PR Notes

## Current State Map

### Frontend
- Routing already preserves the required entry points:
  - `/dashboard`
  - `/frameworks`
  - `/frameworks/:frameworkId`
  - `/frameworks/:frameworkId/targets/:targetId`
  - `/indicators`
  - `/indicators/:uuid`
- `ContextStateService` and `context.models.ts` already define the canonical URL context model (`report_cycle`, `release`, `method`, `geo_type`, `geo_code`, `start_year`, `end_year`, `agg`, `metric`, `view`, etc.) and are used by dashboard/framework/target pages.
- The shell and page-header primitives exist, but header actions do not yet collapse into an overflow menu and the sidenav open state is not persisted.
- Dashboard, framework explorer/detail, and target detail are already redesigned in the mono theme and use shared analytics primitives, but their narratives are static card content and their map tabs are placeholders.
- `/indicators` is already positioned as an indicator database explorer with saved views, watchlist state, compare, and a map-summary mode, but it does not yet use the shared `ContextStateService`.
- `/indicators/:uuid` is the most advanced analytics surface today. It already has KPI/chart/table/detail tabs plus auditable governance/provenance fields, but it manages its own filter form, uses placeholder map content, and still carries explicit TODOs for backend context filters and a dedicated audit endpoint.
- `nbms-narrative-panel` exists as a read-only narrative surface with copy and "Insert to report" affordances, but there is no governed authoring workflow for framework/target/indicator/dashboard entities yet.
- `indicator-map-panel` already renders GeoJSON with MapLibre in the mono palette, but it is read-only: no layer selector, no click-to-filter handoff into shared context, and no reusable map-card contract for framework/target/dashboard pages.

### Backend
- `src/nbms_app/api_urls.py` already exposes a substantial SPA API surface for auth, preferences, dashboard, reporting workspace, indicators, registries, downloads, template packs, report products, and spatial services.
- Existing indicator APIs:
  - `GET /api/indicators`
  - `GET /api/indicators/:uuid`
  - `GET /api/indicators/:uuid/datasets`
  - `GET /api/indicators/:uuid/series`
  - `GET /api/indicators/:uuid/map`
  - `GET /api/indicators/:uuid/validation`
  - `GET /api/indicators/:uuid/methods`
  - workflow transitions on `POST /api/indicators/:uuid/transition` and `POST /api/indicator-series/:seriesUuid/workflow`
- The current indicator explorer/detail contracts are useful but limited:
  - `series` only supports simple `agg` and optional `year`/`geography` filtering.
  - `map` only supports a selected year and admin-layer join.
  - there is no generic cube endpoint, no dimension metadata endpoint, no visual profile endpoint, and no dedicated indicator audit endpoint.
- The backend already has reusable building blocks for the new work:
  - ABAC helpers via `filter_queryset_for_user(...)`
  - indicator data visibility helpers via `indicator_data_series_for_user(...)` and `indicator_data_points_for_user(...)`
  - release workflow helpers via `submit_indicator_release(...)`, `approve_indicator_release(...)`, and `get_release_workflow_state(...)`
  - generic audit capture via `record_audit_event(...)`
  - report narrative block storage/versioning via `ReportNarrativeBlock` and `ReportNarrativeBlockVersion`
- Domain models already cover most of the data we need to expose:
  - indicator, framework, framework-target, framework-indicator, national-target
  - methodology and methodology-version linking
  - datasets, dataset releases, evidence links
  - indicator series/data points with `dataset_release`, `programme_run`, `disaggregation`, `spatial_unit`, and `spatial_layer`
  - audit events
- There is not yet a generic narrative model for dashboard/framework/target/indicator entities, so governed narrative authoring will need either a new entity-scoped wrapper or careful reuse of the existing narrative block/version pattern.

### Testing Baseline
- Frontend unit tests and Playwright smoke coverage already exist.
- Current Playwright coverage is smoke-oriented; it does not yet assert responsive behavior across desktop/tablet/mobile viewports for the four database surfaces.

## What Changed

### Backend analytics and governance APIs
- Extended `GET /api/indicators/:uuid/series` to honor shared context query params:
  - `report_cycle`
  - `release`
  - `method`
  - `geo_type`
  - `geo_code`
  - `start_year`
  - `end_year`
  - `agg`
- Extended `GET /api/indicators/:uuid/map` to honor the same context filters plus map metric selection.
- Added `GET /api/indicators/:uuid/cube` for grouped indicator drilldowns across geography, taxonomy, and categorical dimensions.
- Added `GET /api/indicators/:uuid/dimensions` and `GET /api/dimensions` for dimension metadata.
- Added `GET /api/indicators/:uuid/visual-profile` for rule-based view/profile metadata.
- Added an indicator pack registry in `src/nbms_app/services/indicator_packs.py` so each pack authoritatively defines:
  - available/default views
  - supported dimensions and taxonomy levels
  - legends for category-based views
  - map layer candidates, join keys, and metric options
  - governed narrative prompts
- Added `GET /api/indicators/:uuid/audit` for workflow/audit event timelines.
- Added governed narrative endpoints for `dashboard`, `framework`, `target`, and `indicator` entities:
  - `GET /api/narratives/:entityType/:entityId`
  - `POST /api/narratives/:entityType/:entityId/draft`
  - `POST /api/narratives/:entityType/:entityId/submit`
  - `GET /api/narratives/:entityType/:entityId/versions`
- Added governed narrative models, version history, local-safe markdown rendering, and capability exposure for `can_edit_narratives`.

### PostGIS-first pilot ingest
- Added `docker-compose.test.yml` and `make test-backend` so the primary backend test path is Docker + PostgreSQL/PostGIS, with MinIO available for bronze asset writes during ingest.
- Added `src/nbms_app/pilots/nba_pilot_v1.yml` as the pinned pilot manifest for externally produced NBA outputs.
- Added `python manage.py ingest_nba_pilot_outputs` to create governed:
  - `Dataset`
  - `DatasetRelease`
  - bronze asset storage records in MinIO/S3
  - `Indicator`, `IndicatorDataSeries`, `IndicatorDataPoint`
  - `MethodologyVersion`
  - evidence/provenance links
  - GBF and secondary-framework mappings
- Added `python manage.py seed_indicator_workflow_v2`, which layers the pilot ingest on top of the existing indicator workflow seed and expands the visible demo catalogue to at least 25 published indicators.
- Updated the backend Docker entrypoint so the default compose runtime seeds the v2 catalogue, including pilot indicators and the biome spatial layer used by pilot map views.

### Mono redesign layer
- Added a new `mono_clean` theme pack and made it the default frontend theme.
- Reworked the global shell into a grayscale, compact database UI with a reduced navigation model:
  - `Home`
  - `Frameworks`
  - `Indicators`
- Added global search suggestions and direct drilldown navigation across frameworks, targets, and indicators.
- Applied a consistent visual system across the four main database surfaces:
  - `Dashboard`
  - `Framework detail`
  - `Target detail`
  - `Indicator explorer/detail`

### Shared context model
- Added a shared analytics query-param model in `frontend/src/app/models/context.models.ts`.
- Added `ContextStateService` in `frontend/src/app/services/context-state.service.ts` to parse, default, and write URL-synced context state with `replaceUrl: true`.

### Reusable analytics UI
- Added tokenized shared analytics primitives under `frontend/src/app/ui/`:
  - `nbms-context-bar`
  - `nbms-tab-strip`
  - `nbms-stat-strip`
  - `nbms-chart-card`
  - `nbms-map-card`
  - `nbms-narrative-panel`
  - `nbms-entity-list-table`
  - `nbms-evidence-list`
  - `nbms-distribution-card-grid`
  - `nbms-legend`
  - `nbms-callout`
- Added `nbms-share-menu` for deep-link/citation/share scaffolding in page headers and indicator detail.
- Added `nbms-interpretation-editor` for governed narrative authoring with:
  - local autosave drafts
  - explicit save + submit for review
  - version history
  - latest-vs-current compare
  - insert-into-report routing
- Added a visual-profile-driven indicator host and view suite:
  - `nbms-indicator-view-host`
  - `nbms-view-timeseries`
  - `nbms-view-distribution`
  - `nbms-view-taxonomy-drilldown`
  - `nbms-view-matrix`
  - `nbms-view-binary`
- Extended shared header/KPI/status/readiness components to support the new analytics layouts.
- Tokenized the indicator map panel so it no longer relies on hardcoded colors.

### Framework and target analytics pages
- Added `/frameworks`.
- Added `/frameworks/:frameworkId`.
- Added `/frameworks/:frameworkId/targets/:targetId`.
- Added dashboard and shell links so drilldowns flow `Dashboard -> Framework -> Target -> Indicator`.
- Added a lightweight `FrameworkAnalyticsService` that derives framework and target slices from existing dashboard and indicator endpoints while dedicated backend endpoints are still pending.

### Indicator detail and explorer
- Upgraded `/indicators/:uuid` to a tabbed detail workspace with:
  - `tab=indicator|details|evidence|narrative|audit`
  - context filters for cycle, method, release, geography, and year range
  - KPI strip, charts, distribution cards, detailed table, and narrative rail
- visual-profile-driven `view=timeseries|distribution|taxonomy|matrix|binary` rendering inside `tab=indicator`
- synchronized KPI strip, visuals, map interactions, auditable table, and governed narrative rail
- map click-to-filter and drilldown URL state for geography/category/taxonomy slices
- pack-driven legends, matrix definitions, and narrative prompts now flow through the same indicator host without breaking `/indicators` or `/indicators/:uuid`
- Replaced the detail-page share button with the reusable share menu.
- Added governed narrative authoring to the indicator right rail and the dedicated narrative tab.
- Wired the indicator audit tab to the new backend audit endpoint.
- Kept `/indicators` and `/indicators/:uuid` route compatibility intact.
- Modularized the explorer toolbar, insights rail, and compare panel into separate components.
- Added canonical `geo_type` / `geo_code` compatibility in the explorer while preserving legacy `geography_type` / `geography_code`.

### Dashboard / framework / target experience
- Expanded `/dashboard` into a database home surface with:
  - KPI strip
  - readiness and blocker summary
  - map-first placeholder
  - target spotlight drilldowns
  - recent updates, data quality, and approvals sections
- Added higher-signal framework and target layouts with:
  - summary card grids
  - explicit drilldowns
  - narrative side rails
  - denser analytics/table presentation
- Replaced static narrative side rails on dashboard, framework detail, and target detail with governed narrative authoring.
- Added share menu actions to dashboard, framework detail, and target detail headers.
- Preserved current context query params when drilling from dashboard -> framework/target/indicator and from framework/target -> deeper detail pages.

## New API Endpoints

### Indicator analytics
- `GET /api/indicators/:uuid/series?report_cycle=NR7-2024&release=latest_approved&method=current&geo_type=province&start_year=2018&end_year=2024&agg=province`
- `GET /api/indicators/:uuid/map?report_cycle=NR7-2024&release=latest_approved&method=current&geo_type=province&metric=coverage`
- `GET /api/indicators/:uuid/cube?group_by=taxonomy_family&geo_type=national&start_year=2018&end_year=2024&limit=15`
- `GET /api/indicators/:uuid/dimensions`
- `GET /api/indicators/:uuid/visual-profile`
- `GET /api/indicators/:uuid/audit`

### Indicator pack response shape
- `GET /api/indicators/:uuid/visual-profile` now includes:
  - `packId`
  - `packLabel`
  - `availableViews`
  - `defaultView`
  - `mapLayers[{ layerCode, title, joinKey, dimensionId, availableMetrics, defaultMetric }]`
  - `legends[{ id, title, dimensionId, items[{ value, label, colorToken }] }]`
  - `matrixDefinitions[{ id, label, xDimension, yDimension }]`
  - `narrativeTemplates[{ id, title, body }]`
- `GET /api/indicators/:uuid/dimensions` now returns pack-authored dimensions even when the current point slice does not expose every field observed in the pack.

### Governed narratives
- `GET /api/narratives/framework/GBF`
- `POST /api/narratives/target/GBF%3A1/draft`
- `POST /api/narratives/indicator/:uuid/submit`
- `GET /api/narratives/dashboard/home/versions`

## How To Navigate

### Routes
- `/dashboard`
- `/frameworks`
- `/frameworks/:frameworkId`
- `/frameworks/:frameworkId/targets/:targetId`
- `/indicators`
- `/indicators/:uuid`
- `/reports` redirects to `/reporting`

### Key query params
- `tab`
- `mode`
- `report_cycle`
- `release`
- `method`
- `geo_type`
- `geo_code`
- `start_year`
- `end_year`
- `agg`
- `metric`
- `published_only`
- `q`
- `sort`
- `view`
- `compare`
- `left`
- `right`

### Indicator view params
- `tab=indicator`
- `view=timeseries|distribution|taxonomy|matrix|binary`
- `agg=province|biome|ecoregion|municipality|year`
- `dim=<dimensionId>`
- `dim_value=<dimensionValue>`
- `tax_level=<levelId>`
- `tax_code=<path or keyed path>`
- `top_n=20|50|100`

## Example URLs

### Indicator view switching
- `/indicators/<ecosystem-threat-uuid>?tab=indicator`
  - pack default redirects to `view=distribution`
- `/indicators/<species-threat-uuid>?tab=indicator&view=taxonomy&tax_level=family`
- `/indicators/<ecosystem-protection-uuid>?tab=indicator&view=matrix&dim=protection_category&dim_value=WELL_PROTECTED&compare=threat_category&right=EN`

### Cube / profile endpoints
- `/api/indicators/2a8d3b64-b3d9-4152-9d42-2ac1960d9cc3/visual-profile`
- `/api/indicators/2a8d3b64-b3d9-4152-9d42-2ac1960d9cc3/dimensions`
- `/api/indicators/2a8d3b64-b3d9-4152-9d42-2ac1960d9cc3/cube?group_by=type&report_cycle=NR7-2024&release=latest_approved&method=current`
- Taxonomy cube shape is exercised in `src/nbms_app/tests/test_api_indicator_analytics_rich.py` using the deterministic `IND-RICH` fixture and the endpoint pattern `/api/indicators/<uuid>/cube?group_by=taxonomy_family,threat_category&tax_level=family&tax_code=Felidae`

### Pilot indicator route patterns
- Resolve runtime UUIDs from code:
  - `/api/indicators?page=1&page_size=250&q=NBA_`
- Open pilot detail surfaces:
  - `/indicators/<NBA_ECO_RLE_TERR-uuid>?tab=indicator`
  - `/indicators/<NBA_ECO_RLE_EPL_TERR_MATRIX-uuid>?tab=indicator`
  - `/indicators/<NBA_PLANT_SPI-uuid>?tab=indicator&view=taxonomy`
  - `/indicators/<NBA_TEPI_TERR-uuid>?tab=indicator&view=timeseries`
- Explorer shortcuts:
  - `/indicators?q=NBA_ECO_RLE_TERR`
  - `/indicators?q=NBA_ECO_RLE_EPL_TERR_MATRIX`
  - `/indicators?q=NBA_PLANT_SPI`
  - `/indicators?q=NBA_TEPI_TERR`

## Runtime Examples

### Current seed indicators in `nbms_dev`
- `NBMS-GBF-ECOSYSTEM-THREAT`
  - default `distribution`
  - also supports `matrix` for `threat_category x protection_category`
- `NBMS-GBF-ECOSYSTEM-PROTECTION`
  - default `distribution`
  - also supports `matrix`
- `NBMS-GBF-SPECIES-THREAT`
  - default `taxonomy`
  - runtime taxonomy drilldown is now discoverable without relying on test fixtures
- `NBMS-GBF-SPECIES-PROTECTION`
  - default `taxonomy`
- `NBMS-GBF-PA-COVERAGE`
  - `timeseries` + province map + target-progress distribution
- `NBMS-GBF-IAS-PRESSURE`
  - pathway distribution + province spatial slice
- Additional seeded pack examples:
  - `NBMS-GBF-ECOSYSTEM-EXTENT`
  - `NBMS-GBF-RESTORATION-PROGRESS`
  - `NBMS-GBF-SPECIES-HABITAT-INDEX`
  - `NBMS-GBF-GENETIC-DIVERSITY`

### Pilot indicators now seeded in Docker runtime
- `NBA_ECO_RLE_TERR`
  - source: `askowno/RLE_terr@ac4d80ba627ddf4211515406d87c5f673414c887`
  - pack: `ecosystem_rle`
  - default view: `distribution`
  - GBF mapping: `Target 2`
- `NBA_ECO_RLE_EPL_TERR_MATRIX`
  - source: `askowno/RLE_terr@ac4d80ba627ddf4211515406d87c5f673414c887`
  - pack: `ecosystem_rle_x_epl_matrix`
  - default view: `matrix`
  - GBF mapping: `Targets 2, 3`
- `NBA_ECO_EPL_TERR`
  - source: `askowno/EPL_terr@74a297490f79a010b2d39bd37158cdaf609ed45f`
  - pack: `ecosystem_epl`
  - default view: `distribution`
  - GBF mapping: `Target 3`
- `NBA_ECO_RLE_EST`
  - source: `askowno/RLE_est@69b6b43c4ff8d5feba2568a91b95bdfd593aa29f`
  - pack: `ecosystem_rle`
  - default view: `distribution`
  - GBF mapping: `Target 2`
- `NBA_ECO_RLE_EPL_EST_MATRIX`
  - source: `askowno/RLE_est@69b6b43c4ff8d5feba2568a91b95bdfd593aa29f`
  - pack: `ecosystem_rle_x_epl_matrix`
  - default view: `matrix`
  - GBF mapping: `Targets 2, 3`
- `NBA_TEPI_TERR`
  - source: `askowno/TEPI_terr@6e4ba030c8c899e247f57527141c249424467028`
  - pack: `tepi_timeseries`
  - default view: `timeseries`
  - GBF mapping: `Target 3`
- `NBA_PLANT_SPI`
  - source: `SANBI-NBA/plant-protection-level@7add8433ae9ea9e11e4d66fc2545e97e3ee0ada1`
  - pack: `plant_spi_taxonomy`
  - default view: `taxonomy`
  - GBF mapping: `Target 3`

## Pilot Ingest Manifest Summary

| Indicator code | Repo + pinned ref | Files ingested | Pack | GBF target mapping |
| --- | --- | --- | --- | --- |
| `NBA_ECO_RLE_TERR` | `askowno/RLE_terr@ac4d80ba627ddf4211515406d87c5f673414c887` | `outputs/results_A3.csv`, `outputs/results_A2b.csv`, `outputs/RLE_full_compiled_adjusted.csv`, `outputs/ter_results_for_integration.csv` | `ecosystem_rle` | `2` |
| `NBA_ECO_RLE_EPL_TERR_MATRIX` | `askowno/RLE_terr@ac4d80ba627ddf4211515406d87c5f673414c887` | `outputs/ter_results_for_integration.csv` | `ecosystem_rle_x_epl_matrix` | `2`, `3` |
| `NBA_ECO_EPL_TERR` | `askowno/EPL_terr@74a297490f79a010b2d39bd37158cdaf609ed45f` | `outputs/results_df_EPL_2018_invasives2.csv`, `outputs/results_df_EPL_2024_invasives2.csv`, `outputs/results_df_EPL_2018_biome_invasives2.csv`, `outputs/results_df_EPL_2024_biome_invasives2.csv`, `outputs/results_df_prp_pa_9024_biome.csv` | `ecosystem_epl` | `3` |
| `NBA_ECO_RLE_EST` | `askowno/RLE_est@69b6b43c4ff8d5feba2568a91b95bdfd593aa29f` | `outputs/est_results_type.csv`, `outputs/est_results_for_integration.csv`, `outputs/rle_est_metrics_per_type.csv`, `outputs/rle24_est_sum_count.csv`, `outputs/rle24_est_sum_ext.csv` | `ecosystem_rle` | `2` |
| `NBA_ECO_RLE_EPL_EST_MATRIX` | `askowno/RLE_est@69b6b43c4ff8d5feba2568a91b95bdfd593aa29f` | `outputs/est_results_for_integration.csv` | `ecosystem_rle_x_epl_matrix` | `2`, `3` |
| `NBA_TEPI_TERR` | `askowno/TEPI_terr@6e4ba030c8c899e247f57527141c249424467028` | `outputs/tepi_sum_biome.csv`, `outputs/results_df_prp_pa_9024_biome.csv`, `outputs/results_df_pa_9024_biome.csv` | `tepi_timeseries` | `3` |
| `NBA_PLANT_SPI` | `SANBI-NBA/plant-protection-level@7add8433ae9ea9e11e4d66fc2545e97e3ee0ada1` | `src/nbms_app/pilots/fixtures/SANBI-NBA/plant-protection-level/plant_spi_demo.csv` | `plant_spi_taxonomy` | `3` |

## Known Placeholders / TODOs

- Framework and target pages currently derive their analytics from existing dashboard and indicator APIs. Dedicated framework endpoints are still needed:
  - `GET /api/frameworks`
  - `GET /api/frameworks/:frameworkId`
  - `GET /api/frameworks/:frameworkId/targets/:targetId`
- Framework and target map tabs are placeholders until aggregate map endpoints exist:
  - `GET /api/frameworks/:frameworkId/map`
  - `GET /api/frameworks/:frameworkId/targets/:targetId/map`
- Pack configs also exist for pollution and climate-biodiversity pressure archetypes, but runtime seed data currently stops at the first 10 priority packs.
- Responsive Playwright coverage now validates desktop/tablet/mobile navigation and overflow behavior, but framework/target routes are feature-detected in e2e because the current served environment does not expose direct deep-link handling for every SPA route.
- Angular still emits a non-blocking style budget warning for `frontend/src/app/pages/indicator-detail-page.component.ts`.

## How To Test

```bash
docker compose --profile minimal up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py ensure_system_admin
docker compose exec backend python manage.py ingest_nba_pilot_outputs --manifest src/nbms_app/pilots/nba_pilot_v1.yml
docker compose exec backend python manage.py seed_indicator_workflow_v2
npm --prefix frontend run build
npm --prefix frontend run test -- --watch=false
COMPOSE_PROJECT_NAME=nbms_dev npm --prefix frontend run e2e
make test-backend
```

### Backend test modes
- Authoritative integration path:
  - `make test-backend`
  - equivalent: `docker compose -f compose.yml -f docker-compose.test.yml up -d --build postgis redis minio minio-init backend && docker compose -f compose.yml -f docker-compose.test.yml exec backend pytest -q`
- Explicit fallback only when Docker/PostGIS is unavailable:
  - `PYTHONPATH=src DATABASE_URL=sqlite:///test_nbms.sqlite3 ENABLE_GIS=false pytest -q src/nbms_app/tests/test_nba_pilot_ingest.py`

### Docker runbook
- `docker compose --profile minimal up -d --build`
- `docker compose exec backend python manage.py migrate`
- `docker compose exec backend python manage.py ensure_system_admin`
- `docker compose exec backend python manage.py ingest_nba_pilot_outputs --manifest src/nbms_app/pilots/nba_pilot_v1.yml`
- `docker compose exec backend python manage.py seed_indicator_workflow_v2`
- Open `http://localhost:8081`
