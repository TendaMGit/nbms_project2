from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from nbms_app.models import (
    Dataset,
    DatasetRelease,
    Evidence,
    ExportPackage,
    ExportStatus,
    Indicator,
    LifecycleStatus,
    NationalTarget,
)
from nbms_app.services.audit import record_audit_event
from nbms_app.services.authorization import ROLE_DATA_STEWARD, ROLE_SECRETARIAT, user_has_role
from nbms_app.services.metrics import inc_counter
from nbms_app.services.notifications import create_notification


def _is_admin(user):
    return bool(user and (getattr(user, "is_superuser", False) or getattr(user, "is_staff", False)))


def _require_status(obj, *allowed_statuses):
    if obj.status not in allowed_statuses:
        raise ValidationError("Invalid export status transition.")


def _require_reviewer(user):
    if not user_has_role(user, ROLE_DATA_STEWARD, ROLE_SECRETARIAT) and not _is_admin(user):
        raise PermissionDenied("Not allowed to review exports.")


def build_export_payload():
    now_iso = timezone.now().isoformat()
    targets = NationalTarget.objects.filter(
        status=LifecycleStatus.PUBLISHED,
        export_approved=True,
    ).order_by("code")
    indicators = Indicator.objects.filter(
        status=LifecycleStatus.PUBLISHED,
        export_approved=True,
    ).order_by("code")
    evidence_items = Evidence.objects.filter(
        status=LifecycleStatus.PUBLISHED,
        export_approved=True,
    ).order_by("title")
    datasets = Dataset.objects.filter(
        status=LifecycleStatus.PUBLISHED,
        export_approved=True,
    ).order_by("title")
    releases = DatasetRelease.objects.filter(
        status=LifecycleStatus.PUBLISHED,
        export_approved=True,
    ).order_by("created_at")

    return {
        "version": "0.1",
        "generated_at": now_iso,
        "targets": [
            {"uuid": str(target.uuid), "code": target.code, "title": target.title}
            for target in targets
        ],
        "indicators": [
            {
                "uuid": str(indicator.uuid),
                "code": indicator.code,
                "title": indicator.title,
                "national_target_uuid": str(indicator.national_target.uuid),
            }
            for indicator in indicators
        ],
        "evidence": [
            {
                "uuid": str(evidence.uuid),
                "title": evidence.title,
                "evidence_type": evidence.evidence_type,
                "source_url": evidence.source_url,
            }
            for evidence in evidence_items
        ],
        "datasets": [
            {
                "uuid": str(dataset.uuid),
                "title": dataset.title,
                "description": dataset.description,
                "methodology": dataset.methodology,
                "source_url": dataset.source_url,
            }
            for dataset in datasets
        ],
        "dataset_releases": [
            {
                "uuid": str(release.uuid),
                "dataset_uuid": str(release.dataset.uuid),
                "version": release.version,
                "release_date": release.release_date.isoformat() if release.release_date else "",
                "snapshot_title": release.snapshot_title,
            }
            for release in releases
        ],
    }


def submit_export_for_review(package, user):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    if not (package.created_by_id == user.id or user_has_role(user, ROLE_SECRETARIAT) or _is_admin(user)):
        raise PermissionDenied("Not allowed to submit exports for review.")

    _require_status(package, ExportStatus.DRAFT)
    package.status = ExportStatus.PENDING_REVIEW
    package.review_note = ""
    package.save(update_fields=["status", "review_note"])
    record_audit_event(user, "export_submit", package, metadata={"status": package.status})
    inc_counter(
        "workflow_transitions_total",
        labels={"action": "export_submit", "object_type": package.__class__.__name__},
    )
    create_notification(
        getattr(package, "created_by", None),
        f"Export package submitted for review: {package.title}",
        url="",
    )
    return package


def approve_export(package, user, note=""):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    _require_reviewer(user)

    _require_status(package, ExportStatus.PENDING_REVIEW)
    package.status = ExportStatus.APPROVED
    package.review_note = note or ""
    package.save(update_fields=["status", "review_note"])
    record_audit_event(user, "export_approve", package, metadata={"status": package.status})
    inc_counter(
        "workflow_transitions_total",
        labels={"action": "export_approve", "object_type": package.__class__.__name__},
    )
    create_notification(
        getattr(package, "created_by", None),
        f"Export package approved: {package.title}",
        url="",
    )
    return package


def reject_export(package, user, note):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    _require_reviewer(user)
    if not note:
        raise ValidationError("Rejection note is required.")

    _require_status(package, ExportStatus.PENDING_REVIEW)
    package.status = ExportStatus.DRAFT
    package.review_note = note
    package.save(update_fields=["status", "review_note"])
    record_audit_event(user, "export_reject", package, metadata={"status": package.status, "note": note})
    inc_counter(
        "workflow_transitions_total",
        labels={"action": "export_reject", "object_type": package.__class__.__name__},
    )
    create_notification(
        getattr(package, "created_by", None),
        f"Export package rejected: {package.title}",
        url="",
    )
    return package


def release_export(package, user):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    if not (user_has_role(user, ROLE_SECRETARIAT) or _is_admin(user)):
        raise PermissionDenied("Not allowed to release exports.")

    _require_status(package, ExportStatus.APPROVED)
    payload = build_export_payload()
    now = timezone.now()
    package.status = ExportStatus.RELEASED
    package.payload = payload
    package.generated_at = now
    package.released_at = now
    package.save(update_fields=["status", "payload", "generated_at", "released_at"])
    record_audit_event(user, "export_release", package, metadata={"status": package.status})
    inc_counter(
        "workflow_transitions_total",
        labels={"action": "export_release", "object_type": package.__class__.__name__},
    )
    create_notification(
        getattr(package, "created_by", None),
        f"Export package released: {package.title}",
        url="",
    )
    return package
