# Pilot Extraction Matrix (nbms_project -> nbms_project2)

| Pilot entity / feature | Pilot file/location | Valuable metadata fields (summary) | Proposed nbms_project2 representation | Risks |
| --- | --- | --- | --- | --- |
| GlobalGoal | `nbms_project/nbms_app/models.py` | framework, code, short_title, official_text, description, is_active | **FrameworkGoal** + Framework | Risk of duplicate goal models if ported directly |
| GlobalTarget | `nbms_project/nbms_app/models.py` | framework, number, title, official_text, description, goal | **FrameworkTarget** + FrameworkGoal | Must preserve official numbering |
| TargetAlignment | `nbms_project/nbms_app/models.py` | national_target, global_target, alignment_degree, explanation | **NationalTargetFrameworkTargetLink** | Mapping semantics may differ from new AlignmentRelationType |
| NationalTarget | `nbms_project/nbms_app/models.py` | code, title, description, baseline/target fields, lead_agency, data_source | **NationalTarget** (existing) + optional metadata | Risk of mixing reporting narrative fields with registry |
| Indicator (mixed) | `nbms_project/nbms_app/models.py` | name, code, type, status, unit, metadata | **NationalIndicator** + **FrameworkIndicator** | Must keep national vs framework separation |
| IndicatorData | `nbms_project/nbms_app/models.py` | year, value/text/boolean, geometry | **IndicatorDataSeries/DataPoint** | GIS fields out of scope for Phase 1 |
| IndicatorVersion | `nbms_project/nbms_app/models.py` | version_label, method_version, effective dates | **DO NOT PORT** (prefer MethodologyVersion links) | Versioning semantics may conflict with readiness |
| IndicatorDatasetLink | `nbms_project/nbms_app/models.py` | indicator, dataset, role | **Indicator <-> DatasetCatalog** link | Role vocab differs; align to RelationshipType |
| Framework/FrameworkTarget/FrameworkIndicator | `nbms_project/nbms_app/models.py` | code, title, description | **Framework*** (existing) | Minimal pilot metadata; ensure provenance captured |
| MonitoringProgramme | `nbms_project/nbms_app/models.py` | title, objectives, frequency, lead/partner orgs | **MonitoringProgramme** (existing) | Ensure consent/sensitivity added |
| Dataset (registry) | `nbms_project/nbms_app/models.py` | title, version, licence, owner, agreement, sensitivity, urls | **DatasetCatalog** (existing) | Map is_public to sensitivity + status |
| DatasetRelease | `nbms_project/nbms_app/models.py` | version, release_date, download_url | **DatasetRelease** (existing) | Ensure immutability vs pilot edits |
| MethodologyVersion | `nbms_project/nbms_app/models.py` | name, version, status, repo/validation URLs | **Methodology + MethodologyVersion** (existing) | Split parent vs version data cleanly |
| Organisation | `nbms_project/nbms_app/models.py` | name, org_type, contacts, website | **Organisation** (existing) | Personal data governance (contacts) |
| SensitivityClass | `nbms_project/nbms_app/models.py` | name, level, description | **SensitivityClass** (existing) | Align to IPLC consent semantics |
| DataAgreement | `nbms_project/nbms_app/models.py` | title, description, reference_url | **DataAgreement** (existing) | Must align to access/consent policy |
| SdgGoal/SdgTarget | `nbms_project/nbms_app/models.py` | code, title, goal link | **FrameworkGoal/FrameworkTarget** (Framework=SDG) | Avoid parallel SDG tables |
| Evidence | `nbms_project/nbms_app/models.py` | indicator, file/url, evidence_type | **Evidence** (existing) | Stay in reporting layer, not registry |
| ReportCycle/ReportSection/ReportSnapshot | `nbms_project/nbms_app/models.py` | cycle/section content, snapshots | **DO NOT PORT** (use ReportingInstance + templates) | High risk of schema drift |
| SpatialUnitType/SpatialUnit | `nbms_project/nbms_app/models.py` | spatial geometry, type | **Future phase** | GIS handling out of scope for Phase 1 |
| MapLayer | `nbms_project/nbms_app/models.py` | geojson file, visibility | **Future phase** | IPLC sensitivity risk for spatial data |

**Phase 1 spec only.** Any extraction or migration is a Phase 2 task.
