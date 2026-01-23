# Reference Catalog Inventory Pack (PR-1)

This directory contains the **Pilot Registry Inventory Pack** for the legacy
`nbms_project` prototype. It is a requirements and metadata source intended to
inform future registry rebuilds in `nbms_project2`.

**Important:** PR-1 is **docs/templates only**. No schema, migrations, endpoints,
or runtime behavior changes are included here.

## Who this is for

- Product owners and registry stewards defining reference data needs.
- Developers implementing the follow-on registry PRs.
- Data administrators preparing CSV imports.

## How to use this pack

1. Review `pilot_registry_inventory_pack.md` to see what existed in the pilot
   and where it appeared (models, admin, API, seed scripts, fixtures).
2. Use `target_model_plan.md` as the concrete implementation guide for the
   **future** registry PRs.
3. Use `controlled_vocabularies.md` and the CSV templates in `csv_templates/`
   to prepare seed data in a consistent, governance-safe format.

## What is *not* included

- No migrations or model changes.
- No endpoints or UI updates.
- No data import jobs.

These are intentionally deferred to later PRs.
