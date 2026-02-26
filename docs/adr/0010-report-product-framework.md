# ADR 0010: Report Product Framework for One Biodiversity Publishing
Date: 2026-02-07
Status: Accepted

## Context
NBMS must generate report products beyond NR7 (NBA, GMO, invasive) using the same governed data foundation, with deterministic previews and export outputs.

## Decision
- Add first-class report product models:
  - `ReportProductTemplate`
  - `ReportProductRun`
- Implement a report product service layer:
  - template seeding (`seed_default_report_products`)
  - deterministic payload builders
  - HTML/PDF rendering
  - run persistence for auditability
- Ship three v1 templates:
  - `nba_v1`
  - `gmo_v1`
  - `invasive_v1`
- Expose report product API surface:
  - `GET /api/report-products`
  - `GET /api/report-products/{code}/preview`
  - `GET /api/report-products/{code}/export.html`
  - `GET /api/report-products/{code}/export.pdf`
  - `GET /api/report-products/runs`

## Consequences
- Pros:
  - Report generation is modular and reusable.
  - Products can be generated with or without binding to a reporting instance.
  - Each run is tracked for governance and reproducibility.
- Tradeoffs:
  - v1 templates are shells with selected live tables/maps, not fully authored publications.
  - richer citation/layout management remains a follow-up increment.

## Implementation references
- `src/nbms_app/models.py`
- `src/nbms_app/services/report_products.py`
- `src/nbms_app/api_spa.py`
- `templates/nbms_app/reporting/report_product_preview.html`
