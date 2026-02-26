from __future__ import annotations

import csv
import hashlib
import json
from io import StringIO
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Q
from django.utils import timezone

from nbms_app.models import (
    AccessLevel,
    AlienTaxonProfile,
    Dataset,
    DownloadRecord,
    DownloadRecordStatus,
    DownloadRecordType,
    EcosystemType,
    Indicator,
    IndicatorDatasetLink,
    MonitoringProgramme,
    MonitoringProgrammeRun,
    ReportProductTemplate,
    ReportLabel,
    ReportTemplatePack,
    ReportingInstance,
    ReportingStatus,
    SensitivityLevel,
    SpatialLayer,
    TaxonConcept,
)
from nbms_app.services.catalog_access import filter_monitoring_programmes_for_user
from nbms_app.services.metrics import observe_download_created, observe_export_request
from nbms_app.services.authorization import (
    ROLE_ADMIN,
    ROLE_DATA_STEWARD,
    ROLE_PUBLISHING_AUTHORITY,
    ROLE_SECTION_LEAD,
    ROLE_SECRETARIAT,
    ROLE_TECHNICAL_COMMITTEE,
    filter_queryset_for_user,
    is_system_admin,
    user_has_role,
)
from nbms_app.services.indicator_data import indicator_data_points_for_user, indicator_data_series_for_user
from nbms_app.services.report_products import (
    build_report_product_payload,
    render_report_product_html,
    render_report_product_pdf_bytes,
)
from nbms_app.services.reporting_exports import (
    build_cbd_report_payload,
    render_cbd_docx_bytes,
    render_cbd_pdf_bytes,
)
from nbms_app.services.template_pack_registry import resolve_pack_exporter
from nbms_app.services.template_packs import render_pack_pdf_bytes
from nbms_app.services.spatial_access import (
    filter_spatial_layers_for_user,
    parse_bbox,
    parse_datetime_range,
    parse_property_filters,
    spatial_feature_collection,
)


_REPORT_EXPORT_ALLOWED_STATES = {
    ReportingStatus.SUBMITTED,
    ReportingStatus.RELEASED,
    ReportingStatus.PUBLIC_RELEASED,
}

_REGISTRY_KIND_TO_MODEL = {
    "taxa": TaxonConcept,
    "ecosystems": EcosystemType,
    "ias": AlienTaxonProfile,
}


def _safe_filename(value: str, fallback: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in (value or "").strip())
    cleaned = cleaned.strip("-.")
    return cleaned or fallback


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _storage_path(record_uuid: UUID, file_name: str) -> str:
    return f"downloads/{record_uuid}/{file_name}"


def _store_asset(record: DownloadRecord, *, file_name: str, content_type: str, content_bytes: bytes) -> DownloadRecord:
    safe_name = _safe_filename(file_name, "download.bin")
    storage_path = _storage_path(record.uuid, safe_name)
    if default_storage.exists(storage_path):
        default_storage.delete(storage_path)
    default_storage.save(storage_path, ContentFile(content_bytes))
    record.file_asset_path = storage_path
    record.file_asset_name = safe_name
    record.file_content_type = content_type
    record.file_size_bytes = len(content_bytes)
    record.file_hash = _sha256_bytes(content_bytes)
    record.status = DownloadRecordStatus.READY
    record.save(
        update_fields=[
            "file_asset_path",
            "file_asset_name",
            "file_content_type",
            "file_size_bytes",
            "file_hash",
            "status",
            "updated_at",
        ]
    )
    return record


def _access_level_for_sensitivity(sensitivity: str) -> str:
    if sensitivity == SensitivityLevel.PUBLIC:
        return AccessLevel.PUBLIC
    if sensitivity in {SensitivityLevel.RESTRICTED, SensitivityLevel.IPLC_SENSITIVE}:
        return AccessLevel.RESTRICTED
    return AccessLevel.INTERNAL


def _report_access_level(instance: ReportingInstance) -> str:
    if instance.is_public and instance.status in _REPORT_EXPORT_ALLOWED_STATES:
        return AccessLevel.PUBLIC
    return AccessLevel.INTERNAL


