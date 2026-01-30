# Alignment Coverage

Purpose: provide a deterministic, ABAC- and consent-aware view of alignment coverage for a ReportingInstance.

## Coverage semantics

Scopes:
- selected (default)
  - If Section III/IV progress exists:
    - National targets come from Section III progress entries for the instance.
    - Indicators come from indicator data series linked to Section III/IV progress entries.
  - Else, if instance export approvals exist:
    - National targets come from `approved_queryset(instance, NationalTarget)`.
    - Indicators come from `approved_queryset(instance, Indicator)`.
  - Else:
    - Selected totals are **0** (no silent fallback to "all visible").
- all
  - Uses all published NationalTarget/Indicator objects visible to the requesting user.

Notes:
- Totals reflect ABAC + consent filters for the requesting user.
- If a user cannot see an object, it is excluded from totals and lists.
- A link only counts as "mapped" if the user can see **both** ends and consent requirements are satisfied.
- Sorting is deterministic and lexicographic by `(code, title, uuid)`.
  - Example ordering: `T1`, `T10`, `T2` (lexicographic, not natural).

## CLI usage

JSON (default):
```
python manage.py alignment_coverage --instance <uuid>
```

CSV (single stream to stdout):
```
python manage.py alignment_coverage --instance <uuid> --format csv
```

CSV to files:
```
python manage.py alignment_coverage --instance <uuid> --format csv --output-dir .\coverage_out
```

Optional flags:
- `--scope selected|all`
- `--framework GBF --framework SDG` (repeatable or comma-separated)
- `--no-details`
- `--user <username>` (evaluate ABAC/consent as another user)

## Output shape (JSON)

Key fields:
- `summary`: totals and percent mapped for national targets and indicators
- `by_framework`: link counts by framework
- `orphans`: unmapped national targets and indicators
- `coverage_details`: mapped/unmapped status with linked framework items

All lists are deterministically ordered to support stable downstream usage.

## Performance notes

- UI integrations should call `compute_alignment_coverage(..., include_details=False)` to avoid heavy detail payloads.
- The service relies on `select_related` and filtered link queries to avoid N+1 access patterns.

## UI integration

Alignment coverage is surfaced read-only in:
- Reporting instance review dashboard (`/reporting/instances/<uuid>/review/`)
- Reporting instance readiness page (`/reporting/instances/<uuid>/`)
- Full coverage page (`/reporting/instances/<uuid>/alignment-coverage/`)

Phase 2.2 bulk alignment pages (instance-scoped):
- Orphan NationalTargets: `/reporting/instances/<uuid>/alignment/orphans/national-targets/`
- Orphan Indicators: `/reporting/instances/<uuid>/alignment/orphans/indicators/`
- Mapping management: `/reporting/instances/<uuid>/alignment/mappings/`
