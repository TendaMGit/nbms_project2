# Pilot Extraction Acceptance Checklist

This checklist defines preconditions, validation gates, and rollback procedures for the pilot extraction.

## Preconditions (before any import)
- Snapshot target database:
  - `pg_dump -Fc -f nbms_project2_pre_import.dump <database_name>`
- Confirm target environment:
  - `ENABLE_GIS=false` and local Postgres is reachable.
  - Required roles exist (`python manage.py bootstrap_roles`).
- Confirm deterministic identifiers strategy in use (UUIDv5 namespace and ID ledger path).
- Confirm consent/sensitivity mapping rules are loaded and reviewed.

## Validation gates by dataset group

### 1) Framework registry (Framework, Goal, Target, Indicator)
- Row counts match expected totals from source.
- Uniqueness:
  - Framework `code` unique.
  - FrameworkGoal unique per framework+goal_code.
  - FrameworkTarget unique per framework+code.
  - FrameworkIndicator unique per framework+code.
- Required fields present: code/title for each entity.
- Spot-check GBF/SDG codes for correct normalization.

### 2) National targets
- All rows have a non-empty code and title.
- If code was generated, an entry exists in `migration_id_map.csv`.
- Sensitivity set (PUBLIC/INTERNAL/RESTRICTED/IPLC_SENSITIVE), never null.
- `requires_consent=true` for IPLC-sensitive rows.

### 3) Indicators
- Indicator codes unique and non-empty.
- All indicators have a valid `national_target` (resolved by rule).
- Sensitivity set and consent flags applied where available.
- Indicator type is mapped to NBMS2 enum.

### 4) Alignment mappings
- NationalTargetFrameworkTargetLink:
  - No duplicates (unique pair enforced).
  - Links only to existing targets and framework targets.
- IndicatorFrameworkIndicatorLink:
  - No duplicates.
  - Links only to existing indicators and framework indicators.
- Sample validation: at least 10 known links match expectations.

### 5) Catalog entities (MonitoringProgramme, DatasetCatalog, DatasetRelease, Methodology, MethodologyVersion, Evidence)
- Dataset releases match dataset codes and versions.
- Data agreements and sensitivity classes resolved where present.
- Evidence has valid type and sensitivity.
- MethodologyVersion rows reference existing Methodology.

### 6) Indicator data (IndicatorDataSeries/Point)
- Every data point has a valid series.
- Year is integer and within expected ranges.
- Values are consistent (numeric vs binary vs text).
- Dataset releases referenced by points exist.

## Consent/IPLC validation checks
- No IPLC-sensitive rows with `requires_consent=false`.
- No restricted rows marked PUBLIC by default.
- If governance metadata is missing, imported rows default to INTERNAL.

## Sample validation output format

```
[PASS] Frameworks: 5 rows, 0 duplicates
[PASS] FrameworkTargets: 123 rows, 0 duplicates
[FAIL] Indicators: 2 rows missing national_target (see row 18, 42)
[PASS] Alignment links: 210 rows, 0 duplicates
[WARN] 14 indicators mapped to multiple national targets (see mapping ledger)
```

## Rollback plan

1) Pre-import backup (required):
```
pg_dump -Fc -f nbms_project2_pre_import.dump nbms_project2_db
```

2) If import fails:
```
# Stop app server
# Drop and recreate database, then restore
psql -d postgres -c "DROP DATABASE nbms_project2_db;"
psql -d postgres -c "CREATE DATABASE nbms_project2_db OWNER nbms_user;"
pg_restore -d nbms_project2_db nbms_project2_pre_import.dump
```

3) If partial import occurred:
- Use the import log and `migration_id_map.csv` to identify created UUIDs.
- Remove affected rows via targeted delete scripts (future Phase 3.1 task).

## Cutover plan (pilot-ready)
- Extraction is considered "done enough" when:
  - All in-scope datasets pass validation gates.
  - Consent and sensitivity rules pass spot checks.
  - Mappings and indicator data support at least one end-to-end demo instance.
- At this point, proceed to Phase 4 demo seed plan (no further legacy imports).

