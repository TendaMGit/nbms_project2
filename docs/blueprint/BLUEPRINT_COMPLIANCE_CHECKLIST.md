# Blueprint Compliance Checklist

## Binding Non-Negotiables

- NBMS is a governed registry/publication platform, not an internal indicator computation engine.
- Contributors own and run indicator calculation pipelines outside NBMS; NBMS receives approved releases.
- Governance is minimal:
  - ITSC approves method versions only.
  - Data Steward review is conditional, triggered by sensitivity/licence/embargo/IPLC-type flags.
  - No Data Governance Council (DGC) process in production workflows.
- Delivery framing is a single phase:
  - `Phase 1 - National MVP (Reporting + Interoperability + Scale Path)`.
  - Any future items are backlog items, not separate phase commitments.
- Publication is periodic release-based; avoid real-time/near-real-time system claims.

## Scope Boundaries

### In Scope (MVP)

- Search and discovery across indicators, targets, goals, and datasets.
- Role-aware dashboards and indicator detail pages with status metadata.
- Dataset and indicator release registration, validation, versioning, and publication.
- Conditional sensitive-data workflow with steward approval path.
- Method submission/versioning and ITSC approval workflow.
- Downloads/exports (CSV, GeoJSON, API outputs) and reporting packs (NR7/NR8 + additional MEA templates).
- Basic partner integration contracts for scheduled ingestion.
- Audit trail and operational hardening (security, backup, monitoring baseline).

### Out of Scope (MVP)

- On-demand indicator recalculation inside NBMS.
- Near-real-time ingestion/streaming as a baseline capability.
- Heavy AI/ML analytical automation inside publication workflows.
- Broad “all-MEA/all-indicator” completeness beyond priority reporting scope.

## Functional Requirements Summary (FR-001 to FR-017)

### FR-001 to FR-005 (Discovery, dashboards, views)

- `FR-001`: Search indicators/targets/datasets by keyword and filters.
  - Acceptance intent: user search (for example "forest") returns relevant indicator cards/details.
- `FR-002`: Browse dataset and target catalog metadata.
  - Acceptance intent: users can list datasets by target and open source/date/sensitivity metadata.
- `FR-003`: Home dashboard summary (counts, freshness/status snapshots).
  - Acceptance intent: logged-in user sees indicator counts and readiness/freshness summary.
- `FR-004`: Indicator detail page with metadata, trends, map context, and downloads.
  - Acceptance intent: detail view exposes values-over-time, status fields, and export actions.
- `FR-005`: Goal/target pages aggregating linked indicator status.
  - Acceptance intent: target pages show indicator list with current status and key values.

### FR-006 to FR-008 (Reporting + exports + API)

- `FR-006`: Reporting-template integration (auto-populate report drafts from approved releases).
  - Acceptance intent: user can create report draft and obtain generated artifact (PDF/table pack).
- `FR-007`: Multi-template MEA packs (NR7/NR8 plus additional template sets).
  - Acceptance intent: administrators can enable/select template packs when generating reports.
- `FR-008`: Download and API access for non-sensitive data.
  - Acceptance intent: CSV/GeoJSON/API output is available for authorized users; restricted data is gated.

### FR-009 to FR-014 (Ingestion, governance, publication)

- `FR-009`: Register ingested datasets with metadata and uploaded files.
  - Acceptance intent: newly registered dataset appears with lifecycle state.
- `FR-010`: Validate ingested dataset payloads and publish immutable releases.
  - Acceptance intent: invalid uploads fail with clear errors; valid releases version and lock.
- `FR-011`: Sensitive data handling with steward queue.
  - Acceptance intent: flagged releases route to steward review; non-flagged releases fast-path publish.
- `FR-012`: Method submission/versioning for ITSC review.
  - Acceptance intent: method version enters ITSC queue and records approval decision metadata.
- `FR-013`: Indicator release submission linked to approved method + source releases.
  - Acceptance intent: contributor submits release package with lineage and interpretation fields.
- `FR-014`: Indicator release validation and publication.
  - Acceptance intent: valid release is published and visible; invalid payload gets actionable errors.

### FR-015 to FR-017 (Readiness + integration + audit)

- `FR-015`: Indicator readiness and update-status tracking.
  - Acceptance intent: indicator shows last update, next expected update, maturity/readiness indicators.
- `FR-016`: Partner integration contract support for scheduled data exchange.
  - Acceptance intent: configurable connector can pull/validate and produce release artifacts.
- `FR-017`: Audit logging for key workflow actions.
  - Acceptance intent: reviewers/admins can inspect publish/approval/auth actions with timestamps/users.

## NFR Summary (Paraphrased)

- `Performance`: common dashboard/API actions remain responsive under expected indicator volume.
- `Scalability`: horizontal growth path exists (web/API scaling and database growth strategy).
- `Availability`: monitored uptime baseline and controlled maintenance approach.
- `Backup/Recovery`: daily backup baseline and restore drill process.
- `Security`: robust authn/authz, HTTPS, least-privilege role controls, secure defaults.
- `Audit/Compliance`: long-lived audit trail and governance evidence.
- `UX/A11y`: responsive and accessible interfaces with clear user workflows.
- `Observability`: logs, error monitoring hooks, and operational alerting.
- `Standards`: open formats/APIs (CSV/JSON/GeoJSON and OGC-compatible spatial outputs where used).
- `Maintainability`: modular architecture with environment-specific configuration and containerized runtime.
- `Documentation/Testability`: current runbooks and automated tests for critical paths.
- `Data Integrity`: enforce referential/transactional consistency (e.g., no publish without required method lineage).
- `Concurrency`: practical handling of contributor/admin and reader workloads.
- `Efficiency`: operationally efficient defaults and resource-conscious processing.

## Language Rules for Repository Docs

- Do not claim NBMS performs automatic indicator recomputation.
- Avoid `real-time`, `near-real-time`, or `live recompute` claims for MVP behavior.
- Frame updates as periodic approved releases supplied by contributors.
- State governance as ITSC (methods-only) + conditional Data Steward review; do not reference DGC.
- Frame roadmap as one delivery phase (`Phase 1 - National MVP`) with backlog tiers (`P1/P2`) inside that phase.
