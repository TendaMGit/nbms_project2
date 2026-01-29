# Pilot Registry Inventory Pack

**Purpose:** Capture the pilot registry/catalog layer as a requirements and
metadata source for future registry rebuilds in `nbms_project2`.

**Important:** This is documentation-only. No schema or runtime changes are in
this PR.

## Inventory scope (in-scope registries)

| Entity | Why in scope | Pilot evidence (high-level) |
| --- | --- | --- |
| Organisation | Core registry for custodian/lead/partner org references | `nbms_project/nbms_app/models.py` (class Organisation), admin + API + serializers |
| DataAgreement | Registry for data sharing and usage constraints | `models.py` (class DataAgreement), admin + API |
| SensitivityClass | Registry for sensitivity classifications | `models.py` (class SensitivityClass), admin + API |
| MonitoringProgramme | Registry linking programmes to datasets/indicators | `models.py` (class MonitoringProgramme), admin + API + forms |
| Dataset (pilot registry) | Metadata catalog of datasets | `models.py` (class Dataset), admin + API + forms |
| DatasetRelease | Versioned dataset releases | `models.py` (class DatasetRelease), admin + API |
| MethodologyVersion | Methods registry with versioning | `models.py` (class MethodologyVersion), admin + API + forms |
| IndicatorVersion | Indicator version registry | `models.py` (class IndicatorVersion), admin |
| IndicatorDatasetLink | Link registry for indicator->dataset role | `models.py` (class IndicatorDatasetLink), admin + API |
| SpatialUnitType / SpatialUnit | Reference spatial lookup registry (optional) | `models.py` (class SpatialUnitType/SpatialUnit), admin |
| MapLayer | GeoJSON layer registry (optional) | `models.py` (class MapLayer), admin |

## Pilot evidence (per entity)

**Organisation**
- Model: `nbms_project/nbms_app/models.py` lines ~661-681
- Admin: `nbms_project/nbms_app/admin.py` lines ~194-199
- API/Serializer: `nbms_project/nbms_app/api.py` lines ~374-376, router registration ~623
- Migrations: `nbms_project/nbms_app/migrations/0011_dataagreement_organisation_sensitivityclass_and_more.py`
- Pilot DB: `nbms_project/db.sqlite3` contains registry records

**DataAgreement**
- Model: `models.py` lines ~683-693
- Admin: `admin.py` lines ~201-206
- API/Serializer: `api.py` lines ~383-385, router ~624
- Migrations: `0011_dataagreement_organisation_sensitivityclass_and_more.py`

**SensitivityClass**
- Model: `models.py` lines ~695-711
- Admin: `admin.py` lines ~207-212
- API/Serializer: `api.py` lines ~392-394, router ~625
- Migrations: `0011_dataagreement_organisation_sensitivityclass_and_more.py`

**MonitoringProgramme**
- Model: `models.py` lines ~813-829
- Admin: `admin.py` lines ~242-247
- API/Serializer: `api.py` lines ~443-445, router ~630
- Forms/UI: `nbms_project/nbms_app/forms.py` MonitoringProgrammeForm

**Dataset (pilot registry)**
- Model: `models.py` lines ~831-853
- Admin: `admin.py` lines ~250-256
- API/Serializer: `api.py` lines ~453-457, router ~631
- Forms/UI: `forms.py` DatasetForm
- Migrations: `0011_dataagreement_organisation_sensitivityclass_and_more.py`

**DatasetRelease**
- Model: `models.py` lines ~855-873
- Admin: `admin.py` lines ~258-263
- API/Serializer: `api.py` lines ~465-467, router ~632
- Migrations: `0013_datasetrelease.py`

**MethodologyVersion**
- Model: `models.py` lines ~875-899
- Admin: `admin.py` lines ~265-272
- API/Serializer: `api.py` lines ~475-477, router ~633
- Forms/UI: `forms.py` MethodologyVersionForm
- Migrations: `0011_dataagreement_organisation_sensitivityclass_and_more.py`

