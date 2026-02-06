from nbms_app.exports.ort_nr7_narrative import build_ort_nr7_narrative_payload
from nbms_app.exports.ort_nr7_v2 import build_ort_nr7_v2_payload
from nbms_app.models import ReportTemplatePack, ReportTemplatePackResponse, ReportTemplatePackSection


def _export_cbd_ort_nr7_v2(instance, user):
    return build_ort_nr7_v2_payload(instance=instance, user=user)


def _export_cbd_ort_nr7_narrative(instance, user):
    return build_ort_nr7_narrative_payload(instance=instance, user=user)


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


EXPORT_HANDLER_REGISTRY = {
    "cbd_ort_nr7_v2": _export_cbd_ort_nr7_v2,
    "cbd_ort_nr7_narrative": _export_cbd_ort_nr7_narrative,
    "ramsar_v1": lambda instance, user: _export_stub(instance, user, "ramsar_v1"),
    "cites_v1": lambda instance, user: _export_stub(instance, user, "cites_v1"),
    "cms_v1": lambda instance, user: _export_stub(instance, user, "cms_v1"),
}


def resolve_pack_exporter(pack: ReportTemplatePack):
    handler_name = pack.export_handler or pack.code
    return EXPORT_HANDLER_REGISTRY.get(handler_name)
