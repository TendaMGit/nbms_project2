from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from nbms_app.models import (
    ApprovalDecision,
    Dataset,
    DatasetRelease,
    Evidence,
    ExportStatus,
    Indicator,
    InstanceExportApproval,
    LifecycleStatus,
    NationalTarget,
    ReportSectionResponse,
    ReportSectionTemplate,
    SensitivityLevel,
)
from nbms_app.services.authorization import filter_queryset_for_user
from nbms_app.services.consent import consent_is_granted, requires_consent


def _readiness_result(blockers, warnings, details):
    return {
        "ok": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "details": details,
    }


def _blocker(code, message, count=None):
    data = {"code": code, "message": message}
    if count is not None:
        data["count"] = count
    return data


def _warning(code, message, count=None):
    data = {"code": code, "message": message}
    if count is not None:
        data["count"] = count
    return data


def _visible_queryset(model, user):
    return filter_queryset_for_user(
        model.objects.select_related("organisation", "created_by"),
        user,
    )


def _approved_ids(instance, model):
    content_type = ContentType.objects.get_for_model(model)
    return InstanceExportApproval.objects.filter(
        reporting_instance=instance,
        content_type=content_type,
        approval_scope="export",
        decision=ApprovalDecision.APPROVED,
    ).values_list("object_uuid", flat=True)


def _approval_counts(instance, model, user):
    visible = _visible_queryset(model, user)
    approved = visible.filter(uuid__in=_approved_ids(instance, model))
    total = visible.count()
    approved_count = approved.count()
    return {"total": total, "approved": approved_count, "pending": max(0, total - approved_count)}


def _consent_missing(instance, model, user):
    visible = _visible_queryset(model, user)
    approved_visible = visible.filter(
        uuid__in=_approved_ids(instance, model),
        sensitivity=SensitivityLevel.IPLC_SENSITIVE,
    )
    missing = 0
    for obj in approved_visible:
        if not consent_is_granted(instance, obj):
            missing += 1
    return {"total": approved_visible.count(), "missing": missing}


def _section_state(instance):
    templates = ReportSectionTemplate.objects.filter(is_active=True).order_by("ordering", "code")
    responses = ReportSectionResponse.objects.filter(
        reporting_instance=instance,
        template__in=templates,
    ).select_related("template", "updated_by")
    response_map = {resp.template_id: resp for resp in responses}
    sections = []
    missing_required = []
    for template in templates:
        response = response_map.get(template.id)
        required = bool((template.schema_json or {}).get("required", False))
        complete = bool(response and response.response_json)
        if required and not complete:
            missing_required.append(template.code)
        sections.append(
            {
                "code": template.code,
                "title": template.title,
                "required": required,
                "complete": complete,
                "response": response,
            }
        )
    return {
        "sections": sections,
        "missing_required_sections": missing_required,
        "total": templates.count(),
    }


def get_instance_readiness(instance, user):
    blockers = []
    warnings = []
    section_state = _section_state(instance)
    missing_required = section_state["missing_required_sections"]
    if missing_required:
        message = f"Missing required sections: {', '.join(missing_required)}"
        if settings.EXPORT_REQUIRE_SECTIONS:
            blockers.append(_blocker("sections_missing", message, count=len(missing_required)))
        else:
            warnings.append(_warning("sections_missing", message, count=len(missing_required)))
    if section_state["total"] == 0:
        warnings.append(_warning("sections_none", "No active section templates configured."))

    approvals = {
        "indicators": _approval_counts(instance, Indicator, user),
        "targets": _approval_counts(instance, NationalTarget, user),
        "evidence": _approval_counts(instance, Evidence, user),
        "datasets": _approval_counts(instance, Dataset, user),
    }
    for key, counts in approvals.items():
        if counts["pending"]:
            warnings.append(_warning(f"{key}_pending", f"{counts['pending']} {key} pending approval."))

    consent = {
        "indicators": _consent_missing(instance, Indicator, user),
        "targets": _consent_missing(instance, NationalTarget, user),
        "evidence": _consent_missing(instance, Evidence, user),
        "datasets": _consent_missing(instance, Dataset, user),
    }
    missing_consent = sum(item["missing"] for item in consent.values())
    if missing_consent:
        blockers.append(_blocker("consent_missing", "Missing consent for approved IPLC records.", count=missing_consent))

    details = {
        "sections": section_state,
        "approvals": approvals,
        "consent": consent,
        "export_require_sections": settings.EXPORT_REQUIRE_SECTIONS,
    }
    return _readiness_result(blockers, warnings, details)


def _object_base_readiness(obj, instance=None):
    blockers = []
    warnings = []
    if getattr(obj, "status", None) != LifecycleStatus.PUBLISHED:
        blockers.append(_blocker("not_published", "Status is not published."))
    if instance:
        if not InstanceExportApproval.objects.filter(
            reporting_instance=instance,
            content_type=ContentType.objects.get_for_model(obj.__class__),
            object_uuid=obj.uuid,
            approval_scope="export",
            decision=ApprovalDecision.APPROVED,
        ).exists():
            blockers.append(_blocker("not_approved", "Not approved for the current reporting instance."))
        if requires_consent(obj) and not consent_is_granted(instance, obj):
            blockers.append(_blocker("consent_required", "Consent required for IPLC-sensitive content."))
    elif requires_consent(obj):
        warnings.append(_warning("consent_required", "Consent required for IPLC-sensitive content."))
    return blockers, warnings


def get_indicator_readiness(indicator, user, instance=None):
    blockers, warnings = _object_base_readiness(indicator, instance=instance)
    details = {"status": indicator.status, "sensitivity": indicator.sensitivity}
    return _readiness_result(blockers, warnings, details)


def get_target_readiness(target, user, instance=None):
    blockers, warnings = _object_base_readiness(target, instance=instance)
    details = {"status": target.status, "sensitivity": target.sensitivity}
    return _readiness_result(blockers, warnings, details)


def get_evidence_readiness(evidence, user, instance=None):
    blockers, warnings = _object_base_readiness(evidence, instance=instance)
    if not evidence.file and not evidence.source_url:
        warnings.append(_warning("missing_source", "Evidence is missing a file or source URL."))
    details = {"status": evidence.status, "sensitivity": evidence.sensitivity}
    return _readiness_result(blockers, warnings, details)


def get_dataset_readiness(dataset, user, instance=None):
    blockers, warnings = _object_base_readiness(dataset, instance=instance)
    has_release = DatasetRelease.objects.filter(
        dataset=dataset,
        status=LifecycleStatus.PUBLISHED,
    ).exists()
    if not has_release:
        warnings.append(_warning("missing_release", "No published dataset release."))
    details = {"status": dataset.status, "sensitivity": dataset.sensitivity}
    return _readiness_result(blockers, warnings, details)


def get_export_package_readiness(pkg, user):
    blockers = []
    warnings = []
    if not pkg.reporting_instance:
        blockers.append(_blocker("missing_instance", "Reporting instance is required."))
        details = {"status": pkg.status, "instance": None}
        return _readiness_result(blockers, warnings, details)

    if pkg.status not in {ExportStatus.APPROVED, ExportStatus.RELEASED}:
        blockers.append(_blocker("not_approved", "Export package must be approved before release."))

    instance_readiness = get_instance_readiness(pkg.reporting_instance, user)
    if instance_readiness["blockers"]:
        for blocker in instance_readiness["blockers"]:
            blockers.append(blocker)

    details = {
        "status": pkg.status,
        "instance_uuid": str(pkg.reporting_instance.uuid),
        "instance_readiness": instance_readiness,
    }
    return _readiness_result(blockers, warnings, details)
