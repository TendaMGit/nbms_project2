# GBF/MEA Goals, Targets, Indicators Import Template (spec only)

Use this template to load framework goals, targets, and indicators for a given framework (e.g., GBF, SDG).

## Section A: Goals

| Column name | Required? | Example | Lookup key strategy | Notes (idempotent upsert) |
| --- | --- | --- | --- | --- |
| goal_uuid | No | `11111111-2222-3333-4444-555555555555` | If present, primary upsert key | Immutable once created |
| framework_code | Yes | `GBF` | FK by code | Must exist in Framework |
| goal_code | Yes | `A` | Unique per framework | E.g., A, B, C, D |
| goal_title | Yes | `Ecosystem integrity` | N/A | Display name |
| official_text | No | `Full official wording...` | N/A | Required for publish if available |
| description | No | `Summary` | N/A | Optional |
| sort_order | No | `1` | N/A | Stable ordering |
| is_active | No | `true` | N/A | Defaults true |
| source_system | No | `CBD` | Controlled list | Provenance |
| source_ref | No | `Decision 15/4` | Free text | Provenance |

## Section B: Targets

| Column name | Required? | Example | Lookup key strategy | Notes (idempotent upsert) |
| --- | --- | --- | --- | --- |
| target_uuid | No | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` | If present, primary upsert key | Immutable once created |
| framework_code | Yes | `GBF` | FK by code | Must exist in Framework |
| goal_code | No | `A` | FK by code | Required if framework has goals |
| target_code | Yes | `1` | Unique per framework | E.g., 1..23 |
| target_title | Yes | `Reduce threats to biodiversity` | N/A | Display name |
| official_text | No | `Full official wording...` | N/A | Required for publish if available |
| description | No | `Summary` | N/A | Optional |
| status | No | `published` | LifecycleStatus | Defaults draft |
| sensitivity | No | `public` | SensitivityClass | Default public |
| source_system | No | `CBD` | Controlled list | Provenance |
| source_ref | No | `Decision 15/4` | Free text | Provenance |

## Section C: Indicators

| Column name | Required? | Example | Lookup key strategy | Notes (idempotent upsert) |
| --- | --- | --- | --- | --- |
| indicator_uuid | No | `99999999-8888-7777-6666-555555555555` | If present, primary upsert key | Immutable once created |
| framework_code | Yes | `GBF` | FK by code | Must exist in Framework |
| target_code | No | `1` | FK by code | Required if indicator belongs to a target |
| indicator_code | Yes | `1.1` | Unique per framework | Use official numbering |
| indicator_title | Yes | `Progress toward target 1` | N/A | Display name |
| indicator_type | Yes | `headline` | FrameworkIndicatorType | headline/binary/component/complementary |
| description | No | `Summary` | N/A | Optional |
| status | No | `published` | LifecycleStatus | Defaults draft |
| sensitivity | No | `public` | SensitivityClass | Default public |
| source_system | No | `CBD` | Controlled list | Provenance |
| source_ref | No | `Decision 15/4` | Free text | Provenance |

Idempotent upsert behavior (future implementation):
- Goals: `goal_uuid` or (`framework_code`, `goal_code`).
- Targets: `target_uuid` or (`framework_code`, `target_code`).
- Indicators: `indicator_uuid` or (`framework_code`, `indicator_code`).
