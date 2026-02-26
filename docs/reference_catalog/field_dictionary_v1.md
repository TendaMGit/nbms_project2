# Field Dictionary v1 (Reference Catalog) - Phase 1 specification only

> This document defines **proposed** normalized fields and validation rules.
> No schema changes are implemented in Phase 1.

## Conventions

- **Type**: string / int / uuid / fk / m2m / json / date / choice / bool
- **Cardinality**: 1, 0..1, 0..N, 1..N
- **Validation rules** explicitly state Draft vs Publish vs Export requirements.
- **Pilot source** references `nbms_project` (legacy) where applicable.

---

## 1) Framework (MEA registry)

| Field name (proposed) | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| uuid | uuid | 1 | System-generated | Draft: required; Publish: required; Export: n/a | Immutable identifier | Pilot Framework (code/name) |
| code | string | 1 | Controlled pattern | Draft: required; Publish: required; Unique; Regex `^[A-Z0-9_-]+$` | Admin-curated | Pilot GlobalGoal.framework (choice) |
| title | string | 1 | Free text | Draft: required; Publish: required | Public by default | Pilot Framework.name |
| description | text | 0..1 | Free text | Draft: optional; Publish: required for official frameworks | Public | Pilot GlobalGoal.description |
| framework_type | choice | 1 | FK/enum (FrameworkType/MEA) | Draft: required; Publish: required | Controlled vocab | Pilot GlobalGoal.framework choices |
| status | choice | 1 | LifecycleStatus | Draft: required; Publish: must be `published` | Publication gate | Pilot not explicit |
| sensitivity | choice | 1 | SensitivityClass / SensitivityLevel | Draft: required; Publish: required (default public) | Should remain public; IPLC not expected | Pilot is_public |
| organisation | fk | 0..1 | Organisation | Draft: optional; Publish: required for national frameworks | ABAC owner | Pilot Organisation (owner) |
| created_by | fk | 0..1 | User | Draft: optional; Publish: required | Audit | Pilot N/A |
| review_note | text | 0..1 | Free text | Draft: optional; Publish: optional | Review trace | Pilot review_summary (Indicator) |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: required if external source | Provenance | Pilot GlobalGoal source docs |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: required if external source | Provenance | Pilot GlobalGoal official_text source |
| source_document | fk | 0..1 | SourceDocument | Draft: optional; Publish: required if external source | Provenance | Pilot docs/PDF references |

## 2) FrameworkGoal (first-class)

| Field name (proposed) | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| uuid | uuid | 1 | System-generated | Draft: required; Publish: required | Immutable | Pilot GlobalGoal |
| framework | fk | 1 | Framework | Draft: required; Publish: required | Parent link | Pilot GlobalGoal.framework |
| code | string | 1 | Controlled pattern | Draft: required; Publish: required; Unique per framework | Admin-curated | Pilot GlobalGoal.code |
| title | string | 1 | Free text | Draft: required; Publish: required | Public | Pilot GlobalGoal.short_title |
| official_text | text | 0..1 | Free text | Draft: optional; Publish: required when official text exists | Public | Pilot GlobalGoal.official_text |
| description | text | 0..1 | Free text | Draft: optional; Publish: optional | Public | Pilot GlobalGoal.description |
| sort_order | int | 0..1 | Numeric | Draft: optional; Publish: required for stable ordering | Admin-curated | Pilot ordering |
| is_active | bool | 0..1 | N/A | Draft: optional; Publish: required (true) | Archive control | Pilot GlobalGoal.is_active |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: required for external source | Provenance | Pilot docs |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: required for external source | Provenance | Pilot docs |

## 3) FrameworkTarget

