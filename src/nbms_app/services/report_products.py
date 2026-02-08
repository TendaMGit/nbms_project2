from __future__ import annotations

from io import BytesIO

from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils import timezone

from nbms_app.models import (
    EcosystemGoldSummary,
    IASGoldSummary,
    Indicator,
    ReportProductRun,
    ReportProductStatus,
    ReportProductTemplate,
    SpatialLayer,
    TaxonGoldSummary,
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
                "layer_code": layer.layer_code,
                "slug": layer.slug,
                "name": layer.title or layer.name,
                "source_type": layer.source_type,
                "indicator_code": layer.indicator.code if layer.indicator_id else "",
                "attribution": layer.attribution,
                "license": layer.license,
            }
        )
    return rows


def _latest_snapshot(model):
    return model.objects.order_by("-snapshot_date").values_list("snapshot_date", flat=True).first()


def _ecosystem_gold_rows(user, *, limit=20):
    snapshot = _latest_snapshot(EcosystemGoldSummary)
    if not snapshot:
        return {"snapshot": None, "rows": []}
    queryset = filter_queryset_for_user(
        EcosystemGoldSummary.objects.filter(snapshot_date=snapshot).select_related("organisation"),
        user,
    ).order_by("dimension", "dimension_key", "id")
    rows = [
        {
            "dimension": row.dimension,
            "dimension_key": row.dimension_key,
            "dimension_label": row.dimension_label,
            "ecosystem_count": row.ecosystem_count,
            "threatened_count": row.threatened_count,
            "total_area_km2": float(row.total_area_km2),
            "protected_area_km2": float(row.protected_area_km2),
            "protected_percent": float(row.protected_percent),
        }
        for row in queryset[:limit]
    ]
    return {"snapshot": snapshot.isoformat(), "rows": rows}


def _taxon_gold_rows(user, *, limit=20):
    snapshot = _latest_snapshot(TaxonGoldSummary)
    if not snapshot:
        return {"snapshot": None, "rows": []}
    queryset = filter_queryset_for_user(
        TaxonGoldSummary.objects.filter(snapshot_date=snapshot).select_related("organisation"),
        user,
    ).order_by("taxon_rank", "-taxon_count", "id")
    rows = [
        {
            "taxon_rank": row.taxon_rank,
            "is_native": row.is_native,
            "is_endemic": row.is_endemic,
            "has_voucher": row.has_voucher,
            "is_ias": row.is_ias,
            "taxon_count": row.taxon_count,
            "voucher_count": row.voucher_count,
            "ias_profile_count": row.ias_profile_count,
        }
        for row in queryset[:limit]
    ]
    return {"snapshot": snapshot.isoformat(), "rows": rows}


def _ias_gold_rows(user, *, limit=20):
    snapshot = _latest_snapshot(IASGoldSummary)
    if not snapshot:
        return {"snapshot": None, "rows": []}
    queryset = filter_queryset_for_user(
        IASGoldSummary.objects.filter(snapshot_date=snapshot).select_related("organisation"),
        user,
    ).order_by("dimension", "dimension_key", "-profile_count", "id")
    rows = [
        {
            "dimension": row.dimension,
            "dimension_key": row.dimension_key,
            "dimension_label": row.dimension_label,
            "eicat_category": row.eicat_category,
            "seicat_category": row.seicat_category,
            "profile_count": row.profile_count,
            "invasive_count": row.invasive_count,
        }
        for row in queryset[:limit]
    ]
    return {"snapshot": snapshot.isoformat(), "rows": rows}


