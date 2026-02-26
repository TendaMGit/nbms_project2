# ADR 0015: DownloadRecord Citation Landing Pattern

## Status
Accepted

## Context
NBMS exports (report files, spatial GeoJSON, indicator/registry extracts) previously returned raw files directly. This made provenance and citation tracking inconsistent and reduced auditability for reuse in reports.

The Phase 1 MVP requires a persistent download landing record that captures:
- what was downloaded,
- a citation string,
- provenance snapshot (filters/time/geography),
- source references,
- and history for the requesting user.

NBMS remains a release registry and publishing platform, not an on-demand computation engine.

## Decision
Introduce a first-class `DownloadRecord` model and API:
- `POST /api/downloads/records`
- `GET /api/downloads/records`
- `GET /api/downloads/records/{uuid}`
- `GET /api/downloads/records/{uuid}/file`

Each record stores:
- record type and object reference,
- query/provenance snapshot,
- contributing sources metadata,
- citation text + citation id (non-DOI),
- file asset metadata and storage path,
- access level at creation,
- ready/failed status.

Existing report and spatial export endpoints now auto-create download records, so legacy direct export URLs remain compatible while still producing auditable landing artifacts.

## Consequences
Positive:
- Consistent citation and provenance UX across exports.
- Download history for users and stronger reproducibility.
- File access can be re-authorized at retrieval time; records remain visible even if file access is later revoked.

Trade-offs:
- Additional storage for export artifacts.
- Additional API/model complexity for export flow orchestration.
