# Monitoring Programmes Import Template (spec only)

| Column name | Required? | Example | Lookup key strategy | Notes (idempotent upsert) |
| --- | --- | --- | --- | --- |
| programme_uuid | No | `deafbeef-0000-1111-2222-333333333333` | If present, primary upsert key | Immutable once created |
| programme_code | Yes | `MP-001` | Fallback upsert key | Must be unique |
| title | Yes | `National Biodiversity Monitoring Programme` | N/A | Required for publish |
| description | No | `Programme summary` | N/A | Optional |
| programme_type | No | `national` | ProgrammeType | Required for publish |
| lead_org_code | No | `SANBI` | FK by code | Required for publish |
| partner_org_codes | No | `DFFE;CSIR` | FK list (semicolon) | Optional |
| start_year | No | `2015` | N/A | Optional |
| end_year | No | `2030` | N/A | Optional |
| geographic_scope | No | `national` | SpatialCoverageType | Optional |
| update_frequency | No | `annual` | UpdateCadence | Required for publish |
| sensitivity_code | No | `internal` | SensitivityClass | Required for publish |
| consent_required | No | `false` | N/A | Required for publish |
| agreement_code | No | `DA-001` | DataAgreement code | Required if restricted |
| website_url | No | `https://example.org` | URL | Optional |
| primary_contact_name | No | `Dr Jane Doe` | Person/Contact | Optional |
| primary_contact_email | No | `jane@example.org` | Person/Contact | Optional |
| is_active | No | `true` | N/A | Defaults true |
| source_system | No | `SANBI` | Controlled list | Provenance |
| source_ref | No | `Internal registry` | Free text | Provenance |

Idempotent upsert behavior (future implementation):
- If `programme_uuid` provided, update that record.
- Else match on `programme_code`.
