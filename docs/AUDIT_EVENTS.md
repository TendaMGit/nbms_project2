# Audit Event Types

This reference lists the audit event types emitted by the NBMS application. All audit events include `object_type`, `object_uuid`, and request context (path, method, IP, UA, session) when available. Metadata is sanitized using a denylist (geometry, narrative text, contact fields, file/payload content, consent notes) and will show `[redacted]` where applicable.

## CRUD (signal-driven)

| event_type pattern | When it fires | Metadata keys | Sensitivity notes |
| --- | --- | --- | --- |
| `create_<model>` | Post-save on create for any `nbms_app` model | `status`, `sensitivity`, `access_level`, `is_active` (if present) | Redaction applied to metadata values/keys when sensitive |
| `update_<model>` | Post-save on update for any `nbms_app` model | `status`, `sensitivity`, `access_level`, `is_active` (if present) | Redaction applied |
| `delete_<model>` | Post-delete for any `nbms_app` model | `status`, `sensitivity`, `access_level`, `is_active` (if present) | Redaction applied |

Note: For workflow transitions, approvals, exports, and other domain actions, CRUD signal logging is suppressed to avoid duplicate audit events. Those actions emit explicit domain events instead.

## Workflow / Lifecycle

| event_type | When it fires | Metadata keys | Sensitivity notes |
| --- | --- | --- | --- |
| `submit_for_review` | Draft -> Pending review | `status` | Redaction applies to other keys |
| `approve` | Pending review -> Approved | `status`, `note` | `note` redacted |
| `reject` | Pending review -> Draft | `status`, `note` | `note` redacted |
| `publish` | Approved -> Published | `status` | Redaction applies |
| `archive` | Published -> Archived | `status` | Redaction applies |
| `archive_reason` | Archive action recorded with reason | `reason` | `reason` redacted |
| `unarchive` | Reactivation of `is_active` objects | `reason` | `reason` redacted |
| `instance_freeze` | Reporting instance frozen | `instance_uuid` | Redaction applies |
| `instance_unfreeze` | Reporting instance unfrozen | `instance_uuid` | Redaction applies |

## Consent & Approvals

| event_type | When it fires | Metadata keys | Sensitivity notes |
| --- | --- | --- | --- |
| `consent_granted` / `consent_denied` / `consent_required` | Consent status change on consent-gated objects | `instance_uuid`, `status` | No sensitive content stored |
| `instance_export_approve` | Export approval granted for object | `instance_uuid`, `decision`, `scope`, `admin_override` | No sensitive content stored |
| `instance_export_revoke` | Export approval revoked for object | `instance_uuid`, `decision`, `scope`, `admin_override` | No sensitive content stored |
| `instance_export_bulk` | Bulk approval/revoke summary | `instance_uuid`, `action`, `obj_type`, `count`, `skipped` | No sensitive content stored |
| `instance_export_override` | Admin override used on frozen instance | `instance_uuid`, `decision` | No sensitive content stored |
| `instance_export_blocked_consent` | Approval blocked due to missing consent | `instance_uuid` | No sensitive content stored |

## Exports & Downloads

| event_type | When it fires | Metadata keys | Sensitivity notes |
| --- | --- | --- | --- |
| `export_submit` | Export package submitted | `status` | No sensitive content stored |
| `export_approve` | Export package approved | `status` | No sensitive content stored |
| `export_reject` | Export package rejected | `status`, `note` | `note` redacted |
| `export_release` | Export package released | `status` | No sensitive content stored |
| `export_download` | Download of released export package | `status` | No sensitive content stored |
| `export_nr7_narrative` | ORT NR7 narrative payload generated | `download` | No sensitive content stored |
| `export_nr7_v2` | ORT NR7 v2 payload generated | `download` | No sensitive content stored |

## Snapshots & Review

| event_type | When it fires | Metadata keys | Sensitivity notes |
| --- | --- | --- | --- |
| `snapshot_view` | Snapshot detail view | `instance_uuid`, `counts` | No sensitive content stored |
| `snapshot_download` | Snapshot JSON download | `instance_uuid` | No sensitive content stored |
| `snapshot_diff` | Snapshot diff view | `instance_uuid`, `snapshot_a`, `snapshot_b` | No sensitive content stored |

## Sensitive Access

These events are emitted when sensitive/consent-gated objects are viewed (detail or list). The `action` metadata describes the context (for example: `view`, `list`, `api_view`, `api_list`).

| event_type | When it fires | Metadata keys | Sensitivity notes |
| --- | --- | --- | --- |
| `admin_view` | SystemAdmin views non-sensitive object | `action`, `sensitive`, `consent_required` | No sensitive content stored |
| `admin_view_sensitive` | SystemAdmin views sensitive or consent-gated object | `action`, `sensitive`, `consent_required` | No sensitive content stored |
| `view_sensitive` | Non-admin views sensitive/consent-gated object (when permitted) | `action`, `sensitive`, `consent_required` | No sensitive content stored |
