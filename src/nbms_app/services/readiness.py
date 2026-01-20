from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nbms_app.models import (
    ApprovalDecision,
    Dataset,
    DatasetRelease,
    Evidence,
    ExportStatus,
    FrameworkTarget,
    Indicator,
    InstanceExportApproval,
    LifecycleStatus,
    NationalTarget,
    ReportSectionResponse,
    ReportSectionTemplate,
    SensitivityLevel,
    SectionIIINationalTargetProgress,
    SectionIVFrameworkTargetProgress,
    ValidationRuleSet,
    ValidationScope,
)
from nbms_app.services.authorization import filter_queryset_for_user
from nbms_app.services.consent import consent_is_granted, consent_status_for_instance, requires_consent
from nbms_app.services.section_progress import scoped_framework_targets, scoped_national_targets


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


def _load_validation_rules(instance=None):
    queryset = ValidationRuleSet.objects.filter(is_active=True).order_by("-created_at")
    if instance:
        instance_rule = queryset.filter(applies_to=ValidationScope.INSTANCE, code=str(instance.uuid)).first()
        if instance_rule:
            return instance_rule.rules_json or {}
        cycle_rule = queryset.filter(applies_to=ValidationScope.CYCLE, code=instance.cycle.code).first()
        if cycle_rule:
            return cycle_rule.rules_json or {}
    default_rule = queryset.filter(applies_to=ValidationScope.REPORT_TYPE, code="7NR_DEFAULT").first()
    if default_rule:
        return default_rule.rules_json or {}
    return {}


def _normalize_section_code(code):
    if not code:
        return ""
    trimmed = str(code).strip().lower()
    if trimmed.startswith("section-"):
        return trimmed
    roman_map = {
        "i": "section-i",
        "ii": "section-ii",
        "iii": "section-iii",
        "iv": "section-iv",
        "v": "section-v",
        "1": "section-i",
        "2": "section-ii",
        "3": "section-iii",
        "4": "section-iv",
        "5": "section-v",
    }
    return roman_map.get(trimmed, trimmed)


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


def _section_state(instance, rules):
    templates = ReportSectionTemplate.objects.filter(is_active=True).order_by("ordering", "code")
    responses = ReportSectionResponse.objects.filter(
        reporting_instance=instance,
        template__in=templates,
    ).select_related("template", "updated_by")
    response_map = {resp.template_id: resp for resp in responses}
    sections = []
    missing_required = []
    incomplete_required = []
    section_rules = (rules or {}).get("sections", {})
    required_codes = section_rules.get("required", [])
    required_codes = {_normalize_section_code(code) for code in (required_codes or []) if code}
    if not required_codes:
        required_codes = {
            template.code for template in templates if (template.schema_json or {}).get("required", False)
        }

    required_fields_map = {}
    for code, fields in (section_rules.get("required_fields", {}) or {}).items():
        required_fields_map[_normalize_section_code(code)] = fields or []

    for template in templates:
        response = response_map.get(template.id)
        schema = template.schema_json or {}
        required_setting = schema.get("required", False)
        required = template.code in required_codes
        required_fields = required_fields_map.get(template.code)
        if required_fields is None:
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
                "template": template,
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
        "required_section_codes": sorted(required_codes),
        "total": templates.count(),
    }


def _progress_state(instance, user, section_state):
    required_codes = set(section_state.get("required_section_codes", []))
    require_section_iii = "section-iii" in required_codes
    require_section_iv = "section-iv" in required_codes

    scoped_targets = scoped_national_targets(instance, user) if require_section_iii else NationalTarget.objects.none()
    scoped_fw_targets = scoped_framework_targets(instance, user) if require_section_iv else FrameworkTarget.objects.none()

    section_iii_total = scoped_targets.count()
    section_iv_total = scoped_fw_targets.count()

    section_iii_completed = 0
    if section_iii_total:
        section_iii_completed = (
            SectionIIINationalTargetProgress.objects.filter(
                reporting_instance=instance,
                national_target__in=scoped_targets,
            )
            .values_list("national_target_id", flat=True)
            .distinct()
            .count()
        )

    section_iv_completed = 0
    if section_iv_total:
        section_iv_completed = (
            SectionIVFrameworkTargetProgress.objects.filter(
                reporting_instance=instance,
                framework_target__in=scoped_fw_targets,
            )
            .values_list("framework_target_id", flat=True)
            .distinct()
            .count()
        )

    return {
        "require_section_iii": require_section_iii,
        "require_section_iv": require_section_iv,
        "section_iii_total": section_iii_total,
        "section_iii_completed": section_iii_completed,
        "section_iii_missing": max(0, section_iii_total - section_iii_completed),
        "section_iv_total": section_iv_total,
        "section_iv_completed": section_iv_completed,
        "section_iv_missing": max(0, section_iv_total - section_iv_completed),
    }


