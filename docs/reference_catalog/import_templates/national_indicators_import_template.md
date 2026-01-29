# National Indicators Import Template (spec only)

| Column name | Required? | Example | Lookup key strategy | Notes (idempotent upsert) |
| --- | --- | --- | --- | --- |
| indicator_uuid | No | `cc1c1c1c-2d2d-3e3e-4f4f-555555555555` | If present, primary upsert key | Immutable once created |
| indicator_code | Yes | `NI-01` | Fallback upsert key | Must be unique |
| title | Yes | `Area of protected ecosystems` | N/A | Required for publish |
| description | No | `Indicator definition` | N/A | Optional |
| national_target_code | Yes | `SA-T3.1` | FK by code | Required |
| indicator_type | Yes | `headline` | IndicatorType | headline/binary/component/complementary/national |
| value_type | Yes | `percent` | IndicatorValueType | numeric/percent/index/text |
| unit | No | `percent` | Unit vocab | Optional metadata |
| methodology_version_code | No | `METH-01:v1` | FK by code/version | Required for exportable indicators |
| organisation_code | No | `SANBI` | FK by code | Required for publish |
| status | No | `draft` | LifecycleStatus | Draft default |
| sensitivity | No | `internal` | SensitivityClass | Default internal |
| export_approved | No | `false` | N/A | Export gate |
| data_source_type | No | `national` | Controlled vocab | Optional metadata |
| confidence | No | `high` | Controlled vocab | Optional metadata |
| update_frequency | No | `annual` | UpdateCadence | Optional metadata |

Idempotent upsert behavior (future implementation):
- If `indicator_uuid` provided, update that record.
- Else match on `indicator_code`.
