# GLOBAL_READINESS

## DaRT and Multi-MEA Alignment

NBMS aligns to DaRT-style interoperability through:
- shared indicator registry across reporting packs,
- runtime template packs (`ReportTemplatePack*`) for convention-specific question structures,
- reusable export handlers (`template_pack_registry.py`) rather than hard-coded report logic,
- report products (`ReportProductTemplate` / `ReportProductRun`) that compile shared indicators/maps/narratives into different publication outputs.

Current convention coverage:
- CBD/ORT NR7: first-class structured implementation with contract-validated export.
- Ramsar: COP14-oriented runtime pack with QA + PDF/JSON export.
- CITES/CMS: scaffold packs active in runtime and ready for question-bank expansion.

## Indicator Method SDK Coverage

The indicator method SDK (`src/nbms_app/services/indicator_method_sdk.py`) supports method diversity via:
- explicit method profile metadata (`IndicatorMethodProfile`),
- deterministic input hashing and cache keys,
- audited run history (`IndicatorMethodRun`),
- readiness states for operational planning.

Supported method classes:
- `MANUAL`
- `CSV_IMPORT`
- `API_CONNECTOR`
- `SCRIPTED_PYTHON`
- `SCRIPTED_R_CONTAINER`
- `SPATIAL_OVERLAY`
- `SEEA_ACCOUNTING`
- `BINARY_QUESTIONNAIRE`

Implemented execution methods in this increment:
- binary questionnaire aggregation,
- CSV aggregation,
- spatial overlay aggregation,
- BIRDIE API connector method.

## One Biodiversity Operational Readiness

The current platform can:
- run national monitoring programme operations with auditable run history,
- ingest an external pipeline (BIRDIE) into bronze/silver/gold layers,
- seed and manage full GBF headline/binary catalog baseline,
- generate multiple report outputs (NR7 + Ramsar + NBA/GMO/Invasive shells) from shared data foundations.
