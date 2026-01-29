from django.core.exceptions import ValidationError

from nbms_app.services.audit import record_event, suppress_audit_events
from nbms_app.services.workflows import archive as workflow_archive


def archive_object(user, obj, reason="", request=None):
    if hasattr(obj, "status"):
        workflow_archive(obj, user)
        if reason:
            record_event(
                user,
                "archive_reason",
                obj=obj,
                metadata={"reason": reason},
                request=request,
            )
        return obj
    if hasattr(obj, "is_active"):
        obj.is_active = False
        with suppress_audit_events():
            obj.save(update_fields=["is_active"])
        record_event(
            user,
            "archive",
            obj=obj,
            metadata={"reason": reason} if reason else {},
            request=request,
        )
        return obj
    raise ValidationError("Object does not support archiving.")


def reactivate_object(user, obj, reason="", request=None):
    if hasattr(obj, "status"):
        raise ValidationError("Status-based objects must be reactivated via workflow transitions.")
    if hasattr(obj, "is_active"):
        if obj.is_active:
            return obj
        obj.is_active = True
        with suppress_audit_events():
            obj.save(update_fields=["is_active"])
        record_event(
            user,
            "unarchive",
            obj=obj,
            metadata={"reason": reason} if reason else {},
            request=request,
        )
        return obj
    raise ValidationError("Object does not support reactivation.")
