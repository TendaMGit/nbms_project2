from nbms_app.exports.ort_nr7_narrative import build_ort_nr7_narrative_payload
from nbms_app.exports.ort_nr7_v2 import build_ort_nr7_v2_payload
from nbms_app.models import ReportTemplatePack, ReportTemplatePackResponse, ReportTemplatePackSection
from nbms_app.services.reporting_exports import build_cbd_report_payload
from nbms_app.services.template_packs import build_default_response_payload


def _export_cbd_ort_nr7_v2(instance, user):
    return build_ort_nr7_v2_payload(instance=instance, user=user)


def _export_cbd_ort_nr7_narrative(instance, user):
    return build_ort_nr7_narrative_payload(instance=instance, user=user)


def _export_cbd_national_report_v1(instance, user):
    return build_cbd_report_payload(instance=instance)


def _export_stub(instance, user, pack_code):
    sections = (
        ReportTemplatePackSection.objects.filter(pack__code=pack_code, is_active=True)
        .order_by("ordering", "code")
        .values("code", "title")
    )
    responses = (
        ReportTemplatePackResponse.objects.filter(
            reporting_instance=instance,
            section__pack__code=pack_code,
        )
        .select_related("section")
        .order_by("section__ordering", "section__code")
    )
    response_map = {item.section.code: item.response_json for item in responses}
    return {
        "schema": f"nbms.mea.{pack_code}.v1",
        "reporting_instance_uuid": str(instance.uuid),
        "sections": [
            {
                "code": section["code"],
                "title": section["title"],
                "response": response_map.get(section["code"], {}),
            }
            for section in sections
        ],
    }


def _export_ramsar_v1(instance, user):
    pack_code = "ramsar_v1"
    sections = (
        ReportTemplatePackSection.objects.filter(pack__code=pack_code, is_active=True)
        .order_by("ordering", "code")
    )
    responses = (
        ReportTemplatePackResponse.objects.filter(
            reporting_instance=instance,
            section__pack__code=pack_code,
        )
        .select_related("section")
        .order_by("section__ordering", "section__code")
    )
    response_map = {item.section.code: item.response_json for item in responses}
    section_payloads = []
    for section in sections:
        response_json = response_map.get(section.code) or build_default_response_payload(section)
        if section.code == "section_3_implementation_indicators":
            rows = response_json.get("implementation_questions") or []
            normalized_rows = []
            for row in rows:
                normalized_rows.append(
                    {
                        "question_code": row.get("question_code"),
                        "question_title": row.get("question_title"),
                        "response": row.get("response", ""),
                        "notes": row.get("notes", ""),
                        "linked_indicator_codes": sorted(
                            str(item).strip()
                            for item in (row.get("linked_indicator_codes") or [])
                            if str(item).strip()
                        ),
                        "linked_programme_codes": sorted(
                            str(item).strip()
                            for item in (row.get("linked_programme_codes") or [])
                            if str(item).strip()
                        ),
                        "linked_evidence_uuids": sorted(
                            str(item).strip()
                            for item in (row.get("linked_evidence_uuids") or [])
                            if str(item).strip()
                        ),
                    }
                )
            normalized_rows = sorted(normalized_rows, key=lambda item: (item["question_code"] or ""))
            response_json = {**response_json, "implementation_questions": normalized_rows}
        section_payloads.append(
            {
                "code": section.code,
                "title": section.title,
                "response": response_json,
            }
        )

    return {
        "schema": "nbms.mea.ramsar_v1.v1",
        "reporting_instance_uuid": str(instance.uuid),
        "sections": section_payloads,
    }


EXPORT_HANDLER_REGISTRY = {
    "cbd_national_report_v1": _export_cbd_national_report_v1,
    "cbd_ort_nr7_v2": _export_cbd_ort_nr7_v2,
    "cbd_ort_nr7_narrative": _export_cbd_ort_nr7_narrative,
    "ramsar_v1": _export_ramsar_v1,
    "cites_v1": lambda instance, user: _export_stub(instance, user, "cites_v1"),
    "cms_v1": lambda instance, user: _export_stub(instance, user, "cms_v1"),
}


def resolve_pack_exporter(pack: ReportTemplatePack):
    handler_name = pack.export_handler or pack.code
    return EXPORT_HANDLER_REGISTRY.get(handler_name)
