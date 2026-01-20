# NBMS Alignment Graph (Current + Gaps)

This document verifies the NBMS domain model against the desired alignment chain
and captures the minimal, additive link tables added for multi-framework
alignment. It also notes remaining gaps.

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
Indicator data layer:
- IndicatorDataSeries (FK to Indicator or FrameworkIndicator)
- IndicatorDataPoint (FK to IndicatorDataSeries)
- BinaryIndicatorQuestion (FK to FrameworkIndicator)
- BinaryIndicatorResponse (FK to ReportingInstance + BinaryIndicatorQuestion)
Framework alignment objects:
- Framework
- FrameworkTarget
- FrameworkIndicator

Existing link tables:
- IndicatorEvidenceLink (Indicator <-> Evidence)
- IndicatorDatasetLink (Indicator <-> Dataset)
Alignment link tables (new):
- NationalTargetFrameworkTargetLink (NationalTarget <-> FrameworkTarget)
- IndicatorFrameworkIndicatorLink (Indicator <-> FrameworkIndicator)

## What is supported today

Supported segments:
- National Indicator -> National Target (Indicator.national_target FK)
- National Dataset Release -> National Dataset (DatasetRelease.dataset FK)
- National Dataset -> National Indicator (IndicatorDatasetLink)
Indicator data storage:
- IndicatorDataSeries -> Indicator or FrameworkIndicator
- IndicatorDataPoint -> IndicatorDataSeries
- BinaryIndicatorQuestion -> FrameworkIndicator (binary type)

Partial chain currently possible (with inference):
- DatasetRelease -> Dataset -> Indicator -> NationalTarget
  (no explicit release-to-indicator link, but can infer via dataset)

## Gaps vs. required chain

Missing objects / links:
- National Monitoring Programme (no model)
- Programme -> DatasetRelease / Programme -> Indicator links (no link tables)
- Global Target registry (no model)
- Global Indicator -> Global Target mapping (no link table)

## Minimal additive schema implemented in Phase 3

The smallest forward-safe approach uses lightweight alignment/link tables with
minimal framework registries. This supports many-to-many mapping between
national and global layers without porting pilot schemas.

### 1) NationalTarget <-> Framework/MEA Target mapping (many-to-many)

Implemented model: NationalTargetFrameworkTargetLink
- national_target (FK -> NationalTarget)
- framework_target (FK -> FrameworkTarget)
- relation_type, confidence, notes, source
- unique constraint on (national_target, framework_target)

Rationale:
- Supports many-to-many links (e.g., National Target -> GBF Target 2 and SDG 15).
- Avoids a full global target registry.

### 2) Indicator <-> Global Indicator mapping (many-to-many)

Implemented model: IndicatorFrameworkIndicatorLink
- indicator (FK -> Indicator)
- framework_indicator (FK -> FrameworkIndicator)
- relation_type, confidence, notes, source
- unique constraint on (indicator, framework_indicator)

Rationale:
- Matches ORT indicator categories without maintaining large taxonomies.

### 3) Global Indicator -> Global Target link (optional, if needed)

If a direct global indicator-to-target map is required for reporting:

Proposed model: FrameworkIndicatorTargetLink
- framework (FK -> Framework)
- framework_indicator (FK -> FrameworkIndicator)
- framework_target (FK -> FrameworkTarget)
- unique constraint on (framework_indicator, framework_target)

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

Current (post Phase 3):

MonitoringProgramme
  -> MonitoringProgrammeDatasetReleaseLink -> DatasetRelease
  -> MonitoringProgrammeIndicatorLink -> Indicator

Indicator -> IndicatorFrameworkIndicatorLink -> FrameworkIndicator
NationalTarget -> NationalTargetFrameworkTargetLink -> FrameworkTarget
FrameworkIndicator -> FrameworkIndicatorTargetLink -> FrameworkTarget (pending)

## Notes

- The alignment tables are intentionally minimal and avoid bulk-importing
  global registries.
- All mappings are many-to-many and do not force a linear 1:1 chain.
- No ABAC/consent/export gating changes are implied by these proposals.
