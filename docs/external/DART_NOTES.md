# DaRT Interoperability Notes

## Sources
- Intended source URL: https://www.informea.org/en/dart
  - Saved response: `informea_dart.html`
- Supplementary URLs (currently returning site-level 404 content in this environment):
  - `unep_wcmc_dart_tool_news.html`
  - `unep_wcmc_dart_cbd_approval_news.html`

## Key Direction Used for NBMS

Even where source pages were not fully retrievable, the integration direction remains:
- Multi-MEA workflow reuse over one-off report silos.
- “Enter once, reuse many times” for shared narratives/indicators.
- Modular template packs and export handlers.

## NBMS Features Aligned
- Multi-MEA template runtime:
  - `ReportTemplatePack`, `ReportTemplatePackSection`, `ReportTemplatePackResponse`
  - `src/nbms_app/services/template_pack_registry.py`
- Reusable reporting artifacts:
  - reporting snapshots and scoped export services
- Programme/indicator operationalization for repeatable runs:
  - `MonitoringProgrammeRun` and `IndicatorMethodRun`

## Follow-up
- Re-validate DaRT official page references and capture a non-404 canonical document when accessible.
