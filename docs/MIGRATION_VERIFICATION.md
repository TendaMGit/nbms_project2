# Migration Verification (Attempted)

Environment used for verification attempts (Windows):
- `DJANGO_SETTINGS_MODULE=config.settings.base`
- `DJANGO_DB_ENGINE=django.db.backends.sqlite3`
- `NBMS_DB_NAME=.scratch_db.sqlite3`

## Commands + Results

1) `python manage.py makemigrations --check --dry-run`
- Result: FAILED during Django startup.
- Error: `OSError: [WinError 127] The specified procedure could not be found` while importing `django.contrib.gis` (GDAL binding).

2) `python manage.py migrate --plan`
- Result: NOT RUN (blocked by the same GDAL import error at startup).

3) `python manage.py migrate`
- Result: NOT RUN (blocked by the same GDAL import error at startup).

4) `python manage.py bootstrap_roles`
- Result: NOT RUN (blocked by the same GDAL import error at startup).

5) `python manage.py seed_reporting_defaults`
- Result: NOT RUN (blocked by the same GDAL import error at startup).

6) `python manage.py seed_report_templates`
- Result: NOT RUN (blocked by the same GDAL import error at startup).

7) `python manage.py seed_validation_rules`
- Result: NOT RUN (blocked by the same GDAL import error at startup).

8) `python manage.py seed_end_to_end_demo`
- Result: NOT RUN (blocked by the same GDAL import error at startup).

## Resolution Needed
The repo imports `django.contrib.gis` (admin) at startup, which requires GDAL libraries. Run the migration verification steps in an environment with:
- GDAL installed and on PATH
- PostGIS-enabled PostgreSQL (preferred) OR GIS-capable local setup

Once GDAL is available, rerun the commands above and update this file with actual outputs and backfill validation results.

## Backfill Checks (Pending)
- FrameworkGoal status migration from `is_active`.
- AuditEvent `event_type` backfill samples.
- Indicator to MethodologyVersion link backfill (only when exactly one active version).

These checks are pending until migrations can run successfully.
