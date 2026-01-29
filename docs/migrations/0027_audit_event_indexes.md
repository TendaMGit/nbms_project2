# 0027 AuditEvent indexes

Adds indexes to support audit log filtering and retention:
- created_at
- (event_type, created_at)
- (actor, created_at)
- (content_type, object_id)

No data migration.