**IndicatorVersion**
- Model: `models.py` lines ~901-916
- Admin: `admin.py` lines ~273-279
- Migrations: `0012_indicator_active_method_version_and_more.py`

**IndicatorDatasetLink**
- Model: `models.py` lines ~918-935
- Admin: `admin.py` lines ~280-286
- API/Serializer: `api.py` lines ~504-506, router ~642
- Migrations: `0012_indicator_active_method_version_and_more.py`

**SpatialUnitType / SpatialUnit**
- Model: `models.py` lines ~937-972
- Admin: `admin.py` lines ~287-301
- Tests: `nbms_project/nbms_app/tests_registries.py`

**MapLayer**
- Model: `models.py` lines ~648-658
- Admin: `admin.py` lines ~475-480

## Field-level metadata (pilot)

> Governance classification and consent relevance are inferred. The pilot does
> not encode consent/ABAC fields for these registries; recommendations reflect
> likely governance expectations in `nbms_project2`.

### Organisation

| Field (pilot) | Type | Required? | Description | Governance class | Consent relevance | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| name | CharField | Yes | Organisation name | Public | No | `models.py` Organisation |
| org_type | CharField (choices) | No | Organisation type (government, NGO, etc.) | Public | No | `models.py` Organisation |
| contact_name | CharField | No | Primary contact person | Restricted | Yes (personal data) | `models.py` Organisation |
| contact_email | CharField | No | Primary contact email | Restricted | Yes (personal data) | `models.py` Organisation |
| website | URLField | No | Website URL | Public | No | `models.py` Organisation |

### DataAgreement

| Field (pilot) | Type | Required? | Description | Governance class | Consent relevance | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| title | CharField | Yes | Agreement title | Internal | Yes (may govern data sharing) | `models.py` DataAgreement |
| description | TextField | No | Agreement summary | Internal | Yes | `models.py` DataAgreement |
| reference_url | URLField | No | Link to agreement document | Restricted | Yes | `models.py` DataAgreement |

### SensitivityClass

| Field (pilot) | Type | Required? | Description | Governance class | Consent relevance | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| name | CharField | Yes | Sensitivity name | Public | No | `models.py` SensitivityClass |
| level | CharField (choices) | Yes | low / medium / high | Public | No | `models.py` SensitivityClass |
| description | TextField | No | Explanation of class | Public | No | `models.py` SensitivityClass |

### MonitoringProgramme

| Field (pilot) | Type | Required? | Description | Governance class | Consent relevance | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| title | CharField | Yes | Programme title | Public | No | `models.py` MonitoringProgramme |
| description | TextField | No | Programme description | Public | No | `models.py` MonitoringProgramme |
| objectives | TextField | No | Programme objectives | Internal | No | `models.py` MonitoringProgramme |
| geographic_scope | CharField | No | Geographic scope text | Internal | Potential (location sensitivity) | `models.py` MonitoringProgramme |
| frequency | CharField | No | Update frequency | Internal | No | `models.py` MonitoringProgramme |
| lead_organisation | FK -> Organisation | No | Lead organisation | Internal | No | `models.py` MonitoringProgramme |
| partner_organisations | M2M -> Organisation | No | Partner orgs | Internal | No | `models.py` MonitoringProgramme |
| indicators | M2M -> Indicator | No | Indicators monitored | Internal | No | `models.py` MonitoringProgramme |
| is_public | Boolean | Yes | Visibility flag | Public | No | `models.py` MonitoringProgramme |

### Dataset (pilot registry)

