# Reporting Snapshots (NR7 v2)

Snapshots provide immutable, governance-grade records of the v2 export payload
for a reporting instance. They support internal sign-off, review traceability,
and auditability.

## When snapshots are created

- Staff can create a snapshot explicitly from the instance snapshots page.
- If a freeze hook is added later, snapshot creation can be triggered on freeze.

Snapshots are only created using the v2 export builder to ensure export gating,
consent checks, and ABAC filters are honored.

## What is captured

- Full v2 export payload JSON
- SHA256 hash of the canonicalized JSON
- Exporter schema and version
- Readiness report JSON (release-mode catalog completeness + blockers)
- Readiness summary fields (overall_ready, blocking_gap_count)
- Created by and timestamp

Snapshots are immutable and never updated in place.

## Viewing and diffing

- Snapshot list: `/reporting/instances/<uuid>/snapshots/`
- Snapshot detail: `/reporting/instances/<uuid>/snapshots/<snapshot_uuid>/`
- Diff view: `/reporting/instances/<uuid>/snapshots/diff/`

The diff view highlights changes in:

- Narrative sections
- Section III progress entries
- Section IV progress entries
- Indicator series and datapoints
- Binary indicator responses
- Readiness status (overall ready + blocker counts)

## Governance

- Staff-only access with instance-scoped ABAC enforcement
- No export gating bypass
- Immutable records for audit trails
