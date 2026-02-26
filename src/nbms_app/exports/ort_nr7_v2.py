import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from nbms_app.exports.ort_nr7_narrative import _active_ruleset_code, _required_templates
from nbms_app.models import (
    BinaryIndicatorGroupResponse,
    BinaryIndicatorResponse,
    Dataset,
    DatasetRelease,
    Evidence,
    Indicator,
    FrameworkGoal,
    LifecycleStatus,
    NbsapStatus,
    ReportSectionResponse,
    SectionIINBSAPStatus,
    SectionIReportContext,
    SectionIIINationalTargetProgress,
    SectionIVFrameworkGoalProgress,
    SectionIVFrameworkTargetProgress,
    SectionVConclusions,
    StakeholderInvolvement,
)
from nbms_app.services.authorization import filter_queryset_for_user
from nbms_app.services.consent import consent_is_granted, requires_consent
from nbms_app.services.exports import assert_instance_exportable
from nbms_app.services.indicator_data import (
    binary_indicator_responses_for_user,
    indicator_data_points_for_user,
    indicator_data_series_for_user,
)
from nbms_app.services.instance_approvals import approved_queryset
from nbms_app.services.export_contracts import validate_ort_nr7_v2_payload_shape
from nbms_app.services.section_progress import scoped_framework_targets, scoped_national_targets


EXPORTER_VERSION = "0.2.0"


