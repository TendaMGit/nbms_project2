from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

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
from nbms_app.services.consent import consent_is_granted, consent_status_for_instance, requires_consent


def _readiness_result(blockers, warnings, details, checks=None, counts=None):
    return {
        "ok": not blockers,
        "status": _status_from(blockers, warnings),
        "blockers": blockers,
        "warnings": warnings,
        "checks": checks or [],
        "counts": counts or {},
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


def _status_from(blockers, warnings):
    if blockers:
        return "red"
    if warnings:
        return "amber"
    return "green"


def _check(key, label, state, action_url=""):
    return {"key": key, "label": label, "state": state, "action_url": action_url}


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
    visible = _visible_queryset(model, user).filter(status=LifecycleStatus.PUBLISHED)
    approved = visible.filter(uuid__in=_approved_ids(instance, model))
    total = visible.count()
    approved_count = approved.count()
    return {"total": total, "approved": approved_count, "pending": max(0, total - approved_count)}


def _consent_missing(instance, model, user):
    visible = _visible_queryset(model, user).filter(status=LifecycleStatus.PUBLISHED)
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
    incomplete_required = []
    for template in templates:
        response = response_map.get(template.id)
        schema = template.schema_json or {}
        required_setting = schema.get("required", False)
        required = bool(required_setting)
        required_fields = [field.get("key") for field in schema.get("fields", []) if field.get("required")]
        if isinstance(required_setting, (list, tuple)):
            required_fields = list({*required_fields, *[key for key in required_setting if key]})
        response_json = response.response_json if response else {}
        has_any_content = any(str(value).strip() for value in response_json.values()) if response_json else False
        if required_fields:
            complete = all(str(response_json.get(key, "")).strip() for key in required_fields)
        else:
            complete = has_any_content

        if required and not response:
            missing_required.append(template.code)
        elif required and response and not complete:
            incomplete_required.append(template.code)

        if not response:
            state = "missing"
        elif complete:
            state = "completed"
        else:
            state = "draft"
        sections.append(
            {
                "code": template.code,
                "title": template.title,
                "required": required,
                "complete": complete,
                "state": state,
                "response": response,
            }
        )
    return {
        "sections": sections,
        "missing_required_sections": missing_required,
        "incomplete_required_sections": incomplete_required,
        "total": templates.count(),
    }


def _approval_status(instance, obj):
    content_type = ContentType.objects.get_for_model(obj.__class__)
    approval = InstanceExportApproval.objects.filter(
        reporting_instance=instance,
        content_type=content_type,
        object_uuid=obj.uuid,
        approval_scope="export",
    ).first()
    if not approval:
        return "not_approved"
    if approval.decision == ApprovalDecision.REVOKED:
        return "revoked"
    return "approved"


def _eligible_for_export(obj, instance):
    if getattr(obj, "status", None) != LifecycleStatus.PUBLISHED:
        return False
    if not instance:
        return False
    if _approval_status(instance, obj) != "approved":
        return False
    if requires_consent(obj) and not consent_is_granted(instance, obj):
        return False
    return True


def get_instance_readiness(instance, user):
    blockers = []
    warnings = []
    section_state = _section_state(instance)
    missing_required = section_state["missing_required_sections"]
    incomplete_required = section_state["incomplete_required_sections"]
    if missing_required:
        message = f"Missing required sections: {', '.join(missing_required)}"
        if settings.EXPORT_REQUIRE_SECTIONS:
            blockers.append(_blocker("sections_missing", message, count=len(missing_required)))
        else:
            warnings.append(_warning("sections_missing", message, count=len(missing_required)))
    if incomplete_required:
        warnings.append(
            _warning(
                "sections_incomplete",
                f"Incomplete required sections: {', '.join(incomplete_required)}",
                count=len(incomplete_required),
            )
        )
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

    section_state_label = "ok"
    if missing_required:
        section_state_label = "blocked" if settings.EXPORT_REQUIRE_SECTIONS else "missing"
    elif incomplete_required:
        section_state_label = "incomplete"

    checks = [
        _check(
            "sections",
            "Sections completeness",
            section_state_label,
            reverse("nbms_app:reporting_instance_sections", kwargs={"instance_uuid": instance.uuid}),
        ),
        _check(
            "approvals",
            "Approvals completeness",
            "incomplete" if any(item["pending"] for item in approvals.values()) else "ok",
            reverse("nbms_app:reporting_instance_approvals", kwargs={"instance_uuid": instance.uuid}),
        ),
        _check(
            "consent",
            "Consent readiness",
            "blocked" if missing_consent else "ok",
            reverse("nbms_app:reporting_instance_consent", kwargs={"instance_uuid": instance.uuid}),
        ),
        _check(
            "freeze",
            "Freeze state",
            "locked" if instance.frozen_at else "ok",
            reverse("nbms_app:reporting_instance_detail", kwargs={"instance_uuid": instance.uuid}),
        ),
    ]

    details = {
        "sections": section_state,
        "approvals": approvals,
        "consent": consent,
        "export_require_sections": settings.EXPORT_REQUIRE_SECTIONS,
        "frozen_at": instance.frozen_at,
        "frozen_by": instance.frozen_by,
    }
    counts = {
        "approvals": approvals,
        "missing_consents": missing_consent,
    }
    return _readiness_result(blockers, warnings, details, checks=checks, counts=counts)


def _object_base_readiness(obj, instance=None):
    blockers = []
    warnings = []
    if getattr(obj, "status", None) != LifecycleStatus.PUBLISHED:
        blockers.append(_blocker("not_published", "Status is not published."))
    if instance:
        approval_status = _approval_status(instance, obj)
        if approval_status != "approved":
            blockers.append(_blocker("not_approved", "Not approved for the current reporting instance."))
        if requires_consent(obj) and not consent_is_granted(instance, obj):
            blockers.append(_blocker("consent_required", "Consent required for IPLC-sensitive content."))
    elif requires_consent(obj):
        warnings.append(_warning("consent_required", "Consent required for IPLC-sensitive content."))
    return blockers, warnings


def get_indicator_readiness(indicator, user, instance=None):
    blockers, warnings = _object_base_readiness(indicator, instance=instance)
    checks = []
    missing_fields = []
    for key, label in [
        ("code", "Code"),
        ("title", "Title"),
        ("national_target_id", "National target"),
        ("organisation_id", "Organisation"),
        ("created_by_id", "Created by"),
    ]:
        if not getattr(indicator, key, None):
            missing_fields.append(label)
    if missing_fields:
        warnings.append(_warning("missing_metadata", f"Missing required fields: {', '.join(missing_fields)}"))
    for label in ["Code", "Title", "National target", "Organisation", "Created by"]:
        state = "ok" if label not in missing_fields else "missing"
        checks.append(_check(f"field_{label.lower().replace(' ', '_')}", label, state))

    evidence_qs = Evidence.objects.filter(indicator_links__indicator=indicator).distinct()
    evidence_qs = filter_queryset_for_user(evidence_qs, user)
    dataset_qs = Dataset.objects.filter(indicator_links__indicator=indicator).distinct()
    dataset_qs = filter_queryset_for_user(dataset_qs, user)
    if evidence_qs.count() == 0:
        warnings.append(_warning("missing_evidence", "No linked evidence."))
    if dataset_qs.count() == 0:
        warnings.append(_warning("missing_dataset", "No linked datasets."))

    checks.append(
        _check("status", "Status", "ok" if indicator.status == LifecycleStatus.PUBLISHED else "incomplete")
    )
    checks.append(
        _check("evidence_links", "Evidence links", "ok" if evidence_qs.exists() else "missing")
    )
    checks.append(
        _check("dataset_links", "Dataset links", "ok" if dataset_qs.exists() else "missing")
    )

    approval_status = _approval_status(instance, indicator) if instance else None
    consent_status = consent_status_for_instance(instance, indicator) if instance else None
    eligible = _eligible_for_export(indicator, instance) if instance else False
    if instance:
        checks.extend(
            [
                _check("approval", "Instance approval", "ok" if approval_status == "approved" else "missing"),
                _check(
                    "consent",
                    "Consent",
                    "ok" if not requires_consent(indicator) or consent_status == "granted" else "missing",
                ),
            ]
        )
    details = {
        "status": indicator.status,
        "sensitivity": indicator.sensitivity,
        "review_note": indicator.review_note,
        "evidence_count": evidence_qs.count(),
        "dataset_count": dataset_qs.count(),
        "approval_status": approval_status,
        "consent_status": consent_status,
        "eligible_for_export": eligible,
    }
    counts = {"evidence": evidence_qs.count(), "datasets": dataset_qs.count()}
    return _readiness_result(blockers, warnings, details, checks=checks, counts=counts)


def get_target_readiness(target, user, instance=None):
    blockers, warnings = _object_base_readiness(target, instance=instance)
    missing_fields = []
    for key, label in [
        ("code", "Code"),
        ("title", "Title"),
        ("description", "Description"),
    ]:
        if not getattr(target, key, None):
            missing_fields.append(label)
    if missing_fields:
        warnings.append(_warning("missing_metadata", f"Missing required fields: {', '.join(missing_fields)}"))
    indicators_qs = Indicator.objects.filter(national_target=target).distinct()
    indicators_qs = filter_queryset_for_user(indicators_qs, user).filter(status=LifecycleStatus.PUBLISHED)
    published_indicator_count = indicators_qs.count()
    if published_indicator_count == 0:
        warnings.append(_warning("missing_indicators", "No published indicators linked to this target."))

    checks = []
    for label in ["Code", "Title", "Description"]:
        state = "ok" if label not in missing_fields else "missing"
        checks.append(_check(f"field_{label.lower()}", label, state))
    checks.append(
        _check(
            "linked_indicators",
            "Published indicators",
            "ok" if published_indicator_count else "missing",
        )
    )

    approval_status = _approval_status(instance, target) if instance else None
    indicators_approved = 0
    if instance:
        approved_ids = _approved_ids(instance, Indicator)
        indicators_approved = indicators_qs.filter(uuid__in=approved_ids).count()
        if approval_status == "approved" and indicators_approved == 0:
            warnings.append(_warning("approved_no_indicators", "Target approved but no indicators approved."))

    consent_status = consent_status_for_instance(instance, target) if instance else None
    eligible = _eligible_for_export(target, instance) if instance else False
    if instance:
        checks.extend(
            [
                _check("approval", "Instance approval", "ok" if approval_status == "approved" else "missing"),
                _check(
                    "consent",
                    "Consent",
                    "ok" if not requires_consent(target) or consent_status == "granted" else "missing",
                ),
            ]
        )
    details = {
        "status": target.status,
        "sensitivity": target.sensitivity,
        "review_note": target.review_note,
        "published_indicator_count": published_indicator_count,
        "approved_indicator_count": indicators_approved,
        "approval_status": approval_status,
        "consent_status": consent_status,
        "eligible_for_export": eligible,
    }
    counts = {
        "indicators_published": published_indicator_count,
        "indicators_approved": indicators_approved,
    }
    return _readiness_result(blockers, warnings, details, checks=checks, counts=counts)


def get_evidence_readiness(evidence, user, instance=None):
    blockers, warnings = _object_base_readiness(evidence, instance=instance)
    checks = []
    if not evidence.title:
        warnings.append(_warning("missing_title", "Missing evidence title."))
    if not evidence.evidence_type:
        warnings.append(_warning("missing_type", "Missing evidence type."))
    if not evidence.file and not evidence.source_url:
        warnings.append(_warning("missing_source", "Evidence is missing a file or source URL."))
    checks.append(_check("title", "Title", "ok" if evidence.title else "missing"))
    checks.append(_check("type", "Type", "ok" if evidence.evidence_type else "missing"))
    checks.append(
        _check("source", "File or URL", "ok" if evidence.file or evidence.source_url else "missing")
    )
    approval_status = _approval_status(instance, evidence) if instance else None
    consent_status = consent_status_for_instance(instance, evidence) if instance else None
    eligible = _eligible_for_export(evidence, instance) if instance else False
    if instance:
        checks.extend(
            [
                _check("approval", "Instance approval", "ok" if approval_status == "approved" else "missing"),
                _check(
                    "consent",
                    "Consent",
                    "ok" if not requires_consent(evidence) or consent_status == "granted" else "missing",
                ),
            ]
        )
    details = {
        "status": evidence.status,
        "sensitivity": evidence.sensitivity,
        "review_note": evidence.review_note,
        "approval_status": approval_status,
        "consent_status": consent_status,
        "eligible_for_export": eligible,
    }
    return _readiness_result(blockers, warnings, details, checks=checks)


def get_dataset_readiness(dataset, user, instance=None):
    blockers, warnings = _object_base_readiness(dataset, instance=instance)
    checks = []
    if not dataset.title:
        warnings.append(_warning("missing_title", "Missing dataset title."))
    if not dataset.methodology:
        warnings.append(_warning("missing_methodology", "Missing methodology."))
    if not dataset.source_url:
        warnings.append(_warning("missing_source", "Missing source URL."))
    has_release = DatasetRelease.objects.filter(
        dataset=dataset,
        status=LifecycleStatus.PUBLISHED,
    ).exists()
    if not has_release:
        warnings.append(_warning("missing_release", "No published dataset release."))
    checks.append(_check("title", "Title", "ok" if dataset.title else "missing"))
    checks.append(_check("methodology", "Methodology", "ok" if dataset.methodology else "missing"))
    checks.append(_check("source", "Source URL", "ok" if dataset.source_url else "missing"))
    checks.append(_check("release", "Published release", "ok" if has_release else "missing"))

    approval_status = _approval_status(instance, dataset) if instance else None
    consent_status = consent_status_for_instance(instance, dataset) if instance else None
    eligible = _eligible_for_export(dataset, instance) if instance else False
    if instance:
        checks.extend(
            [
                _check("approval", "Instance approval", "ok" if approval_status == "approved" else "missing"),
                _check(
                    "consent",
                    "Consent",
                    "ok" if not requires_consent(dataset) or consent_status == "granted" else "missing",
                ),
            ]
        )
    linked_indicators = Indicator.objects.filter(dataset_links__dataset=dataset).distinct()
    linked_indicators = filter_queryset_for_user(linked_indicators, user)
    approved_linked_indicators = 0
    if instance:
        approved_linked_indicators = linked_indicators.filter(
            status=LifecycleStatus.PUBLISHED,
            uuid__in=_approved_ids(instance, Indicator),
        ).count()
    linked_indicator_codes = list(linked_indicators.values_list("code", flat=True)[:5])
    details = {
        "status": dataset.status,
        "sensitivity": dataset.sensitivity,
        "review_note": dataset.review_note,
        "approval_status": approval_status,
        "consent_status": consent_status,
        "eligible_for_export": eligible,
        "linked_indicator_count": linked_indicators.count(),
        "linked_indicator_codes": linked_indicator_codes,
        "approved_linked_indicator_count": approved_linked_indicators,
    }
    counts = {
        "linked_indicators": linked_indicators.count(),
        "approved_linked_indicators": approved_linked_indicators,
    }
    return _readiness_result(blockers, warnings, details, checks=checks, counts=counts)


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

    approvals = instance_readiness["details"]["approvals"]
    total_approved = approvals["indicators"]["approved"] + approvals["targets"]["approved"]
    if total_approved == 0:
        warnings.append(_warning("low_coverage", "No approved indicators or targets for this instance."))

    missing_required_sections = instance_readiness["details"]["sections"]["missing_required_sections"]
    section_check_state = "ok"
    if missing_required_sections:
        section_check_state = "blocked" if settings.EXPORT_REQUIRE_SECTIONS else "missing"

    checks = [
        _check(
            "instance",
            "Instance linked",
            "ok",
            reverse("nbms_app:reporting_instance_detail", kwargs={"instance_uuid": pkg.reporting_instance.uuid}),
        ),
        _check(
            "sections",
            "Sections complete",
            section_check_state,
            reverse("nbms_app:reporting_instance_sections", kwargs={"instance_uuid": pkg.reporting_instance.uuid}),
        ),
        _check(
            "consent",
            "Consent ready",
            "blocked" if instance_readiness["counts"]["missing_consents"] else "ok",
            reverse("nbms_app:reporting_instance_consent", kwargs={"instance_uuid": pkg.reporting_instance.uuid}),
        ),
        _check(
            "coverage",
            "Approved indicators/targets",
            "ok" if total_approved else "missing",
            reverse("nbms_app:reporting_instance_approvals", kwargs={"instance_uuid": pkg.reporting_instance.uuid}),
        ),
    ]

    details = {
        "status": pkg.status,
        "instance_uuid": str(pkg.reporting_instance.uuid),
        "instance_readiness": instance_readiness,
    }
    counts = {
        "approved_indicators": approvals["indicators"]["approved"],
        "approved_targets": approvals["targets"]["approved"],
        "approved_evidence": approvals["evidence"]["approved"],
        "approved_datasets": approvals["datasets"]["approved"],
    }
    return _readiness_result(blockers, warnings, details, checks=checks, counts=counts)