| Field (pilot) | Type | Required? | Description | Governance class | Consent relevance | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| title | CharField | Yes | Dataset title | Public | No | `models.py` Dataset |
| description | TextField | No | Dataset description | Public | No | `models.py` Dataset |
| version | CharField | No | Dataset version label | Internal | No | `models.py` Dataset |
| license | CharField | No | License text | Public | No | `models.py` Dataset |
| owner | FK -> Organisation | No | Custodian org | Internal | No | `models.py` Dataset |
| data_agreement | FK -> DataAgreement | No | Agreement reference | Internal | Yes | `models.py` Dataset |
| sensitivity | FK -> SensitivityClass | No | Sensitivity class | Restricted | Yes | `models.py` Dataset |
| monitoring_programmes | M2M -> MonitoringProgramme | No | Programme associations | Internal | No | `models.py` Dataset |
| indicators | M2M -> Indicator | No | Indicator associations | Internal | No | `models.py` Dataset |
| national_targets | M2M -> NationalTarget | No | Target associations | Internal | No | `models.py` Dataset |
| source_url | URLField | No | Source URL | Internal | No | `models.py` Dataset |
| download_url | URLField | No | Download URL | Restricted | Yes | `models.py` Dataset |
| is_public | Boolean | Yes | Visibility flag | Public | No | `models.py` Dataset |
| created_at | DateTime | Yes | Creation timestamp | Internal | No | `models.py` Dataset |
| updated_at | DateTime | Yes | Update timestamp | Internal | No | `models.py` Dataset |

### DatasetRelease

| Field (pilot) | Type | Required? | Description | Governance class | Consent relevance | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| dataset | FK -> Dataset | Yes | Dataset reference | Internal | Yes | `models.py` DatasetRelease |
| version | CharField | Yes | Release version | Internal | No | `models.py` DatasetRelease |
| release_date | DateField | Yes | Release date | Internal | No | `models.py` DatasetRelease |
| description | TextField | No | Release notes | Internal | No | `models.py` DatasetRelease |
| download_url | URLField | No | Release download URL | Restricted | Yes | `models.py` DatasetRelease |
| is_public | Boolean | Yes | Visibility flag | Public | No | `models.py` DatasetRelease |
| created_at | DateTime | Yes | Created timestamp | Internal | No | `models.py` DatasetRelease |

### MethodologyVersion

| Field (pilot) | Type | Required? | Description | Governance class | Consent relevance | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| name | CharField | Yes | Method name | Public | No | `models.py` MethodologyVersion |
| version | CharField | Yes | Version label | Public | No | `models.py` MethodologyVersion |
| description | TextField | No | Method description | Public | No | `models.py` MethodologyVersion |
| status | CharField (choices) | Yes | draft / active / deprecated | Public | No | `models.py` MethodologyVersion |
| code_repository_url | URLField | No | Source code URL | Internal | No | `models.py` MethodologyVersion |
| validation_report_url | URLField | No | Validation report URL | Internal | No | `models.py` MethodologyVersion |
| effective_from | DateField | No | Effective date start | Internal | No | `models.py` MethodologyVersion |
| effective_to | DateField | No | Effective date end | Internal | No | `models.py` MethodologyVersion |
| indicators | M2M -> Indicator | No | Linked indicators | Internal | No | `models.py` MethodologyVersion |
| datasets | M2M -> Dataset | No | Linked datasets | Internal | No | `models.py` MethodologyVersion |
| is_public | Boolean | Yes | Visibility flag | Public | No | `models.py` MethodologyVersion |

### IndicatorVersion

| Field (pilot) | Type | Required? | Description | Governance class | Consent relevance | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| indicator | FK -> Indicator | Yes | Indicator reference | Internal | No | `models.py` IndicatorVersion |
| version_label | CharField | Yes | Version label | Internal | No | `models.py` IndicatorVersion |
| method_version | FK -> MethodologyVersion | No | Linked method version | Internal | No | `models.py` IndicatorVersion |
| effective_from | DateField | No | Effective date start | Internal | No | `models.py` IndicatorVersion |
| effective_to | DateField | No | Effective date end | Internal | No | `models.py` IndicatorVersion |
| notes | TextField | No | Notes | Internal | No | `models.py` IndicatorVersion |
| is_active | Boolean | Yes | Active flag | Internal | No | `models.py` IndicatorVersion |

### IndicatorDatasetLink

| Field (pilot) | Type | Required? | Description | Governance class | Consent relevance | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| indicator | FK -> Indicator | Yes | Indicator reference | Internal | No | `models.py` IndicatorDatasetLink |
| dataset | FK -> Dataset | Yes | Dataset reference | Internal | Yes | `models.py` IndicatorDatasetLink |
| role | CharField (choices) | Yes | raw/supporting/contextual | Internal | No | `models.py` IndicatorDatasetLink |

