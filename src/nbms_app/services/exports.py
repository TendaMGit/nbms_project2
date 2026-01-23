from django.conf import settings
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
    ReportSectionResponse,
    ReportSectionTemplate,
    SensitivityLevel,
)
from nbms_app.services.audit import record_audit_event
from nbms_app.services.authorization import ROLE_DATA_STEWARD, ROLE_SECRETARIAT, user_has_role
from nbms_app.services.consent import consent_is_granted
from nbms_app.services.instance_approvals import approved_queryset
from nbms_app.services.metrics import inc_counter
from nbms_app.services.notifications import create_notification
from nbms_app.services.readiness import compute_reporting_readiness, get_instance_readiness


def _is_admin(user):
    return bool(user and (getattr(user, "is_superuser", False) or getattr(user, "is_staff", False)))


def assert_instance_exportable(instance, user):
    if not instance:
        raise ValidationError("Reporting instance is required for exports.")
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")

    readiness = get_instance_readiness(instance, user)
    blockers = readiness.get("blockers", [])
    if blockers:
        messages = "; ".join(blocker.get("message", "") for blocker in blockers if blocker)
        raise ValidationError(messages or "Export blocked by readiness checks.")

    readiness_report = compute_reporting_readiness(instance.uuid, scope="selected", user=user)
    summary = readiness_report.get("summary", {})
    if getattr(settings, "EXPORT_REQUIRE_READINESS", False) and not summary.get("overall_ready", True):
        top_blockers = readiness_report.get("diagnostics", {}).get("top_blockers", [])
        codes = ", ".join(item.get("code", "") for item in top_blockers if item.get("code"))
        raise ValidationError(f"Reporting readiness blockers: {codes or 'unknown blockers'}")
    readiness.setdefault("details", {})["readiness_report"] = readiness_report

    approvals = readiness.get("details", {}).get("approvals", {})
    pending = sum(item.get("pending", 0) for item in approvals.values())
    if pending:
        raise ValidationError("Missing instance approvals for one or more published items.")

    return readiness


def _require_status(obj, *allowed_statuses):
    if obj.status not in allowed_statuses:
        raise ValidationError("Invalid export status transition.")


def _require_reviewer(user):
    if not user_has_role(user, ROLE_DATA_STEWARD, ROLE_SECRETARIAT) and not _is_admin(user):
        raise PermissionDenied("Not allowed to review exports.")


def build_export_payload(instance):
    if not instance:
        raise ValidationError("Reporting instance is required for exports.")
    now_iso = timezone.now().isoformat()
    templates = ReportSectionTemplate.objects.filter(is_active=True).order_by("ordering", "code")
    responses = ReportSectionResponse.objects.filter(reporting_instance=instance, template__in=templates).select_related(
        "template",
        "updated_by",
    )
    response_map = {resp.template_id: resp for resp in responses}
    sections = []
    missing_required_sections = []
    for template in templates:
        response = response_map.get(template.id)
        is_required = bool((template.schema_json or {}).get("required", False))
        if is_required and not response:
            missing_required_sections.append(template.code)
        sections.append(
            {
                "code": template.code,
                "title": template.title,
                "required": is_required,
                "response": response.response_json if response else {},
                "updated_at": response.updated_at.isoformat() if response else None,
                "updated_by": response.updated_by.username if response and response.updated_by else None,
            }
        )
    targets = approved_queryset(instance, NationalTarget).filter(
        status=LifecycleStatus.PUBLISHED,
    ).order_by("code")
    indicators = approved_queryset(instance, Indicator).filter(
        status=LifecycleStatus.PUBLISHED,
    ).order_by("code")
    evidence_items = approved_queryset(instance, Evidence).filter(
        status=LifecycleStatus.PUBLISHED,
    ).order_by("title")
    datasets = approved_queryset(instance, Dataset).filter(
        status=LifecycleStatus.PUBLISHED,
    ).order_by("title")
    releases = approved_queryset(instance, DatasetRelease).filter(
        status=LifecycleStatus.PUBLISHED,
    ).order_by("created_at")

    return {
        "version": "0.1",
        "generated_at": now_iso,
        "reporting_instance": {
            "uuid": str(instance.uuid),
            "cycle_code": instance.cycle.code,
            "cycle_title": instance.cycle.title,
            "version_label": instance.version_label,
            "status": instance.status,
            "frozen_at": instance.frozen_at.isoformat() if instance.frozen_at else None,
        },
        "sections": sections,
        "missing_required_sections": missing_required_sections,
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


def _validate_consents(instance):
    missing = []
    checks = [
        (NationalTarget, "code"),
        (Indicator, "code"),
        (Evidence, "title"),
        (Dataset, "title"),
        (DatasetRelease, "version"),
    ]
    for model, label_attr in checks:
        queryset = approved_queryset(instance, model).filter(
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.IPLC_SENSITIVE,
        )
        for obj in queryset:
            if not consent_is_granted(instance, obj):
                label = getattr(obj, label_attr, None) or str(obj.uuid)
                missing.append(f"{model.__name__}:{label}")
    if missing:
        raise ValidationError(f"Missing consent for: {', '.join(missing)}")


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
    if not package.reporting_instance:
        raise ValidationError("Reporting instance is required to release exports.")
    _validate_consents(package.reporting_instance)
    readiness_report = compute_reporting_readiness(
        package.reporting_instance.uuid,
        scope="selected",
        user=user,
    )
    summary = readiness_report.get("summary", {})
    if getattr(settings, "EXPORT_REQUIRE_READINESS", False) and not summary.get("overall_ready", True):
        top_blockers = readiness_report.get("diagnostics", {}).get("top_blockers", [])
        codes = ", ".join(item.get("code", "") for item in top_blockers if item.get("code"))
        raise ValidationError(f"Reporting readiness blockers: {codes or 'unknown blockers'}")
    payload = build_export_payload(package.reporting_instance)
    if not getattr(settings, "EXPORT_REQUIRE_READINESS", False):
        payload["readiness_report"] = readiness_report
        payload["readiness_summary"] = summary
    missing_sections = payload.get("missing_required_sections", [])
    if missing_sections and getattr(settings, "EXPORT_REQUIRE_SECTIONS", False):
        raise ValidationError(f"Missing required sections: {', '.join(missing_sections)}")
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
