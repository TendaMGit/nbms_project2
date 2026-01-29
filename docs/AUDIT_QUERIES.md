# Audit Query Examples

Use these snippets in `python manage.py shell` to inspect audit events.

```python
from nbms_app.models import AuditEvent

# 1) Events for a specific object UUID
obj_uuid = "<uuid-here>"
AuditEvent.objects.filter(object_uuid=obj_uuid).order_by("-created_at")[:50]

# 2) SystemAdmin sensitive views
AuditEvent.objects.filter(event_type="admin_view_sensitive").order_by("-created_at")[:50]

# 3) Any sensitive views (admin + non-admin)
AuditEvent.objects.filter(event_type__in=["admin_view_sensitive", "view_sensitive"]).order_by("-created_at")[:50]

# 4) Export approvals
AuditEvent.objects.filter(event_type__in=["instance_export_approve", "instance_export_revoke"]).order_by("-created_at")[:50]

# 5) Export package lifecycle
AuditEvent.objects.filter(event_type__startswith="export_").order_by("-created_at")[:50]

# 6) Workflow transitions
AuditEvent.objects.filter(event_type__in=["submit_for_review", "approve", "reject", "publish", "archive"]).order_by("-created_at")[:50]
```

Note: `event_type` and `action` are aligned. Use either field for filtering based on your reporting needs.