| Field name (proposed) | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| uuid | uuid | 1 | System-generated | Draft: required; Publish: required | Immutable | Pilot GlobalTarget |
| framework | fk | 1 | Framework | Draft: required; Publish: required | Parent link | Pilot GlobalTarget.framework |
| goal | fk | 0..1 | FrameworkGoal | Draft: optional; Publish: required if framework has goals | Consistency | Pilot GlobalTarget.goal |
| code | string | 1 | Controlled pattern | Draft: required; Publish: required; Unique per framework | Admin-curated | Pilot GlobalTarget.number |
| title | string | 1 | Free text | Draft: required; Publish: required | Public | Pilot GlobalTarget.title |
| official_text | text | 0..1 | Free text | Draft: optional; Publish: required when official text exists | Public | Pilot GlobalTarget.official_text |
| description | text | 0..1 | Free text | Draft: optional; Publish: optional | Public | Pilot GlobalTarget.description |
| organisation | fk | 0..1 | Organisation | Draft: optional; Publish: optional | ABAC owner | Pilot N/A |
| created_by | fk | 0..1 | User | Draft: optional; Publish: optional | Audit | Pilot N/A |
| status | choice | 1 | LifecycleStatus | Draft: required; Publish: must be `published` | Publish gate | Pilot N/A |
| sensitivity | choice | 1 | SensitivityClass | Draft: required; Publish: required | Default public | Pilot is_public |
| review_note | text | 0..1 | Free text | Draft: optional; Publish: optional | Review trace | Pilot N/A |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: required for external source | Provenance | Pilot docs |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: required for external source | Provenance | Pilot docs |

## 4) FrameworkIndicator (GBF/MEA indicator)

| Field name (proposed) | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| uuid | uuid | 1 | System-generated | Draft: required; Publish: required | Immutable | Pilot FrameworkIndicator |
| framework | fk | 1 | Framework | Draft: required; Publish: required | Parent link | Pilot FrameworkIndicator.framework_target.framework |
| framework_target | fk | 0..1 | FrameworkTarget | Draft: optional; Publish: required when target exists | Consistency | Pilot FrameworkIndicator.framework_target |
| code | string | 1 | Controlled pattern | Draft: required; Publish: required; Unique per framework | Admin-curated | Pilot FrameworkIndicator.code |
| title | string | 1 | Free text | Draft: required; Publish: required | Public | Pilot FrameworkIndicator.title |
| description | text | 0..1 | Free text | Draft: optional; Publish: optional | Public | Pilot FrameworkIndicator.description |
| indicator_type | choice | 1 | FrameworkIndicatorType | Draft: required; Publish: required | Controlled vocab | Pilot Indicator.indicator_type |
| value_type | choice | 0..1 | IndicatorValueType | Draft: optional; Publish: optional | Inform data-series expectations | Pilot Indicator.unit/value types |
| status | choice | 1 | LifecycleStatus | Draft: required; Publish: must be `published` | Publish gate | Pilot status |
| sensitivity | choice | 1 | SensitivityClass | Draft: required; Publish: required | Default public | Pilot is_public |
| organisation | fk | 0..1 | Organisation | Draft: optional; Publish: optional | ABAC owner | Pilot N/A |
| created_by | fk | 0..1 | User | Draft: optional; Publish: optional | Audit | Pilot N/A |
| review_note | text | 0..1 | Free text | Draft: optional; Publish: optional | Review trace | Pilot review_summary |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: required for external source | Provenance | Pilot docs |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: required for external source | Provenance | Pilot docs |

## 5) NationalTarget

