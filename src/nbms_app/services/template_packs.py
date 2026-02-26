from __future__ import annotations

from io import BytesIO

from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils import timezone

from nbms_app.models import (
    Evidence,
    Indicator,
    MonitoringProgramme,
    ReportTemplatePack,
    ReportTemplatePackResponse,
    ReportTemplatePackSection,
)
from nbms_app.services.authorization import filter_queryset_for_user
from nbms_app.services.catalog_access import filter_monitoring_programmes_for_user


def _normalise_multivalue(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value).strip()]


def build_default_response_payload(section: ReportTemplatePackSection):
    payload = {}
    for field in section.schema_json.get("fields", []):
        key = field.get("key")
        if not key:
            continue
        field_type = (field.get("type") or "").strip().lower()
        if field_type == "questionnaire":
            payload[key] = [
                {
                    "question_code": item.get("code"),
                    "question_title": item.get("title"),
                    "response": "",
                    "notes": "",
                    "linked_indicator_codes": [],
                    "linked_programme_codes": [],
                    "linked_evidence_uuids": [],
                }
                for item in field.get("question_catalog", [])
            ]
        elif field_type in {"multivalue", "table"}:
            payload[key] = []
        else:
            payload[key] = ""
    return payload


def _resolve_accessible_lookups(*, user):
    indicator_codes = set(
        filter_queryset_for_user(
            Indicator.objects.order_by("code"),
            user,
            perm="nbms_app.view_indicator",
        ).values_list("code", flat=True)
    )
    programme_codes = set(
        filter_monitoring_programmes_for_user(
            MonitoringProgramme.objects.order_by("programme_code"),
            user,
        ).values_list("programme_code", flat=True)
    )
    evidence_uuids = set(
        str(item)
        for item in filter_queryset_for_user(
            Evidence.objects.order_by("uuid"),
            user,
            perm="nbms_app.view_evidence",
        ).values_list("uuid", flat=True)
    )
    return indicator_codes, programme_codes, evidence_uuids


def build_pack_validation(*, pack: ReportTemplatePack, instance, user):
    responses = {
        row.section.code: row.response_json
        for row in ReportTemplatePackResponse.objects.filter(
            reporting_instance=instance,
            section__pack=pack,
        ).select_related("section")
    }
    indicator_codes, programme_codes, evidence_uuids = _resolve_accessible_lookups(user=user)

    qa_items = []
    sections = []
    ordered_sections = pack.sections.filter(is_active=True).order_by("ordering", "code")
    for section in ordered_sections:
        schema_fields = section.schema_json.get("fields", [])
        response_payload = responses.get(section.code) or build_default_response_payload(section)
        missing_fields = []
        warnings = []

        for field in schema_fields:
            key = field.get("key")
            if not key:
                continue
            required = bool(field.get("required"))
            field_type = (field.get("type") or "").strip().lower()
            value = response_payload.get(key)
            if required:
                if field_type == "questionnaire":
                    if not isinstance(value, list) or not value:
                        missing_fields.append(key)
                    else:
                        unanswered = [row for row in value if not (row.get("response") or "").strip()]
                        if unanswered:
                            missing_fields.append(key)
                            qa_items.append(
                                {
                                    "severity": "BLOCKER",
                                    "section": section.code,
                                    "field": key,
                                    "code": "unanswered_questionnaire_items",
                                    "message": f"{len(unanswered)} questionnaire rows are missing responses.",
                                }
                            )
                elif field_type == "multivalue":
                    if not _normalise_multivalue(value):
                        missing_fields.append(key)
                elif field_type == "table":
                    if not isinstance(value, list) or not value:
                        missing_fields.append(key)
                    else:
                        required_columns = field.get("required_columns") or field.get("columns") or []
                        for idx, row in enumerate(value):
                            if not isinstance(row, dict):
                                qa_items.append(
                                    {
                                        "severity": "BLOCKER",
                                        "section": section.code,
                                        "field": key,
                                        "code": "table_row_not_object",
                                        "message": f"Row {idx + 1} in '{key}' must be an object.",
                                    }
                                )
                                continue
                            for column in required_columns:
                                if not str(row.get(column) or "").strip():
                                    qa_items.append(
                                        {
                                            "severity": "BLOCKER",
                                            "section": section.code,
                                            "field": key,
                                            "code": "table_required_cell_missing",
                                            "message": (
                                                f"Row {idx + 1} in '{key}' is missing required value for '{column}'."
                                            ),
                                        }
                                    )
                elif not str(value or "").strip():
                    missing_fields.append(key)

            if field_type == "questionnaire" and isinstance(value, list):
                allowed_values = set(field.get("allowed_values") or [])
                for row in value:
                    response_value = (row.get("response") or "").strip()
                    if response_value and allowed_values and response_value not in allowed_values:
                        warnings.append(f"{row.get('question_code')}: response '{response_value}' is not in allowed values.")
                    for code in _normalise_multivalue(row.get("linked_indicator_codes")):
                        if code not in indicator_codes:
                            warnings.append(
                                f"{row.get('question_code')}: linked indicator '{code}' is not accessible."
                            )
                    for code in _normalise_multivalue(row.get("linked_programme_codes")):
                        if code not in programme_codes:
                            warnings.append(
                                f"{row.get('question_code')}: linked programme '{code}' is not accessible."
                            )
                    for evidence_uuid in _normalise_multivalue(row.get("linked_evidence_uuids")):
                        if evidence_uuid not in evidence_uuids:
                            warnings.append(
                                f"{row.get('question_code')}: linked evidence '{evidence_uuid}' is not accessible."
                            )

            if field_type == "multivalue":
                values = _normalise_multivalue(value)
                if key.endswith("indicator_codes"):
                    for code in values:
                        if code not in indicator_codes:
                            warnings.append(f"Linked indicator '{code}' is not accessible.")
                if key.endswith("programme_codes"):
                    for code in values:
                        if code not in programme_codes:
                            warnings.append(f"Linked programme '{code}' is not accessible.")

        for field_name in missing_fields:
            qa_items.append(
                {
                    "severity": "BLOCKER",
                    "section": section.code,
                    "field": field_name,
                    "code": "required_field_missing",
                    "message": f"Required field '{field_name}' is missing.",
                }
            )
        for warning in warnings:
            qa_items.append(
                {
                    "severity": "WARNING",
                    "section": section.code,
                    "code": "reference_warning",
                    "message": warning,
                }
            )

        if section.code == "section-iii":
            rows = response_payload.get("target_progress_rows") or []
            if isinstance(rows, list) and rows:
                rows_without_evidence = []
                rows_without_links = []
                for idx, row in enumerate(rows):
                    if not isinstance(row, dict):
                        continue
                    evidence = row.get("evidence_links") or []
                    datasets = row.get("dataset_links") or []
                    indicators = row.get("indicator_links") or []
                    if not evidence:
                        rows_without_evidence.append(idx + 1)
                    if not datasets and not indicators:
                        rows_without_links.append(idx + 1)
                if len(rows_without_evidence) == len(rows):
                    qa_items.append(
                        {
                            "severity": "BLOCKER",
                            "section": section.code,
                            "code": "missing_evidence_links",
                            "message": "At least one Section III target row must include evidence links.",
                        }
                    )
                elif rows_without_evidence:
                    qa_items.append(
                        {
                            "severity": "WARNING",
                            "section": section.code,
                            "code": "partial_missing_evidence_links",
                            "message": (
                                "Target rows missing evidence links: "
                                + ", ".join(str(row) for row in rows_without_evidence[:8])
                            ),
                        }
                    )
                if rows_without_links:
                    qa_items.append(
                        {
                            "severity": "WARNING",
                            "section": section.code,
                            "code": "partial_missing_data_links",
                            "message": (
                                "Target rows missing indicator/dataset links: "
                                + ", ".join(str(row) for row in rows_without_links[:8])
                            ),
                        }
                    )

        completion_total = len(schema_fields) or 1
        completed = completion_total - len(missing_fields)
        sections.append(
            {
                "code": section.code,
                "title": section.title,
                "completion": int((completed / completion_total) * 100),
                "missing_fields": missing_fields,
                "warning_count": len(warnings),
            }
        )

    if not instance.is_public:
        qa_items.append(
            {
                "severity": "WARNING",
                "section": "instance",
                "code": "internal_visibility",
                "message": "Report visibility is internal only; confirm before public release workflow.",
            }
        )

    return {
        "pack_code": pack.code,
        "instance_uuid": str(instance.uuid),
        "generated_at": timezone.now().isoformat(),
        "overall_ready": not any(item["severity"] == "BLOCKER" for item in qa_items),
        "qa_items": qa_items,
        "sections": sections,
    }


