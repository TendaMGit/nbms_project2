# TESTING_AND_CI_PLAN

## Current Test Surface (as-built)
- Test modules: 80+ under `src/nbms_app/tests/`.
- Coverage themes present:
  - authorization/ABAC/object perms
  - consent and approvals
  - reporting sections and freeze behavior
  - readiness diagnostics and exports
  - snapshot/review workflows
  - catalog import/export commands
  - settings/metrics/smoke checks

## Local Test Status (this review pass)

### Targeted hardening suite
Command:
```powershell
$env:PYTHONPATH="$PWD\src"
pytest -q src/nbms_app/tests/test_metrics.py src/nbms_app/tests/test_reporting_approvals_ui.py src/nbms_app/tests/test_reporting_freeze.py src/nbms_app/tests/test_export_contracts.py src/nbms_app/tests/test_ort_nr7_v2_export.py src/nbms_app/tests/test_prod_settings.py src/nbms_app/tests/test_seed_binary_indicator_questions_command.py src/nbms_app/tests/test_indicator_data.py src/nbms_app/tests/test_sections_structured_models.py
```
Result: `39 passed`.

### Windows tmp-path compatibility coverage
Command:
```powershell
$env:PYTHONPATH="$PWD\src"
pytest -q src/nbms_app/tests/test_demo_seed.py::test_demo_verify_hash_deterministic src/nbms_app/tests/test_indicator_reporting_metadata.py::test_indicator_import_export_roundtrip src/nbms_app/tests/test_reference_catalog_import.py::test_reference_catalog_import_upsert_updates src/nbms_app/tests/test_reference_catalog_import.py::test_reference_catalog_import_invalid_vocab_rejected src/nbms_app/tests/test_reference_catalog_import.py::test_reference_catalog_import_requires_references src/nbms_app/tests/test_reference_catalog_import.py::test_reference_catalog_import_framework_happy_path src/nbms_app/tests/test_reference_catalog_import.py::test_reference_catalog_import_reports_row_errors src/nbms_app/tests/test_reference_catalog_import.py::test_reference_catalog_export_template_includes_example src/nbms_app/tests/test_reporting_readiness_diagnostics.py::test_csv_output_format
```
Result: `9 passed`.

Compatibility change:
- Added Windows/Python 3.13-safe `tmp_path` fixture override in `src/nbms_app/tests/conftest.py` to avoid pytest ACL failures while preserving test intent.

### Full suite
Command:
```powershell
$env:PYTHONPATH="$PWD\src"
pytest -q
```
Result: `308 passed`.

## Current CI State
- Workflows present:
  - `.github/workflows/migration-verify.yml`
  - `.github/workflows/ci.yml`
- `ci.yml` implemented jobs:
  - `quality-fast` (dependency consistency, syntax compile check, Django check, migrations check)
  - `tests-linux-full` (PostGIS-backed full `pytest -q`)
  - `tests-windows-smoke` (Windows smoke checks with settings and script/utility tests)
  - `security-baseline` (dependency audit, secret scan, deploy checks)
- Remaining gap:
  - No dedicated SAST/static-code-security analyzer job yet.

## Testing Gaps to Close
- Replace temporary Windows/Python 3.13 `tmp_path` compatibility shim with an upstream-supported pytest path once available.
- Route-policy matrix tests for all staff-only mutating/reporting routes.
- Deeper semantic export contract tests (not only payload shape).
- Longitudinal migration tests (upgrade from selected previous schema snapshots).

## Acceptance Criteria for "Tighten & Proceed" CI Baseline
- PRs must pass:
  - quality-fast
  - tests-linux-full
  - migration-verify (existing workflow)
  - security-baseline
- Windows smoke job must remain green for critical governance flows.
- Any temporary test-infra shims must be tracked with retirement criteria.

