# INTEGRATIONS_MATRIX

This matrix tracks concrete integrations represented in code. `_2bi` means planned next-step capability, not yet operational.

| Integration Point | implemented | _2bi (to be implemented) |
|---|---|---|
| CBD ORT NR7 structured export | `GET /exports/instances/<uuid>/ort-nr7-v2.json` via `src/nbms_app/exports/ort_nr7_v2.py` + contract validation in `src/nbms_app/services/export_contracts.py` | Direct ORT submission adapter and submission-status sync |
| CBD ORT narrative export | `GET /exports/instances/<uuid>/ort-nr7-narrative.json` via `src/nbms_app/exports/ort_nr7_narrative.py` | Narrative-to-structured reconciliation tooling |
| Multi-MEA template runtime | `ReportTemplatePack*` models (`src/nbms_app/models.py`), pack seeding (`seed_mea_template_packs`), API runtime handlers in `src/nbms_app/api_spa.py` | Ramsar/CITES/CMS full export contracts beyond current stub payloads |
| GBF framework registry | `Framework`, `FrameworkGoal`, `FrameworkTarget`, `FrameworkIndicator` plus mapping tables in `src/nbms_app/models.py`; seeded GBF goal/target scaffold in `seed_indicator_workflow_v1` | Full GBF indicator method packs with computation runners per indicator fact sheet |
| SDG scaffold | SDG framework scaffold seeded in `seed_indicator_workflow_v1` | SDG-specific dashboard pack and reporting exports |
| Indicator workflow v1 pack | Four seeded indicators with methodologies, datasets, releases, series/datapoints, evidence, workflow state readiness in `seed_indicator_workflow_v1` | Additional GBF indicator packs and automated method execution |
| Monitoring programme integration | `MonitoringProgramme`, `ProgrammeIndicatorLink`, `ProgrammeDatasetLink` and seeded NBMS core programme relationships in `seed_indicator_workflow_v1` | Scheduled ingest pipelines from programme source systems |
| Indicator CSV exchange | `import_indicator_data` / `export_indicator_data` management commands | API-upload path and scheduled ingestion jobs |
| Dataset/reference catalog exchange | `reference_catalog_import` / `reference_catalog_export` commands | External API contracts with partner institutions |
| Spatial layer integration | `SpatialLayer` + `SpatialFeature` models, `seed_spatial_demo_layers`, GeoJSON APIs (`/api/spatial/*`) | PostGIS-native geometry tables and vector-tile publishing |
| Angular primary UI integration | Angular app in `/frontend`, served via nginx container (`docker/frontend/nginx.conf`), backend API integration via `/api/*` | Full replacement of remaining Django form-heavy reporting pages |
| SANBI organizational integration surface | SANBI org seeded in indicator workflow command and organization model usage across governance fields | Production SANBI system adapters and directory sync |
| DFFE organizational integration surface | DFFE org seeded in indicator workflow command and reporting ownership fields | Formal DFFE data exchange and review workflow integration |
| Stats SA integration | Not yet implemented in executable adapters | Stats SA dataset/profile adapters and QA mapping |
| SAEON integration | Not yet implemented in executable adapters | SAEON ingest connectors and provenance checks |
| DaRT-style enter-once/reuse-many | Reporting snapshots/export packages + reusable indicator metadata surfaces | Cross-cycle package manifests, workspace sync, and replay/export orchestration |
