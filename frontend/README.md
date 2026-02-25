# NBMS Frontend

Angular frontend for NBMS national biodiversity registry/reporting workflows.

## Run

```bash
npm --prefix frontend install
npm --prefix frontend run start
```

App runs at `http://localhost:4200` and proxies API calls to backend routes configured for local development.

## Validate

```bash
npm --prefix frontend run build
npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless
npm --prefix frontend run e2e
```

## UI Architecture

- App shell: `src/app/ui/nbms-app-shell.component.ts`
  - Top bar: environment badge, global search, notifications/help entry points, profile menu.
  - Sidebar: role-aware navigation for dashboard, workspaces, reporting, registries, spatial, programmes, downloads, admin/system pages.
  - Global command palette: keyboard-first navigation (`Ctrl/Cmd + K`).
- UI primitives live under `src/app/ui/` and are reused by feature pages:
  - `nbms-page-header`, `nbms-kpi-card`, `nbms-data-table`, `nbms-filter-rail`,
    `nbms-status-pill`, `nbms-readiness-badge`, `nbms-empty-state`,
    `nbms-map-panel`, `nbms-evidence-panel`, `nbms-audit-timeline`.

## Theme System

- Design tokens: `src/styles/_tokens.scss`
- Theme application: `src/styles/_theme.scss`
- Global imports: `src/styles.scss`
- Preference service: `src/app/services/user-preferences.service.ts`

The current baseline includes tokenized color, typography, spacing, focus, elevation, and component surface variables with light/dark support. New theme packs should be added through tokens and mapped through theme root classes instead of per-component hardcoded colors.

Theme/runtime attributes are applied on the document root:

- `data-theme`: `light|dark`
- `data-theme-pack`: `fynbos|gbif_clean|high_contrast|dark_pro`
- `data-density`: `comfortable|compact`

## Routing

Root routes are defined in `src/app/app.routes.ts` with feature sections scaffolded for:

- dashboard
- work
- indicators
- reporting/template packs
- registries
- spatial
- programmes/integrations
- downloads
- admin/system health
- account preferences (`/account/preferences`)
- work queue (`/work`) backed by watchlist + pinned saved filters

When replacing placeholder pages, preserve route compatibility unless migration redirects are explicitly added.