def _score_progress(progress_state):
    scores = []
    if progress_state["section_iii_total"]:
        scores.append(
            round(100 * progress_state["section_iii_completed"] / progress_state["section_iii_total"])
        )
    if progress_state["section_iv_total"]:
        scores.append(
            round(100 * progress_state["section_iv_completed"] / progress_state["section_iv_total"])
        )
    if not scores:
        return 100
    return round(sum(scores) / len(scores))


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


def _score_sections(section_state):
    required_sections = [section for section in section_state["sections"] if section.get("required")]
    if not required_sections:
        return 100
    scores = []
    for section in required_sections:
        if section["state"] == "missing":
            scores.append(0)
        elif section["state"] == "draft":
            scores.append(50)
        else:
            scores.append(100)
    return round(sum(scores) / len(scores))


def _score_approvals(approvals):
    scores = []
    for counts in approvals.values():
        if counts["total"] == 0:
            scores.append(0)
        else:
            scores.append(round(100 * counts["approved"] / counts["total"]))
    if not scores:
        return 100
    return round(sum(scores) / len(scores))


def _score_consent(consent):
    total = sum(item["total"] for item in consent.values())
    missing = sum(item["missing"] for item in consent.values())
    if total == 0:
        return 100
    return round(100 * (1 - (missing / total)))


def _score_publication_quality(instance, user):
    total = 0
    published = 0
    for model in (Indicator, NationalTarget, Evidence, Dataset):
        approved_ids = _approved_ids(instance, model)
        if not approved_ids:
            continue
        approved_qs = filter_queryset_for_user(model.objects.filter(uuid__in=approved_ids), user)
        total += approved_qs.count()
        published += approved_qs.filter(status=LifecycleStatus.PUBLISHED).count()
    if total == 0:
        return 100
    return round(100 * published / total)


