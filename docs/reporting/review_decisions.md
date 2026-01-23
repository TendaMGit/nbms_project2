# Review Decisions (NR7 internal sign-off)

Review decisions provide an append-only sign-off record tied to a specific
reporting snapshot. This ensures governance decisions are traceable to an
immutable v2 export payload.

## Decision rules

- Decisions are tied to a ReportingSnapshot for the same reporting instance.
- Decisions are append-only; updates are blocked at the model layer.
- A new decision supersedes the prior decision rather than editing it.
- Approval is allowed only when:
  - the instance is frozen, and
  - the snapshot is the latest for the instance, and
  - the snapshot schema is `nbms.ort.nr7.v2`.

## How it fits the workflow

1) Resolve readiness, approvals, and consent.
2) Freeze the instance.
3) Create a v2 snapshot.
4) Review content and diffs.
5) Record a review decision tied to the latest snapshot.
