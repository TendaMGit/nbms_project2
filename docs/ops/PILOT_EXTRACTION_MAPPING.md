# Pilot Extraction Mapping (nbms_project -> nbms_project2)

This document defines field-level mapping rules for the pilot extraction. It is **implementation-grade** and should be used by the Phase 3.1 import scripts.

## Deterministic identifier strategy (required)
- Prefer source UUIDs if present in `nbms_project`.
- If UUIDs are missing, generate UUIDv5 from a namespace + stable key.
- If no stable key exists, generate UUIDv4 and record the mapping.

**Proposed UUIDv5 namespace keys**
- Framework: `framework:<framework_code>`
- FrameworkGoal: `framework_goal:<framework_code>:<goal_code>`
- FrameworkTarget: `framework_target:<framework_code>:<target_code>`
- FrameworkIndicator: `framework_indicator:<framework_code>:<indicator_code>`
- NationalTarget: `national_target:<target_code>` (fallback: `<title>`)
- Indicator: `indicator:<indicator_code>` (fallback: `<title>`) + record conflicts
- MonitoringProgramme: `programme:<programme_code>`
- DatasetCatalog: `dataset:<dataset_code>`
- Methodology: `methodology:<methodology_code>`
- MethodologyVersion: `methodology_version:<methodology_code>:<version>`

**ID mapping ledger** (docs-only artifact to produce later):
- `migration_id_map.csv`
- Columns: `entity_type,source_pk,source_code,source_title,dest_uuid,notes`

## A. Framework registry

### A1. Framework (nbms_project Framework + GlobalGoal.framework)
| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Framework` | `code` | string | `Framework` | `code` | Uppercase + trim | Required | Must be unique | Primary framework record from legacy `Framework` table. |
| `Framework` | `name` | string | `Framework` | `title` | Trim | If missing, use code | Non-empty | |
| `GlobalGoal` | `framework` | string enum | `Framework` | `code` | Normalize to `GBF`/`SDG`/`CBD`/`RAMSAR`/`UNCCD`/`UNFCCC` | Create framework if missing | Must be in allowed set | Use as extra framework seeds where `Framework` table lacks entries. |
| `GlobalGoal` | (derived) | string | `Framework` | `title` | Map from framework code to official name | If unknown, use code | Non-empty | Document mapping table in scripts. |

### A2. FrameworkGoal (nbms_project GlobalGoal)
| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GlobalGoal` | `framework` | string enum | `FrameworkGoal` | `framework` | Resolve via framework code | Required | Framework exists | |
| `GlobalGoal` | `code` | string | `FrameworkGoal` | `goal_code` | Trim | Required | Unique per framework | |
| `GlobalGoal` | `short_title` | string | `FrameworkGoal` | `title` | Trim | Use `official_text` if short_title missing | Non-empty | |
| `GlobalGoal` | `official_text` | text | `FrameworkGoal` | `description` | Trim | Empty allowed | None | |