| Field name (proposed) | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| uuid | uuid | 1 | System-generated | Draft: required; Publish: required | Immutable | Pilot NationalTarget |
| code | string | 1 | Controlled pattern | Draft: required; Publish: required; Unique | Admin-curated | Pilot NationalTarget.code |
| title | string | 1 | Free text | Draft: required; Publish: required | Public | Pilot NationalTarget.title |
| description | text | 0..1 | Free text | Draft: optional; Publish: required | Public/Internal | Pilot NationalTarget.description |
| organisation | fk | 0..1 | Organisation | Draft: optional; Publish: required | ABAC owner | Pilot lead_agency (string) |
| created_by | fk | 0..1 | User | Draft: optional; Publish: required | Audit | Pilot N/A |
| status | choice | 1 | LifecycleStatus | Draft: required; Publish: must be `published` | Publish gate | Pilot N/A |
| sensitivity | choice | 1 | SensitivityClass | Draft: required; Publish: required | IPLC gating | Pilot is_public |
| export_approved | bool | 0..1 | N/A | Draft: optional; Export: must be true | Export gate | Pilot N/A |
| review_note | text | 0..1 | Free text | Draft: optional; Publish: optional | Review trace | Pilot review_summary |
| baseline_year | int | 0..1 | N/A | Draft: optional; Publish: optional | Reporting context | Pilot NationalTarget.baseline_year |
| baseline_value | string/number | 0..1 | N/A | Draft: optional; Publish: optional | Reporting context | Pilot NationalTarget.baseline_value |
| target_year | int | 0..1 | N/A | Draft: optional; Publish: optional | Reporting context | Pilot NationalTarget.target_year |
| target_value | string/number | 0..1 | N/A | Draft: optional; Publish: optional | Reporting context | Pilot NationalTarget.target_value |
| unit | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Use Unit vocab | Pilot NationalTarget.unit |
| lead_agency | string | 0..1 | FK Organisation (future) | Draft: optional; Publish: optional | Prefer Organization FK in Phase 1 P2 backlog | Pilot NationalTarget.lead_agency |
| data_source | string | 0..1 | FK SourceDocument (future) | Draft: optional; Publish: optional | Prefer SourceDocument | Pilot NationalTarget.data_source |

## 6) NationalIndicator (Indicator)

| Field name (proposed) | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| uuid | uuid | 1 | System-generated | Draft: required; Publish: required | Immutable | Pilot Indicator |
| code | string | 1 | Controlled pattern | Draft: required; Publish: required; Unique | Admin-curated | Pilot Indicator.code |
| title | string | 1 | Free text | Draft: required; Publish: required | Public | Pilot Indicator.name |
| description | text | 0..1 | Free text | Draft: optional; Publish: optional | Public/Internal | Pilot Indicator.description |
| national_target | fk | 1 | NationalTarget | Draft: required; Publish: required | Parent link | Pilot Indicator.national_targets |
| indicator_type | choice | 1 | IndicatorType | Draft: required; Publish: required | Distinguish national vs global usage | Pilot Indicator.indicator_type |
| value_type | choice | 1 | IndicatorValueType | Draft: required; Publish: required | Drives data series validation | Pilot IndicatorData.value/boolean/text |
| unit | string | 0..1 | Unit vocab | Draft: optional; Publish: optional | Display + validation | Pilot Indicator.unit |
| methodology_version | fk | 0..1 | MethodologyVersion | Draft: optional; Publish: required for exportable indicators | Readiness blocker if missing | Pilot Indicator.active_method_version |
| organisation | fk | 0..1 | Organisation | Draft: optional; Publish: required | ABAC owner | Pilot Indicator.data_provider_org |
| created_by | fk | 0..1 | User | Draft: optional; Publish: required | Audit | Pilot Indicator.indicator_lead (user) |
| status | choice | 1 | LifecycleStatus | Draft: required; Publish: must be `published` | Publish gate | Pilot Indicator.status |
| sensitivity | choice | 1 | SensitivityClass | Draft: required; Publish: required | IPLC gating | Pilot is_public |
| export_approved | bool | 0..1 | N/A | Draft: optional; Export: must be true | Export gate | Pilot N/A |
| review_note | text | 0..1 | Free text | Draft: optional; Publish: optional | Review trace | Pilot review_summary |
| data_source_type | choice | 0..1 | Controlled vocab | Draft: optional; Publish: optional | National/global/both/no data | Pilot Indicator.data_source_type |
| data_source_description | text | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot Indicator.data_source_description |
| data_provider_contact | string | 0..1 | Person/Contact | Draft: optional; Publish: optional | Personal data governance | Pilot Indicator.data_provider_contact |
| confidence | choice | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Quality metadata | Pilot Indicator.confidence |
| update_frequency | choice | 0..1 | UpdateCadence | Draft: optional; Publish: optional | Metadata | Pilot Indicator.frequency |

