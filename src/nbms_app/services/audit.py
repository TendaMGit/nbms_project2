from nbms_app.models import AuditEvent


def record_audit_event(actor, action, obj, metadata=None):
    AuditEvent.objects.create(
        actor=actor,
        action=action,
        object_type=obj.__class__.__name__,
        object_uuid=obj.uuid,
        metadata=metadata or {},
    )
