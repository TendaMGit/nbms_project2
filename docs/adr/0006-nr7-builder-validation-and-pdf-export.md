# ADR 0006: NR7 Builder API, QA Engine, and PDF Export

- Status: Accepted
- Date: 2026-02-06

## Context

The Angular reporting area needed to move beyond a launcher page into an authoring-oriented NR7 workflow with:

- section-level completion visibility,
- QA findings before release,
- live preview data,
- deterministic PDF export output.

The codebase already had structured Section I-V storage and ORT NR7 v2 exporter logic.

## Decision

1. Add dedicated NR7 builder API endpoints under `/api/reporting/instances/*`.
- `GET /api/reporting/instances`
- `GET /api/reporting/instances/{uuid}/nr7/summary`
- `GET /api/reporting/instances/{uuid}/nr7/export.pdf`

2. Implement an NR7 validation service (`services/nr7_builder.py`) that composes:
- readiness diagnostics (`get_instance_readiness`),
- explicit required field checks for Section I/II/V,
- cross-section gap checks for Section III/IV/V evidence usage.

3. Reuse ORT NR7 exporter payload as preview source.
- If export preconditions fail, return preview error instead of breaking the builder shell.

4. Implement server-side PDF generation through `xhtml2pdf`.
- Keep deterministic ordering by relying on existing exporter/readiness ordering.
- Keep payload snapshot and QA list embedded in the PDF for audit/review traceability.

5. Keep Django section editors as editing fallback while Angular expands capture coverage.

## Consequences

Positive:
- Users get an integrated QA + preview workflow in the Angular app.
- Structured QA checks are reusable for readiness and pre-export checks.
- PDF output is available directly from API in Docker runtime.

Tradeoffs:
- PDF dependency chain increases backend image requirements (`libcairo2-dev`, `pkg-config`).
- Current Angular builder uses linked Django editors for field capture; native Angular forms remain a subsequent increment.

## Implementation references

- `src/nbms_app/api_urls.py`
- `src/nbms_app/api_spa.py`
- `src/nbms_app/services/nr7_builder.py`
- `templates/nbms_app/reporting/nr7_report_pdf.html`
- `frontend/src/app/pages/reporting-page.component.ts`
- `frontend/src/app/services/nr7-builder.service.ts`
- `docker/backend/Dockerfile`
