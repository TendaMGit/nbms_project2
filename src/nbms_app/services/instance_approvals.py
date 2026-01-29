from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from nbms_app.models import ApprovalDecision, InstanceExportApproval
from nbms_app.services.authorization import ROLE_ADMIN, ROLE_DATA_STEWARD, ROLE_SECRETARIAT, is_system_admin, user_has_role
from nbms_app.services.audit import record_audit_event, suppress_audit_events
from nbms_app.services.consent import consent_is_granted, requires_consent
from nbms_app.services.notifications import create_notification


def _is_admin(user):
    return bool(user and (is_system_admin(user) or user_has_role(user, ROLE_ADMIN)))


def can_approve_instance(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if _is_admin(user):
        return True
    return user_has_role(user, ROLE_DATA_STEWARD, ROLE_SECRETARIAT)


def approve_for_instance(instance, obj, user, note="", scope="export", admin_override=False):
    if not can_approve_instance(user):
        raise PermissionDenied("Not allowed to approve for export.")
    if instance.frozen_at and not (_is_admin(user) and admin_override):
        raise PermissionDenied("Reporting instance is frozen.")
    if requires_consent(obj) and not (consent_is_granted(instance, obj) or (_is_admin(user) and admin_override)):
        record_audit_event(
            user,
            "instance_export_blocked_consent",
            obj,
            metadata={"instance_uuid": str(instance.uuid)},
        )
        create_notification(
            user,
            f"Approval blocked: consent required for {obj.__class__.__name__} {getattr(obj, 'code', None) or getattr(obj, 'title', '')}",
            url="",
        )
        raise PermissionDenied("Consent required before export approval.")

    content_type = ContentType.objects.get_for_model(obj.__class__)
    with suppress_audit_events():
        approval, _ = InstanceExportApproval.objects.update_or_create(
            reporting_instance=instance,
            content_type=content_type,
            object_uuid=obj.uuid,
            approval_scope=scope,
            defaults={
                "decision": ApprovalDecision.APPROVED,
                "approved_by": user,
                "approved_at": timezone.now(),
                "decision_note": note or "",
            },
        )
    record_audit_event(
        user,
        "instance_export_approve",
        obj,
        metadata={
            "instance_uuid": str(instance.uuid),
            "decision": ApprovalDecision.APPROVED,
            "scope": scope,
            "admin_override": bool(admin_override),
        },
    )
    return approval


def bulk_approve_for_instance(
    instance,
    queryset,
    user,
    note="",
    scope="export",
    admin_override=False,
    skip_missing_consent=True,
):
    approved = []
    skipped = []
    for obj in queryset:
        if requires_consent(obj) and not consent_is_granted(instance, obj):
            if skip_missing_consent:
                skipped.append(obj)
                continue
        approval = approve_for_instance(
            instance,
            obj,
            user,
            note=note,
            scope=scope,
            admin_override=admin_override,
        )
        approved.append((obj, approval))
    return {"approved": approved, "skipped": skipped}


def revoke_for_instance(instance, obj, user, note="", scope="export", admin_override=False):
    if not can_approve_instance(user):
        raise PermissionDenied("Not allowed to revoke export approval.")
    if instance.frozen_at and not (_is_admin(user) and admin_override):
        raise PermissionDenied("Reporting instance is frozen.")

    content_type = ContentType.objects.get_for_model(obj.__class__)
    with suppress_audit_events():
        approval, _ = InstanceExportApproval.objects.update_or_create(
            reporting_instance=instance,
            content_type=content_type,
            object_uuid=obj.uuid,
            approval_scope=scope,
            defaults={
                "decision": ApprovalDecision.REVOKED,
                "approved_by": user,
                "approved_at": timezone.now(),
                "decision_note": note or "",
            },
        )
    record_audit_event(
        user,
        "instance_export_revoke",
        obj,
        metadata={
            "instance_uuid": str(instance.uuid),
            "decision": ApprovalDecision.REVOKED,
            "scope": scope,
            "admin_override": bool(admin_override),
        },
    )
    return approval


def bulk_revoke_for_instance(instance, queryset, user, note="", scope="export", admin_override=False):
    revoked = []
    for obj in queryset:
        approval = revoke_for_instance(
            instance,
            obj,
            user,
            note=note,
            scope=scope,
            admin_override=admin_override,
        )
        revoked.append((obj, approval))
    return revoked


def is_approved_for_instance(instance, obj, scope="export"):
    content_type = ContentType.objects.get_for_model(obj.__class__)
    return InstanceExportApproval.objects.filter(
        reporting_instance=instance,
        content_type=content_type,
        object_uuid=obj.uuid,
        approval_scope=scope,
        decision=ApprovalDecision.APPROVED,
    ).exists()


def approved_queryset(instance, model, scope="export"):
    content_type = ContentType.objects.get_for_model(model)
    approved_ids = InstanceExportApproval.objects.filter(
        reporting_instance=instance,
        content_type=content_type,
        approval_scope=scope,
        decision=ApprovalDecision.APPROVED,
    ).values_list("object_uuid", flat=True)
    return model.objects.filter(uuid__in=approved_ids)
