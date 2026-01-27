# Methodology + Version Import Template (spec only)

## Section A: Methodology (parent)

| Column name | Required? | Example | Lookup key strategy | Notes (idempotent upsert) |
| --- | --- | --- | --- | --- |
| methodology_uuid | No | `0d0e0f0a-1111-2222-3333-444444444444` | If present, primary upsert key | Immutable once created |
| methodology_code | Yes | `METH-01` | Fallback upsert key | Must be unique |
| title | Yes | `Habitat extent calculation` | N/A | Required for publish |
| description | No | `Method summary` | N/A | Optional |
| owner_org_code | No | `SANBI` | FK by code | Required for publish |
| scope | No | `national` | Controlled vocab | Optional |
| references_url | No | `https://example.org/methods/1` | URL | Optional |
| is_active | No | `true` | N/A | Defaults true |
| source_system | No | `SANBI` | Controlled list | Provenance |
| source_ref | No | `Internal registry` | Free text | Provenance |

## Section B: MethodologyVersion (child)

| Column name | Required? | Example | Lookup key strategy | Notes (idempotent upsert) |
| --- | --- | --- | --- | --- |
| method_version_uuid | No | `aaabbbcc-1111-2222-3333-444455556666` | If present, primary upsert key | Immutable once created |
| methodology_code | Yes | `METH-01` | FK by code | Must exist in Methodology |
| version | Yes | `v1.0` | Unique per methodology | Required |
| status | Yes | `active` | MethodologyStatus | Required |
| effective_date | No | `2024-01-01` | Date | Required if active |
| deprecated_date | No | `2026-01-01` | Date | Optional |
| change_log | No | `Updated thresholds` | Text | Optional |
| protocol_url | No | `https://example.org/protocol.pdf` | URL | Optional |
| computational_script_url | No | `https://github.com/org/repo` | URL | Optional |
| parameters_json | No | `{ "threshold": 0.4 }` | JSON | Optional |
| qa_steps_summary | No | `Peer review completed` | Text | Optional |
| peer_reviewed | No | `true` | Bool | Optional |
| approval_body | No | `SANBI` | Text | Optional |
| approval_reference | No | `APP-2024-01` | Text | Optional |
| is_active | No | `true` | N/A | Defaults true |
| source_system | No | `SANBI` | Controlled list | Provenance |
| source_ref | No | `Internal registry` | Free text | Provenance |

Idempotent upsert behavior (future implementation):
- Methodology: `methodology_uuid` or `methodology_code`.
- Version: `method_version_uuid` or (`methodology_code`, `version`).