### A3. FrameworkTarget (nbms_project GlobalTarget)
| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GlobalTarget` | `framework` | string | `FrameworkTarget` | `framework` | Resolve by framework code | Required | Framework exists | |
| `GlobalTarget` | `number` | string | `FrameworkTarget` | `code` | Trim | Required | Unique per framework | `number` becomes `code`. |
| `GlobalTarget` | `title` | string | `FrameworkTarget` | `title` | Trim | Required | Non-empty | |
| `GlobalTarget` | `official_text` | text | `FrameworkTarget` | `description` | Trim | Optional | None | |
| `GlobalTarget` | `goal` | FK | `FrameworkTarget` | `goal` | Resolve `FrameworkGoal` by framework + goal code | Optional | If missing, allow null | |

### A4. FrameworkIndicator (nbms_project FrameworkIndicator)
| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `FrameworkIndicator` | `framework_target` | FK | `FrameworkIndicator` | `framework` | Resolve via FrameworkTarget.framework | Required | Framework exists | NBMS2 does not require framework_target for indicator; map to framework. |
| `FrameworkIndicator` | `code` | string | `FrameworkIndicator` | `code` | Trim | Required | Unique per framework | |
| `FrameworkIndicator` | `title` | string | `FrameworkIndicator` | `title` | Trim | Required | Non-empty | |
| `FrameworkIndicator` | `description` | text | `FrameworkIndicator` | `description` | Trim | Optional | None | |

## B. NationalTarget registry

| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `NationalTarget` | `code` | string | `NationalTarget` | `code` | Trim | Required | Must be unique in NBMS2 | If missing, generate code `NT-<row>` and record in ledger. |
| `NationalTarget` | `title` | string | `NationalTarget` | `title` | Trim | Required | Non-empty | |
| `NationalTarget` | `description` | text | `NationalTarget` | `description` | Trim | Empty allowed | None | |
| `NationalTarget` | `is_public` | boolean | `NationalTarget` | `sensitivity` | Map: true -> PUBLIC; false -> INTERNAL | If null, treat as INTERNAL | Must be valid SensitivityLevel | Never assume public. |
| `NationalTarget` | (governance) | mixed | `NationalTarget` | `requires_consent` | If `GovernanceMetadata.is_ip_lc_sensitive` true -> requires_consent true | Default false | Must be boolean | See governance mapping section. |
| `NationalTarget` | (metadata) | mixed | `NationalTarget` | `status` | Map to PUBLISHED only if public + approved in governance; else DRAFT | Default DRAFT | Must be LifecycleStatus | Avoid leaking restricted data. |
| `NationalTarget` | (metadata) | mixed | `NationalTarget` | `organisation` | Resolve from source org if available | Default to national secretariat org | Must exist | Requires org mapping table. |
| `NationalTarget` | (metadata) | mixed | `NationalTarget` | `source_system/source_ref` | `source_system='nbms_project'`, `source_ref=source_pk` | Required | None | For provenance. |

## C. Indicator registry

| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Indicator` | `code` | string | `Indicator` | `code` | Trim | Required | Must be unique in NBMS2 | If missing, generate `IND-<row>` and record. |
| `Indicator` | `name` | string | `Indicator` | `title` | Trim | Required | Non-empty | |
| `Indicator` | `description` | text | `Indicator` | `description` | Trim | Optional | None | |
| `Indicator` | `unit` | string | `Indicator` | `unit` | Trim | Optional | None | |
| `Indicator` | `indicator_type` | enum | `Indicator` | `indicator_type` | Map values to NBMS2 `NationalIndicatorType` | Default `OTHER` | Must be in enum | Document mapping table in scripts. |
| `Indicator` | `national_targets` (M2M) | list | `Indicator` | `national_target` | If exactly one, map directly; if multiple, choose lowest code and record conflicts | Required | NationalTarget exists | Multi-target indicators require manual resolution or a future link model. |
| `Indicator` | `is_public` | boolean | `Indicator` | `sensitivity` | true -> PUBLIC; false -> INTERNAL | If null, INTERNAL | Must be SensitivityLevel | |
| `Indicator` | (governance) | mixed | `Indicator` | `requires_consent` | If IPLC-sensitive flag exists, set true | Default false | Boolean | |
| `Indicator` | (metadata) | mixed | `Indicator` | `status` | PUBLISHED only if governance approved + public; else DRAFT | Default DRAFT | Must be LifecycleStatus | |

## D. Mapping tables

### D1. NationalTargetFrameworkTargetLink
Source alignment is `TargetAlignment` (NationalTarget -> GlobalTarget).

| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `TargetAlignment` | `national_target` | FK | `NationalTargetFrameworkTargetLink` | `national_target` | Resolve by national target code/uuid | Required | Must exist | |
| `TargetAlignment` | `global_target` | FK | `NationalTargetFrameworkTargetLink` | `framework_target` | Resolve FrameworkTarget by framework+target code | Required | Must exist | Uses GlobalTarget.number as FrameworkTarget.code. |
| `TargetAlignment` | `alignment_degree` | enum (H/M/L) | `NationalTargetFrameworkTargetLink` | `confidence` | Map H/M/L -> 90/60/30 | Default null | 0-100 | Document mapping in scripts. |
| `TargetAlignment` | `explanation` | text | `NationalTargetFrameworkTargetLink` | `notes` | Trim | Optional | None | |
| (none) | (none) | | `NationalTargetFrameworkTargetLink` | `source` | Leave blank | Blank | None | If source citation exists elsewhere, map it. |

### D2. IndicatorFrameworkIndicatorLink
Source alignment is `Indicator.framework_indicators` (M2M to FrameworkIndicator).

| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Indicator` | `framework_indicators` | M2M | `IndicatorFrameworkIndicatorLink` | `indicator`/`framework_indicator` | Create link per M2M row | Required | Both sides exist | |
| `Indicator` | `confidence` | enum (high/medium/low) | `IndicatorFrameworkIndicatorLink` | `confidence` | Map high/medium/low -> 90/60/30 | Default null | 0-100 | If confidence missing, leave null. |
| (none) | (none) | | `IndicatorFrameworkIndicatorLink` | `notes` | Blank | Blank | None | No source notes in legacy; record gap. |
| (none) | (none) | | `IndicatorFrameworkIndicatorLink` | `source` | Blank | Blank | None | |

## E. Catalog entities

### E1. MonitoringProgramme
| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `MonitoringProgramme` | `title` | string | `MonitoringProgramme` | `title` | Trim | Required | Non-empty | |
| `MonitoringProgramme` | (derived) | | `MonitoringProgramme` | `programme_code` | Slug from title or use existing code column if added | Required | Unique | Legacy model has no code; generate deterministic code and store in ledger. |
| `MonitoringProgramme` | `description` | text | `MonitoringProgramme` | `description` | Trim | Optional | None | |
| `MonitoringProgramme` | `objectives` | text | `MonitoringProgramme` | `objectives` | Trim | Optional | None | |
| `MonitoringProgramme` | `lead_organisation` | FK | `MonitoringProgramme` | `lead_org` | Resolve via org mapping | Optional | Org exists | |
| `MonitoringProgramme` | `partner_organisations` | M2M | `MonitoringProgramme` | `partners` | Resolve via org mapping | Optional | All orgs exist | |
| `MonitoringProgramme` | `is_public` | boolean | `MonitoringProgramme` | `access_level`/`sensitivity_class` | Map to `AccessLevel.PUBLIC` if true; else INTERNAL | Default INTERNAL | Valid AccessLevel | |

### E2. DatasetCatalog + DatasetRelease
| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Dataset` | `title` | string | `DatasetCatalog` | `title` | Trim | Required | Non-empty | |
| `Dataset` | (derived) | | `DatasetCatalog` | `dataset_code` | Slug from title or use existing code if available | Required | Unique | Legacy model has no code; generate deterministic code. |
| `Dataset` | `description` | text | `DatasetCatalog` | `description` | Trim | Optional | None | |
| `Dataset` | `owner` | FK | `DatasetCatalog` | `custodian_org` | Resolve org | Optional | Org exists | |
| `Dataset` | `data_agreement` | FK | `DatasetCatalog` | `agreement` | Resolve DataAgreement | Optional | Agreement exists | |
| `Dataset` | `sensitivity` | FK | `DatasetCatalog` | `sensitivity_class` | Resolve by sensitivity name | Optional | Class exists | |
| `Dataset` | `is_public` | boolean | `DatasetCatalog` | `access_level` | true -> PUBLIC; false -> INTERNAL | Default INTERNAL | Valid AccessLevel | |
| `Dataset` | `source_url` | URL | `DatasetCatalog` | `landing_page_url` | Copy | Optional | URL valid | |
| `Dataset` | `download_url` | URL | `DatasetCatalog` | `api_endpoint_url` | Copy | Optional | URL valid | |
| `DatasetRelease` | `version` | string | `DatasetRelease` | `version` | Trim | Required | Unique per dataset | |
| `DatasetRelease` | `release_date` | date | `DatasetRelease` | `release_date` | Copy | Required | Valid date | |
| `DatasetRelease` | `description` | text | `DatasetRelease` | `snapshot_description` | Trim | Optional | None | |
| `DatasetRelease` | `download_url` | URL | `DatasetRelease` | `download_url` | Copy | Optional | URL valid | |

### E3. Methodology + MethodologyVersion
| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `MethodologyVersion` | `name` | string | `Methodology` | `title` | Trim | Required | Non-empty | Legacy has no Methodology parent; create one per distinct name. |
| `MethodologyVersion` | (derived) | | `Methodology` | `methodology_code` | Slug from name | Required | Unique | Record code in ledger. |
| `MethodologyVersion` | `description` | text | `Methodology` | `description` | Trim | Optional | None | |
| `MethodologyVersion` | `version` | string | `MethodologyVersion` | `version` | Trim | Required | Unique per methodology | |
| `MethodologyVersion` | `status` | enum | `MethodologyVersion` | `status` | Map draft/active/deprecated -> NBMS2 enums | Default DRAFT | Valid enum | |
| `MethodologyVersion` | `code_repository_url` | URL | `MethodologyVersion` | `computational_script_url` | Copy | Optional | URL valid | |
| `MethodologyVersion` | `validation_report_url` | URL | `MethodologyVersion` | `protocol_url` | Copy | Optional | URL valid | |