def _stable_json(value):
    return json.dumps(value or {}, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _sorted_uuid_list(queryset):
    return sorted({str(item.uuid) for item in queryset})


def _sort_series_key(series):
    framework_code = series.framework_indicator.code if series.framework_indicator_id else ""
    indicator_code = series.indicator.code if series.indicator_id else str(series.uuid)
    return (framework_code, indicator_code)


def _section_response_by_code(*, templates, response_map):
    by_code = {}
    for template in templates:
        by_code[template.code] = response_map.get(template.id)
    return by_code


def _serialize_section_i_content(*, instance, fallback):
    section = SectionIReportContext.objects.filter(reporting_instance=instance).first()
    additional_languages = []
    if section:
        additional_languages = sorted([str(value) for value in section.additional_languages or []])
    elif isinstance(fallback.get("additional_languages"), list):
        additional_languages = sorted([str(value) for value in fallback.get("additional_languages") or []])

    return {
        "reporting_party_name": (
            section.reporting_party_name
            if section
            else str(fallback.get("reporting_party_name") or getattr(settings, "NBMS_REPORTING_PARTY_NAME", "South Africa"))
        ),
        "submission_language": (
            section.submission_language
            if section
            else str(fallback.get("submission_language") or getattr(settings, "NBMS_SUBMISSION_LANGUAGE", "English"))
        ),
        "additional_languages": additional_languages,
        "responsible_authorities": section.responsible_authorities if section else str(fallback.get("responsible_authorities") or ""),
        "contact_name": section.contact_name if section else str(fallback.get("contact_name") or ""),
        "contact_email": section.contact_email if section else str(fallback.get("contact_email") or ""),
        "preparation_process": section.preparation_process if section else str(fallback.get("preparation_process") or ""),
        "preparation_challenges": (
            section.preparation_challenges if section else str(fallback.get("preparation_challenges") or "")
        ),
        "acknowledgements": section.acknowledgements if section else str(fallback.get("acknowledgements") or ""),
        "updated_at": section.updated_at.isoformat() if section else None,
        "updated_by": section.updated_by.username if section and section.updated_by else None,
    }


def _serialize_section_ii_content(*, instance, fallback):
    section = SectionIINBSAPStatus.objects.filter(reporting_instance=instance).first()
    stakeholder_groups = []
    if section:
        stakeholder_groups = sorted([str(value) for value in section.stakeholder_groups or []])
    elif isinstance(fallback.get("stakeholder_groups"), list):
        stakeholder_groups = sorted([str(value) for value in fallback.get("stakeholder_groups") or []])

    return {
        "nbsap_updated_status": section.nbsap_updated_status if section else str(fallback.get("nbsap_updated_status") or NbsapStatus.UNKNOWN),
        "nbsap_updated_other_text": section.nbsap_updated_other_text if section else str(fallback.get("nbsap_updated_other_text") or ""),
        "nbsap_expected_completion_date": (
            section.nbsap_expected_completion_date.isoformat()
            if section and section.nbsap_expected_completion_date
            else None
        ),
        "stakeholders_involved": section.stakeholders_involved if section else str(fallback.get("stakeholders_involved") or StakeholderInvolvement.UNKNOWN),
        "stakeholder_groups": stakeholder_groups,
        "stakeholder_groups_other_text": (
            section.stakeholder_groups_other_text if section else str(fallback.get("stakeholder_groups_other_text") or "")
        ),
        "stakeholder_groups_notes": section.stakeholder_groups_notes if section else str(fallback.get("stakeholder_groups_notes") or ""),
        "nbsap_adopted_status": section.nbsap_adopted_status if section else str(fallback.get("nbsap_adopted_status") or NbsapStatus.UNKNOWN),
        "nbsap_adopted_other_text": section.nbsap_adopted_other_text if section else str(fallback.get("nbsap_adopted_other_text") or ""),
        "nbsap_adoption_mechanism": section.nbsap_adoption_mechanism if section else str(fallback.get("nbsap_adoption_mechanism") or ""),
        "nbsap_expected_adoption_date": (
            section.nbsap_expected_adoption_date.isoformat()
            if section and section.nbsap_expected_adoption_date
            else None
        ),
        "monitoring_system_description": (
            section.monitoring_system_description if section else str(fallback.get("monitoring_system_description") or "")
        ),
        "updated_at": section.updated_at.isoformat() if section else None,
        "updated_by": section.updated_by.username if section and section.updated_by else None,
    }


def _serialize_section_v_content(*, instance, fallback):
    section = SectionVConclusions.objects.filter(reporting_instance=instance).prefetch_related("evidence_items").first()
    evidence_uuids = _sorted_uuid_list(section.evidence_items.all()) if section else []
    return {
        "overall_assessment": section.overall_assessment if section else str(fallback.get("overall_assessment") or ""),
        "decision_15_8_information": (
            section.decision_15_8_information if section else str(fallback.get("decision_15_8_information") or "")
        ),
        "decision_15_7_information": (
            section.decision_15_7_information if section else str(fallback.get("decision_15_7_information") or "")
        ),
        "decision_15_11_information": (
            section.decision_15_11_information if section else str(fallback.get("decision_15_11_information") or "")
        ),
        "plant_conservation_information": (
            section.plant_conservation_information if section else str(fallback.get("plant_conservation_information") or "")
        ),
        "additional_notes": section.additional_notes if section else str(fallback.get("additional_notes") or ""),
        "evidence_uuids": evidence_uuids,
        "updated_at": section.updated_at.isoformat() if section else None,
        "updated_by": section.updated_by.username if section and section.updated_by else None,
    }


def _serialize_section_iv_goals(*, instance, user, scoped_framework_targets):
    goals_qs = filter_queryset_for_user(
        FrameworkGoal.objects.select_related("framework"),
        user,
        perm="nbms_app.view_frameworkgoal",
    ).filter(status=LifecycleStatus.PUBLISHED)
    if scoped_framework_targets.exists():
        goal_ids = scoped_framework_targets.values_list("goal_id", flat=True)
        goals_qs = goals_qs.filter(id__in=goal_ids)
    goal_entries = (
        SectionIVFrameworkGoalProgress.objects.filter(
            reporting_instance=instance,
            framework_goal__in=goals_qs,
        )
        .select_related("framework_goal", "framework_goal__framework")
        .prefetch_related("evidence_items")
        .order_by("framework_goal__framework__code", "framework_goal__sort_order", "framework_goal__code")
    )
    payload = []
    for entry in goal_entries:
        payload.append(
            {
                "uuid": str(entry.uuid),
                "framework_goal": {
                    "uuid": str(entry.framework_goal.uuid),
                    "code": entry.framework_goal.code,
                    "title": entry.framework_goal.title,
                    "framework_code": entry.framework_goal.framework.code,
                },
                "progress_summary": entry.progress_summary,
                "actions_taken": entry.actions_taken,
                "outcomes": entry.outcomes,
                "challenges_and_approaches": entry.challenges_and_approaches,
                "sdg_and_other_agreements": entry.sdg_and_other_agreements,
                "evidence_uuids": _sorted_uuid_list(entry.evidence_items.all()),
            }
        )
    return payload


def _binary_group_sort_key(group_response):
    group = group_response.group
    framework_target_code = group.framework_target.code if group.framework_target_id and group.framework_target else ""
    indicator_code = group.framework_indicator.code if group.framework_indicator_id and group.framework_indicator else ""
    return (framework_target_code, indicator_code, group.ordering, group.key)


def _serialize_binary_group_responses(*, instance, user):
    allowed_question_ids = binary_indicator_responses_for_user(user, instance).values_list("question_id", flat=True)
    group_responses = (
        BinaryIndicatorGroupResponse.objects.filter(
            reporting_instance=instance,
            group__questions__id__in=allowed_question_ids,
        )
        .select_related("group", "group__framework_target", "group__framework_indicator")
        .distinct()
    )
    payload = []
    for response in sorted(group_responses, key=_binary_group_sort_key):
        group = response.group
        payload.append(
            {
                "uuid": str(response.uuid),
                "group": {
                    "uuid": str(group.uuid),
                    "key": group.key,
                    "framework_target_code": group.framework_target.code if group.framework_target_id else group.target_code,
                    "framework_indicator_code": group.framework_indicator.code if group.framework_indicator_id else None,
                    "binary_indicator_code": group.binary_indicator_code,
                    "title": group.title,
                    "ordering": group.ordering,
                },
                "comments": response.comments,
            }
        )
    return payload


def _require_referential_integrity(*, instance, user, section_iii_entries, section_iv_entries):
    referenced_series = set()
    referenced_binary = set()
    referenced_evidence = set()
    referenced_releases = set()

    for entry in list(section_iii_entries) + list(section_iv_entries):
        referenced_series.update(entry.indicator_data_series.values_list("uuid", flat=True))
        referenced_binary.update(entry.binary_indicator_responses.values_list("uuid", flat=True))
        referenced_evidence.update(entry.evidence_items.values_list("uuid", flat=True))
        referenced_releases.update(entry.dataset_releases.values_list("uuid", flat=True))

    approved_indicator_ids = approved_queryset(instance, Indicator).values_list("id", flat=True)
    allowed_series = indicator_data_series_for_user(user, instance).filter(
        Q(indicator_id__in=approved_indicator_ids) | Q(indicator__isnull=True)
    )
    allowed_series_ids = set(allowed_series.values_list("uuid", flat=True))

    allowed_binary_ids = set(
        binary_indicator_responses_for_user(user, instance).values_list("uuid", flat=True)
    )

    allowed_evidence = filter_queryset_for_user(approved_queryset(instance, Evidence), user)
    allowed_evidence_ids = set(allowed_evidence.values_list("uuid", flat=True))

    approved_datasets = filter_queryset_for_user(approved_queryset(instance, Dataset), user)
    allowed_releases = filter_queryset_for_user(
        DatasetRelease.objects.filter(dataset__in=approved_datasets),
        user,
    )
    allowed_release_ids = {
        release.uuid
        for release in allowed_releases
        if not requires_consent(release) or consent_is_granted(instance, release)
    }

    blocked = {}
    blocked_series = sorted(str(uid) for uid in referenced_series if uid not in allowed_series_ids)
    blocked_binary = sorted(str(uid) for uid in referenced_binary if uid not in allowed_binary_ids)
    blocked_evidence = sorted(str(uid) for uid in referenced_evidence if uid not in allowed_evidence_ids)
    blocked_releases = sorted(str(uid) for uid in referenced_releases if uid not in allowed_release_ids)

    if blocked_series:
        blocked["indicator_data_series"] = blocked_series
    if blocked_binary:
        blocked["binary_indicator_responses"] = blocked_binary
    if blocked_evidence:
        blocked["evidence_items"] = blocked_evidence
    if blocked_releases:
        blocked["dataset_releases"] = blocked_releases

    if blocked:
        parts = [f"{key}: {', '.join(values)}" for key, values in blocked.items()]
        raise ValidationError("Export blocked by reference checks: " + "; ".join(parts))

    return {
        "series_ids": allowed_series_ids,
        "binary_ids": allowed_binary_ids,
        "release_ids": allowed_release_ids,
        "allowed_series": allowed_series,
    }


def _serialize_points(points):
    payloads = []
    for point in points:
        payloads.append(
            {
                "uuid": str(point.uuid),
                "year": point.year,
                "value_numeric": str(point.value_numeric) if point.value_numeric is not None else None,
                "value_text": point.value_text,
                "uncertainty": point.uncertainty,
                "disaggregation": point.disaggregation or {},
                "dataset_release_uuid": str(point.dataset_release.uuid) if point.dataset_release else None,
                "source_url": point.source_url,
                "footnote": point.footnote,
            }
        )
    return sorted(payloads, key=lambda item: (item["year"], _stable_json(item["disaggregation"])))


def build_ort_nr7_v2_payload(*, instance, user):
    readiness = assert_instance_exportable(instance, user)
    templates = _required_templates()

    responses = ReportSectionResponse.objects.filter(
        reporting_instance=instance,
        template__in=templates,
    ).select_related("template", "updated_by")
    response_map = {response.template_id: response for response in responses}
    response_by_code = _section_response_by_code(templates=templates, response_map=response_map)

    sections = []
    for template in templates:
        response = response_by_code.get(template.code)
        fallback_content = response.response_json if response else {}
        if template.code == "section-i":
            content = _serialize_section_i_content(instance=instance, fallback=fallback_content)
        elif template.code == "section-ii":
            content = _serialize_section_ii_content(instance=instance, fallback=fallback_content)
        elif template.code == "section-v":
            content = _serialize_section_v_content(instance=instance, fallback=fallback_content)
        else:
            content = fallback_content
        sections.append(
            {
                "code": template.code,
                "title": template.title,
                "content": content,
            }
        )

    scoped_targets = scoped_national_targets(instance, user)
    scoped_framework = scoped_framework_targets(instance, user)

    section_iii_entries = (
        SectionIIINationalTargetProgress.objects.filter(
            reporting_instance=instance,
            national_target__in=scoped_targets,
        )
        .select_related("national_target")
        .prefetch_related(
            "indicator_data_series",
            "binary_indicator_responses__question__framework_indicator",
            "evidence_items",
            "dataset_releases",
        )
        .order_by("national_target__code")
    )

    section_iv_entries = (
        SectionIVFrameworkTargetProgress.objects.filter(
            reporting_instance=instance,
            framework_target__in=scoped_framework,
        )
        .select_related("framework_target", "framework_target__framework")
        .prefetch_related(
            "indicator_data_series",
            "binary_indicator_responses__question__framework_indicator",
            "evidence_items",
            "dataset_releases",
        )
        .order_by("framework_target__code")
    )
    section_iv_goal_payload = _serialize_section_iv_goals(
        instance=instance,
        user=user,
        scoped_framework_targets=scoped_framework,
    )

    eligibility = _require_referential_integrity(
        instance=instance,
        user=user,
        section_iii_entries=section_iii_entries,
        section_iv_entries=section_iv_entries,
    )

    referenced_series = set()
    referenced_binary = set()

    section_iii_payload = []
    for entry in section_iii_entries:
        series_uuids = _sorted_uuid_list(entry.indicator_data_series.all())
        binary_uuids = _sorted_uuid_list(entry.binary_indicator_responses.all())
        evidence_uuids = _sorted_uuid_list(entry.evidence_items.all())
        release_uuids = _sorted_uuid_list(entry.dataset_releases.all())
        referenced_series.update(series_uuids)
        referenced_binary.update(binary_uuids)
        section_iii_payload.append(
            {
                "uuid": str(entry.uuid),
                "national_target": {
                    "uuid": str(entry.national_target.uuid),
                    "code": entry.national_target.code,
                    "title": entry.national_target.title,
                },
                "progress_status": entry.progress_status,
                "progress_level": entry.progress_level,
                "progress_summary": entry.summary,
                "summary": entry.summary,
                "actions_taken": entry.actions_taken,
                "outcomes": entry.outcomes,
                "challenges": entry.challenges,
                "challenges_and_approaches": entry.challenges_and_approaches,
                "effectiveness_examples": entry.effectiveness_examples,
                "sdg_and_other_agreements": entry.sdg_and_other_agreements,
                "support_needed": entry.support_needed,
                "period_start": entry.period_start.isoformat() if entry.period_start else None,
                "period_end": entry.period_end.isoformat() if entry.period_end else None,
                "references": {
                    "indicator_data_series_uuids": series_uuids,
                    "binary_indicator_response_uuids": binary_uuids,
                    "evidence_uuids": evidence_uuids,
                    "dataset_release_uuids": release_uuids,
                },
            }
        )

    section_iv_payload = []
    for entry in section_iv_entries:
        series_uuids = _sorted_uuid_list(entry.indicator_data_series.all())
        binary_uuids = _sorted_uuid_list(entry.binary_indicator_responses.all())
        evidence_uuids = _sorted_uuid_list(entry.evidence_items.all())
        release_uuids = _sorted_uuid_list(entry.dataset_releases.all())
        referenced_series.update(series_uuids)
        referenced_binary.update(binary_uuids)
        section_iv_payload.append(
            {
                "uuid": str(entry.uuid),
                "framework_target": {
                    "uuid": str(entry.framework_target.uuid),
                    "code": entry.framework_target.code,
                    "title": entry.framework_target.title,
                    "framework_code": entry.framework_target.framework.code,
                },
                "progress_status": entry.progress_status,
                "progress_level": entry.progress_level,
                "progress_summary": entry.summary,
                "summary": entry.summary,
                "actions_taken": entry.actions_taken,
                "outcomes": entry.outcomes,
                "challenges": entry.challenges,
                "challenges_and_approaches": entry.challenges_and_approaches,
                "effectiveness_examples": entry.effectiveness_examples,
                "sdg_and_other_agreements": entry.sdg_and_other_agreements,
                "support_needed": entry.support_needed,
                "period_start": entry.period_start.isoformat() if entry.period_start else None,
                "period_end": entry.period_end.isoformat() if entry.period_end else None,
                "references": {
                    "indicator_data_series_uuids": series_uuids,
                    "binary_indicator_response_uuids": binary_uuids,
                    "evidence_uuids": evidence_uuids,
                    "dataset_release_uuids": release_uuids,
                },
            }
        )

    allowed_series = eligibility["allowed_series"].filter(uuid__in=referenced_series).select_related(
        "framework_indicator",
        "indicator",
    )
    points_qs = indicator_data_points_for_user(user, instance).filter(series__in=allowed_series)
    points_qs = points_qs.filter(
        Q(dataset_release__isnull=True) | Q(dataset_release__uuid__in=eligibility["release_ids"])
    )
    points_qs = points_qs.select_related("dataset_release")

    points_by_series = {}
    for point in points_qs.order_by("year", "id"):
        points_by_series.setdefault(point.series_id, []).append(point)

    series_payloads = []
    for series in sorted(allowed_series, key=_sort_series_key):
        points = _serialize_points(points_by_series.get(series.id, []))
        identity = {}
        if series.framework_indicator_id:
            identity = {"framework_indicator_code": series.framework_indicator.code}
        elif series.indicator_id:
            identity = {
                "indicator_uuid": str(series.indicator.uuid),
                "indicator_code": series.indicator.code,
            }
        series_payloads.append(
            {
                "uuid": str(series.uuid),
                "identity": identity,
                "title": series.title,
                "unit": series.unit,
                "value_type": series.value_type,
                "methodology": series.methodology,
                "source_notes": series.source_notes,
                "disaggregation_schema": series.disaggregation_schema or {},
                "points": points,
            }
        )

    binary_qs = BinaryIndicatorResponse.objects.filter(uuid__in=referenced_binary).select_related(
        "question",
        "question__framework_indicator",
    )
    binary_payloads = []
    for response in sorted(
        binary_qs,
        key=lambda item: (
            item.question.framework_indicator.code,
            item.question.group_key,
            item.question.question_key,
        ),
    ):
        question = response.question
        binary_payloads.append(
            {
                "uuid": str(response.uuid),
                "reporting_instance_uuid": str(response.reporting_instance.uuid),
                "question": {
                    "uuid": str(question.uuid),
                    "framework_indicator_code": question.framework_indicator.code,
                    "group_key": question.group_key,
                    "question_key": question.question_key,
                    "section": question.section,
                    "number": question.number,
                    "question_type": question.question_type,
                    "question_text": question.question_text,
                    "help_text": question.help_text,
                    "options": question.options,
                    "sort_order": question.sort_order,
                },
                "response": response.response,
                "comments": response.comments,
            }
        )

    binary_group_payloads = _serialize_binary_group_responses(instance=instance, user=user)

    generated_at = timezone.now().isoformat()
    payload = {
        "schema": "nbms.ort.nr7.v2",
        "exporter_version": EXPORTER_VERSION,
        "generated_at": generated_at,
        "reporting_instance": {
            "uuid": str(instance.uuid),
            "title": str(instance),
            "status": str(instance.status),
            "version_label": instance.version_label,
            "cycle": {
                "uuid": str(instance.cycle.uuid),
                "code": instance.cycle.code,
                "title": instance.cycle.title,
                "start_date": instance.cycle.start_date.isoformat(),
                "end_date": instance.cycle.end_date.isoformat(),
                "due_date": instance.cycle.due_date.isoformat(),
            },
        },
        "sections": sections,
        "section_iii_progress": section_iii_payload,
        "section_iv_goal_progress": section_iv_goal_payload,
        "section_iv_progress": section_iv_payload,
        "indicator_data_series": series_payloads,
        "binary_indicator_data": binary_payloads,
        "binary_indicator_group_responses": binary_group_payloads,
        "nbms_meta": {
            "instance_uuid": str(instance.uuid),
            "ruleset_code": _active_ruleset_code(instance),
            "generated_at": generated_at,
            "exporter_version": EXPORTER_VERSION,
            "export_require_sections": bool(getattr(settings, "EXPORT_REQUIRE_SECTIONS", False)),
            "missing_required_sections": readiness.get("details", {})
            .get("sections", {})
            .get("missing_required_sections", []),
            "conformance_flags": {
                "structured_progress": True,
                "indicator_data": True,
                "binary_indicator_data": True,
            },
        },
    }
    return validate_ort_nr7_v2_payload_shape(payload)