def _metadata_complete(obj, required_fields, field_map):
    for field_key in required_fields:
        mapped = field_map.get(field_key, field_key)
        if mapped == "file":
            if not getattr(obj, "file", None) and not getattr(obj, "source_url", None):
                return False
            continue
        if mapped.endswith("_id"):
            if not getattr(obj, mapped, None):
                return False
            continue
        value = getattr(obj, mapped, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            return False
    return True


def _metadata_rules(rules, key, default):
    required_fields = (rules or {}).get(key, {}).get("required_fields", None)
    if required_fields is None:
        return default
    return required_fields


def _score_metadata(instance, user, rules):
    totals = 0
    complete = 0
    definitions = [
        (
            "indicator",
            Indicator,
            ["code", "title", "national_target", "organisation", "created_by"],
            {
                "national_target": "national_target_id",
                "organisation": "organisation_id",
                "created_by": "created_by_id",
                "name": "title",
            },
        ),
        (
            "target",
            NationalTarget,
            ["code", "title", "description", "organisation", "created_by"],
            {
                "organisation": "organisation_id",
                "created_by": "created_by_id",
                "name": "title",
            },
        ),
        (
            "evidence",
            Evidence,
            ["title", "evidence_type", "file"],
            {"source_url": "source_url"},
        ),
        (
            "dataset",
            Dataset,
            ["title", "methodology", "source_url"],
            {"organisation": "organisation_id", "created_by": "created_by_id"},
        ),
    ]
    for key, model, default_fields, field_map in definitions:
        required_fields = _metadata_rules(rules, key, default_fields)
        if not required_fields:
            continue
        queryset = filter_queryset_for_user(model.objects.all(), user).filter(status=LifecycleStatus.PUBLISHED)
        if not queryset.exists():
            continue
        for obj in queryset:
            totals += 1
            if _metadata_complete(obj, required_fields, field_map):
                complete += 1
    if totals == 0:
        return 100
    return round(100 * complete / totals)


def _build_action_queue(instance, user, readiness):
    items = []
    approvals = readiness["details"]["approvals"]
    consent = readiness["details"]["consent"]
    section_state = readiness["details"]["sections"]

    missing_required = section_state["missing_required_sections"]
    if missing_required:
        severity = "BLOCKER" if settings.EXPORT_REQUIRE_SECTIONS else "WARNING"
        items.append(
            {
                "severity": severity,
                "title": "Missing required sections",
                "details": ", ".join(missing_required),
                "count_affected": len(missing_required),
                "action_url": reverse("nbms_app:reporting_instance_sections", kwargs={"instance_uuid": instance.uuid}),
                "owner_hint": "Contributor",
            }
        )

    missing_consents = readiness["counts"]["missing_consents"]
    if missing_consents:
        items.append(
            {
                "severity": "BLOCKER",
                "title": "Missing IPLC consent",
                "details": "Consent required before export approval.",
                "count_affected": missing_consents,
                "action_url": reverse("nbms_app:reporting_instance_consent", kwargs={"instance_uuid": instance.uuid}),
                "owner_hint": "Community Representative",
            }
        )

    pending_count = sum(item["pending"] for item in approvals.values())
    if pending_count:
        items.append(
            {
                "severity": "WARNING",
                "title": "Pending approvals",
                "details": "Approved items required for export.",
                "count_affected": pending_count,
                "action_url": reverse("nbms_app:reporting_instance_approvals", kwargs={"instance_uuid": instance.uuid}),
                "owner_hint": "Data Steward",
            }
        )

    not_published_total = 0
    for model in (Indicator, NationalTarget, Evidence, Dataset):
        approved_ids = _approved_ids(instance, model)
        if not approved_ids:
            continue
        approved_qs = filter_queryset_for_user(model.objects.filter(uuid__in=approved_ids), user)
        not_published_total += approved_qs.exclude(status=LifecycleStatus.PUBLISHED).count()
    if not_published_total:
        items.append(
            {
                "severity": "BLOCKER",
                "title": "Approved items not published",
                "details": "Only published items are exportable.",
                "count_affected": not_published_total,
                "action_url": reverse("nbms_app:review_queue"),
                "owner_hint": "Secretariat",
            }
        )

    if instance.frozen_at:
        if missing_required or pending_count:
            items.append(
                {
                    "severity": "WARNING",
                    "title": "Instance frozen with gaps",
                    "details": "Unfreeze or use admin override to resolve items.",
                    "count_affected": pending_count + len(missing_required),
                    "action_url": reverse(
                        "nbms_app:reporting_instance_detail", kwargs={"instance_uuid": instance.uuid}
                    ),
                    "owner_hint": "Admin",
                }
            )
    else:
        items.append(
            {
                "severity": "WARNING",
                "title": "Instance not frozen",
                "details": "Freeze before releasing export packages.",
                "count_affected": 1,
                "action_url": reverse(
                    "nbms_app:reporting_instance_detail", kwargs={"instance_uuid": instance.uuid}
                ),
                "owner_hint": "Secretariat",
            }
        )

    severity_rank = {"BLOCKER": 0, "WARNING": 1}
    items.sort(key=lambda item: (severity_rank.get(item["severity"], 2), -item.get("count_affected", 0)))
    return items[:10]


def get_instance_readiness(instance, user):
    blockers = []
    warnings = []
    rules = _load_validation_rules(instance)
    section_state = _section_state(instance, rules)
    progress_state = _progress_state(instance, user, section_state)
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

    if progress_state["require_section_iii"] and progress_state["section_iii_missing"]:
        message = (
            f"Missing Section III progress entries for {progress_state['section_iii_missing']} "
            f"of {progress_state['section_iii_total']} scoped national targets."
        )
        if settings.EXPORT_REQUIRE_SECTIONS:
            blockers.append(
                _blocker(
                    "section_iii_progress_missing",
                    message,
                    count=progress_state["section_iii_missing"],
                )
            )
        else:
            warnings.append(
                _warning(
                    "section_iii_progress_missing",
                    message,
                    count=progress_state["section_iii_missing"],
                )
            )

    if progress_state["require_section_iv"] and progress_state["section_iv_missing"]:
        message = (
            f"Missing Section IV progress entries for {progress_state['section_iv_missing']} "
            f"of {progress_state['section_iv_total']} scoped framework targets."
        )
        if settings.EXPORT_REQUIRE_SECTIONS:
            blockers.append(
                _blocker(
                    "section_iv_progress_missing",
                    message,
                    count=progress_state["section_iv_missing"],
                )
            )
        else:
            warnings.append(
                _warning(
                    "section_iv_progress_missing",
                    message,
                    count=progress_state["section_iv_missing"],
                )
            )

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
            "section_iii_progress",
            "Section III progress entries",
            "ok" if not progress_state["section_iii_missing"] else "missing",
            reverse("nbms_app:reporting_instance_section_iii", kwargs={"instance_uuid": instance.uuid}),
        ),
        _check(
            "section_iv_progress",
            "Section IV progress entries",
            "ok" if not progress_state["section_iv_missing"] else "missing",
            reverse("nbms_app:reporting_instance_section_iv", kwargs={"instance_uuid": instance.uuid}),
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
        "progress": progress_state,
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
    result = _readiness_result(blockers, warnings, details, checks=checks, counts=counts)
    section_score = _score_sections(section_state)
    progress_score = _score_progress(progress_state)
    if progress_state["require_section_iii"] or progress_state["require_section_iv"]:
        section_score = round((section_score + progress_score) / 2)
    approvals_score = _score_approvals(approvals)
    consent_score = _score_consent(consent)
    publication_score = _score_publication_quality(instance, user)
    metadata_score = _score_metadata(instance, user, rules)
    weighted_score = round(
        (
            section_score * 30
            + approvals_score * 25
            + consent_score * 25
            + publication_score * 10
            + metadata_score * 10
        )
        / 100
    )
    if weighted_score >= 80:
        band = "green"
    elif weighted_score >= 50:
        band = "amber"
    else:
        band = "red"
    action_queue = _build_action_queue(instance, user, result)
    result.update(
        {
            "readiness_score": weighted_score,
            "readiness_band": band,
            "score_breakdown": [
                {"key": "sections", "label": "Sections completeness", "score": section_score, "weight": 30},
                {"key": "approvals", "label": "Approvals coverage", "score": approvals_score, "weight": 25},
                {"key": "consent", "label": "Consent clearance", "score": consent_score, "weight": 25},
                {"key": "publication", "label": "Publication quality", "score": publication_score, "weight": 10},
                {"key": "metadata", "label": "Metadata completeness", "score": metadata_score, "weight": 10},
            ],
            "action_queue": action_queue,
            "top_10_actions": action_queue,
        }
    )
    return result


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
    rules = _load_validation_rules(instance)
    blockers, warnings = _object_base_readiness(indicator, instance=instance)
    checks = []
    field_map = {
        "national_target": "national_target_id",
        "organisation": "organisation_id",
        "created_by": "created_by_id",
        "name": "title",
    }
    required_fields = _metadata_rules(
        rules,
        "indicator",
        ["code", "title", "national_target", "organisation", "created_by"],
    )
    missing_fields = []
    for field in required_fields:
        if not _metadata_complete(indicator, [field], field_map):
            missing_fields.append(field)
    if missing_fields:
        labels = [field.replace("_", " ").title() for field in missing_fields]
        warnings.append(_warning("missing_metadata", f"Missing required fields: {', '.join(labels)}"))
    for field in required_fields:
        label = field.replace("_", " ").title()
        if field == "national_target":
            label = "National target"
        state = "missing" if field in missing_fields else "ok"
        checks.append(_check(f"field_{field}", label, state))

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
        "consent_required": requires_consent(indicator),
        "eligible_for_export": eligible,
    }
    counts = {"evidence": evidence_qs.count(), "datasets": dataset_qs.count()}
    return _readiness_result(blockers, warnings, details, checks=checks, counts=counts)