def _can_view_report_instance(user, instance: ReportingInstance) -> bool:
    if is_system_admin(user):
        return True
    if instance.is_public and instance.status in _REPORT_EXPORT_ALLOWED_STATES:
        return True
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if instance.created_by_id and instance.created_by_id == user.id:
        return True
    if instance.focal_point_org_id and instance.focal_point_org_id == getattr(user, "organisation_id", None):
        return True
    if instance.publishing_authority_org_id and instance.publishing_authority_org_id == getattr(user, "organisation_id", None):
        return True
    return bool(
        user_has_role(
            user,
            ROLE_SECTION_LEAD,
            ROLE_SECRETARIAT,
            ROLE_DATA_STEWARD,
            ROLE_TECHNICAL_COMMITTEE,
            ROLE_PUBLISHING_AUTHORITY,
            ROLE_ADMIN,
        )
    )


def _citation_text(record: DownloadRecord) -> str:
    created = timezone.localtime(record.created_at).strftime("%Y-%m-%d %H:%M:%S %Z")
    object_ref = f"{record.object_type}:{record.object_uuid}" if record.object_uuid else record.object_type
    return (
        f"National Biodiversity Monitoring System (NBMS). Download record {record.citation_id}; "
        f"type={record.record_type}; object={object_ref or 'n/a'}; generated {created}. "
        "No DOI is assigned to this download record."
    )


def _normalise_query_snapshot(value):
    return value if isinstance(value, dict) else {}


def _build_indicator_series_export(*, user, indicator_uuid: UUID, query_snapshot: dict):
    indicator = filter_queryset_for_user(
        Indicator.objects.select_related("national_target"),
        user,
        perm="nbms_app.view_indicator",
    ).filter(uuid=indicator_uuid).first()
    if not indicator:
        raise PermissionDenied("Indicator not found or inaccessible.")

    points_qs = (
        indicator_data_points_for_user(user)
        .filter(series__in=indicator_data_series_for_user(user).filter(indicator=indicator))
        .select_related("series", "spatial_unit", "spatial_layer")
        .order_by("year", "series__title", "id")
    )
    year_from = query_snapshot.get("year_from")
    year_to = query_snapshot.get("year_to")
    try:
        if year_from is not None:
            points_qs = points_qs.filter(year__gte=int(year_from))
        if year_to is not None:
            points_qs = points_qs.filter(year__lte=int(year_to))
    except (TypeError, ValueError):
        pass

    writer_buffer = StringIO()
    writer = csv.writer(writer_buffer)
    writer.writerow(
        [
            "indicator_uuid",
            "indicator_code",
            "indicator_title",
            "series_uuid",
            "series_title",
            "year",
            "value_numeric",
            "value_text",
            "spatial_resolution",
            "spatial_unit_code",
            "spatial_unit_name",
            "spatial_layer_code",
            "disaggregation_json",
        ]
    )
    for point in points_qs:
        writer.writerow(
            [
                str(indicator.uuid),
                indicator.code,
                indicator.title,
                str(point.series.uuid),
                point.series.title,
                point.year,
                point.value_numeric if point.value_numeric is not None else "",
                point.value_text or "",
                point.spatial_resolution or point.series.spatial_resolution or "",
                point.spatial_unit.unit_code if point.spatial_unit_id else "",
                point.spatial_unit.name if point.spatial_unit_id else "",
                point.spatial_layer.layer_code if point.spatial_layer_id else "",
                json.dumps(point.disaggregation or {}, sort_keys=True, ensure_ascii=True),
            ]
        )

    dataset_links = IndicatorDatasetLink.objects.filter(indicator=indicator).select_related("dataset")
    visible_datasets = filter_queryset_for_user(
        Dataset.objects.filter(id__in=dataset_links.values_list("dataset_id", flat=True)),
        user,
        perm="nbms_app.view_dataset",
    )
    visible_ids = set(visible_datasets.values_list("id", flat=True))
    contributing_sources = [
        {
            "kind": "indicator",
            "uuid": str(indicator.uuid),
            "code": indicator.code,
            "title": indicator.title,
        }
    ]
    for link in dataset_links:
        if link.dataset_id not in visible_ids:
            continue
        contributing_sources.append(
            {
                "kind": "dataset",
                "uuid": str(link.dataset.uuid),
                "code": link.dataset.dataset_code,
                "title": link.dataset.title,
            }
        )

    return {
        "object_type": "indicator",
        "object_uuid": indicator.uuid,
        "access_level_at_time": _access_level_for_sensitivity(indicator.sensitivity),
        "contributing_sources": contributing_sources,
        "file_name": f"{indicator.code.lower()}-series.csv",
        "content_type": "text/csv; charset=utf-8",
        "content_bytes": writer_buffer.getvalue().encode("utf-8"),
    }