def _auto_sections_for_template(template_code, *, ecosystem_gold, taxon_gold, ias_gold, indicator_rows, map_rows):
    if template_code == "nba_v1":
        return [
            {
                "code": "ecosystem_state_table",
                "title": "Ecosystem State and Protection",
                "table_rows": ecosystem_gold["rows"],
                "chart_hint": "stacked_bar_by_dimension",
                "map_layers": [row["layer_code"] for row in map_rows if "ecosystem" in (row["layer_code"] or "").lower()][:3],
                "snapshot_date": ecosystem_gold["snapshot"],
            },
            {
                "code": "species_readiness_table",
                "title": "Species and Voucher Coverage",
                "table_rows": taxon_gold["rows"],
                "chart_hint": "rank_distribution",
                "map_layers": [row["layer_code"] for row in map_rows if "province" in (row["layer_code"] or "").lower()][:1],
                "snapshot_date": taxon_gold["snapshot"],
            },
            {
                "code": "ias_pressure_table",
                "title": "IAS Pressure Summary",
                "table_rows": ias_gold["rows"],
                "chart_hint": "heatmap_eicat_seicat",
                "map_layers": [row["layer_code"] for row in map_rows if "protected" in (row["layer_code"] or "").lower()][:1],
                "snapshot_date": ias_gold["snapshot"],
            },
        ]
    if template_code == "gmo_v1":
        return [
            {
                "code": "indicator_trajectory",
                "title": "Indicator Trajectory Snapshot",
                "table_rows": indicator_rows[:20],
                "chart_hint": "line_trend_bundle",
                "map_layers": [],
                "snapshot_date": timezone.now().date().isoformat(),
            },
            {
                "code": "ecosystem_baselines",
                "title": "Ecosystem Baselines",
                "table_rows": ecosystem_gold["rows"],
                "chart_hint": "protection_vs_threat",
                "map_layers": [row["layer_code"] for row in map_rows][:2],
                "snapshot_date": ecosystem_gold["snapshot"],
            },
            {
                "code": "ias_risk_watch",
                "title": "IAS Risk Watch",
                "table_rows": ias_gold["rows"],
                "chart_hint": "category_watchlist",
                "map_layers": [row["layer_code"] for row in map_rows if "ias" in (row["layer_code"] or "").lower()][:2],
                "snapshot_date": ias_gold["snapshot"],
            },
        ]
    return [
        {
            "code": "ias_profiles_by_dimension",
            "title": "IAS Profiles by Dimension",
            "table_rows": ias_gold["rows"],
            "chart_hint": "dimension_distribution",
            "map_layers": [row["layer_code"] for row in map_rows if "ias" in (row["layer_code"] or "").lower()][:2],
            "snapshot_date": ias_gold["snapshot"],
        },
        {
            "code": "invasive_species_voucher_status",
            "title": "Invasive Species Voucher Status",
            "table_rows": [row for row in taxon_gold["rows"] if row.get("is_ias")][:20],
            "chart_hint": "voucher_gap",
            "map_layers": [],
            "snapshot_date": taxon_gold["snapshot"],
        },
        {
            "code": "protection_overlap_context",
            "title": "Protection Overlap Context",
            "table_rows": [row for row in ecosystem_gold["rows"] if row.get("dimension") == "province"][:20],
            "chart_hint": "choropleth_protected_percent",
            "map_layers": [row["layer_code"] for row in map_rows if "protected" in (row["layer_code"] or "").lower()][:2],
            "snapshot_date": ecosystem_gold["snapshot"],
        },
    ]


def build_report_product_payload(*, template: ReportProductTemplate, instance, user):
    indicator_rows = _indicator_rows(user)
    map_rows = _map_rows(user)
    ecosystem_gold = _ecosystem_gold_rows(user)
    taxon_gold = _taxon_gold_rows(user)
    ias_gold = _ias_gold_rows(user)
    sections = template.schema_json.get("sections", [])
    auto_sections = _auto_sections_for_template(
        template.code,
        ecosystem_gold=ecosystem_gold,
        taxon_gold=taxon_gold,
        ias_gold=ias_gold,
        indicator_rows=indicator_rows,
        map_rows=map_rows,
    )
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
    empty_auto = [section["code"] for section in auto_sections if not section.get("table_rows")]
    if empty_auto:
        qa_items.append(
            {
                "severity": "WARNING",
                "code": "empty_auto_sections",
                "message": f"Auto sections missing source rows: {', '.join(empty_auto)}",
            }
        )

    citations = [
        {"source": "Ecosystem Gold Summary", "snapshot_date": ecosystem_gold["snapshot"]},
        {"source": "Taxon Gold Summary", "snapshot_date": taxon_gold["snapshot"]},
        {"source": "IAS Gold Summary", "snapshot_date": ias_gold["snapshot"]},
    ]
    evidence_hooks = [
        {
            "code": "indicator_evidence_links",
            "description": "Attach supporting evidence URLs or documents per populated section.",
            "required_for_publish": True,
        },
        {
            "code": "map_layer_attribution",
            "description": "Ensure map attribution/licence metadata is retained in exported product.",
            "required_for_publish": True,
        },
    ]
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
        "auto_sections": auto_sections,
        "indicator_table": indicator_rows,
        "map_layers": map_rows,
        "citations": citations,
        "evidence_hooks": evidence_hooks,
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