def get_target_readiness(target, user, instance=None):
    rules = _load_validation_rules(instance)
    blockers, warnings = _object_base_readiness(target, instance=instance)
    field_map = {"organisation": "organisation_id", "created_by": "created_by_id", "name": "title"}
    required_fields = _metadata_rules(
        rules,
        "target",
        ["code", "title", "description", "organisation", "created_by"],
    )
    missing_fields = []
    for field in required_fields:
        if not _metadata_complete(target, [field], field_map):
            missing_fields.append(field)
    if missing_fields:
        labels = [field.replace("_", " ").title() for field in missing_fields]
        warnings.append(_warning("missing_metadata", f"Missing required fields: {', '.join(labels)}"))
    indicators_qs = Indicator.objects.filter(national_target=target).distinct()
    indicators_qs = filter_queryset_for_user(indicators_qs, user).filter(status=LifecycleStatus.PUBLISHED)
    published_indicator_count = indicators_qs.count()
    if published_indicator_count == 0:
        warnings.append(_warning("missing_indicators", "No published indicators linked to this target."))

    checks = []
    for field in required_fields:
        label = field.replace("_", " ").title()
        state = "missing" if field in missing_fields else "ok"
        checks.append(_check(f"field_{field}", label, state))
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
        "consent_required": requires_consent(target),
        "eligible_for_export": eligible,
    }
    counts = {
        "indicators_published": published_indicator_count,
        "indicators_approved": indicators_approved,
    }
    return _readiness_result(blockers, warnings, details, checks=checks, counts=counts)


