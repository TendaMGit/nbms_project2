from django.core.exceptions import PermissionDenied, ValidationError

from nbms_app.models import LifecycleStatus
from nbms_app.services.audit import record_audit_event
from nbms_app.services.authorization import (
    ROLE_ADMIN,
    ROLE_DATA_STEWARD,
    ROLE_INDICATOR_LEAD,
    ROLE_SECRETARIAT,
    user_has_role,
)


def _is_admin(user):
    return bool(user and (getattr(user, "is_superuser", False) or user_has_role(user, ROLE_ADMIN)))


def _require_status(obj, *allowed_statuses):
    if obj.status not in allowed_statuses:
        raise ValidationError("Invalid status transition.")


def submit_for_review(obj, user):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    if not (obj.created_by_id == user.id or user_has_role(user, ROLE_INDICATOR_LEAD) or _is_admin(user)):
        raise PermissionDenied("Not allowed to submit for review.")

    _require_status(obj, LifecycleStatus.DRAFT)
    obj.status = LifecycleStatus.PENDING_REVIEW
    obj.review_note = ""
    obj.save(update_fields=["status", "review_note"])
    record_audit_event(user, "submit_for_review", obj, metadata={"status": obj.status})
    return obj


def approve(obj, user, note=""):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    if not (user_has_role(user, ROLE_DATA_STEWARD, ROLE_SECRETARIAT) or _is_admin(user)):
        raise PermissionDenied("Not allowed to approve.")

    _require_status(obj, LifecycleStatus.PENDING_REVIEW)
    obj.status = LifecycleStatus.APPROVED
    obj.review_note = note or ""
    obj.save(update_fields=["status", "review_note"])
    record_audit_event(user, "approve", obj, metadata={"status": obj.status, "note": obj.review_note})
    return obj


def reject(obj, user, note):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    if not (user_has_role(user, ROLE_DATA_STEWARD, ROLE_SECRETARIAT) or _is_admin(user)):
        raise PermissionDenied("Not allowed to reject.")
    if not note:
        raise ValidationError("Rejection note is required.")

    _require_status(obj, LifecycleStatus.PENDING_REVIEW)
    obj.status = LifecycleStatus.DRAFT
    obj.review_note = note
    obj.save(update_fields=["status", "review_note"])
    record_audit_event(user, "reject", obj, metadata={"status": obj.status, "note": obj.review_note})
    return obj


def publish(obj, user):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    if not (user_has_role(user, ROLE_SECRETARIAT) or _is_admin(user)):
        raise PermissionDenied("Not allowed to publish.")

    _require_status(obj, LifecycleStatus.APPROVED)
    obj.status = LifecycleStatus.PUBLISHED
    obj.save(update_fields=["status"])
    record_audit_event(user, "publish", obj, metadata={"status": obj.status})
    return obj


def archive(obj, user):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    if not (user_has_role(user, ROLE_SECRETARIAT) or _is_admin(user)):
        raise PermissionDenied("Not allowed to archive.")

    _require_status(obj, LifecycleStatus.PUBLISHED)
    obj.status = LifecycleStatus.ARCHIVED
    obj.save(update_fields=["status"])
    record_audit_event(user, "archive", obj, metadata={"status": obj.status})
    return obj