def _build_spatial_layer_export(*, user, layer_uuid: UUID | None, query_snapshot: dict):
    layer_code = str(query_snapshot.get("layer_code") or "").strip()
    layer_qs = filter_spatial_layers_for_user(SpatialLayer.objects.select_related("indicator"), user)
    layer = None
    if layer_uuid:
        layer = layer_qs.filter(uuid=layer_uuid).first()
    if not layer and layer_code:
        layer = layer_qs.filter(layer_code=layer_code).first()
    if not layer:
        raise PermissionDenied("Spatial layer not found or inaccessible.")

    bbox = parse_bbox(query_snapshot.get("bbox"))
    datetime_range = parse_datetime_range(query_snapshot.get("datetime"))
    property_filters = parse_property_filters(query_snapshot.get("filter"))
    try:
        limit = int(query_snapshot.get("limit") or 10000)
    except (TypeError, ValueError):
        limit = 10000
    limit = max(1, min(limit, 20000))

    _layer, payload = spatial_feature_collection(
        user=user,
        layer_code=layer.layer_code,
        bbox=bbox,
        datetime_range=datetime_range,
        property_filters=property_filters,
        limit=limit,
        offset=0,
    )
    if not payload.get("features"):
        payload.setdefault("numberReturned", 0)

    contributing_sources = [
        {
            "kind": "spatial_layer",
            "uuid": str(layer.uuid),
            "layer_code": layer.layer_code,
            "title": layer.title or layer.name,
        }
    ]
    if layer.indicator_id:
        contributing_sources.append(
            {
                "kind": "indicator",
                "uuid": str(layer.indicator.uuid),
                "code": layer.indicator.code,
                "title": layer.indicator.title,
            }
        )

    return {
        "object_type": "spatial_layer",
        "object_uuid": layer.uuid,
        "access_level_at_time": _access_level_for_sensitivity(layer.sensitivity),
        "contributing_sources": contributing_sources,
        "file_name": f"{layer.layer_code}.geojson",
        "content_type": "application/geo+json",
        "content_bytes": json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8"),
    }


def _build_report_export(*, user, instance_uuid: UUID, query_snapshot: dict):
    instance = ReportingInstance.objects.select_related("cycle").filter(uuid=instance_uuid).first()
    if not instance:
        raise PermissionDenied("Reporting instance not found.")
    if not _can_view_report_instance(user, instance):
        raise PermissionDenied("Forbidden.")

    fmt = str(query_snapshot.get("format") or "pdf").strip().lower()
    if fmt not in {"pdf", "docx", "json"}:
        raise ValidationError("Unsupported report export format.")

    payload = build_cbd_report_payload(instance=instance)
    if fmt == "pdf":
        content_bytes = render_cbd_pdf_bytes(payload=payload)
        content_type = "application/pdf"
        extension = "pdf"
    elif fmt == "docx":
        content_bytes = render_cbd_docx_bytes(payload=payload)
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        extension = "docx"
    else:
        content_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        content_type = "application/json"
        extension = "json"

    report_label = instance.report_label.lower() if instance.report_label in {ReportLabel.NR7, ReportLabel.NR8} else "report"
    file_name = f"{report_label}-report-{instance.uuid}.{extension}"
    contributing_sources = [
        {
            "kind": "reporting_instance",
            "uuid": str(instance.uuid),
            "cycle_code": instance.cycle.code if instance.cycle_id else "",
            "report_label": instance.report_label,
            "version_label": instance.version_label,
        }
    ]
    return {
        "object_type": "reporting_instance",
        "object_uuid": instance.uuid,
        "access_level_at_time": _report_access_level(instance),
        "contributing_sources": contributing_sources,
        "file_name": file_name,
        "content_type": content_type,
        "content_bytes": content_bytes,
    }


