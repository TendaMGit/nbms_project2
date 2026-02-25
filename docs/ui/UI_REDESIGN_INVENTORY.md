# NBMS UI Redesign Inventory

Date: 2026-02-25  
Branch: `chore/align-blueprint-2026Q1`  
Scope: current Angular UI inventory before redesign rollout

## Current route map

Source: `frontend/src/app/app.routes.ts`

- `/dashboard` -> `DashboardPageComponent`
- `/indicators` -> `IndicatorExplorerPageComponent`
- `/indicators/:uuid` -> `IndicatorDetailPageComponent`
- `/map` -> `MapViewerPageComponent`
- `/programmes` -> `ProgrammeOpsPageComponent`
- `/programmes/templates` -> `ProgrammeTemplatesPageComponent`
- `/programmes/birdie` -> `BirdieProgrammePageComponent`
- `/nr7-builder` -> `ReportingPageComponent`
- `/template-packs` -> `TemplatePacksPageComponent`
- `/registries/ecosystems` -> `EcosystemRegistryPageComponent`
- `/registries/taxa` -> `TaxonRegistryPageComponent`
- `/registries/ias` -> `IasRegistryPageComponent`
- `/system-health` -> `SystemHealthPageComponent`
- `/report-products` -> `ReportProductsPageComponent`

## Current app shell

Sources:
- `frontend/src/app/app.ts`
- `frontend/src/app/app.html`
- `frontend/src/app/app.scss`

Current shell is a single static sidenav + top toolbar layout with:
- fixed left nav list.
- page title from route data.
- auth identity + logout/login links.
- contextual help strip from `/api/help/sections`.

Gaps relative to redesign brief:
- no environment badge.
- no global search/typeahead.
- no command palette.
- no notifications center.
- no theme toggle (light/dark).
- no grouped navigation model (My Work, Downloads, Admin, Integrations).
- no mobile-first responsive behavior for navigation.

## Current page/component inventory

### Pages (`frontend/src/app/pages`)

- `dashboard-page.component.ts`
- `indicator-explorer-page.component.ts`
- `indicator-detail-page.component.ts`
- `reporting-page.component.ts`
- `template-packs-page.component.ts`
- `ecosystem-registry-page.component.ts`
- `taxon-registry-page.component.ts`
- `ias-registry-page.component.ts`
- `map-viewer-page.component.ts`
- `programme-ops-page.component.ts`
- `programme-templates-page.component.ts`
- `birdie-programme-page.component.ts`
- `system-health-page.component.ts`
- `report-products-page.component.ts`

### Shared components (`frontend/src/app/components`)

- `help-tooltip.component.ts`
- `plotly-chart.component.ts`
- `indicator-map-panel.component.ts`

### Services (`frontend/src/app/services`)

- `api-client.service.ts`
- `auth.service.ts`
- `dashboard.service.ts`
- `indicator.service.ts`
- `national-report.service.ts`
- `template-pack.service.ts`
- `registry.service.ts`
- `spatial.service.ts`
- `programme-ops.service.ts`
- `birdie.service.ts`
- `system-health.service.ts`
- `report-product.service.ts`
- `nr7-builder.service.ts`
- `help.service.ts`

## What will be replaced or refactored

## Shell and design system

- Replace root shell with reusable `NbmsAppShell`.
- Add global tokenized theme architecture:
  - `frontend/src/styles/_tokens.scss`
  - `frontend/src/styles/_theme.scss`
- Move from page-specific shell styling to shared UI primitives:
  - `NbmsPageHeader`
  - `NbmsKpiCard`
  - `NbmsStatusPill`
  - `NbmsReadinessBadge`
  - `NbmsEmptyState`
  - `NbmsSearchBar`
  - `NbmsHelpDrawer`
  - `NbmsCommandPalette`

## Routes and information architecture

Planned route set adds/normalizes:
- `/work`
- `/reporting`
- `/reports/:uuid`
- `/template-packs` and `/template-packs/:pack_code`
- `/registries`
- `/spatial/map`
- `/spatial/layers`
- `/integrations`
- `/downloads`
- `/admin`
- `/system/health` (canonical), with compatibility redirect from `/system-health`

Legacy routes kept as compatibility redirects where needed (for existing e2e/tests).

## Planned replacement mapping

- `DashboardPageComponent` -> redesigned KPI + queue dashboard with readiness focus.
- `IndicatorExplorerPageComponent` -> redesigned data table + saved filters + watchlist.
- `IndicatorDetailPageComponent` -> tabbed detail with status/readiness/checklist/download record UX.
- `ReportingPageComponent` -> report workspace route `/reports/:uuid`.
- `TemplatePacksPageComponent` -> template pack library/detail split.
- registry explorers/details -> unified explorer/detail pattern per object.
- `MapViewerPageComponent` + layer listing -> spatial map + layers registry split.
- programme/integration pages -> perspective dashboards + run controls.

## Known API/UI gaps to track

Will capture in `docs/UI_BACKLOG.md` during later phases if missing endpoints block UX flows (instead of inventing backend contracts).