### SpatialUnitType (optional)

| Field (pilot) | Type | Required? | Description | Governance class | Consent relevance | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| code | CharField | Yes | Type code | Public | No | `models.py` SpatialUnitType |
| name | CharField | Yes | Type name | Public | No | `models.py` SpatialUnitType |
| description | TextField | No | Description | Public | No | `models.py` SpatialUnitType |

### SpatialUnit (optional)

| Field (pilot) | Type | Required? | Description | Governance class | Consent relevance | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| type | FK -> SpatialUnitType | Yes | Spatial unit type | Public | No | `models.py` SpatialUnit |
| code | CharField | No | Unit code | Public | No | `models.py` SpatialUnit |
| name | CharField | Yes | Unit name | Public | No | `models.py` SpatialUnit |
| geometry | GeometryField | Yes | Geometry | Restricted | Yes (sensitive locations) | `models.py` SpatialUnit |
| centroid | PointField | No | Centroid | Restricted | Yes | `models.py` SpatialUnit |
| bbox | PolygonField | No | Bounding box | Restricted | Yes | `models.py` SpatialUnit |
| external_id | CharField | No | External reference | Internal | No | `models.py` SpatialUnit |
| is_public | Boolean | Yes | Visibility flag | Public | No | `models.py` SpatialUnit |

### MapLayer (optional)

| Field (pilot) | Type | Required? | Description | Governance class | Consent relevance | Provenance |
| --- | --- | --- | --- | --- | --- | --- |
| name | CharField | Yes | Layer name | Public | No | `models.py` MapLayer |
| description | TextField | No | Layer description | Public | No | `models.py` MapLayer |
| geojson_file | FileField | Yes | GeoJSON data | Restricted | Yes | `models.py` MapLayer |
| is_public | Boolean | Yes | Visibility flag | Public | No | `models.py` MapLayer |
| created_at | DateTime | Yes | Created timestamp | Internal | No | `models.py` MapLayer |

## Relationship sketch (pilot registry layer)

```mermaid
flowchart LR
  Org[Organisation]
  Sens[SensitivityClass]
  Agreement[DataAgreement]
  Programme[MonitoringProgramme]
  Dataset[Dataset (catalog)]
  Release[DatasetRelease]
  Method[MethodologyVersion]
  Indicator[Indicator]
  Target[NationalTarget]
  Framework[Framework/FrameworkTarget/FrameworkIndicator]

  Programme -->|lead/partner| Org
  Programme --> Indicator
  Programme --> Dataset
  Dataset --> Org
  Dataset --> Agreement
  Dataset --> Sens
  Dataset --> Target
  Dataset --> Indicator
  Release --> Dataset
  Method --> Dataset
  Method --> Indicator
  Indicator --> Target
  Indicator --> Framework
```

## Do Not Recreate (already handled in nbms_project2)

These concepts already exist in `nbms_project2` and should **not** be duplicated
as new registries:

- Framework, FrameworkTarget, FrameworkIndicator
- NationalTarget, Indicator
- Alignment join tables (NationalTargetFrameworkTargetLink, IndicatorFrameworkIndicatorLink)
- Reporting cycles/instances, report section templates/responses
- Validation ruleset and readiness scoring
- Approvals and consent gating (instance approvals, consent records)
- Export packages and ORT export builders
- Snapshot and review decision records

## Open questions

- Should spatial registries (SpatialUnitType/SpatialUnit/MapLayer) be in the
  reference catalog scope for `nbms_project2`, or remain out-of-scope?
- Should `Organisation` be extended in `nbms_project2` or separated into a
  dedicated registry model (vs the current Organisation in user accounts)?
- Should `DatasetRelease` be treated as part of the catalog registry or remain
  in the governed Dataset/DatasetRelease approval workflow only?
- Pilot used `is_public`; `nbms_project2` uses sensitivity + ABAC. Confirm how
  to map `is_public` into future registry fields.
