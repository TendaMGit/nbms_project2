from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from nbms_app.models import ConsentRecord, ConsentStatus, SensitivityLevel
from nbms_app.services.audit import record_audit_event, suppress_audit_events
from nbms_app.services.notifications import create_notification


def requires_consent(obj):
    return getattr(obj, "sensitivity", None) == SensitivityLevel.IPLC_SENSITIVE or getattr(obj, "consent_required", False)


def consent_is_granted(instance, obj):
    content_type = ContentType.objects.get_for_model(obj.__class__)
    return ConsentRecord.objects.filter(
        content_type=content_type,
        object_uuid=obj.uuid,
        status=ConsentStatus.GRANTED,
        reporting_instance=instance,
    ).exists() or ConsentRecord.objects.filter(
        content_type=content_type,
        object_uuid=obj.uuid,
        status=ConsentStatus.GRANTED,
        reporting_instance__isnull=True,
    ).exists()


def consent_status_for_instance(instance, obj):
    content_type = ContentType.objects.get_for_model(obj.__class__)
    record = ConsentRecord.objects.filter(
        content_type=content_type,
        object_uuid=obj.uuid,
        reporting_instance=instance,
    ).first()
    if record:
        return record.status
    record = ConsentRecord.objects.filter(
        content_type=content_type,
        object_uuid=obj.uuid,
        reporting_instance__isnull=True,
    ).first()
    if record:
        return record.status
    return ConsentStatus.REQUIRED


def set_consent_status(instance, obj, user, status, note="", document=None):
    content_type = ContentType.objects.get_for_model(obj.__class__)
    with suppress_audit_events():
        record, _ = ConsentRecord.objects.update_or_create(
            content_type=content_type,
            object_uuid=obj.uuid,
            reporting_instance=instance,
            defaults={
                "status": status,
                "granted_by": user,
                "granted_at": timezone.now(),
                "notes": note or "",
                "consent_document": document,
            },
        )
    record_audit_event(
        user,
        f"consent_{status}",
        obj,
        metadata={"instance_uuid": str(instance.uuid) if instance else None, "status": status},
    )
    create_notification(
        getattr(obj, "created_by", None),
        f"Consent {status} for {obj.__class__.__name__}: {getattr(obj, 'code', None) or getattr(obj, 'title', '')}",
        url="",
    )
    return record
