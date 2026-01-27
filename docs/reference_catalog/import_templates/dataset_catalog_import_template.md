# Dataset Catalog Import Template (spec only)

| Column name | Required? | Example | Lookup key strategy | Notes (idempotent upsert) |
| --- | --- | --- | --- | --- |
| dataset_uuid | No | `123e4567-e89b-12d3-a456-426614174000` | If present, primary upsert key | Immutable once created |
| dataset_code | Yes | `DS-001` | Fallback upsert key | Must be unique |
| title | Yes | `National Land Cover 2020` | N/A | Required for publish |
| description | No | `Dataset summary` | N/A | Optional |
| dataset_type | No | `land_cover` | Controlled vocab | Optional |
| custodian_org_code | No | `SANBI` | FK by code | Required for publish |
| producer_org_code | No | `CSIR` | FK by code | Optional |
| licence_code | No | `CC-BY` | License vocab | Required for publish |
| access_level | Yes | `public` | AccessLevel | Required |
| sensitivity_code | No | `internal` | SensitivityClass | Required if restricted |
| consent_required | No | `false` | N/A | Required if IPLC |
| agreement_code | No | `DA-001` | DataAgreement | Required if restricted |
| temporal_start | No | `2020-01-01` | Date | Optional |
| temporal_end | No | `2020-12-31` | Date | Optional |
| update_frequency | No | `annual` | UpdateCadence | Optional |
| spatial_coverage_description | No | `National` | Text | Optional |
| spatial_resolution | No | `30m` | Controlled vocab | Optional |
| taxonomy_standard | No | `IUCN` | Controlled vocab | Optional |
| ecosystem_classification | No | `SAEON` | Controlled vocab | Optional |
| doi_or_identifier | No | `10.1234/example` | DOI format | Optional |
| landing_page_url | No | `https://example.org/ds-001` | URL | Optional |
| api_endpoint_url | No | `https://api.example.org/ds-001` | URL | Optional |
| file_formats | No | `GeoTIFF;CSV` | Controlled vocab | Optional |
| qa_status | No | `validated` | QAStatus | Optional |
| citation | No | `Author (2024)` | Text | Optional |
| keywords | No | `ecosystem;land_cover` | ThematicTag list | Optional |
| last_updated_date | No | `2024-12-01` | Date | Optional |
| is_active | No | `true` | N/A | Defaults true |
| source_system | No | `SANBI` | Controlled list | Provenance |
| source_ref | No | `Internal registry` | Free text | Provenance |

Idempotent upsert behavior (future implementation):
- If `dataset_uuid` provided, update that record.
- Else match on `dataset_code`.
