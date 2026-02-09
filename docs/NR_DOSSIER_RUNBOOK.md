# National Report Dossier Runbook

## Endpoints
- `POST /api/reports/{uuid}/dossier`  
Generates latest dossier ZIP.
- `GET /api/reports/{uuid}/dossier/latest`  
Returns dossier metadata.
- `GET /api/reports/{uuid}/dossier/latest?download=1`  
Downloads dossier ZIP.

## Dossier Contents
1. `submission.json`
2. `report.pdf`
3. `report.docx`
4. `evidence_manifest.json`
5. `audit_log.json`
6. `integrity.json`
7. `visibility.json`

## Integrity Fields
- `report_content_hash`
- `revision_hash_chain`
- `export_hashes` (`pdf_hash`, `docx_hash`, `json_hash`)
- environment metadata (`git_commit`, `django_version`, `python_version`)
- data lineage summary

## Access Control
- Internal reports: dossier access requires authorized authenticated users.
- Public reports: dossier metadata/download available through public gating rules.

## Audit
- Dossier generation writes `AuditEvent` action: `report_dossier_generated`.