def _build_registry_export(*, user, object_type: str, object_uuid: UUID | None, query_snapshot: dict):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication is required for registry exports.")
    kind = str(query_snapshot.get("registry_kind") or object_type or "").strip().lower()
    if kind.startswith("registry_"):
        kind = kind.replace("registry_", "", 1)
    if kind not in _REGISTRY_KIND_TO_MODEL:
        raise ValidationError("Unsupported registry export kind.")

    model_class = _REGISTRY_KIND_TO_MODEL[kind]
    queryset = filter_queryset_for_user(model_class.objects.all().order_by("id"), user)
    if kind == "taxa":
        search = str(query_snapshot.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(scientific_name__icontains=search)
                | Q(canonical_name__icontains=search)
                | Q(taxon_code__icontains=search)
            )
        rank = str(query_snapshot.get("rank") or "").strip()
        if rank:
            queryset = queryset.filter(taxon_rank__iexact=rank)
    elif kind == "ecosystems":
        biome = str(query_snapshot.get("biome") or "").strip()
        if biome:
            queryset = queryset.filter(biome__icontains=biome)
        threat_category = str(query_snapshot.get("threat_category") or "").strip()
        if threat_category:
            queryset = queryset.filter(risk_assessments__category__iexact=threat_category).distinct()
    elif kind == "ias":
        search = str(query_snapshot.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(taxon__scientific_name__icontains=search)
                | Q(taxon__canonical_name__icontains=search)
                | Q(taxon__taxon_code__icontains=search)
            )
        eicat = str(query_snapshot.get("eicat") or "").strip()
        if eicat:
            queryset = queryset.filter(eicat_assessments__category__iexact=eicat).distinct()
        seicat = str(query_snapshot.get("seicat") or "").strip()
        if seicat:
            queryset = queryset.filter(seicat_assessments__category__iexact=seicat).distinct()

    if object_uuid:
        queryset = queryset.filter(uuid=object_uuid)
    rows = list(queryset[:10000])

    buffer = StringIO()
    writer = csv.writer(buffer)
    if kind == "taxa":
        writer.writerow(
            [
                "uuid",
                "taxon_code",
                "scientific_name",
                "taxon_rank",
                "taxonomic_status",
                "primary_source_system",
                "is_native",
                "is_endemic",
                "voucher_specimen_count",
                "status",
                "sensitivity",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    str(row.uuid),
                    row.taxon_code,
                    row.scientific_name,
                    row.taxon_rank,
                    row.taxonomic_status,
                    row.primary_source_system,
                    row.is_native,
                    row.is_endemic,
                    row.voucher_specimen_count,
                    row.status,
                    row.sensitivity,
                ]
            )
    elif kind == "ecosystems":
        writer.writerow(
            [
                "uuid",
                "ecosystem_code",
                "name",
                "realm",
                "biome",
                "bioregion",
                "vegmap_version",
                "status",
                "sensitivity",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    str(row.uuid),
                    row.ecosystem_code,
                    row.name,
                    row.realm,
                    row.biome,
                    row.bioregion,
                    row.vegmap_version,
                    row.status,
                    row.sensitivity,
                ]
            )
    else:
        writer.writerow(
            [
                "uuid",
                "taxon_uuid",
                "taxon_code",
                "scientific_name",
                "country_code",
                "degree_of_establishment_code",
                "pathway_code",
                "is_invasive",
                "status",
                "sensitivity",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    str(row.uuid),
                    str(row.taxon.uuid),
                    row.taxon.taxon_code,
                    row.taxon.scientific_name,
                    row.country_code,
                    row.degree_of_establishment_code,
                    row.pathway_code,
                    row.is_invasive,
                    row.status,
                    row.sensitivity,
                ]
            )

    contributing_sources = [
        {
            "kind": f"registry_{kind}",
            "row_count": len(rows),
        }
    ]
    return {
        "object_type": f"registry_{kind}",
        "object_uuid": object_uuid,
        "access_level_at_time": AccessLevel.INTERNAL,
        "contributing_sources": contributing_sources,
        "file_name": f"{kind}-registry-export.csv",
        "content_type": "text/csv; charset=utf-8",
        "content_bytes": buffer.getvalue().encode("utf-8"),
    }


