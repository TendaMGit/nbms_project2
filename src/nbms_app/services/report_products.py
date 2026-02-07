from __future__ import annotations

from io import BytesIO

from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils import timezone

from nbms_app.models import (
    Indicator,
    ReportProductRun,
    ReportProductStatus,
    ReportProductTemplate,
    SpatialLayer,
)
from nbms_app.services.authorization import filter_queryset_for_user
from nbms_app.services.spatial_access import filter_spatial_layers_for_user


def seed_default_report_products():
    definitions = [
        {
            "code": "nba_v1",
            "title": "National Biodiversity Assessment (NBA) Report",
            "description": "NBA product shell with indicator tables, maps, and evidence references.",
            "schema_json": {
                "sections": [
                    "Executive summary",
                    "State and trends",
                    "Pressures and responses",
                    "Policy implications",
                ]
            },
            "export_handler": "nba_v1",
        },
        {
            "code": "gmo_v1",
            "title": "National Biodiversity Monitoring Outlook (GMO) Report",
            "description": "Monitoring outlook shell focused on programme readiness and trends.",
            "schema_json": {
                "sections": [
                    "Monitoring system status",
                    "Indicator trajectory outlook",
                    "Critical risks and opportunities",
                ]
            },
            "export_handler": "gmo_v1",
        },
        {
            "code": "invasive_v1",
            "title": "Invasive Species Status Report",
            "description": "Status report shell for invasive alien species pressure and response.",
            "schema_json": {
                "sections": [
                    "Invasion extent",
                    "Pressure indicators",
                    "Control effectiveness",
                    "Priority response actions",
                ]
            },
            "export_handler": "invasive_v1",
        },
    ]
    templates = []
    for item in definitions:
        template, _ = ReportProductTemplate.objects.update_or_create(
            code=item["code"],
            defaults={
                "title": item["title"],
                "version": "v1",
                "description": item["description"],
                "schema_json": item["schema_json"],
                "export_handler": item["export_handler"],
                "is_active": True,
            },
        )
        templates.append(template)
    return templates


def _indicator_rows(user):
    queryset = filter_queryset_for_user(
        Indicator.objects.select_related("national_target", "organisation").order_by("code", "title"),
        user,
        perm="nbms_app.view_indicator",
    )
    published = queryset.filter(status="published")
    return [
        {
            "code": indicator.code,
            "title": indicator.title,
            "indicator_type": indicator.indicator_type,
            "national_target_code": indicator.national_target.code if indicator.national_target_id else "",
            "last_updated_on": indicator.last_updated_on.isoformat() if indicator.last_updated_on else "",
            "coverage_geography": indicator.coverage_geography or "",
            "qa_status": indicator.qa_status,
        }
        for indicator in published
    ]


def _map_rows(user):
    layers = filter_spatial_layers_for_user(
        SpatialLayer.objects.select_related("indicator").order_by("slug"),
        user,
    )
    rows = []
    for layer in layers:
        rows.append(
            {
                "slug": layer.slug,
                "name": layer.name,
                "source_type": layer.source_type,
                "indicator_code": layer.indicator.code if layer.indicator_id else "",
            }
        )
    return rows


def build_report_product_payload(*, template: ReportProductTemplate, instance, user):
    indicator_rows = _indicator_rows(user)
    map_rows = _map_rows(user)
    sections = template.schema_json.get("sections", [])
    qa_items = []
    if not indicator_rows:
        qa_items.append(
            {
                "severity": "BLOCKER",
                "code": "no_published_indicators",
                "message": "No published indicators were available for this report product.",
            }
        )
    if not map_rows:
        qa_items.append(
            {
                "severity": "WARNING",
                "code": "no_map_layers",
                "message": "No spatial layers are currently available.",
            }
        )
    return {
        "schema": f"nbms.report_product.{template.code}.{template.version}",
        "generated_at": timezone.now().isoformat(),
        "template": {
            "code": template.code,
            "title": template.title,
            "version": template.version,
            "description": template.description,
        },
        "reporting_instance_uuid": str(instance.uuid) if instance else None,
        "sections": [{"title": title, "summary": ""} for title in sections],
        "indicator_table": indicator_rows,
        "map_layers": map_rows,
        "qa": {
            "overall_ready": not any(item["severity"] == "BLOCKER" for item in qa_items),
            "items": qa_items,
        },
    }


def render_report_product_html(*, template: ReportProductTemplate, payload):
    context = {"template": template, "payload": payload, "generated_at": timezone.now()}
    return render_to_string("nbms_app/reporting/report_product_preview.html", context)


def render_report_product_pdf_bytes(*, template: ReportProductTemplate, payload):
    try:
        from xhtml2pdf import pisa  # noqa: WPS433
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"PDF renderer dependency missing: {exc}") from exc

    html = render_report_product_html(template=template, payload=payload)
    output = BytesIO()
    result = pisa.CreatePDF(src=html, dest=output, encoding="utf-8")
    if result.err:
        raise ValidationError("Failed to render report product PDF output.")
    return output.getvalue()


def generate_report_product_run(*, template: ReportProductTemplate, instance, user):
    run = ReportProductRun.objects.create(
        template=template,
        reporting_instance=instance,
        generated_by=user if getattr(user, "is_authenticated", False) else None,
        status=ReportProductStatus.DRAFT,
    )
    try:
        payload = build_report_product_payload(template=template, instance=instance, user=user)
        html = render_report_product_html(template=template, payload=payload)
        run.status = ReportProductStatus.GENERATED
        run.payload_json = payload
        run.html_content = html
        run.generated_at = timezone.now()
        run.error_message = ""
    except Exception as exc:  # noqa: BLE001
        run.status = ReportProductStatus.FAILED
        run.error_message = str(exc)
    run.save(
        update_fields=[
            "status",
            "payload_json",
            "html_content",
            "generated_at",
            "error_message",
            "updated_at",
        ]
    )
    return run
