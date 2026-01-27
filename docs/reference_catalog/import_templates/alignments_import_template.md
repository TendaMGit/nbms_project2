# Alignment and Link Imports (spec only)

This template covers alignment and linkage tables across the reference catalog.

| Column name | Required? | Example | Lookup key strategy | Notes (idempotent upsert) |
| --- | --- | --- | --- | --- |
| link_type | Yes | `national_target_to_framework_target` | Controlled enum | Determines which link table is used |
| link_uuid | No | `f1f2f3f4-1111-2222-3333-444444444444` | If present, primary upsert key | Immutable once created |
| left_code | Yes | `SA-T3.1` | Code lookup | For target/indicator/programme/methodology/dataset |
| right_code | Yes | `GBF-3` | Code lookup | For target/indicator/programme/methodology/dataset |
| left_uuid | No | `...` | Optional FK | Use if codes not available |
| right_uuid | No | `...` | Optional FK | Use if codes not available |
| relation_type | No | `contributes_to` | AlignmentRelationType | Required for alignment links |
| confidence | No | `80` | 0-100 | Optional |
| role | No | `supporting` | RelationshipType | For non-alignment links |
| notes | No | `Derived from policy mapping` | Text | Optional |
| source_url | No | `https://example.org` | URL | Provenance |
| source_system | No | `CBD` | Controlled list | Provenance |
| source_ref | No | `Annex 9` | Free text | Provenance |
| is_active | No | `true` | Bool | Defaults true |

Supported link_type values:
- `national_target_to_framework_target`
- `national_indicator_to_framework_indicator`
- `framework_indicator_to_framework_indicator` (cross-framework)
- `programme_to_indicator`
- `programme_to_dataset`
- `methodology_version_to_indicator`
- `methodology_version_to_dataset`
- `indicator_to_dataset`

Idempotent upsert behavior (future implementation):
- If `link_uuid` provided, update that record.
- Else use composite key: (`link_type`, left_id, right_id).