def _build_custom_bundle_export(*, user, query_snapshot: dict):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication is required for custom bundle exports.")
    kind = str(query_snapshot.get("kind") or "").strip().lower()
    if not kind:
        raise ValidationError("query_snapshot.kind is required for custom_bundle downloads.")

    if kind in {"template_pack_pdf", "template_pack_export_json"}:
        pack_code = str(query_snapshot.get("pack_code") or "").strip()
        instance_uuid = _parse_uuid(query_snapshot.get("instance_uuid"))
        if not pack_code or not instance_uuid:
            raise ValidationError("pack_code and instance_uuid are required.")
        pack = ReportTemplatePack.objects.filter(is_active=True, code=pack_code).first()
        if not pack:
            raise ValidationError("Unknown template pack code.")
        instance = ReportingInstance.objects.filter(uuid=instance_uuid).first()
        if not instance:
            raise ValidationError("Reporting instance not found.")
        if not _can_view_report_instance(user, instance):
            raise PermissionDenied("Forbidden.")
        if kind == "template_pack_pdf":
            content_bytes = render_pack_pdf_bytes(pack=pack, instance=instance, user=user)
            content_type = "application/pdf"
            extension = "pdf"
        else:
            exporter = resolve_pack_exporter(pack)
            if not exporter:
                raise ValidationError("No exporter is registered for this template pack.")
            payload = exporter(instance, user)
            content_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
            content_type = "application/json"
            extension = "json"
        return {
            "object_type": "reporting_instance",
            "object_uuid": instance.uuid,
            "access_level_at_time": _report_access_level(instance),
            "contributing_sources": [
                {
                    "kind": "template_pack",
                    "pack_code": pack.code,
                    "instance_uuid": str(instance.uuid),
                }
            ],
            "file_name": f"{pack.code}_{instance.uuid}.{extension}",
            "content_type": content_type,
            "content_bytes": content_bytes,
        }

    if kind in {"report_product_pdf", "report_product_html"}:
        product_code = str(query_snapshot.get("product_code") or "").strip().lower()
        if not product_code:
            raise ValidationError("product_code is required.")
        template = ReportProductTemplate.objects.filter(is_active=True, code=product_code).first()
        if not template:
            raise ValidationError("Report product template not found.")
        instance = None
        instance_uuid = _parse_uuid(query_snapshot.get("instance_uuid"))
        if instance_uuid:
            instance = ReportingInstance.objects.filter(uuid=instance_uuid).first()
            if not instance:
                raise ValidationError("Reporting instance not found.")
            if not _can_view_report_instance(user, instance):
                raise PermissionDenied("Forbidden.")
        payload = build_report_product_payload(template=template, instance=instance, user=user)
        if kind == "report_product_pdf":
            content_bytes = render_report_product_pdf_bytes(template=template, payload=payload)
            content_type = "application/pdf"
            extension = "pdf"
        else:
            content_bytes = render_report_product_html(template=template, payload=payload).encode("utf-8")
            content_type = "text/html; charset=utf-8"
            extension = "html"
        scope = str(instance.uuid) if instance else "global"
        return {
            "object_type": "reporting_instance" if instance else "report_product",
            "object_uuid": instance.uuid if instance else None,
            "access_level_at_time": _report_access_level(instance) if instance else AccessLevel.INTERNAL,
            "contributing_sources": [
                {
                    "kind": "report_product",
                    "code": template.code,
                    "version": template.version,
                    "instance_uuid": str(instance.uuid) if instance else None,
                }
            ],
            "file_name": f"{template.code}_{scope}.{extension}",
            "content_type": content_type,
            "content_bytes": content_bytes,
        }

    if kind == "programme_run_report":
        run_uuid = _parse_uuid(query_snapshot.get("run_uuid"))
        if not run_uuid:
            raise ValidationError("run_uuid is required.")
        run = (
            MonitoringProgrammeRun.objects.select_related("programme", "requested_by")
            .prefetch_related("steps", "artefacts", "qa_results")
            .filter(
                uuid=run_uuid,
                programme__in=filter_monitoring_programmes_for_user(MonitoringProgramme.objects.all(), user),
            )
            .first()
        )
        if not run:
            raise PermissionDenied("Programme run not found or inaccessible.")
        payload = {
            "generated_at": timezone.now().isoformat(),
            "programme": {
                "uuid": str(run.programme.uuid),
                "programme_code": run.programme.programme_code,
                "title": run.programme.title,
            },
            "run": {
                "uuid": str(run.uuid),
                "status": run.status,
                "run_type": run.run_type,
                "trigger": run.trigger,
                "requested_by": run.requested_by.username if run.requested_by_id else None,
                "created_at": run.created_at.isoformat(),
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "lineage_json": run.lineage_json,
                "output_summary_json": run.output_summary_json,
            },
        }
        return {
            "object_type": "programme_run",
            "object_uuid": run.uuid,
            "access_level_at_time": AccessLevel.INTERNAL,
            "contributing_sources": [
                {
                    "kind": "monitoring_programme_run",
                    "run_uuid": str(run.uuid),
                    "programme_uuid": str(run.programme.uuid),
                    "programme_code": run.programme.programme_code,
                }
            ],
            "file_name": f"programme-run-{run.uuid}.json",
            "content_type": "application/json",
            "content_bytes": json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8"),
        }

    raise ValidationError("Unsupported custom_bundle export kind.")