## 7) MonitoringProgramme

| Field name (proposed) | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| uuid | uuid | 1 | System-generated | Draft: required; Publish: required | Immutable | Pilot MonitoringProgramme |
| programme_code | string | 1 | Controlled pattern | Draft: required; Publish: required; Unique | Admin-curated | Pilot title/code |
| title | string | 1 | Free text | Draft: required; Publish: required | Public | Pilot MonitoringProgramme.title |
| description | text | 0..1 | Free text | Draft: optional; Publish: optional | Public | Pilot MonitoringProgramme.description |
| programme_type | choice | 0..1 | ProgrammeType | Draft: optional; Publish: required | Controlled vocab | Pilot geographic_scope/type |
| lead_org | fk | 0..1 | Organisation | Draft: optional; Publish: required | ABAC owner | Pilot lead_organisation |
| partners | m2m | 0..N | Organisation | Draft: optional; Publish: optional | Collaboration | Pilot partner_organisations |
| start_year | int | 0..1 | N/A | Draft: optional; Publish: optional | Temporal scope | Pilot N/A |
| end_year | int | 0..1 | N/A | Draft: optional; Publish: optional | Temporal scope | Pilot N/A |
| geographic_scope | string | 0..1 | SpatialCoverageType | Draft: optional; Publish: optional | Sensitive if site-level | Pilot geographic_scope |
| spatial_coverage_description | text | 0..1 | Free text | Draft: optional; Publish: optional | Sensitive if site-level | Pilot geographic_scope |
| taxonomic_scope | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Domain metadata | Pilot N/A |
| ecosystem_scope | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Domain metadata | Pilot N/A |
| objectives | text | 0..1 | Free text | Draft: optional; Publish: optional | Public/Internal | Pilot objectives |
| sampling_design_summary | text | 0..1 | Free text | Draft: optional; Publish: optional | Internal | Pilot N/A |
| update_frequency | choice | 0..1 | UpdateCadence | Draft: optional; Publish: required | Controlled vocab | Pilot frequency |
| qa_process_summary | text | 0..1 | Free text | Draft: optional; Publish: optional | Internal | Pilot N/A |
| sensitivity_class | fk | 0..1 | SensitivityClass | Draft: optional; Publish: required | Consent gating | Pilot N/A |
| consent_required | bool | 0..1 | N/A | Draft: optional; Publish: required | IPLC gate | Pilot N/A |
| agreement | fk | 0..1 | DataAgreement | Draft: optional; Publish: required if restricted | Security Officer oversight | Pilot N/A |
| website_url | string | 0..1 | URL | Draft: optional; Publish: optional | Public | Pilot N/A |
| primary_contact_name | string | 0..1 | Person/Contact | Draft: optional; Publish: optional | Personal data governance | Pilot contact_name |
| primary_contact_email | string | 0..1 | Person/Contact | Draft: optional; Publish: optional | Personal data governance | Pilot contact_email |
| notes | text | 0..1 | Free text | Draft: optional; Publish: optional | Internal | Pilot N/A |
| is_active | bool | 0..1 | N/A | Draft: optional; Publish: required | Archive control | Pilot is_public (inverse) |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: optional | Provenance | Pilot N/A |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot N/A |

## 8) DatasetCatalog (metadata record)

