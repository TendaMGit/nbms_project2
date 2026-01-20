from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from nbms_app.models import (
    ReportSectionResponse,
    ReportSectionTemplate,
    ValidationRuleSet,
    ValidationScope,
)
from nbms_app.services.exports import assert_instance_exportable


REQUIRED_SECTION_CODES = (
    "section-i",
    "section-ii",
    "section-iii",
    "section-iv",
    "section-v",
    "section-other-information",
)


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


def _required_templates():
    templates = ReportSectionTemplate.objects.filter(
        is_active=True,
        code__in=REQUIRED_SECTION_CODES,
    ).order_by("ordering", "code")
    template_map = {template.code: template for template in templates}
    missing = [code for code in REQUIRED_SECTION_CODES if code not in template_map]
    if missing:
        raise ValidationError(f"Missing required section templates: {', '.join(missing)}")
    return templates


def build_ort_nr7_narrative_payload(*, instance, user):
    readiness = assert_instance_exportable(instance, user)
    templates = _required_templates()

    responses = ReportSectionResponse.objects.filter(
        reporting_instance=instance,
        template__in=templates,
    ).select_related("template", "updated_by")
    response_map = {response.template_id: response for response in responses}

    sections = []
    for template in templates:
        response = response_map.get(template.id)
        sections.append(
            {
                "code": template.code,
                "title": template.title,
                "content": response.response_json if response else {},
            }
        )

    payload = {
        "schema": "nbms.ort.nr7.narrative.v1",
        "exporter_version": "0.1.0",
        "generated_at": timezone.now().isoformat(),
        "reporting_instance": {
            "uuid": str(instance.uuid),
            "title": str(instance),
            "status": instance.status,
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
        "nbms_meta": {
            "reporting_instance_status": instance.status,
            "ruleset_code": _active_ruleset_code(instance),
            "export_require_sections": bool(getattr(settings, "EXPORT_REQUIRE_SECTIONS", False)),
            "missing_required_sections": readiness.get("details", {})
            .get("sections", {})
            .get("missing_required_sections", []),
        },
    }
    return payload
