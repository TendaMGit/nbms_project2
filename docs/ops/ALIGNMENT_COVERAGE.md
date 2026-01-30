# Alignment Coverage

Purpose: provide a deterministic, ABAC- and consent-aware view of alignment coverage for a ReportingInstance.

## Coverage semantics

Scopes:
- selected (default)
  - National targets come from `scoped_national_targets(instance, user)`.
  - Indicators come from `approved_queryset(instance, Indicator)`.
- all
  - Uses all published NationalTarget/Indicator objects visible to the requesting user.

Notes:
- Totals reflect ABAC + consent filters for the requesting user.
- If a user cannot see an object, it is excluded from totals and lists.
- Sorting is deterministic: targets/indicators are ordered by (code, title, uuid).

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