| Field name (proposed) | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| uuid | uuid | 1 | System-generated | Draft: required; Publish: required | Immutable | Pilot Dataset |
| dataset_code | string | 1 | Controlled pattern | Draft: required; Publish: required; Unique | Admin-curated | Pilot Dataset.title/version |
| title | string | 1 | Free text | Draft: required; Publish: required | Public | Pilot Dataset.title |
| description | text | 0..1 | Free text | Draft: optional; Publish: optional | Public | Pilot Dataset.description |
| dataset_type | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Metadata | Pilot N/A |
| custodian_org | fk | 0..1 | Organisation | Draft: optional; Publish: required | ABAC owner | Pilot Dataset.owner |
| producer_org | fk | 0..1 | Organisation | Draft: optional; Publish: optional | Metadata | Pilot N/A |
| licence | choice | 0..1 | License | Draft: optional; Publish: required | Security Officer oversight | Pilot Dataset.license |
| access_level | choice | 1 | AccessLevel | Draft: required; Publish: required | Public/internal/restricted | Pilot is_public |
| sensitivity_class | fk | 0..1 | SensitivityClass | Draft: optional; Publish: required if restricted | IPLC gating | Pilot Dataset.sensitivity |
| consent_required | bool | 0..1 | N/A | Draft: optional; Publish: required if IPLC | Consent gating | Pilot N/A |
| agreement | fk | 0..1 | DataAgreement | Draft: optional; Publish: required if restricted | Security Officer oversight | Pilot Dataset.data_agreement |
| temporal_start | date | 0..1 | N/A | Draft: optional; Publish: optional | Metadata | Pilot N/A |
| temporal_end | date | 0..1 | N/A | Draft: optional; Publish: optional | Metadata | Pilot N/A |
| update_frequency | choice | 0..1 | UpdateCadence | Draft: optional; Publish: optional | Metadata | Pilot Dataset.version |
| spatial_coverage_description | text | 0..1 | Free text | Draft: optional; Publish: optional | Sensitive if site-level | Pilot N/A |
| spatial_resolution | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Metadata | Pilot N/A |
| taxonomy_standard | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Metadata | Pilot N/A |
| ecosystem_classification | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Metadata | Pilot N/A |
| doi_or_identifier | string | 0..1 | Controlled format | Draft: optional; Publish: optional | Metadata | Pilot N/A |
| landing_page_url | string | 0..1 | URL | Draft: optional; Publish: optional | Public | Pilot Dataset.source_url |
| api_endpoint_url | string | 0..1 | URL | Draft: optional; Publish: optional | Public | Pilot Dataset.download_url |
| file_formats | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Metadata | Pilot N/A |
| qa_status | choice | 0..1 | QAStatus | Draft: optional; Publish: optional | Metadata | Pilot N/A |
| citation | text | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot N/A |
| keywords | string | 0..1 | ThematicTag | Draft: optional; Publish: optional | Metadata | Pilot N/A |
| last_updated_date | date | 0..1 | N/A | Draft: optional; Publish: optional | Metadata | Pilot Dataset.updated_at |
| is_active | bool | 0..1 | N/A | Draft: optional; Publish: required | Archive control | Pilot is_public |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: optional | Provenance | Pilot N/A |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot N/A |

## 9) DatasetRelease (reference only)

| Field name (proposed) | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| uuid | uuid | 1 | System-generated | Draft: required; Publish: required | Immutable | Pilot DatasetRelease |
| dataset | fk | 1 | DatasetCatalog | Draft: required; Publish: required | Parent link | Pilot DatasetRelease.dataset |
| version | string | 1 | Controlled pattern | Draft: required; Publish: required; Unique per dataset | Release identifier | Pilot DatasetRelease.version |
| release_date | date | 0..1 | N/A | Draft: optional; Publish: required | Metadata | Pilot DatasetRelease.release_date |
| snapshot_title | string | 0..1 | Free text | Draft: optional; Publish: optional | Snapshot of dataset title | Pilot Dataset.title |
| snapshot_description | text | 0..1 | Free text | Draft: optional; Publish: optional | Snapshot of dataset description | Pilot Dataset.description |
| snapshot_methodology | text | 0..1 | Free text | Draft: optional; Publish: optional | Snapshot of methodology | Pilot MethodologyVersion |
| organisation | fk | 0..1 | Organisation | Draft: optional; Publish: optional | ABAC owner | Pilot Dataset.owner |
| created_by | fk | 0..1 | User | Draft: optional; Publish: optional | Audit | Pilot N/A |
| status | choice | 1 | LifecycleStatus | Draft: required; Publish: must be `published` | Export gate | Pilot is_public |
| sensitivity | choice | 1 | SensitivityClass | Draft: required; Publish: required | IPLC gating | Pilot Dataset.sensitivity |
| export_approved | bool | 0..1 | N/A | Draft: optional; Export: must be true | Export gate | Pilot N/A |
| review_note | text | 0..1 | Free text | Draft: optional; Publish: optional | Review trace | Pilot N/A |