def render_pack_pdf_bytes(*, pack: ReportTemplatePack, instance, user):
    try:
        from xhtml2pdf import pisa  # noqa: WPS433
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"PDF renderer dependency missing: {exc}") from exc

    validation = build_pack_validation(pack=pack, instance=instance, user=user)
    sections = pack.sections.filter(is_active=True).order_by("ordering", "code")
    responses = {
        row.section.code: row.response_json
        for row in ReportTemplatePackResponse.objects.filter(
            reporting_instance=instance,
            section__pack=pack,
        ).select_related("section")
    }
    rendered_sections = []
    for section in sections:
        response_json = responses.get(section.code) or build_default_response_payload(section)
        field_rows = []
        for field in section.schema_json.get("fields", []):
            key = field.get("key")
            if not key:
                continue
            field_type = (field.get("type") or "").strip().lower()
            value = response_json.get(key)
            if field_type == "questionnaire":
                questionnaire_rows = value if isinstance(value, list) else []
                field_rows.append(
                    {
                        "label": field.get("label", key),
                        "key": key,
                        "type": field_type,
                        "questionnaire_rows": questionnaire_rows,
                    }
                )
            else:
                if isinstance(value, list):
                    value_text = ", ".join(str(item) for item in value)
                elif isinstance(value, dict):
                    value_text = str(value)
                else:
                    value_text = str(value or "")
                field_rows.append(
                    {
                        "label": field.get("label", key),
                        "key": key,
                        "type": field_type,
                        "value_text": value_text,
                    }
                )
        rendered_sections.append(
            {
                "code": section.code,
                "title": section.title,
                "field_rows": field_rows,
            }
        )

    context = {
        "pack": pack,
        "instance": instance,
        "sections": rendered_sections,
        "validation": validation,
        "generated_at": timezone.now(),
    }
    html = render_to_string("nbms_app/reporting/template_pack_pdf.html", context)
    output = BytesIO()
    result = pisa.CreatePDF(src=html, dest=output, encoding="utf-8")
    if result.err:
        raise ValidationError("Failed to render template pack PDF output.")
    return output.getvalue()
