# Reference Catalog Requirements v1 (Phase 1 specification only)

> Phase 1 delivers **requirements + data dictionary only**. No schema, migrations,
> forms, routes, or runtime changes are included.

## 1) Purpose and scope

| Layer | Purpose | Examples | In/Out of Reference Catalog v1 |
| --- | --- | --- | --- |
| Reference Catalog | Canonical registry of reference entities used across reporting, readiness, and exports. Stable identifiers, controlled vocabularies, provenance. | Frameworks (GBF/SDG/MEA), goals/targets/indicators, national targets/indicators, monitoring programmes, dataset catalog, methodologies, alignments. | **In scope** |
| Reporting Instance Data | Time-bound reporting content tied to a reporting cycle/instance, approvals, consent, and review workflow. | Section III/IV progress entries, narrative sections, approvals/consent, snapshots, review decisions. | **Out of scope** (must link to Reference Catalog) |
| Indicator Data Series | Observations/time-series and binary responses used in reporting and exports. | IndicatorDataSeries, IndicatorDataPoint, BinaryIndicatorQuestion/Response. | **Out of scope** (must reference catalog indicators/methodologies/datasets) |

**National vs Framework indicators**
- **FrameworkIndicator** represents global/MEA indicators (GBF/SDG/Ramsar/etc.).
- **NationalIndicator** (Indicator) represents country-specific indicators aligned to national targets.
- Alignment between the two is explicit via **Indicator <-> FrameworkIndicator** links; they are not interchangeable.

## 2) Canonical entities + relationships (high-level ER)

```
Organisation
  +- owns/hosts -> MonitoringProgramme
  +- owns/hosts -> DatasetCatalog
  +- owns/hosts -> Methodology
  +- owns/hosts -> NationalTarget
  +- owns/hosts -> NationalIndicator

Framework (MEA)
  +-< FrameworkGoal
        +-< FrameworkTarget
              +-< FrameworkIndicator

NationalTarget --< NationalIndicator
NationalTarget <-> FrameworkTarget  (alignment link + provenance)
NationalIndicator <-> FrameworkIndicator (alignment link + provenance)
FrameworkIndicator <-> FrameworkIndicator (cross-framework alignment)

Methodology --< MethodologyVersion
MethodologyVersion <-> NationalIndicator
MethodologyVersion <-> DatasetCatalog

MonitoringProgramme <-> NationalIndicator
MonitoringProgramme <-> DatasetCatalog
DatasetCatalog --< DatasetRelease (reference only)

NationalIndicator -> IndicatorDataSeries -> IndicatorDataPoint (reporting data layer)
```

## 3) Mandatory vs optional fields rules

**General rule:** Draft requires minimal identifiers and parent links. Published content requires complete metadata, provenance, and governance fields. Export eligibility adds readiness + approval + consent gates.

| Entity | Draft required fields | Publish required fields | Export eligibility (in addition to publish) |
| --- | --- | --- | --- |
| Framework | code, title | description, status=published, sensitivity=public/internal, provenance (source ref) | Not applicable (reference layer only) |
| FrameworkGoal | framework, code, title | official_text (if available), sort_order, is_active, provenance | Not applicable |
| FrameworkTarget | framework, code, title | goal (if applicable), official_text, status=published, sensitivity, provenance | Not applicable |
| FrameworkIndicator | framework, code, title | framework_target, indicator_type, status=published, sensitivity, provenance | Not applicable |
| NationalTarget | code, title | description, organisation, status=published, sensitivity, provenance | Must be approved for reporting instance + consent resolved if IPLC-sensitive |
| NationalIndicator | code, title, national_target | indicator_type, value_type, methodology_version link, organisation, status=published, sensitivity, provenance | Must be approved for reporting instance + consent resolved + readiness links (programme/dataset/methodology) |
| MonitoringProgramme | programme_code, title | programme_type, lead_org, update_frequency, sensitivity_class, consent_required, provenance | Must be linked to indicators/datasets used in reporting instance (readiness blocker if missing) |
| DatasetCatalog | dataset_code, title | access_level, custodian_org, sensitivity_class, consent_required, agreement (if restricted), provenance | Must have at least one eligible dataset release if used in reporting instance |
| Methodology | methodology_code, title | owner_org, scope, references_url, provenance | Not directly exported; required for indicator readiness |
| MethodologyVersion | methodology, version, status | effective_date (if active), protocol_url/qa_steps_summary (if available), provenance | Must be active and linked to indicator if used in reporting instance |
| Alignment links | left/right refs | relation_type, confidence, source/provenance | Required for readiness: national targets/indicators should be aligned to framework counterparts |

**Publish eligibility vs Export eligibility**
- **Publish eligibility**: metadata completeness + lifecycle status + sensitivity set + provenance.
- **Export eligibility**: publish eligibility **plus** instance approval + consent gating + readiness link checks (programme, dataset, methodology version, framework mapping).

## 4) Governance rules by entity (role intent)

| Entity | Create/Edit | Publish/Archive | Sensitivity & consent notes |
| --- | --- | --- | --- |
| Framework / Goal / Target / Indicator | Admin, Secretariat | Admin, Secretariat | Default public; IPLC not expected for global references |
| NationalTarget | Contributor (own org), Data Steward | Secretariat, Data Steward | IPLC-sensitive targets require Community Representative consent before publish/export |
| NationalIndicator | Contributor (own org), Indicator Lead, Data Steward | Secretariat, Data Steward | Must enforce IPLC consent gating and ABAC visibility |
| MonitoringProgramme | Contributor (own org), Data Steward | Secretariat, Data Steward | SensitivityClass + consent_required govern visibility; Security Officer oversight when restricted |
| DatasetCatalog | Contributor (own org), Data Steward | Secretariat, Data Steward, Security Officer (restricted) | Restricted/IPLC datasets require Security Officer + Community Representative consent |
| Methodology / MethodologyVersion | Data Steward, Indicator Lead | Secretariat, Data Steward | Typically public; allow internal/restricted classification if necessary |
| Alignment links | Data Steward, Secretariat | Secretariat | Provenance required for cross-framework mappings |