def _parse_uuid(raw_value):
    if raw_value in (None, ""):
        return None
    try:
        return UUID(str(raw_value))
    except (TypeError, ValueError):
        raise ValidationError("Invalid object_uuid.")


def create_download_record_from_payload(*, user, payload: dict) -> DownloadRecord:
    if not isinstance(payload, dict):
        raise ValidationError("Payload must be an object.")

    record_type = str(payload.get("record_type") or "").strip().lower()
    object_type = str(payload.get("object_type") or "").strip().lower()
    object_uuid = _parse_uuid(payload.get("object_uuid"))
    query_snapshot = _normalise_query_snapshot(payload.get("query_snapshot"))
    regen_params = _normalise_query_snapshot(payload.get("regen_params"))

    allowed = {choice for choice, _label in DownloadRecordType.choices}
    if record_type not in allowed:
        raise ValidationError("Invalid record_type.")

    if record_type == DownloadRecordType.INDICATOR_SERIES:
        if not object_uuid:
            raise ValidationError("object_uuid is required for indicator_series downloads.")
        build = _build_indicator_series_export(user=user, indicator_uuid=object_uuid, query_snapshot=query_snapshot)
    elif record_type == DownloadRecordType.SPATIAL_LAYER:
        build = _build_spatial_layer_export(user=user, layer_uuid=object_uuid, query_snapshot=query_snapshot)
    elif record_type == DownloadRecordType.REPORT_EXPORT:
        if not object_uuid:
            raise ValidationError("object_uuid is required for report_export downloads.")
        build = _build_report_export(user=user, instance_uuid=object_uuid, query_snapshot=query_snapshot)
    elif record_type == DownloadRecordType.REGISTRY_EXPORT:
        build = _build_registry_export(
            user=user,
            object_type=object_type,
            object_uuid=object_uuid,
            query_snapshot=query_snapshot,
        )
    else:
        build = _build_custom_bundle_export(
            user=user,
            query_snapshot=query_snapshot,
        )

    actor = user if getattr(user, "is_authenticated", False) else None
    record = DownloadRecord.objects.create(
        created_by=actor,
        record_type=record_type,
        object_type=build["object_type"],
        object_uuid=build["object_uuid"],
        query_snapshot=query_snapshot,
        contributing_sources=build["contributing_sources"],
        access_level_at_time=build["access_level_at_time"],
        regen_params=regen_params,
        status=DownloadRecordStatus.PENDING,
    )
    record.citation_id = f"NBMS-DL-{record.uuid}"
    record.citation_text = _citation_text(record)
    record.save(update_fields=["citation_id", "citation_text", "updated_at"])
    observe_download_created(record_type=record.record_type)
    observe_export_request(export_type=record.record_type)
    return _store_asset(
        record,
        file_name=build["file_name"],
        content_type=build["content_type"],
        content_bytes=build["content_bytes"],
    )


