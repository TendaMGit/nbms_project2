from io import BytesIO

from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils import timezone

from nbms_app.exports.ort_nr7_v2 import build_ort_nr7_v2_payload
from nbms_app.models import (
    SectionIINBSAPStatus,
    SectionIIINationalTargetProgress,
    SectionIReportContext,
    SectionIVFrameworkTargetProgress,
    SectionVConclusions,
)
from nbms_app.services.readiness import get_instance_readiness


def _missing_text_fields(instance):
    missing = []

    section_i = SectionIReportContext.objects.filter(reporting_instance=instance).first()
    if not section_i:
        missing.extend(
            [
                {"section": "section-i", "field": "reporting_party_name", "message": "Section I record is missing."},
                {"section": "section-i", "field": "submission_language", "message": "Section I record is missing."},
            ]
        )
    else:
        if not (section_i.reporting_party_name or "").strip():
            missing.append(
                {"section": "section-i", "field": "reporting_party_name", "message": "Reporting party name is required."}
            )
        if not (section_i.submission_language or "").strip():
            missing.append(
                {"section": "section-i", "field": "submission_language", "message": "Submission language is required."}
            )

    section_ii = SectionIINBSAPStatus.objects.filter(reporting_instance=instance).first()
    if not section_ii:
        missing.append(
            {
                "section": "section-ii",
                "field": "monitoring_system_description",
                "message": "Section II record is missing.",
            }
        )
    elif not (section_ii.monitoring_system_description or "").strip():
        missing.append(
            {
                "section": "section-ii",
                "field": "monitoring_system_description",
                "message": "Monitoring system description is required.",
            }
        )

    section_v = SectionVConclusions.objects.filter(reporting_instance=instance).first()
    if not section_v:
        missing.append(
            {"section": "section-v", "field": "overall_assessment", "message": "Section V record is missing."}
        )
    elif not (section_v.overall_assessment or "").strip():
        missing.append(
            {"section": "section-v", "field": "overall_assessment", "message": "Overall assessment is required."}
        )

    return missing


def _cross_section_gaps(instance):
    gaps = []

    if not SectionIIINationalTargetProgress.objects.filter(reporting_instance=instance).exists():
        gaps.append(
            {
                "code": "section_iii_missing",
                "message": "Section III has no target progress records yet.",
            }
        )
    if not SectionIVFrameworkTargetProgress.objects.filter(reporting_instance=instance).exists():
        gaps.append(
            {
                "code": "section_iv_missing",
                "message": "Section IV has no framework target progress records yet.",
            }
        )

    section_v = (
        SectionVConclusions.objects.filter(reporting_instance=instance)
        .prefetch_related("evidence_items")
        .first()
    )
    if section_v and not section_v.evidence_items.exists():
        gaps.append(
            {
                "code": "section_v_no_evidence",
                "message": "Section V has no linked evidence items.",
            }
        )
    return gaps


def build_nr7_validation_summary(*, instance, user):
    readiness = get_instance_readiness(instance, user)
    missing_fields = _missing_text_fields(instance)
    cross_section = _cross_section_gaps(instance)

    blockers = list(readiness.get("blockers", []))
    warnings = list(readiness.get("warnings", []))
    section_details = readiness.get("details", {}).get("sections", {})
    missing_required_sections = sorted(section_details.get("missing_required_sections", []))
    incomplete_required_sections = sorted(section_details.get("incomplete_required_sections", []))

    qa_items = []
    for item in missing_fields:
        qa_items.append({"severity": "BLOCKER", "code": "missing_field", **item})
    for code in missing_required_sections:
        qa_items.append(
            {
                "severity": "BLOCKER",
                "code": "missing_required_section",
                "section": code,
                "message": f"Required section is missing: {code}",
            }
        )
    for code in incomplete_required_sections:
        qa_items.append(
            {
                "severity": "WARNING",
                "code": "incomplete_required_section",
                "section": code,
                "message": f"Required section is incomplete: {code}",
            }
        )
    for item in cross_section:
        qa_items.append({"severity": "WARNING", "section": "cross-section", **item})
    for blocker in blockers:
        qa_items.append(
            {
                "severity": "BLOCKER",
                "code": blocker.get("code", "readiness_blocker"),
                "section": "readiness",
                "message": blocker.get("message", "Readiness blocker."),
            }
        )
    for warning in warnings:
        qa_items.append(
            {
                "severity": "WARNING",
                "code": warning.get("code", "readiness_warning"),
                "section": "readiness",
                "message": warning.get("message", "Readiness warning."),
            }
        )

    sections = []
    for item in section_details.get("sections", []):
        template = item.get("template", {})
        sections.append(
            {
                "code": template.get("code"),
                "title": template.get("title"),
                "required": bool(item.get("required")),
                "state": item.get("state"),
                "completion": item.get("completion", 0),
                "missing_fields": item.get("missing_fields", []),
                "incomplete_fields": item.get("incomplete_fields", []),
            }
        )

    return {
        "overall_ready": not any(item.get("severity") == "BLOCKER" for item in qa_items),
        "generated_at": timezone.now().isoformat(),
        "qa_items": qa_items,
        "sections": sections,
    }


def build_nr7_preview_payload(*, instance, user):
    try:
        payload = build_ort_nr7_v2_payload(instance=instance, user=user)
        return {"preview_payload": payload, "preview_error": None}
    except Exception as exc:  # noqa: BLE001
        return {"preview_payload": None, "preview_error": str(exc)}


def render_nr7_pdf_bytes(*, instance, user):
    try:
        from xhtml2pdf import pisa  # noqa: WPS433
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"PDF renderer dependency missing: {exc}") from exc

    preview = build_nr7_preview_payload(instance=instance, user=user)
    validation = build_nr7_validation_summary(instance=instance, user=user)
    context = {
        "instance": instance,
        "preview_payload": preview["preview_payload"],
        "preview_error": preview["preview_error"],
        "validation": validation,
        "generated_at": timezone.now(),
    }
    html = render_to_string("nbms_app/reporting/nr7_report_pdf.html", context)
    output = BytesIO()
    result = pisa.CreatePDF(src=html, dest=output, encoding="utf-8")
    if result.err:
        raise ValidationError("Failed to render NR7 PDF output.")
    return output.getvalue()