**ABAC & consent constraints (must remain strict):**
- Visibility is gated by lifecycle status + sensitivity level + organisation membership + role.
- IPLC-sensitive records require explicit consent before publish or export.
- Export eligibility inherits instance approvals and consent state.

## 5) Deletion/archival policy

- **Default: archive** (status=archived or is_active=false).
- **Hard delete** only if no references across reporting, alignments, datasets, methodologies, evidence, or exports.
- **Alignment links** may be deleted only if both sides remain valid and no reporting snapshots depend on them.
- **Dataset releases** should be immutable; deprecate/replace rather than delete.

## 6) Normalization plan (reference tables / controlled vocabularies)

| Reference table / vocab | Why needed | Linked entities | Curation owner |
| --- | --- | --- | --- |
| FrameworkType / MEA | Standardize GBF/SDG/MEA identifiers | Framework | Secretariat/Admin |
| LifecycleStatus | Uniform publish/archival lifecycle | All catalog entities | Admin |
| SensitivityClass | IPLC and access gating alignment | DatasetCatalog, MonitoringProgramme, NationalTarget/Indicator | Security Officer + IPLC Custodian |
| AccessLevel | Public/internal/restricted visibility | DatasetCatalog, Methodology | Admin |
| UpdateCadence | Standard frequency reporting | MonitoringProgramme, DatasetCatalog | Admin |
| QAStatus | Data quality classification | DatasetCatalog, MethodologyVersion | Data Steward |
| ProgrammeType | Programme categorization | MonitoringProgramme | Admin |
| IndicatorType | Indicator classification | FrameworkIndicator, NationalIndicator | Secretariat/Data Steward |
| IndicatorValueType | Numeric/percent/index/text | IndicatorDataSeries / NationalIndicator | Data Steward |
| AlignmentRelationType | Standard mapping semantics | Alignment links | Secretariat |
| RelationshipType | Programme/dataset/methodology links | Link tables | Data Steward |
| License | Standardize licences & URLs | DatasetCatalog | Security Officer |
| SpatialCoverageType | High-level spatial scope | DatasetCatalog, MonitoringProgramme | Admin |
| TemporalCoverageType | Time-series vs point-in-time | DatasetCatalog | Admin |
| ThematicTag | Controlled thematic tags | FrameworkIndicator, NationalIndicator, DatasetCatalog | Secretariat |
| SourceDocument / Provenance | Traceability for alignments/metadata | All entities + links | Data Steward |
| Organisation | Custodian/owner/org references | Many entities | Admin |
| Person/Contact | Optional structured contacts | Organisation, Programme, Dataset | Admin |

## 7) Pilot-to-clean mapping notes (do not port legacy schema)

| Pilot concept | Pilot location | Clean representation in nbms_project2 | Decision / notes |
| --- | --- | --- | --- |
| GlobalGoal | nbms_project/nbms_app/models.py | FrameworkGoal + Framework (GBF/SDG/etc.) | Represent via Framework*; **do not create GlobalGoal model** |
| GlobalTarget | nbms_project/nbms_app/models.py | FrameworkTarget + Framework | Represent via Framework* |
| TargetAlignment | nbms_project/nbms_app/models.py | NationalTargetFrameworkTargetLink | Already exists; keep alignment metadata + provenance |
| Indicator (pilot mixed) | nbms_project/nbms_app/models.py | NationalIndicator + FrameworkIndicator | Split into two registries; link via alignment table |
| IndicatorData | nbms_project/nbms_app/models.py | IndicatorDataSeries/IndicatorDataPoint | Reporting data layer; out of Reference Catalog |
| IndicatorVersion | nbms_project/nbms_app/models.py | MethodologyVersion <-> Indicator link | Prefer MethodologyVersion link over indicator versioning; **do not port IndicatorVersion** |
| Dataset (pilot registry) | nbms_project/nbms_app/models.py | DatasetCatalog + DatasetRelease | Already exists; retain catalog semantics |
| MonitoringProgramme | nbms_project/nbms_app/models.py | MonitoringProgramme (existing) | Keep, expand normalization |
| MethodologyVersion | nbms_project/nbms_app/models.py | Methodology + MethodologyVersion | Keep; link to indicators/datasets via link tables |
| Evidence | nbms_project/nbms_app/models.py | Evidence (existing) | Reporting layer; not part of Reference Catalog |
| ReportCycle/ReportSection | nbms_project/nbms_app/models.py | ReportingInstance/ReportSectionTemplate/Response | **DO NOT PORT** pilot reporting schema |
| SpatialUnit/MapLayer | nbms_project/nbms_app/models.py | Future phase only | **DO NOT PORT** in Reference Catalog v1 |
| SDG Goal/Target | nbms_project/nbms_app/models.py | FrameworkGoal/FrameworkTarget (SDG framework) | Use Framework with code=SDG |
| is_public flags | multiple pilot models | SensitivityClass + LifecycleStatus | **Do not reintroduce** boolean public flags |

**Phase 1 specification only**
- This document defines requirements and data dictionary only.
- All schema/workflow changes are **Phase 2** implementation tickets.
