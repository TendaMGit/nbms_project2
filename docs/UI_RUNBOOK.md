# UI Runbook

Date: 2026-02-25

## Demo prerequisites

1. Backend running (`http://127.0.0.1:8000`)
2. Frontend running (`http://127.0.0.1:8081` or `:4200`)
3. Seed users and demo content:

```bash
python manage.py seed_demo_users
python manage.py seed_indicator_workflow_v1
python manage.py seed_demo_reports
```

## Core walkthrough

### 1) Indicator Explorer V2

Route: `/indicators`

What to show:
- Filter rail (framework, GBF goal/target, geography type/code, readiness, due-soon, spatial)
- Mode toggle: Table, Cards, Map-first
- Responsive narrative panel driven by API summary payload
- Saved view flow (`Save view`) and restore via `Saved views` selector
- Watch indicator toggle and compare selection

### 2) Watchlist + My Work

Routes:
- `/indicators` (watch toggle)
- `/work` (watchlist and pinned views)

Verification:
- Star at least one indicator
- Open `/work`
- Confirm watched item and pinned view visibility

### 3) Download landing records + citations

Routes:
- `/downloads`
- `/downloads/{uuid}`

Flow:
- Trigger any export action (indicator/report/spatial/template/programme)
- Confirm landing page shows citation + provenance snapshot + file action

### 4) System health and observability

Route: `/system/health`

What to show:
- service checks (DB/storage/cache)
- observability state (metrics/logs/tracing/sentry)
- download backlog / export failures
- copy debug bundle action

## Smoke test commands

```bash
npm --prefix frontend run build
npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless
npm --prefix frontend run e2e
```

## Notes

- UI language reflects periodic release publishing; no near-real-time computation claims.
- Governance copy remains aligned: methods approval (ITSC) and conditional steward review only.