def get_evidence_readiness(evidence, user, instance=None):
    rules = _load_validation_rules(instance)
    blockers, warnings = _object_base_readiness(evidence, instance=instance)
    checks = []
    field_map = {"file": "file", "source_url": "source_url"}
    required_fields = _metadata_rules(rules, "evidence", ["title", "evidence_type", "file"])
    missing_fields = []
    for field in required_fields:
        if not _metadata_complete(evidence, [field], field_map):
            missing_fields.append(field)
    if missing_fields:
        labels = [field.replace("_", " ").title() for field in missing_fields]
        warnings.append(_warning("missing_metadata", f"Missing required fields: {', '.join(labels)}"))
    for field in required_fields:
        label = field.replace("_", " ").title()
        state = "missing" if field in missing_fields else "ok"
        checks.append(_check(f"field_{field}", label, state))
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
        "consent_required": requires_consent(evidence),
        "eligible_for_export": eligible,
    }
    return _readiness_result(blockers, warnings, details, checks=checks)


def get_dataset_readiness(dataset, user, instance=None):
    rules = _load_validation_rules(instance)
    blockers, warnings = _object_base_readiness(dataset, instance=instance)
    checks = []
    field_map = {"organisation": "organisation_id", "created_by": "created_by_id"}
    required_fields = _metadata_rules(rules, "dataset", ["title", "methodology", "source_url"])
    missing_fields = []
    for field in required_fields:
        if not _metadata_complete(dataset, [field], field_map):
            missing_fields.append(field)
    if missing_fields:
        labels = [field.replace("_", " ").title() for field in missing_fields]
        warnings.append(_warning("missing_metadata", f"Missing required fields: {', '.join(labels)}"))
    has_release = DatasetRelease.objects.filter(
        dataset=dataset,
        status=LifecycleStatus.PUBLISHED,
    ).exists()
    if not has_release:
        warnings.append(_warning("missing_release", "No published dataset release."))
    for field in required_fields:
        label = field.replace("_", " ").title()
        state = "missing" if field in missing_fields else "ok"
        checks.append(_check(f"field_{field}", label, state))
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
        "consent_required": requires_consent(dataset),
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
