# NBMS Alignment Graph (Current + Gaps)

This document verifies the NBMS domain model against the desired alignment chain
and proposes minimal, additive link tables where gaps exist. No schema changes
are implemented in this phase.

## Target alignment chain (required)

National Monitoring Programme
-> National Dataset Release
-> National Indicator
-> National Target
-> Framework / MEA Target
-> Global Indicator
-> Global Target

Note: National Target to global/MEA targets must be many-to-many.

## Current NBMS domain objects (models.py)

Primary objects:
- ReportingCycle, ReportingInstance
- NationalTarget
- Indicator (FK to NationalTarget)
- Dataset
- DatasetRelease (FK to Dataset)
- Evidence

Existing link tables:
- IndicatorEvidenceLink (Indicator <-> Evidence)
- IndicatorDatasetLink (Indicator <-> Dataset)

## What is supported today

Supported segments:
- National Indicator -> National Target (Indicator.national_target FK)
- National Dataset Release -> National Dataset (DatasetRelease.dataset FK)
- National Dataset -> National Indicator (IndicatorDatasetLink)

Partial chain currently possible (with inference):
- DatasetRelease -> Dataset -> Indicator -> NationalTarget
  (no explicit release-to-indicator link, but can infer via dataset)

## Gaps vs. required chain

Missing objects / links:
- National Monitoring Programme (no model)
- Programme -> DatasetRelease / Programme -> Indicator links (no link tables)
- Framework / MEA Target registry (no model)
- Global Indicator registry (no model)
- Global Target registry (no model)
- National Target -> Framework/MEA Target mapping (no link table)
- Indicator -> Global Indicator mapping (no link table)
- Global Indicator -> Global Target mapping (no link table)

## Minimal additive schema proposal (not implemented)

The smallest forward-safe approach uses lightweight alignment/link tables with
external identifiers (no full framework registry). This supports many-to-many
mapping between national and global layers without porting pilot schemas.

### 1) NationalTarget <-> Framework/MEA Target mapping (many-to-many)

Proposed model: NationalTargetAlignment
- national_target (FK)
- framework (choice: GBF, SDG, CBD, OTHER)
- global_target_code (string, required)
- global_goal_code (string, optional)
- degree_of_alignment_code (string, optional)
- notes (text, optional)
- unique constraint on (national_target, framework, global_target_code)

Rationale:
- Supports many-to-many links (e.g., National Target -> GBF Target 2 and SDG 15).
- Avoids a full global target registry.

### 2) Indicator <-> Global Indicator mapping (many-to-many)

Proposed model: IndicatorAlignment
- indicator (FK)
- framework (choice: GBF, SDG, CBD, OTHER)
- global_indicator_code (string, required)
- indicator_type (choice: headline, binary, component, complementary, other)
- notes (text, optional)
- unique constraint on (indicator, framework, global_indicator_code)

Rationale:
- Matches ORT indicator categories without maintaining large taxonomies.

### 3) Global Indicator -> Global Target link (optional, if needed)

If a direct global indicator-to-target map is required for reporting:

Proposed model: FrameworkIndicatorTargetLink
- framework (choice)
- global_indicator_code (string)
- global_target_code (string)
- unique constraint on (framework, global_indicator_code, global_target_code)

Rationale:
- Allows a global indicator to map to multiple targets without a registry.

### 4) Monitoring Programme linkage

If monitoring programmes are required as first-class objects:

Proposed model: MonitoringProgramme
- uuid, title, description
- organisation, created_by
- status, sensitivity, review_note (reuse existing patterns)

Proposed link tables:
- MonitoringProgrammeDatasetReleaseLink (programme FK, dataset_release FK)
- MonitoringProgrammeIndicatorLink (programme FK, indicator FK)

Rationale:
- Keeps the chain explicit without overhauling existing dataset/indicator models.
- Link tables are additive and forward-safe.

## Text diagram (current vs. proposed)

Current:

DatasetRelease -> Dataset -> Indicator -> NationalTarget
Indicator -> Evidence

Proposed (minimal, additive):

MonitoringProgramme
  -> MonitoringProgrammeDatasetReleaseLink -> DatasetRelease
  -> MonitoringProgrammeIndicatorLink -> Indicator

Indicator -> IndicatorAlignment -> GlobalIndicatorCode
NationalTarget -> NationalTargetAlignment -> GlobalTargetCode
GlobalIndicatorCode -> FrameworkIndicatorTargetLink -> GlobalTargetCode

## Notes

- The proposed alignment tables are intentionally minimal and use external codes
  rather than embedding full CBD/GBF/SDG registries.
- All mappings are many-to-many and do not force a linear 1:1 chain.
- No ABAC/consent/export gating changes are implied by these proposals.
