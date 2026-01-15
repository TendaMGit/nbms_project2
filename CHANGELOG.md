# Changelog

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
