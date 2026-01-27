# National Targets Import Template (spec only)

| Column name | Required? | Example | Lookup key strategy | Notes (idempotent upsert) |
| --- | --- | --- | --- | --- |
| target_uuid | No | `b1f3e9e0-1234-4f3e-8e4e-123456789abc` | If present, primary upsert key | Immutable once created |
| target_code | Yes | `SA-T3.1` | Fallback upsert key | Must be unique |
| title | Yes | `Restore degraded ecosystems` | N/A | Required for publish |
| description | No | `National target narrative` | N/A | Required for publish |
| organisation_code | No | `SANBI` | FK by code | Required for publish |
| status | No | `draft` | LifecycleStatus | Draft default |
| sensitivity | No | `internal` | SensitivityClass | Default internal |
| export_approved | No | `false` | N/A | Export gate |
| baseline_year | No | `2010` | N/A | Optional metadata |
| baseline_value | No | `45` | N/A | Optional metadata |
| target_year | No | `2030` | N/A | Optional metadata |
| target_value | No | `60` | N/A | Optional metadata |
| unit | No | `percent` | Unit vocab | Optional metadata |
| lead_agency_code | No | `DFFE` | Organisation code | Prefer FK in Phase 2 |
| data_source_ref | No | `NBSAP-2024` | SourceDocument | Prefer FK in Phase 2 |

Idempotent upsert behavior (future implementation):
- If `target_uuid` provided, update that record.
- Else match on `target_code`.
