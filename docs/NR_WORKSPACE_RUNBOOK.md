# National Report Workspace Runbook

## Purpose
Operate unified CBD national report authoring for NR7 and NR8 using the same template pack (`cbd_national_report_v1`).

## Seed Defaults
```powershell
python manage.py seed_mea_template_packs
python manage.py seed_demo_reports
```

NR7/NR8 parity rule:
- Both report cycles use the same section schema and workflow behavior.
- Differences are instance metadata only (`cycle`, title, due windows).

## Workspace API
- `GET /api/reports/{uuid}/workspace`
- `GET|POST /api/reports/{uuid}/sections/{section_code}`
- `POST /api/reports/{uuid}/sections/section-iii/generate-skeleton`
- `POST /api/reports/{uuid}/sections/section-iv/recompute-rollup`
- `GET /api/reports/{uuid}/sections/{section_code}/history`
- `GET|POST /api/reports/{uuid}/sections/{section_code}/comments`
- `POST /api/reports/{uuid}/sections/{section_code}/comments/{thread_uuid}/status`
- `GET|POST /api/reports/{uuid}/sections/{section_code}/suggestions`
- `POST /api/reports/{uuid}/sections/{section_code}/suggestions/{suggestion_uuid}/decision`

## Multi-Author Features
- Versioned section revisions with hash chain
- Comment threads at JSON-path level
- Suggestion mode and accept/reject decisions
- Optimistic version control via `base_version`

## Exports
- `GET /api/reports/{uuid}/export.pdf`
- `GET /api/reports/{uuid}/export.docx`
- `GET /api/reports/{uuid}/export` (JSON)

## Public/Internal Visibility
- Set `ReportingInstance.is_public`
- Internal reports are ABAC-protected
- Public reports expose read-only payload via:
  - `GET /api/reports/{uuid}/public`