def create_download_record_with_asset(
    *,
    user,
    record_type: str,
    object_type: str,
    object_uuid: UUID | None,
    query_snapshot: dict | None,
    contributing_sources: list | None,
    access_level_at_time: str,
    file_name: str,
    content_type: str,
    content_bytes: bytes,
    regen_params: dict | None = None,
) -> DownloadRecord:
    actor = user if getattr(user, "is_authenticated", False) else None
    record = DownloadRecord.objects.create(
        created_by=actor,
        record_type=record_type,
        object_type=(object_type or "").strip(),
        object_uuid=object_uuid,
        query_snapshot=_normalise_query_snapshot(query_snapshot),
        contributing_sources=contributing_sources or [],
        access_level_at_time=access_level_at_time,
        regen_params=_normalise_query_snapshot(regen_params),
        status=DownloadRecordStatus.PENDING,
    )
    record.citation_id = f"NBMS-DL-{record.uuid}"
    record.citation_text = _citation_text(record)
    record.save(update_fields=["citation_id", "citation_text", "updated_at"])
    observe_download_created(record_type=record.record_type)
    observe_export_request(export_type=record.record_type)
    return _store_asset(
        record,
        file_name=file_name,
        content_type=content_type,
        content_bytes=content_bytes,
    )


def can_view_download_record(user, record: DownloadRecord) -> bool:
    if is_system_admin(user):
        return True
    if record.created_by_id:
        return bool(user and getattr(user, "is_authenticated", False) and user.id == record.created_by_id)
    return record.access_level_at_time == AccessLevel.PUBLIC


def _can_access_object_now(user, record: DownloadRecord) -> bool:
    if not record.object_type:
        return record.access_level_at_time == AccessLevel.PUBLIC
    if record.object_type == "indicator":
        if not record.object_uuid:
            return False
        return filter_queryset_for_user(
            Indicator.objects.all(),
            user,
            perm="nbms_app.view_indicator",
        ).filter(uuid=record.object_uuid).exists()
    if record.object_type == "spatial_layer":
        if not record.object_uuid:
            return False
        return filter_spatial_layers_for_user(SpatialLayer.objects.all(), user).filter(uuid=record.object_uuid).exists()
    if record.object_type == "reporting_instance":
        if not record.object_uuid:
            return False
        instance = ReportingInstance.objects.filter(uuid=record.object_uuid).first()
        if not instance:
            return False
        return _can_view_report_instance(user, instance)
    if record.object_type.startswith("registry_"):
        if not user or not getattr(user, "is_authenticated", False):
            return False
        kind = record.object_type.replace("registry_", "", 1)
        model_class = _REGISTRY_KIND_TO_MODEL.get(kind)
        if not model_class:
            return False
        queryset = filter_queryset_for_user(model_class.objects.all(), user)
        if record.object_uuid:
            return queryset.filter(uuid=record.object_uuid).exists()
        return True
    if record.object_type == "programme_run":
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if not record.object_uuid:
            return False
        return MonitoringProgrammeRun.objects.filter(
            uuid=record.object_uuid,
            programme__in=filter_monitoring_programmes_for_user(MonitoringProgramme.objects.all(), user),
        ).exists()
    if record.object_type == "report_product":
        return bool(user and getattr(user, "is_authenticated", False))
    return record.access_level_at_time == AccessLevel.PUBLIC


def can_download_record_file(user, record: DownloadRecord) -> bool:
    if not can_view_download_record(user, record):
        return False
    return _can_access_object_now(user, record)


def serialize_download_record(record: DownloadRecord, *, user) -> dict:
    can_file = can_download_record_file(user, record)
    contributing_sources = record.contributing_sources
    if not can_file:
        contributing_sources = []
    return {
        "uuid": str(record.uuid),
        "record_type": record.record_type,
        "object_type": record.object_type,
        "object_uuid": str(record.object_uuid) if record.object_uuid else None,
        "created_at": record.created_at.isoformat(),
        "status": record.status,
        "access_level_at_time": record.access_level_at_time,
        "query_snapshot": record.query_snapshot,
        "contributing_sources": contributing_sources,
        "citation_text": record.citation_text,
        "citation_id": record.citation_id or None,
        "file": {
            "name": record.file_asset_name,
            "content_type": record.file_content_type,
            "size_bytes": record.file_size_bytes,
            "download_url": f"/api/downloads/records/{record.uuid}/file" if can_file and record.status == DownloadRecordStatus.READY else None,
            "authorized": can_file,
        },
    }