## 10) Methodology

| Field name (proposed) | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| uuid | uuid | 1 | System-generated | Draft: required; Publish: required | Immutable | Pilot MethodologyVersion.name |
| methodology_code | string | 1 | Controlled pattern | Draft: required; Publish: required; Unique | Admin-curated | Pilot MethodologyVersion.name |
| title | string | 1 | Free text | Draft: required; Publish: required | Public | Pilot MethodologyVersion.name |
| description | text | 0..1 | Free text | Draft: optional; Publish: optional | Public | Pilot MethodologyVersion.description |
| owner_org | fk | 0..1 | Organisation | Draft: optional; Publish: required | ABAC owner | Pilot N/A |
| scope | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Metadata | Pilot N/A |
| references_url | string | 0..1 | URL | Draft: optional; Publish: optional | Provenance | Pilot MethodologyVersion.code_repository_url |
| is_active | bool | 0..1 | N/A | Draft: optional; Publish: required | Archive control | Pilot is_public |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: optional | Provenance | Pilot N/A |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot N/A |

## 11) MethodologyVersion

| Field name (proposed) | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| uuid | uuid | 1 | System-generated | Draft: required; Publish: required | Immutable | Pilot MethodologyVersion |
| methodology | fk | 1 | Methodology | Draft: required; Publish: required | Parent link | Pilot MethodologyVersion.name |
| version | string | 1 | Controlled pattern | Draft: required; Publish: required; Unique per methodology | Versioning | Pilot MethodologyVersion.version |
| status | choice | 1 | MethodologyStatus | Draft: required; Publish: required (active/deprecated) | Publish gate | Pilot MethodologyVersion.status |
| effective_date | date | 0..1 | N/A | Draft: optional; Publish: required if active | Validity | Pilot effective_from |
| deprecated_date | date | 0..1 | N/A | Draft: optional; Publish: optional | Validity | Pilot effective_to |
| change_log | text | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot N/A |
| protocol_url | string | 0..1 | URL | Draft: optional; Publish: optional | Provenance | Pilot code_repository_url |
| computational_script_url | string | 0..1 | URL | Draft: optional; Publish: optional | Provenance | Pilot code_repository_url |
| parameters_json | json | 0..1 | N/A | Draft: optional; Publish: optional | Technical metadata | Pilot N/A |
| qa_steps_summary | text | 0..1 | Free text | Draft: optional; Publish: optional | QA metadata | Pilot validation_report_url |
| peer_reviewed | bool | 0..1 | N/A | Draft: optional; Publish: optional | QA metadata | Pilot N/A |
| approval_body | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Governance | Pilot N/A |
| approval_reference | string | 0..1 | Free text | Draft: optional; Publish: optional | Governance | Pilot N/A |
| is_active | bool | 0..1 | N/A | Draft: optional; Publish: required | Archive control | Pilot is_public |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: optional | Provenance | Pilot N/A |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot N/A |

## 12) Link tables (spec only)

### 12a) NationalTarget <-> FrameworkTarget (alignment)

