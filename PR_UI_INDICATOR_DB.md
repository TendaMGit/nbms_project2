# UI Indicator Database PR Notes

## What Changed

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
  - `tab=indicator|details|evidence|audit`
  - context filters for cycle, method, release, geography, and year range
  - KPI strip, charts, distribution cards, detailed table, and narrative rail
- Kept `/indicators` and `/indicators/:uuid` route compatibility intact.
- Modularized the explorer toolbar, insights rail, and compare panel into separate components.
- Added canonical `geo_type` / `geo_code` compatibility in the explorer while preserving legacy `geography_type` / `geography_code`.

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

## Known Placeholders / TODOs

- Framework and target pages currently derive their analytics from existing dashboard and indicator APIs. Dedicated framework endpoints are still needed:
  - `GET /api/frameworks`
  - `GET /api/frameworks/:frameworkId`
  - `GET /api/frameworks/:frameworkId/targets/:targetId`
- Framework and target map tabs are placeholders until aggregate map endpoints exist:
  - `GET /api/frameworks/:frameworkId/map`
  - `GET /api/frameworks/:frameworkId/targets/:targetId/map`
- Indicator analytics still need backend filter support on:
  - `GET /api/indicators/:uuid/series` for `report_cycle`, `method`, `release` and `agg=biome`
  - `GET /api/indicators/:uuid/map` for `report_cycle`, `method`, and `release`
- The indicator audit tab currently reflects published workflow/provenance fields only. A dedicated audit endpoint is still needed for a full event timeline.
- Angular still emits a non-blocking style budget warning for `frontend/src/app/pages/indicator-detail-page.component.ts`.

## How To Test

```bash
npm --prefix frontend run build
npm --prefix frontend run test -- --watch=false
npm --prefix frontend run e2e
```

