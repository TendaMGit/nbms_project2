# Framework Import Template (spec only)

Use for registering MEA/framework containers (GBF, SDG, Ramsar, UNCCD, etc.).

| Column name | Required? | Example | Lookup key strategy | Notes (idempotent upsert) |
| --- | --- | --- | --- | --- |
| framework_uuid | No | `550e8400-e29b-41d4-a716-446655440000` | If present, primary upsert key | Immutable once created |
| framework_code | Yes | `GBF` | Fallback upsert key | Must be unique |
| framework_title | Yes | `Kunming-Montreal Global Biodiversity Framework` | N/A | Title shown in UI |
| framework_type | Yes | `GBF` | Controlled vocab | Use MEA list |
| description | No | `CBD COP-15 Decision 15/4` | N/A | Required for publish |
| status | No | `published` | LifecycleStatus | Defaults to draft if blank |
| sensitivity | No | `public` | SensitivityClass | Default public |
| organisation_code | No | `SANBI` | Organisation lookup | Only for national frameworks |
| source_system | No | `CBD` | Controlled list | Provenance |
| source_ref | No | `COP-15 Decision 15/4` | Free text | Provenance |
| source_url | No | `https://www.cbd.int/` | URL | Provenance link |

Idempotent upsert behavior (future implementation):
- If `framework_uuid` provided, update that record.
- Else match on `framework_code`.