| Field name | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| national_target | fk | 1 | NationalTarget | Draft: required; Publish: required | Alignment context | Pilot TargetAlignment.national_target |
| framework_target | fk | 1 | FrameworkTarget | Draft: required; Publish: required | Alignment context | Pilot TargetAlignment.global_target |
| relation_type | choice | 1 | AlignmentRelationType | Draft: required; Publish: required | Semantic meaning | Pilot alignment_degree |
| confidence | int | 0..1 | 0-100 | Draft: optional; Publish: optional | Confidence score | Pilot alignment_degree |
| notes | text | 0..1 | Free text | Draft: optional; Publish: optional | Rationale | Pilot TargetAlignment.explanation |
| source_url | string | 0..1 | URL | Draft: optional; Publish: optional | Provenance | Pilot docs |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: optional | Provenance | Pilot docs |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot docs |

### 12b) NationalIndicator <-> FrameworkIndicator (alignment)

| Field name | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| indicator | fk | 1 | NationalIndicator | Draft: required; Publish: required | Alignment context | Pilot Indicator.framework_indicators |
| framework_indicator | fk | 1 | FrameworkIndicator | Draft: required; Publish: required | Alignment context | Pilot FrameworkIndicator |
| relation_type | choice | 1 | AlignmentRelationType | Draft: required; Publish: required | Semantic meaning | Pilot Indicator framework mapping |
| confidence | int | 0..1 | 0-100 | Draft: optional; Publish: optional | Confidence score | Pilot N/A |
| notes | text | 0..1 | Free text | Draft: optional; Publish: optional | Rationale | Pilot N/A |
| source_url | string | 0..1 | URL | Draft: optional; Publish: optional | Provenance | Pilot docs |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: optional | Provenance | Pilot docs |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot docs |

### 12c) MonitoringProgramme <-> NationalIndicator

| Field name | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| programme | fk | 1 | MonitoringProgramme | Draft: required; Publish: required | Readiness link | Pilot MonitoringProgramme.indicators |
| indicator | fk | 1 | NationalIndicator | Draft: required; Publish: required | Readiness link | Pilot MonitoringProgramme.indicators |
| relationship_type | choice | 0..1 | RelationshipType | Draft: optional; Publish: optional | Lead/partner/supporting | Pilot N/A |
| role | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Additional role | Pilot N/A |
| notes | text | 0..1 | Free text | Draft: optional; Publish: optional | Rationale | Pilot N/A |
| is_active | bool | 0..1 | N/A | Draft: optional; Publish: optional | Archive control | Pilot N/A |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: optional | Provenance | Pilot N/A |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot N/A |

### 12d) MonitoringProgramme <-> DatasetCatalog

| Field name | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| programme | fk | 1 | MonitoringProgramme | Draft: required; Publish: required | Readiness link | Pilot MonitoringProgramme.datasets |
| dataset | fk | 1 | DatasetCatalog | Draft: required; Publish: required | Readiness link | Pilot Dataset.monitoring_programmes |
| relationship_type | choice | 0..1 | RelationshipType | Draft: optional; Publish: optional | Lead/partner/supporting | Pilot N/A |
| role | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Additional role | Pilot N/A |
| notes | text | 0..1 | Free text | Draft: optional; Publish: optional | Rationale | Pilot N/A |
| is_active | bool | 0..1 | N/A | Draft: optional; Publish: optional | Archive control | Pilot N/A |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: optional | Provenance | Pilot N/A |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot N/A |

### 12e) MethodologyVersion <-> NationalIndicator

| Field name | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| methodology_version | fk | 1 | MethodologyVersion | Draft: required; Publish: required | Readiness link | Pilot Indicator.active_method_version |
| indicator | fk | 1 | NationalIndicator | Draft: required; Publish: required | Readiness link | Pilot Indicator.methodology_versions |
| relationship_type | choice | 0..1 | RelationshipType | Draft: optional; Publish: optional | Lead/supporting | Pilot N/A |
| notes | text | 0..1 | Free text | Draft: optional; Publish: optional | Rationale | Pilot N/A |
| is_active | bool | 0..1 | N/A | Draft: optional; Publish: optional | Archive control | Pilot N/A |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: optional | Provenance | Pilot N/A |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot N/A |

