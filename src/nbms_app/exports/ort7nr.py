from collections import defaultdict

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from nbms_app.models import (
    Indicator,
    LifecycleStatus,
    NationalTarget,
    ReportSectionResponse,
    ReportSectionTemplate,
    ValidationRuleSet,
    ValidationScope,
)
from nbms_app.services.authorization import filter_queryset_for_user
from nbms_app.services.consent import consent_is_granted, requires_consent
from nbms_app.services.instance_approvals import approved_queryset
from nbms_app.services.readiness import get_instance_readiness


def _default_languages():
    code = getattr(settings, "LANGUAGE_CODE", "") or "en"
    return [code.split("-")[0]]


def _as_lstring(value, locale):
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    return {locale: str(value)}


def _government_term():
    gov_id = getattr(settings, "NBMS_ORT_GOVERNMENT_ID", "") or getattr(settings, "NBMS_GOVERNMENT_IDENTIFIER", "")
    return {"identifier": gov_id} if gov_id else {"identifier": ""}


def _header(schema, identifier, languages):
    return {
        "schema": schema,
        "identifier": str(identifier),
        "languages": languages,
        "legacyIdentifier": "",
    }


def _active_ruleset_code(instance):
    queryset = ValidationRuleSet.objects.filter(is_active=True).order_by("-created_at")
    if instance:
        instance_rule = queryset.filter(applies_to=ValidationScope.INSTANCE, code=str(instance.uuid)).first()
        if instance_rule:
            return instance_rule.code
        cycle_rule = queryset.filter(applies_to=ValidationScope.CYCLE, code=instance.cycle.code).first()
        if cycle_rule:
            return cycle_rule.code
    default_rule = queryset.filter(applies_to=ValidationScope.REPORT_TYPE, code="7NR_DEFAULT").first()
    if default_rule:
        return default_rule.code
    return ""


def _require_exportable(instance, user):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")

    readiness = get_instance_readiness(instance, user)
    blockers = readiness.get("blockers", [])
    if blockers:
        messages = "; ".join(blocker.get("message", "") for blocker in blockers if blocker)
        raise ValidationError(messages or "Export blocked by readiness checks.")

    approvals = readiness.get("details", {}).get("approvals", {})
    pending = sum(item.get("pending", 0) for item in approvals.values())
    if pending:
        raise ValidationError("Missing instance approvals for one or more published items.")

    return readiness


def _approved_visible_queryset(instance, model, user, select_related=()):
    approved_ids = approved_queryset(instance, model).values_list("uuid", flat=True)
    queryset = model.objects.select_related(*select_related)
    queryset = filter_queryset_for_user(queryset, user)
    queryset = queryset.filter(uuid__in=approved_ids, status=LifecycleStatus.PUBLISHED)
    return queryset.order_by("code" if hasattr(model, "code") else "title")


def _filter_consent(instance, items):
    allowed = []
    for obj in items:
        if not requires_consent(obj) or consent_is_granted(instance, obj):
            allowed.append(obj)
    return allowed


def _section_payloads(instance):
    templates = ReportSectionTemplate.objects.filter(is_active=True).order_by("ordering", "code")
    responses = ReportSectionResponse.objects.filter(
        reporting_instance=instance,
        template__in=templates,
    ).select_related("template", "updated_by")
    response_map = {resp.template.code: resp for resp in responses}
    payloads = {}
    for template in templates:
        response = response_map.get(template.code)
        payloads[template.code] = response.response_json if response else {}
    return payloads


def build_ort7nr_package(*, instance, user):
    if not instance:
        raise ValidationError("Reporting instance is required.")

    readiness = _require_exportable(instance, user)
    languages = _default_languages()
    locale = languages[0]
    government = _government_term()
    section_payloads = _section_payloads(instance)

    targets = list(
        _approved_visible_queryset(instance, NationalTarget, user, select_related=("organisation", "created_by"))
    )
    indicators = list(
        _approved_visible_queryset(
            instance,
            Indicator,
            user,
            select_related=("organisation", "created_by", "national_target"),
        )
    )

    indicators_by_target = defaultdict(list)
    for indicator in indicators:
        indicators_by_target[indicator.national_target_id].append(indicator)

    targets = _filter_consent(instance, targets)
    indicators = _filter_consent(instance, indicators)

    national_target_docs = []
    for index, target in enumerate(targets, start=1):
        linked_indicators = indicators_by_target.get(target.id, [])
        linked_indicators = [indicator for indicator in linked_indicators if indicator in indicators]
        other_national = []
        for indicator in linked_indicators:
            identifier = indicator.code or f"NBMS-IND-{indicator.uuid}"
            other_national.append(
                {"identifier": identifier, "value": _as_lstring(indicator.title, locale)}
            )

        national_target_docs.append(
            {
                "header": _header("nationalTarget7", target.uuid, languages),
                "government": government,
                "title": _as_lstring(target.title, locale),
                "description": _as_lstring(target.description, locale),
                "sequence": index,
                "otherNationalIndicators": other_national,
                "notes": target.review_note or "",
            }
        )

    report_doc = {
        "header": _header("nationalReport7", instance.uuid, languages),
        "government": government,
        "sectionI": section_payloads.get("section-i", {}),
        "sectionII": section_payloads.get("section-ii", {}),
        "sectionIII": section_payloads.get("section-iii", {}),
        "sectionIV": section_payloads.get("section-iv", {}),
        "sectionV": section_payloads.get("section-v", {}),
        "sectionOtherInfo": section_payloads.get("section-other-information", {}),
        "notes": instance.notes or "",
    }

    package = {
        "exporter_version": "0.1",
        "generated_at": timezone.now().isoformat(),
        "documents": {
            "nationalReport7": [report_doc],
            "nationalTarget7": national_target_docs,
            "nationalTarget7Mapping": [],
            "nationalReport7IndicatorData": [],
            "nationalReport7BinaryIndicatorData": [],
        },
        "nbms_meta": {
            "reporting_instance_uuid": str(instance.uuid),
            "reporting_cycle_code": instance.cycle.code,
            "reporting_cycle_title": instance.cycle.title,
            "reporting_instance_status": instance.status,
            "ruleset_code": _active_ruleset_code(instance),
            "export_require_sections": bool(getattr(settings, "EXPORT_REQUIRE_SECTIONS", False)),
            "missing_required_sections": readiness.get("details", {})
            .get("sections", {})
            .get("missing_required_sections", []),
        },
    }
    return package
