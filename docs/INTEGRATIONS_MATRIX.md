# INTEGRATIONS_MATRIX

This matrix reflects integration points represented in the current codebase. `_2bi` means planned or implied but not implemented as an operational integration.

| Integration Point | implemented | _2bi (to be implemented) |
|---|---|---|
| CBD ORT NR7 narrative export | `GET /exports/instances/<uuid>/ort-nr7-narrative.json` via `src/nbms_app/exports/ort_nr7_narrative.py` | Field-level conformance mapping for full ORT schema parity across all sections |
| CBD ORT NR7 v2 structured export | `GET /exports/instances/<uuid>/ort-nr7-v2.json` via `src/nbms_app/exports/ort_nr7_v2.py` | Direct submit/publish handshake adapter to ORT endpoint APIs |
| ORT binary indicator question bank | Seed command loads `src/nbms_app/data/ort_binary_indicator_questions.json` via `seed_binary_indicator_questions` | Automated version sync against authoritative ORT template releases |
| GBF framework registry | Framework/goal/target/indicator models (`Framework*`) and alignment links in `src/nbms_app/models.py` | Full multi-framework governance workflows (e.g., SDG/Ramsar/UNCCD cross-mapping UX) |
| GBF indicator data model alignment | `Indicator`, `IndicatorDataSeries`, `IndicatorDataPoint`, `SectionIII/IV` structured progress models, and ORT NR7 v2 exporter mappings in `src/nbms_app/exports/ort_nr7_v2.py` | Automated ingestion/computation pipelines per indicator methodology requirements and global submission adapters |
| Reference catalog CSV exchange | `reference_catalog_import` / `reference_catalog_export` commands | Managed API-based integration contracts with partner systems |
| Indicator data CSV exchange | `import_indicator_data` / `export_indicator_data` commands | Excel/native statistical package connectors and scheduled ingest jobs |
| Alignment mappings CSV exchange | `import_alignment_mappings` / `export_alignment_mappings` commands | Bi-directional sync with external alignment registries |
| Internal organisational integration model (SANBI/DFFE/etc.) | Generic `Organisation` model + FK relationships across registry/reporting models | Formal org-master sync (authoritative directory, external IAM/group sync) |
| SANBI-specific presence | Demo fixtures/constants: `src/nbms_app/demo_constants.py`, `docs/demo/DEMO_SEED_PLAN.md` | Production SANBI source-system adapter and managed reference-data sync |
| DFFE-specific presence | Mentioned in import template examples (`docs/reference_catalog/import_templates/*.md`) | Production DFFE integration interface (data/API/ETL contract) |
| Stats SA integration | Not represented in executable integration code | Dedicated Stats SA dataset ingest, metadata mapping, and QA pipeline |
| SAEON integration | Mentioned in dataset template examples (`dataset_catalog_import_template.md`) | Dedicated SAEON catalog/series synchronization and provenance validation |
| Ramsar/CITES/CMS framework packs | Not yet represented in executable template-pack code | Add modular framework/template packs and mapping tables while preserving CBD/GBF first-class behavior |
| API integration surface for partners | Read-only DRF endpoints in `src/nbms_app/api.py` (`/api/v1/*`) | Authenticated write APIs, idempotent upsert contracts, versioned partner schemas |
| DaRT-style enter-once/reuse-many workflow | Partial via snapshots/export packages (`ReportingSnapshot`, `ExportPackage`) and deterministic report pack/export builders | Reusable cross-cycle package manifests, mapping registry, replay automation, and remote workspace sync |