### 12f) MethodologyVersion <-> DatasetCatalog

| Field name | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| methodology_version | fk | 1 | MethodologyVersion | Draft: required; Publish: required | Readiness link | Pilot MethodologyVersion.datasets |
| dataset | fk | 1 | DatasetCatalog | Draft: required; Publish: required | Readiness link | Pilot MethodologyVersion.datasets |
| relationship_type | choice | 0..1 | RelationshipType | Draft: optional; Publish: optional | Lead/supporting | Pilot N/A |
| notes | text | 0..1 | Free text | Draft: optional; Publish: optional | Rationale | Pilot N/A |
| is_active | bool | 0..1 | N/A | Draft: optional; Publish: optional | Archive control | Pilot N/A |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: optional | Provenance | Pilot N/A |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot N/A |

### 12g) NationalIndicator <-> DatasetCatalog

| Field name | Type | Cardinality | Normalization | Validation rules | Governance notes | Pilot source |
| --- | --- | --- | --- | --- | --- | --- |
| indicator | fk | 1 | NationalIndicator | Draft: required; Publish: required | Readiness link | Pilot IndicatorDatasetLink.indicator |
| dataset | fk | 1 | DatasetCatalog | Draft: required; Publish: required | Readiness link | Pilot IndicatorDatasetLink.dataset |
| relationship_type | choice | 0..1 | RelationshipType | Draft: optional; Publish: optional | Raw/supporting/contextual | Pilot IndicatorDatasetLink.role |
| role | string | 0..1 | Controlled vocab | Draft: optional; Publish: optional | Role detail | Pilot IndicatorDatasetLink.role |
| notes | text | 0..1 | Free text | Draft: optional; Publish: optional | Rationale | Pilot N/A |
| is_active | bool | 0..1 | N/A | Draft: optional; Publish: optional | Archive control | Pilot N/A |
| source_system | string | 0..1 | Controlled list | Draft: optional; Publish: optional | Provenance | Pilot N/A |
| source_ref | string | 0..1 | Free text | Draft: optional; Publish: optional | Provenance | Pilot N/A |

---

## Supporting tables / controlled vocabularies (spec only)

| Table / vocab | Why needed | Links to | Curation responsibility |
| --- | --- | --- | --- |
| Organisation | Canonical org registry | Ownership across entities | Admin |
| Person/Contact | Structured contacts | Organisation, Programme, Dataset | Admin |
| RoleType | Owner/custodian/lead/reviewer | Organisation relationships | Admin |
| License | Standard licenses + URLs | DatasetCatalog | Security Officer |
| DataAccessCondition | Public/restricted/IPLC | DatasetCatalog, Evidence | Security Officer + IPLC Custodian |
| SensitivityClass | Sensitivity + consent gating | DatasetCatalog, MonitoringProgramme, NationalTarget/Indicator | Security Officer + IPLC Custodian |
| UpdateCadence | Reporting frequency | Programme, Dataset | Admin |
| QAStatus | Quality state | DatasetCatalog, MethodologyVersion | Data Steward |
| SpatialCoverageType | High-level spatial scope | Programme, Dataset | Admin |
| TemporalCoverageType | Time-series/point-in-time | DatasetCatalog | Admin |
| ThematicTag | Controlled thematic tags | Indicators, Datasets | Secretariat |
| SourceDocument | Provenance and citations | All entities/links | Data Steward |
| FrameworkType | MEA classification | Framework | Secretariat |
| IndicatorType | Headline/binary/component/etc. | Indicators | Secretariat |
| IndicatorValueType | Numeric/text/percent/index | IndicatorDataSeries | Data Steward |
| AlignmentRelationType | Equivalent/contributes_to/etc. | Alignment links | Secretariat |
| RelationshipType | Lead/partner/supporting | Link tables | Data Steward |

**Phase 1 spec only.** Implementation of new tables/vocabs is tracked in Phase 1 P2 backlog.
