# Changelog

## Unreleased

Highlights:
- ORT NR7 v2 exporter now maps structured Section I/II/V models and enriched Section III/IV data, including Section IV goal progress and binary indicator group comments.
- Added export payload contract validation service (`src/nbms_app/services/export_contracts.py`) with tests and golden fixture refresh flow.
- Added centralized section field help dictionary and rendered field-level help/tooltips for Section I-V templates.
- Added route policy registry (`src/nbms_app/services/policy_registry.py`) and policy coverage tests (`src/nbms_app/tests/test_policy_registry.py`).
- Added split CI baseline workflow (`.github/workflows/ci.yml`) with Linux full tests, Windows smoke, and security checks.
- Hardened staff-only decorator behavior for non-regression (redirect contract preserved) and snapshot strict-user handling.
- Docker compose minio init image pin corrected to restore baseline startup.

## v0.3-manager-pack

Highlights:
- ValidationRuleSet seeding and reporting defaults helper commands
- Manager Report Pack preview with readiness score and appendices
- Readiness panels and instance readiness scoring
- Reporting cycles, instances, approvals, and consent gating
- Export packages with instance-scoped approvals

Breaking changes:
- None noted; run migrations and seed reporting defaults after upgrade.

Upgrade notes:
1) python manage.py migrate
2) python manage.py bootstrap_roles
3) python manage.py seed_reporting_defaults