### E4. Evidence
| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Evidence` | `title` | string | `Evidence` | `title` | Trim | Required | Non-empty | |
| `Evidence` | `evidence_type` | enum | `Evidence` | `evidence_type` | Map to NBMS2 enum values | Default `other` | Valid enum | |
| `Evidence` | `source_url` | URL | `Evidence` | `source_url` | Copy | Optional | URL valid | |
| `Evidence` | `is_public` | boolean | `Evidence` | `sensitivity` | true -> PUBLIC; false -> INTERNAL | Default INTERNAL | Valid sensitivity | |

## F. Indicator data

### F1. IndicatorDataSeries + IndicatorDataPoint
Source model is `IndicatorData` (single table per indicator/year/value).

| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `IndicatorData` | `indicator` | FK | `IndicatorDataSeries` | `indicator` | Resolve by indicator code/uuid | Required | Indicator exists | Create one series per unique (indicator, dataset, method_version, unit). |
| `IndicatorData` | `method_version` | FK | `IndicatorDataSeries` | `methodology` | Resolve MethodologyVersion if mapped | Optional | Exists if provided | If missing, leave null. |
| `IndicatorData` | `dataset` | FK | `IndicatorDataSeries` | `dataset_release` | Resolve to latest DatasetRelease if available | Optional | Exists if provided | If no releases, leave null. |
| `IndicatorData` | `year` | int | `IndicatorDataPoint` | `year` | Copy | Required | Must be integer | |
| `IndicatorData` | `value` | float | `IndicatorDataPoint` | `value_numeric` | Copy | Optional | Numeric | Use `value_numeric` for numeric values. |
| `IndicatorData` | `boolean_value` | bool | `IndicatorDataPoint` | `value_binary` | Copy | Optional | Bool | Only if indicator_type is binary. |
| `IndicatorData` | `text_value` | string | `IndicatorDataPoint` | `value_text` | Copy | Optional | None | Use if non-numeric. |
| `IndicatorData` | `data_source` | string | `IndicatorDataPoint` | `source_url` | Copy if URL-like else store in footnote | Optional | None | Normalize to URL if possible. |

### F2. BinaryIndicatorQuestion and BinaryIndicatorResponse
| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (none) | (seeded) | | `BinaryIndicatorQuestion` | (seed) | Do not extract; seed from ORT-aligned dataset | Required | Must match template | Use `seed_binary_indicator_questions`. |
| (optional) | (legacy answers) | | `BinaryIndicatorResponse` | (future) | Out-of-scope unless Mode 2 is approved | N/A | N/A | Requires instance mapping. |

## G. Consent + sensitivity mapping

| Source entity | Source field | Source type/format | Destination entity | Destination field | Transform rule (exact) | Defaults/fallbacks | Validation rule | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GovernanceMetadata` | `is_ip_lc_sensitive` | boolean | Registry entities | `requires_consent` + `sensitivity` | If true: set `requires_consent=true`, `sensitivity=IPLC_SENSITIVE` | Default false | Must be boolean | Applies to NationalTarget/Indicator/Evidence/Dataset where metadata exists. |
| `SensitivityClass` | `name/level` | string | `SensitivityClass` | `sensitivity_name/access_level_default` | Map level: low->PUBLIC, medium->INTERNAL, high->RESTRICTED | Default INTERNAL | Valid AccessLevel | Map to NBMS2 `SensitivityClass` if present. |
| `AccessPolicy` | `policy_level` | enum | Registry entities | `access_level` | public->PUBLIC, restricted->INTERNAL, confidential->RESTRICTED | Default INTERNAL | Valid AccessLevel | Use only if AccessPolicy is attached. |
| (none) | (missing) | | Registry entities | `requires_consent`/`sensitivity` | If missing, set `requires_consent=false`, `sensitivity=INTERNAL` | Default INTERNAL | Must be set | Never assume public. |

## H. Info needed (nbms_project)
The following source fields require validation in the legacy DB before final script implementation:
- Are there UUIDs on registry models or only integer PKs?
- How `GovernanceMetadata` is linked to NationalTarget/Indicator/Evidence/Dataset in practice (content_type usage).
- Whether `Indicator.national_targets` ever includes multiple targets; if so, identify intended primary target.
- Whether `Framework` table in nbms_project is fully populated or if GlobalGoal.framework codes are the true source.
- Whether any consent records exist outside `GovernanceMetadata` (if yes, where and how to map to `ConsentRecord`).
- Presence and usage of `IndicatorData.boolean_value` vs `text_value` in real data.

