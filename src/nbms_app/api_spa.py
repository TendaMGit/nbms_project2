from collections import defaultdict
import base64
from datetime import date, timedelta
import difflib
import json
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.db import connections
from django.db.models import Count, Max, Q
from django.http import FileResponse, HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ParseError, UnsupportedMediaType
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from nbms_app.models import (
    AlienTaxonProfile,
    AuditEvent,
    BirdieModelOutput,
    BirdieSite,
    BirdieSpecies,
    Dataset,
    EICATAssessment,
    EcosystemGoldSummary,
    EcosystemRiskAssessment,
    EcosystemType,
    EcosystemTypologyCrosswalk,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorDatasetLink,
    IndicatorEvidenceLink,
    IndicatorFrameworkIndicatorLink,
    IndicatorInputRequirement,
    IndicatorMethodProfile,
    IndicatorMethodRun,
    IndicatorMethodologyVersionLink,
    InstanceExportApproval,
    LifecycleStatus,
    MonitoringProgramme,
    MonitoringProgrammeAlert,
    MonitoringProgrammeRun,
    MonitoringProgrammeRunStep,
    NationalTarget,
    ProgrammeTemplate,
    ProgrammeAlertState,
    ProgrammeRunStatus,
    ProgrammeRunType,
    ReportProductTemplate,
    ReportProductRun,
    ReportComment,
    ReportCommentThread,
    ReportCommentThreadStatus,
    ReportContext,
    ReportNarrativeBlock,
    ReportDossierArtifact,
    ReportExportArtifact,
    ReportSectionRevision,
    ReportSignoffRecord,
    ReportSuggestedChange,
    ReportTemplatePack,
    SEICATAssessment,
    ReportTemplatePackResponse,
    ReportTemplatePackSection,
    ReportWorkflowSectionApproval,
    ReportWorkflowStatus,
    SuggestedChangeStatus,
    ReportWorkflowInstance,
    ReportingCycle,
    ReportingInstance,
    ReportingStatus,
    SpecimenVoucher,
    SpatialLayer,
    TaxonConcept,
    TaxonGoldSummary,
    TaxonName,
    TaxonSourceRecord,
    IASGoldSummary,
    IASCountryChecklistRecord,
    IntegrationDataAsset,
    PreferenceDensity,
    PreferenceGeographyType,
    PreferenceTheme,
    PreferenceThemeMode,
    SensitivityLevel,
    UserPreference,
)
from nbms_app.section_help import SECTION_FIELD_HELP, build_section_help_payload
from nbms_app.services.audit import record_audit_event
from nbms_app.services.authorization import (
    ROLE_ADMIN,
    ROLE_DATA_STEWARD,
    ROLE_INDICATOR_LEAD,
    ROLE_PUBLISHING_AUTHORITY,
    ROLE_SECURITY_OFFICER,
    ROLE_SECTION_LEAD,
    ROLE_SECRETARIAT,
    ROLE_SYSTEM_ADMIN,
    ROLE_TECHNICAL_COMMITTEE,
    filter_queryset_for_user,
    is_system_admin,
    user_has_role,
)
from nbms_app.services.catalog_access import filter_monitoring_programmes_for_user
from nbms_app.services.capabilities import user_capabilities
from nbms_app.services.indicator_data import indicator_data_points_for_user, indicator_data_series_for_user
from nbms_app.services.indicator_release_workflow import (
    approve_indicator_release,
    get_release_workflow_state,
    submit_indicator_release,
)
from nbms_app.services.indicator_method_sdk import run_method_profile
from nbms_app.services.nr7_builder import (
    build_nr7_preview_payload,
    build_nr7_validation_summary,
    render_nr7_pdf_bytes,
)
from nbms_app.services.reporting_collab import (
    append_revision,
    create_suggested_change,
    decide_suggested_change,
    ensure_initial_revision,
    payload_hash,
)
from nbms_app.services.reporting_dossier import generate_reporting_dossier, read_dossier_manifest
from nbms_app.services.reporting_exports import (
    build_cbd_report_payload,
    render_cbd_docx_bytes,
    render_cbd_pdf_bytes,
    store_report_export_artifact,
)
from nbms_app.services.reporting_narratives import (
    build_docx_bytes_from_text,
    build_section_chart_specs,
    ensure_narrative_block,
    list_section_narrative_blocks,
    normalize_context_filters,
    persist_report_context,
    render_section_narrative,
    resolve_narrative_tokens,
    update_narrative_block_from_callback,
    upsert_narrative_block_content,
)
from nbms_app.services.reporting_workflow import (
    ensure_workflow_instance,
    report_content_snapshot,
    resolve_cbd_pack,
    transition_report_workflow,
)
from nbms_app.services.programme_ops import execute_programme_run, queue_programme_run, user_can_manage_programme
from nbms_app.services.readiness import get_instance_readiness
from nbms_app.services.registry_marts import latest_snapshot_date
from nbms_app.services.registry_workflows import (
    get_registry_object,
    link_registry_evidence,
    list_registry_evidence_links,
    transition_registry_object,
)
from nbms_app.services.section_progress import scoped_framework_targets, scoped_national_targets
from nbms_app.services.spatial_access import (
    filter_spatial_layers_for_user,
    parse_bbox,
    spatial_feature_collection,
)
from nbms_app.services.template_pack_registry import resolve_pack_exporter
from nbms_app.services.template_packs import (
    build_default_response_payload,
    build_pack_validation,
    render_pack_pdf_bytes,
)
from nbms_app.services.report_products import (
    build_report_product_payload,
    generate_report_product_run,
    render_report_product_html,
    render_report_product_pdf_bytes,
    seed_default_report_products,
)
from nbms_app.services.workflows import approve, publish, reject, submit_for_review


def _user_role_names(user):
    if not user or not getattr(user, "is_authenticated", False):
        return []
    return sorted(set(user.groups.values_list("name", flat=True)))


_PREFERENCE_FILTER_NAMESPACES = ("indicators", "registries", "downloads")
_PREFERENCE_WATCHLIST_NAMESPACES = ("indicators", "registries", "reports")
_PREFERENCE_THEMES = set(PreferenceTheme.values)
_PREFERENCE_THEME_MODES = set(PreferenceThemeMode.values)
_PREFERENCE_DENSITIES = set(PreferenceDensity.values)
_PREFERENCE_GEOS = set(PreferenceGeographyType.values)


def _default_saved_filters_payload():
    return {namespace: [] for namespace in _PREFERENCE_FILTER_NAMESPACES}


def _default_watchlist_payload():
    return {namespace: [] for namespace in _PREFERENCE_WATCHLIST_NAMESPACES}


def _normalize_saved_filters_payload(value):
    payload = _default_saved_filters_payload()
    if not isinstance(value, dict):
        return payload
    for namespace in _PREFERENCE_FILTER_NAMESPACES:
        rows = value.get(namespace)
        if isinstance(rows, list):
            payload[namespace] = [row for row in rows if isinstance(row, dict)]
    return payload


def _normalize_watchlist_payload(value):
    payload = _default_watchlist_payload()
    if not isinstance(value, dict):
        return payload
    for namespace in _PREFERENCE_WATCHLIST_NAMESPACES:
        rows = value.get(namespace)
        if isinstance(rows, list):
            payload[namespace] = sorted(
                set(str(item).strip() for item in rows if str(item).strip())
            )
    return payload


def _normalize_dashboard_layout(value):
    if isinstance(value, dict):
        return value
    return {}


def _serialize_user_preference(preference):
    return {
        "theme_id": preference.theme_id,
        "theme_mode": preference.theme_mode,
        "density": preference.density,
        "default_geography": {
            "type": preference.default_geography,
            "code": preference.default_geography_code or None,
        },
        "saved_filters": _normalize_saved_filters_payload(preference.saved_filters),
        "watchlist": _normalize_watchlist_payload(preference.watchlist),
        "dashboard_layout": _normalize_dashboard_layout(preference.dashboard_layout),
        "updated_at": preference.updated_at.isoformat() if preference.updated_at else None,
    }


def _user_preference_for(user):
    preference, created = UserPreference.objects.get_or_create(
        user=user,
        defaults={
            "saved_filters": _default_saved_filters_payload(),
            "watchlist": _default_watchlist_payload(),
            "dashboard_layout": {},
        },
    )
    if created:
        return preference
    dirty = False
    normalized_saved_filters = _normalize_saved_filters_payload(preference.saved_filters)
    if preference.saved_filters != normalized_saved_filters:
        preference.saved_filters = normalized_saved_filters
        dirty = True
    normalized_watchlist = _normalize_watchlist_payload(preference.watchlist)
    if preference.watchlist != normalized_watchlist:
        preference.watchlist = normalized_watchlist
        dirty = True
    normalized_layout = _normalize_dashboard_layout(preference.dashboard_layout)
    if preference.dashboard_layout != normalized_layout:
        preference.dashboard_layout = normalized_layout
        dirty = True
    if dirty:
        preference.save(update_fields=["saved_filters", "watchlist", "dashboard_layout", "updated_at"])
    return preference


def _required_namespace(raw_value, *, allowed, label):
    namespace = str(raw_value or "").strip().lower()
    if namespace not in allowed:
        options = ", ".join(sorted(allowed))
        raise ParseError(f"Invalid {label}. Expected one of: {options}.")
    return namespace


def _can_run_indicator_methods(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return bool(
        user_has_role(user, ROLE_INDICATOR_LEAD, ROLE_DATA_STEWARD, ROLE_SECRETARIAT, ROLE_ADMIN)
        or is_system_admin(user)
    )


def _indicator_base_queryset(user):
    return filter_queryset_for_user(
        Indicator.objects.select_related("national_target", "organisation", "created_by")
        .order_by("code", "title", "uuid"),
        user,
        perm="nbms_app.view_indicator",
    )


_UPDATE_FREQUENCY_DAYS = {
    "monthly": 30,
    "quarterly": 91,
    "annual": 365,
    "biennial": 730,
    "every_3_years": 1095,
}


def _next_expected_update_on(indicator):
    if not indicator.last_updated_on:
        return None
    raw_frequency = (indicator.update_frequency or indicator.reporting_cadence or "").strip().lower()
    delta_days = _UPDATE_FREQUENCY_DAYS.get(raw_frequency)
    if not delta_days:
        return None
    return indicator.last_updated_on + timedelta(days=delta_days)


def _pipeline_maturity(method_readiness_state, latest_pipeline_status=None):
    status = (latest_pipeline_status or "").strip().lower()
    if method_readiness_state == "ready" and status in {"succeeded", "published"}:
        return "operational"
    if method_readiness_state == "ready":
        return "ready"
    if method_readiness_state == "partial" or status in {"queued", "running", "blocked"}:
        return "developing"
    return "blocked"


def _indicator_payload(indicator):
    framework_targets = (
        IndicatorFrameworkIndicatorLink.objects.filter(indicator=indicator, is_active=True)
        .select_related("framework_indicator", "framework_indicator__framework_target")
        .order_by(
            "framework_indicator__framework_target__framework__code",
            "framework_indicator__framework_target__code",
            "framework_indicator__code",
        )
    )
    tags = []
    for link in framework_targets:
        fw_indicator = link.framework_indicator
        fw_target = fw_indicator.framework_target if fw_indicator else None
        if fw_target:
            tags.append(f"{fw_target.framework.code}:{fw_target.code}")
        elif fw_indicator:
            tags.append(f"{fw_indicator.framework.code}:{fw_indicator.code}")
    method_profiles = (
        IndicatorMethodProfile.objects.filter(indicator=indicator, is_active=True)
        .order_by("method_type", "implementation_key", "uuid")
    )
    readiness_rank = {"ready": 2, "partial": 1, "blocked": 0}
    readiness_state = "blocked"
    if method_profiles.exists():
        readiness_state = max(
            [profile.readiness_state for profile in method_profiles],
            key=lambda value: readiness_rank.get(value, -1),
        )
    next_expected = _next_expected_update_on(indicator)
    readiness_score = {"ready": 85, "partial": 55, "blocked": 25}.get(readiness_state, 0)
    if indicator.last_updated_on:
        readiness_score = min(100, readiness_score + 10)
    return {
        "uuid": str(indicator.uuid),
        "code": indicator.code,
        "title": indicator.title,
        "description": indicator.computation_notes,
        "indicator_type": indicator.indicator_type,
        "status": indicator.status,
        "sensitivity": indicator.sensitivity,
        "qa_status": indicator.qa_status,
        "reporting_capability": indicator.reporting_capability,
        "national_target": {
            "uuid": str(indicator.national_target.uuid) if indicator.national_target_id else None,
            "code": indicator.national_target.code if indicator.national_target_id else None,
            "title": indicator.national_target.title if indicator.national_target_id else None,
        },
        "organisation": {
            "id": indicator.organisation_id,
            "name": indicator.organisation.name if indicator.organisation_id else None,
        },
        "last_updated_on": indicator.last_updated_on.isoformat() if indicator.last_updated_on else None,
        "next_expected_update_on": next_expected.isoformat() if next_expected else None,
        "update_frequency": indicator.update_frequency or indicator.reporting_cadence or "",
        "updated_at": indicator.updated_at.isoformat(),
        "tags": sorted(set(tags)),
        "method_readiness_state": readiness_state,
        "pipeline_maturity": _pipeline_maturity(readiness_state),
        "readiness_status": "ready" if readiness_state == "ready" else "warning" if readiness_state == "partial" else "blocked",
        "readiness_score": readiness_score,
        "method_types": sorted(set(method_profiles.values_list("method_type", flat=True))),
        "coverage": {
            "geography": indicator.coverage_geography or indicator.spatial_coverage,
            "time_start_year": indicator.coverage_time_start_year,
            "time_end_year": indicator.coverage_time_end_year,
        },
    }


def _parse_positive_int(value, default, minimum=1, maximum=200):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(parsed, maximum))


def _parse_iso_date(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"Invalid date value '{value}'. Expected YYYY-MM-DD.") from exc


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "public"}


def _can_manage_registry_workflows(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if is_system_admin(user):
        return True
    return bool(user_has_role(user, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_INDICATOR_LEAD))


def _registry_gold_model(kind):
    key = (kind or "").strip().lower()
    if key == "taxa":
        return TaxonGoldSummary
    if key == "ecosystems":
        return EcosystemGoldSummary
    if key == "ias":
        return IASGoldSummary
    return None


def _registry_gold_payload(kind, queryset, limit):
    key = (kind or "").strip().lower()
    rows = queryset.order_by("-snapshot_date", "dimension", "dimension_key", "id")[:limit] if key != "taxa" else queryset.order_by("-snapshot_date", "taxon_rank", "id")[:limit]
    if key == "taxa":
        return [
            {
                "snapshot_date": row.snapshot_date.isoformat(),
                "taxon_rank": row.taxon_rank,
                "is_native": row.is_native,
                "is_endemic": row.is_endemic,
                "has_voucher": row.has_voucher,
                "is_ias": row.is_ias,
                "taxon_count": row.taxon_count,
                "voucher_count": row.voucher_count,
                "ias_profile_count": row.ias_profile_count,
                "organisation": row.organisation.name if row.organisation_id else None,
            }
            for row in rows
        ]
    if key == "ecosystems":
        return [
            {
                "snapshot_date": row.snapshot_date.isoformat(),
                "dimension": row.dimension,
                "dimension_key": row.dimension_key,
                "dimension_label": row.dimension_label,
                "ecosystem_count": row.ecosystem_count,
                "threatened_count": row.threatened_count,
                "total_area_km2": float(row.total_area_km2),
                "protected_area_km2": float(row.protected_area_km2),
                "protected_percent": float(row.protected_percent),
                "organisation": row.organisation.name if row.organisation_id else None,
            }
            for row in rows
        ]
    return [
        {
            "snapshot_date": row.snapshot_date.isoformat(),
            "dimension": row.dimension,
            "dimension_key": row.dimension_key,
            "dimension_label": row.dimension_label,
            "eicat_category": row.eicat_category,
            "seicat_category": row.seicat_category,
            "profile_count": row.profile_count,
            "invasive_count": row.invasive_count,
            "organisation": row.organisation.name if row.organisation_id else None,
        }
        for row in rows
    ]


def _can_view_sensitive_locality(user):
    if is_system_admin(user):
        return True
    return bool(user_has_role(user, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_SECURITY_OFFICER))


def _require_instance_scope(user, instance):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if is_system_admin(user) or user_has_role(user, ROLE_ADMIN):
        return True
    if not getattr(user, "is_staff", False):
        return False
    approvals_exist = InstanceExportApproval.objects.filter(
        reporting_instance=instance,
        approval_scope="export",
    ).exists()
    if not approvals_exist:
        return True
    return scoped_national_targets(instance, user).exists()


def _can_view_report_instance(user, instance):
    if is_system_admin(user):
        return True
    if instance.is_public and instance.status in {ReportingStatus.SUBMITTED, ReportingStatus.RELEASED}:
        return True
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if instance.created_by_id and instance.created_by_id == user.id:
        return True
    if instance.focal_point_org_id and instance.focal_point_org_id == getattr(user, "organisation_id", None):
        return True
    if instance.publishing_authority_org_id and instance.publishing_authority_org_id == getattr(user, "organisation_id", None):
        return True
    if user_has_role(
        user,
        ROLE_SECTION_LEAD,
        ROLE_SECRETARIAT,
        ROLE_DATA_STEWARD,
        ROLE_TECHNICAL_COMMITTEE,
        ROLE_PUBLISHING_AUTHORITY,
        ROLE_ADMIN,
    ):
        return True
    return False


def _can_edit_report_instance(user, instance):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if instance.finalized_at:
        return False
    if is_system_admin(user):
        return True
    return bool(
        _can_view_report_instance(user, instance)
        and user_has_role(
            user,
            ROLE_SECTION_LEAD,
            ROLE_SECRETARIAT,
            ROLE_DATA_STEWARD,
            ROLE_ADMIN,
            ROLE_TECHNICAL_COMMITTEE,
            ROLE_PUBLISHING_AUTHORITY,
        )
    )


def _serialize_section_response(row):
    ensure_initial_revision(section_response=row, author=row.updated_by)
    latest_revision = row.revisions.order_by("-version", "-id").first()
    return {
        "uuid": str(row.uuid),
        "section_code": row.section.code,
        "section_title": row.section.title,
        "ordering": row.section.ordering,
        "response_json": row.response_json,
        "current_version": row.current_version,
        "current_content_hash": row.current_content_hash,
        "locked_for_editing": row.locked_for_editing,
        "updated_by": row.updated_by.username if row.updated_by_id else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "latest_revision_uuid": str(latest_revision.uuid) if latest_revision else None,
    }


def _get_cbd_pack_response(instance, section_code):
    pack = resolve_cbd_pack()
    section = get_object_or_404(pack.sections.filter(is_active=True), code=section_code)
    response, _created = ReportTemplatePackResponse.objects.get_or_create(
        reporting_instance=instance,
        section=section,
        defaults={"response_json": build_default_response_payload(section)},
    )
    ensure_initial_revision(section_response=response, author=response.updated_by)
    return pack, section, response


def _deep_clone(value):
    return json.loads(json.dumps(value or {}))


def _section_preview_html(section_title, response_json, narrative_html=""):
    rows = []
    for key in sorted((response_json or {}).keys()):
        value = response_json.get(key)
        rows.append(
            (
                "<div class='field'>"
                f"<div class='label'>{key}</div>"
                f"<div class='value'>{json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value}</div>"
                "</div>"
            )
        )
    narrative = narrative_html or ""
    return (
        "<section class='report-preview-section'>"
        f"<h2>{section_title}</h2>"
        + "".join(rows)
        + ("<div class='narrative-block'>" + narrative + "</div>" if narrative else "")
        + "</section>"
    )


def _resolve_export_context(instance, user, raw_context):
    parsed = normalize_context_filters(raw_context)
    has_any = any(str(value or "").strip() for value in parsed.values())
    session_key = ""
    if hasattr(user, "is_authenticated") and user.is_authenticated:
        session_key = ""
    if has_any:
        context_row = persist_report_context(
            instance=instance,
            user=user if getattr(user, "is_authenticated", False) else None,
            session_key=session_key,
            filters=parsed,
        )
        return context_row.filters_json
    latest = (
        ReportContext.objects.filter(
            reporting_instance=instance,
            user=user if getattr(user, "is_authenticated", False) else None,
        )
        .order_by("-updated_at", "-id")
        .first()
    )
    return latest.filters_json if latest else {}


def _attach_context_rendering(payload, instance, context_filters):
    payload = _deep_clone(payload)
    sections = payload.get("sections") or []
    manifest = []
    for section in sections:
        section_code = section.get("code")
        if not section_code:
            continue
        rendered = render_section_narrative(
            instance=instance,
            section_code=section_code,
            context_filters=context_filters,
        )
        section["rendered_narrative_html"] = rendered.get("rendered_html", "")
        section_manifest = rendered.get("resolved_values_manifest", [])
        section["resolved_values_manifest"] = section_manifest
        manifest.extend(section_manifest)
    payload["context_filters"] = context_filters or {}
    payload["resolved_values_manifest"] = manifest
    return payload, manifest


def _programme_queryset_for_user(user):
    return filter_monitoring_programmes_for_user(
        MonitoringProgramme.objects.select_related("lead_org", "sensitivity_class", "agreement").prefetch_related(
            "partners",
            "operating_institutions",
            "steward_assignments__user",
        ),
        user,
    ).order_by("programme_code", "uuid")


def _programme_run_payload(run):
    def _row_identifier(row):
        return str(getattr(row, "uuid", row.pk))

    return {
        "uuid": str(run.uuid),
        "run_type": run.run_type,
        "trigger": run.trigger,
        "status": run.status,
        "dry_run": run.dry_run,
        "requested_by": run.requested_by.username if run.requested_by_id else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "input_summary_json": run.input_summary_json,
        "output_summary_json": run.output_summary_json,
        "lineage_json": run.lineage_json,
        "log_excerpt": run.log_excerpt,
        "error_message": run.error_message,
        "created_at": run.created_at.isoformat(),
        "artefacts": [
            {
                "uuid": _row_identifier(row),
                "label": row.label,
                "storage_path": row.storage_path,
                "media_type": row.media_type,
                "checksum_sha256": row.checksum_sha256,
                "size_bytes": row.size_bytes,
                "metadata_json": row.metadata_json,
                "created_at": row.created_at.isoformat(),
            }
            for row in run.artefacts.all().order_by("created_at", "id")
        ],
        "qa_results": [
            {
                "uuid": _row_identifier(row),
                "code": row.code,
                "status": row.status,
                "message": row.message,
                "details_json": row.details_json,
                "created_at": row.created_at.isoformat(),
            }
            for row in run.qa_results.all().order_by("created_at", "id")
        ],
        "report_url": reverse("api_programme_run_report", kwargs={"run_uuid": str(run.uuid)}),
        "steps": [
            {
                "ordering": step.ordering,
                "step_key": step.step_key,
                "step_type": step.step_type,
                "status": step.status,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "finished_at": step.finished_at.isoformat() if step.finished_at else None,
                "details_json": step.details_json,
            }
            for step in run.steps.all().order_by("ordering", "id")
        ],
    }


def _programme_summary_payload(programme):
    latest_run = programme.runs.order_by("-created_at", "-id").first()
    open_alerts = programme.alerts.filter(state=ProgrammeAlertState.OPEN).count()
    return {
        "uuid": str(programme.uuid),
        "programme_code": programme.programme_code,
        "title": programme.title,
        "programme_type": programme.programme_type,
        "refresh_cadence": programme.refresh_cadence,
        "scheduler_enabled": programme.scheduler_enabled,
        "next_run_at": programme.next_run_at.isoformat() if programme.next_run_at else None,
        "last_run_at": programme.last_run_at.isoformat() if programme.last_run_at else None,
        "lead_org": programme.lead_org.name if programme.lead_org_id else None,
        "open_alert_count": open_alerts,
        "latest_run_status": latest_run.status if latest_run else None,
        "dataset_link_count": programme.dataset_links.filter(is_active=True).count(),
        "indicator_link_count": programme.indicator_links.filter(is_active=True).count(),
    }


def _default_pack_response_payload(section):
    return build_default_response_payload(section)


def _service_status(service, status, detail=None):
    payload = {"service": service, "status": status}
    if detail:
        payload["detail"] = detail
    return payload


def _database_health():
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
        return _service_status("database", "ok")
    except Exception as exc:  # noqa: BLE001
        return _service_status("database", "error", str(exc))


def _storage_health():
    if not getattr(settings, "USE_S3", False):
        return _service_status("storage", "disabled", "USE_S3=0")
    try:
        default_storage.listdir("")
        return _service_status("storage", "ok")
    except Exception as exc:  # noqa: BLE001
        return _service_status("storage", "error", str(exc))


def _cache_health():
    cache_key = "__nbms_health_probe__"
    try:
        cache.set(cache_key, "ok", timeout=10)
        echoed = cache.get(cache_key)
        if echoed != "ok":
            return _service_status("cache", "degraded", "Read/write probe did not round-trip.")
        return _service_status("cache", "ok")
    except Exception as exc:  # noqa: BLE001
        return _service_status("cache", "error", str(exc))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_auth_me(request):
    user = request.user
    organisation = getattr(user, "organisation", None)
    return Response(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.get_full_name(),
            "roles": _user_role_names(user),
            "organisation": {
                "id": organisation.id if organisation else None,
                "name": organisation.name if organisation else None,
            },
            "capabilities": user_capabilities(user),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_auth_capabilities(request):
    return Response({"capabilities": user_capabilities(request.user)})


@api_view(["GET"])
@permission_classes([AllowAny])
def api_auth_csrf(request):
    token = get_token(request)
    return Response({"csrfToken": token})


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def api_me_preferences(request):
    preference = _user_preference_for(request.user)
    if request.method == "GET":
        return Response(_serialize_user_preference(preference))

    payload = request.data
    if not isinstance(payload, dict):
        raise ParseError("Expected object payload.")

    update_fields = []

    if "theme_id" in payload:
        theme_id = str(payload.get("theme_id") or "").strip()
        if theme_id not in _PREFERENCE_THEMES:
            options = ", ".join(sorted(_PREFERENCE_THEMES))
            raise ParseError(f"Invalid theme_id. Expected one of: {options}.")
        preference.theme_id = theme_id
        update_fields.append("theme_id")

    if "theme_mode" in payload:
        theme_mode = str(payload.get("theme_mode") or "").strip().lower()
        if theme_mode not in _PREFERENCE_THEME_MODES:
            options = ", ".join(sorted(_PREFERENCE_THEME_MODES))
            raise ParseError(f"Invalid theme_mode. Expected one of: {options}.")
        preference.theme_mode = theme_mode
        update_fields.append("theme_mode")

    if "density" in payload:
        density = str(payload.get("density") or "").strip().lower()
        if density not in _PREFERENCE_DENSITIES:
            options = ", ".join(sorted(_PREFERENCE_DENSITIES))
            raise ParseError(f"Invalid density. Expected one of: {options}.")
        preference.density = density
        update_fields.append("density")

    if "default_geography" in payload:
        geography_payload = payload.get("default_geography") or {}
        if not isinstance(geography_payload, dict):
            raise ParseError("default_geography must be an object with 'type' and optional 'code'.")
        geography_type = str(geography_payload.get("type") or "").strip().lower()
        if geography_type not in _PREFERENCE_GEOS:
            options = ", ".join(sorted(_PREFERENCE_GEOS))
            raise ParseError(f"Invalid default_geography.type. Expected one of: {options}.")
        preference.default_geography = geography_type
        preference.default_geography_code = str(geography_payload.get("code") or "").strip()
        update_fields.extend(["default_geography", "default_geography_code"])

    if "saved_filters" in payload:
        if not isinstance(payload.get("saved_filters"), dict):
            raise ParseError("saved_filters must be an object.")
        preference.saved_filters = _normalize_saved_filters_payload(payload.get("saved_filters"))
        update_fields.append("saved_filters")

    if "watchlist" in payload:
        if not isinstance(payload.get("watchlist"), dict):
            raise ParseError("watchlist must be an object.")
        preference.watchlist = _normalize_watchlist_payload(payload.get("watchlist"))
        update_fields.append("watchlist")

    if "dashboard_layout" in payload:
        if not isinstance(payload.get("dashboard_layout"), dict):
            raise ParseError("dashboard_layout must be an object.")
        preference.dashboard_layout = _normalize_dashboard_layout(payload.get("dashboard_layout"))
        update_fields.append("dashboard_layout")

    if update_fields:
        preference.save(update_fields=[*sorted(set(update_fields)), "updated_at"])

    return Response(_serialize_user_preference(preference))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_me_preferences_watchlist_add(request):
    preference = _user_preference_for(request.user)
    payload = request.data
    if not isinstance(payload, dict):
        raise ParseError("Expected object payload.")
    namespace = _required_namespace(
        payload.get("namespace") or payload.get("kind") or payload.get("feature"),
        allowed=_PREFERENCE_WATCHLIST_NAMESPACES,
        label="watchlist namespace",
    )
    item_id = str(payload.get("uuid") or payload.get("id") or payload.get("item_id") or "").strip()
    if not item_id:
        raise ParseError("uuid (or id/item_id) is required.")

    watchlist = _normalize_watchlist_payload(preference.watchlist)
    if item_id not in watchlist[namespace]:
        watchlist[namespace] = sorted([*watchlist[namespace], item_id])
        preference.watchlist = watchlist
        preference.save(update_fields=["watchlist", "updated_at"])

    return Response(
        {
            "watchlist": watchlist,
            "namespace": namespace,
            "item_id": item_id,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_me_preferences_watchlist_remove(request):
    preference = _user_preference_for(request.user)
    payload = request.data
    if not isinstance(payload, dict):
        raise ParseError("Expected object payload.")
    namespace = _required_namespace(
        payload.get("namespace") or payload.get("kind") or payload.get("feature"),
        allowed=_PREFERENCE_WATCHLIST_NAMESPACES,
        label="watchlist namespace",
    )
    item_id = str(payload.get("uuid") or payload.get("id") or payload.get("item_id") or "").strip()
    if not item_id:
        raise ParseError("uuid (or id/item_id) is required.")

    watchlist = _normalize_watchlist_payload(preference.watchlist)
    if item_id in watchlist[namespace]:
        watchlist[namespace] = [row for row in watchlist[namespace] if row != item_id]
        preference.watchlist = watchlist
        preference.save(update_fields=["watchlist", "updated_at"])

    return Response(
        {
            "watchlist": watchlist,
            "namespace": namespace,
            "item_id": item_id,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_me_preferences_saved_filters(request):
    preference = _user_preference_for(request.user)
    payload = request.data
    if not isinstance(payload, dict):
        raise ParseError("Expected object payload.")

    namespace = _required_namespace(
        payload.get("namespace") or payload.get("kind") or payload.get("feature"),
        allowed=_PREFERENCE_FILTER_NAMESPACES,
        label="saved-filter namespace",
    )
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ParseError("name is required.")

    params = payload.get("params")
    if params is None:
        params = payload.get("query_snapshot")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ParseError("params (or query_snapshot) must be an object.")

    pinned = bool(payload.get("pinned", False))
    saved_filters = _normalize_saved_filters_payload(preference.saved_filters)

    entry_id = str(payload.get("id") or "").strip() or str(uuid4())
    entry = {
        "id": entry_id,
        "name": name,
        "params": params,
        "pinned": pinned,
        "updated_at": timezone.now().isoformat(),
    }

    namespace_rows = [row for row in saved_filters[namespace] if row.get("id") != entry_id]
    namespace_rows.insert(0, entry)
    saved_filters[namespace] = namespace_rows

    preference.saved_filters = saved_filters
    preference.save(update_fields=["saved_filters", "updated_at"])
    return Response(
        {
            "saved_filters": saved_filters,
            "entry": entry,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def api_me_preferences_saved_filter_delete(request, filter_id):
    preference = _user_preference_for(request.user)
    saved_filters = _normalize_saved_filters_payload(preference.saved_filters)
    namespace = (request.GET.get("namespace") or "").strip().lower()

    removed = False
    if namespace:
        _required_namespace(
            namespace,
            allowed=_PREFERENCE_FILTER_NAMESPACES,
            label="saved-filter namespace",
        )
        rows = saved_filters[namespace]
        saved_filters[namespace] = [row for row in rows if str(row.get("id")) != str(filter_id)]
        removed = len(rows) != len(saved_filters[namespace])
    else:
        for key in _PREFERENCE_FILTER_NAMESPACES:
            rows = saved_filters[key]
            saved_filters[key] = [row for row in rows if str(row.get("id")) != str(filter_id)]
            removed = removed or (len(rows) != len(saved_filters[key]))

    if removed:
        preference.saved_filters = saved_filters
        preference.save(update_fields=["saved_filters", "updated_at"])

    return Response(
        {
            "deleted": removed,
            "saved_filters": saved_filters,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_help_sections(request):
    return Response(
        {
            "version": "2026-02-06",
            "sections": SECTION_FIELD_HELP,
            "sections_rich": build_section_help_payload(),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_system_health(request):
    if not (is_system_admin(request.user) or getattr(request.user, "is_staff", False)):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    checks = [
        _database_health(),
        _storage_health(),
        _cache_health(),
    ]
    is_healthy = all(item["status"] in {"ok", "disabled"} for item in checks)
    recent_failures = (
        AuditEvent.objects.filter(
            action__in=[
                "reject",
                "export_reject",
                "instance_export_blocked_consent",
                "instance_export_override",
            ],
            created_at__gte=timezone.now() - timedelta(days=7),
        )
        .order_by("-created_at", "action", "id")[:25]
    )
    return Response(
        {
            "overall_status": "ok" if is_healthy else "degraded",
            "services": checks,
            "recent_failures": [
                {
                    "action": event.action,
                    "event_type": event.event_type,
                    "object_type": event.object_type,
                    "object_uuid": str(event.object_uuid) if event.object_uuid else None,
                    "created_at": event.created_at.isoformat(),
                }
                for event in recent_failures
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_dashboard_summary(request):
    user = request.user
    instances_qs = ReportingInstance.objects.select_related("cycle").order_by("-updated_at")
    if not (is_system_admin(user) or getattr(user, "is_staff", False)):
        instances_qs = instances_qs.none()

    counts = {
        "instances_draft": instances_qs.filter(status=ReportingStatus.DRAFT).count(),
        "instances_in_review": instances_qs.filter(status=ReportingStatus.PENDING_REVIEW).count(),
        "instances_approved": instances_qs.filter(status=ReportingStatus.APPROVED).count(),
        "instances_released": instances_qs.filter(status=ReportingStatus.RELEASED).count(),
    }

    indicator_qs = _indicator_base_queryset(user)
    published_qs = indicator_qs.filter(status=LifecycleStatus.PUBLISHED)

    approvals_queue = indicator_qs.filter(status=LifecycleStatus.PENDING_REVIEW).count()
    latest_updates = [
        _indicator_payload(item)
        for item in published_qs.order_by("-updated_at", "code")[:8]
    ]

    quality_alerts = []
    for indicator in indicator_qs.order_by("code"):
        issues = []
        if indicator.qa_status != "approved":
            issues.append("QA status not approved")
        if not IndicatorDataSeries.objects.filter(indicator=indicator).exists():
            issues.append("No data series linked")
        if issues:
            quality_alerts.append(
                {
                    "indicator_uuid": str(indicator.uuid),
                    "indicator_code": indicator.code,
                    "issues": issues,
                }
            )

    chart_by_target = (
        IndicatorFrameworkIndicatorLink.objects.filter(
            indicator__in=published_qs,
            is_active=True,
            framework_indicator__framework_target__isnull=False,
        )
        .values(
            "framework_indicator__framework_target__framework__code",
            "framework_indicator__framework_target__code",
        )
        .annotate(total=Count("id"))
        .order_by(
            "framework_indicator__framework_target__framework__code",
            "framework_indicator__framework_target__code",
        )
    )

    approvals_over_time = (
        AuditEvent.objects.filter(
            action__in=["approve", "publish"],
            created_at__gte=timezone.now() - timedelta(days=90),
        )
        .extra(select={"day": "date(created_at)"})
        .values("day", "action")
        .annotate(total=Count("id"))
        .order_by("day", "action")
    )

    trend_signals = []
    for indicator in published_qs.order_by("code")[:12]:
        series = indicator_data_series_for_user(user).filter(indicator=indicator).first()
        signal = "flat"
        if series:
            points = list(
                indicator_data_points_for_user(user)
                .filter(series=series, value_numeric__isnull=False)
                .order_by("-year", "-id")[:2]
            )
            if len(points) == 2:
                if points[0].value_numeric > points[1].value_numeric:
                    signal = "up"
                elif points[0].value_numeric < points[1].value_numeric:
                    signal = "down"
        trend_signals.append(
            {
                "indicator_uuid": str(indicator.uuid),
                "indicator_code": indicator.code,
                "trend": signal,
            }
        )

    readiness_totals = {"ready": 0, "warning": 0, "blocked": 0}
    readiness_by_target_data = {}
    for indicator in published_qs.select_related("national_target").order_by("code"):
        payload = _indicator_payload(indicator)
        readiness_status = payload.get("readiness_status") or "blocked"
        readiness_score = int(payload.get("readiness_score") or 0)
        readiness_totals[readiness_status] = readiness_totals.get(readiness_status, 0) + 1
        target = indicator.national_target
        target_key = str(target.uuid) if target else "unmapped"
        row = readiness_by_target_data.setdefault(
            target_key,
            {
                "target_uuid": str(target.uuid) if target else None,
                "target_code": target.code if target else "UNMAPPED",
                "target_title": target.title if target else "Unmapped indicators",
                "indicator_count": 0,
                "readiness_score_total": 0,
                "ready_count": 0,
                "warning_count": 0,
                "blocked_count": 0,
            },
        )
        row["indicator_count"] += 1
        row["readiness_score_total"] += readiness_score
        row[f"{readiness_status}_count"] += 1
    readiness_by_target = []
    for row in readiness_by_target_data.values():
        indicator_count = max(1, row["indicator_count"])
        readiness_by_target.append(
            {
                "target_uuid": row["target_uuid"],
                "target_code": row["target_code"],
                "target_title": row["target_title"],
                "indicator_count": row["indicator_count"],
                "readiness_score_avg": round(row["readiness_score_total"] / indicator_count),
                "ready_count": row["ready_count"],
                "warning_count": row["warning_count"],
                "blocked_count": row["blocked_count"],
            }
        )
    readiness_by_target.sort(key=lambda item: (-item["readiness_score_avg"], item["target_code"] or ""))

    return Response(
        {
            "counts": counts,
            "approvals_queue": approvals_queue,
            "latest_published_updates": latest_updates,
            "data_quality_alerts": quality_alerts[:20],
            "published_by_framework_target": list(chart_by_target),
            "approvals_over_time": list(approvals_over_time),
            "trend_signals": trend_signals,
            "indicator_readiness": {
                "totals": readiness_totals,
                "by_target": readiness_by_target[:20],
            },
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_programme_list(request):
    queryset = _programme_queryset_for_user(request.user)
    status_filter = (request.GET.get("status") or "").strip().lower()
    if status_filter:
        queryset = queryset.filter(runs__status=status_filter)
    search = (request.GET.get("search") or "").strip()
    if search:
        queryset = queryset.filter(
            Q(programme_code__icontains=search)
            | Q(title__icontains=search)
            | Q(description__icontains=search)
        )
    rows = [_programme_summary_payload(programme) for programme in queryset]
    return Response({"programmes": rows})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_programme_detail(request, programme_uuid):
    programme = get_object_or_404(_programme_queryset_for_user(request.user), uuid=programme_uuid)
    runs = (
        programme.runs.select_related("requested_by")
        .prefetch_related("steps", "artefacts", "qa_results")
        .order_by("-created_at", "-id")[:20]
    )
    alerts = (
        programme.alerts.select_related("run", "created_by", "resolved_by")
        .order_by("state", "-created_at", "code")[:50]
    )
    stewards = (
        programme.steward_assignments.filter(is_active=True)
        .select_related("user")
        .order_by("-is_primary", "role", "user__username")
    )
    return Response(
        {
            "programme": {
                **_programme_summary_payload(programme),
                "description": programme.description,
                "geographic_scope": programme.geographic_scope,
                "taxonomic_scope": programme.taxonomic_scope,
                "ecosystem_scope": programme.ecosystem_scope,
                "consent_required": programme.consent_required,
                "sensitivity_class": (
                    programme.sensitivity_class.sensitivity_code if programme.sensitivity_class_id else None
                ),
                "agreement_code": programme.agreement.agreement_code if programme.agreement_id else None,
                "pipeline_definition_json": programme.pipeline_definition_json,
                "data_quality_rules_json": programme.data_quality_rules_json,
                "lineage_notes": programme.lineage_notes,
                "website_url": programme.website_url,
                "operating_institutions": [
                    {"id": org.id, "name": org.name, "org_code": org.org_code}
                    for org in programme.operating_institutions.all().order_by("name", "id")
                ],
                "partners": [
                    {"id": org.id, "name": org.name, "org_code": org.org_code}
                    for org in programme.partners.all().order_by("name", "id")
                ],
                "stewards": [
                    {
                        "user_id": assignment.user_id,
                        "username": assignment.user.username,
                        "role": assignment.role,
                        "is_primary": assignment.is_primary,
                    }
                    for assignment in stewards
                ],
            },
            "runs": [_programme_run_payload(run) for run in runs],
            "alerts": [
                {
                    "uuid": str(alert.uuid),
                    "severity": alert.severity,
                    "state": alert.state,
                    "code": alert.code,
                    "message": alert.message,
                    "details_json": alert.details_json,
                    "run_uuid": str(alert.run.uuid) if alert.run_id else None,
                    "created_by": alert.created_by.username if alert.created_by_id else None,
                    "created_at": alert.created_at.isoformat(),
                    "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                    "resolved_by": alert.resolved_by.username if alert.resolved_by_id else None,
                }
                for alert in alerts
            ],
            "can_manage": user_can_manage_programme(request.user, programme),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_programme_run_create(request, programme_uuid):
    programme = get_object_or_404(_programme_queryset_for_user(request.user), uuid=programme_uuid)
    if not user_can_manage_programme(request.user, programme):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    run_type = (request.data.get("run_type") or ProgrammeRunType.FULL).strip().lower()
    if run_type not in ProgrammeRunType.values:
        return Response({"detail": "Invalid run_type."}, status=status.HTTP_400_BAD_REQUEST)
    dry_run = bool(request.data.get("dry_run", False))
    execute_now = bool(request.data.get("execute_now", True))
    run = queue_programme_run(
        programme=programme,
        requested_by=request.user,
        run_type=run_type,
        dry_run=dry_run,
        execute_now=execute_now,
        request_id=request.headers.get("X-Request-ID", ""),
    )
    run = MonitoringProgrammeRun.objects.select_related("requested_by").prefetch_related("steps").get(pk=run.pk)
    return Response(_programme_run_payload(run), status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_programme_run_detail(request, run_uuid):
    run = get_object_or_404(
        MonitoringProgrammeRun.objects.select_related("programme", "requested_by").prefetch_related(
            "steps",
            "artefacts",
            "qa_results",
        ),
        uuid=run_uuid,
        programme__in=_programme_queryset_for_user(request.user),
    )
    programme = run.programme
    if request.method == "POST":
        if not user_can_manage_programme(request.user, programme):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        if run.status == ProgrammeRunStatus.RUNNING:
            return Response({"detail": "Run is already executing."}, status=status.HTTP_409_CONFLICT)
        run = execute_programme_run(run=run, actor=request.user)
        run.refresh_from_db()
    return Response(_programme_run_payload(run))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_programme_run_report(request, run_uuid):
    run = get_object_or_404(
        MonitoringProgrammeRun.objects.select_related("programme", "requested_by").prefetch_related(
            "steps",
            "artefacts",
            "qa_results",
        ),
        uuid=run_uuid,
        programme__in=_programme_queryset_for_user(request.user),
    )
    payload = {
        "generated_at": timezone.now().isoformat(),
        "programme": {
            "uuid": str(run.programme.uuid),
            "programme_code": run.programme.programme_code,
            "title": run.programme.title,
        },
        "run": _programme_run_payload(run),
    }
    response = Response(payload)
    response["Content-Disposition"] = f'attachment; filename="programme-run-{run.uuid}.json"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_birdie_dashboard(request):
    programme = get_object_or_404(
        _programme_queryset_for_user(request.user).filter(programme_code="NBMS-BIRDIE-INTEGRATION")
    )
    allow_restricted = bool(is_system_admin(request.user) or getattr(request.user, "is_staff", False))

    sites_qs = BirdieSite.objects.order_by("province_code", "site_code")
    species_qs = BirdieSpecies.objects.order_by("species_code")
    outputs_qs = BirdieModelOutput.objects.select_related("site", "species").order_by(
        "metric_code",
        "year",
        "site__site_code",
        "species__species_code",
    )
    if not allow_restricted:
        sites_qs = sites_qs.filter(is_restricted=False)
        species_qs = species_qs.filter(is_restricted=False)
        outputs_qs = outputs_qs.filter(is_restricted=False)

    site_reports = []
    outputs_by_site = defaultdict(list)
    for row in outputs_qs.filter(metric_code="waterbird_abundance_trend"):
        if row.site_id:
            outputs_by_site[row.site_id].append(row)
    richness_by_site = defaultdict(dict)
    for row in outputs_qs.filter(metric_code="species_richness_trend"):
        if row.site_id and row.value_numeric is not None:
            richness_by_site[row.site_id][row.year] = float(row.value_numeric)

    for site in sites_qs:
        rows = outputs_by_site.get(site.id, [])
        latest = rows[-1] if rows else None
        previous = rows[-2] if len(rows) > 1 else None
        trend = "flat"
        if latest and previous and latest.value_numeric is not None and previous.value_numeric is not None:
            if latest.value_numeric > previous.value_numeric:
                trend = "up"
            elif latest.value_numeric < previous.value_numeric:
                trend = "down"
        site_reports.append(
            {
                "site_code": site.site_code,
                "site_name": site.site_name,
                "province_code": site.province_code,
                "last_year": latest.year if latest else None,
                "abundance_index": float(latest.value_numeric) if latest and latest.value_numeric is not None else None,
                "richness": richness_by_site.get(site.id, {}).get(latest.year if latest else None),
                "trend": trend,
            }
        )

    species_reports = []
    outputs_by_species = defaultdict(list)
    for row in outputs_qs.filter(metric_code="waterbird_abundance_trend"):
        if row.species_id:
            outputs_by_species[row.species_id].append(row)
    for species in species_qs:
        rows = outputs_by_species.get(species.id, [])
        latest = rows[-1] if rows else None
        previous = rows[-2] if len(rows) > 1 else None
        trend = "flat"
        if latest and previous and latest.value_numeric is not None and previous.value_numeric is not None:
            if latest.value_numeric > previous.value_numeric:
                trend = "up"
            elif latest.value_numeric < previous.value_numeric:
                trend = "down"
        species_reports.append(
            {
                "species_code": species.species_code,
                "common_name": species.common_name,
                "guild": species.guild,
                "last_year": latest.year if latest else None,
                "last_value": float(latest.value_numeric) if latest and latest.value_numeric is not None else None,
                "trend": trend,
            }
        )

    layers = filter_spatial_layers_for_user(
        SpatialLayer.objects.filter(slug__startswith="birdie-").select_related("indicator"),
        request.user,
    ).order_by("name", "slug")
    provenance_rows = (
        IntegrationDataAsset.objects.filter(source_system="BIRDIE", layer="bronze")
        .order_by("dataset_key", "-updated_at")
    )
    seen_datasets = set()
    provenance = []
    for row in provenance_rows:
        if row.dataset_key in seen_datasets:
            continue
        seen_datasets.add(row.dataset_key)
        provenance.append(
            {
                "dataset_key": row.dataset_key,
                "captured_at": row.updated_at.isoformat(),
                "payload_hash": row.payload_hash,
                "source_endpoint": row.source_endpoint,
            }
        )

    return Response(
        {
            "programme": _programme_summary_payload(programme),
            "site_reports": site_reports,
            "species_reports": species_reports,
            "map_layers": [
                {
                    "slug": layer.slug,
                    "name": layer.name,
                    "indicator_code": layer.indicator.code if layer.indicator_id else None,
                }
                for layer in layers
            ],
            "provenance": provenance,
        }
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_reporting_instances(request):
    if not (is_system_admin(request.user) or getattr(request.user, "is_staff", False)):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "POST":
        if not (
            is_system_admin(request.user)
            or user_has_role(request.user, ROLE_SECTION_LEAD, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN)
        ):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        body = request.data or {}
        report_label = str(body.get("report_label") or "NR7").strip().upper()
        if report_label not in {"NR7", "NR8"}:
            return Response({"detail": "report_label must be NR7 or NR8."}, status=status.HTTP_400_BAD_REQUEST)
        country_name = (body.get("country_name") or "South Africa").strip() or "South Africa"
        is_public = _parse_bool(body.get("is_public"), False)
        version_label = (body.get("version_label") or "v1").strip() or "v1"

        try:
            period_start = _parse_iso_date(body.get("reporting_period_start"))
            period_end = _parse_iso_date(body.get("reporting_period_end"))
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if period_start and period_end and period_end < period_start:
            return Response(
                {"detail": "reporting_period_end must be on or after reporting_period_start."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cycle_code = (body.get("cycle_code") or report_label).strip().upper()
        cycle_defaults = {
            "title": f"{report_label} National Report Cycle",
            "start_date": period_start or date.today().replace(month=1, day=1),
            "end_date": period_end or date.today().replace(month=12, day=31),
            "due_date": (period_end or date.today().replace(month=12, day=31)),
            "default_language": "English",
            "allowed_languages": ["English", "French", "Spanish", "Arabic", "Chinese", "Russian"],
            "is_active": True,
        }
        cycle, _ = ReportingCycle.objects.update_or_create(code=cycle_code, defaults=cycle_defaults)

        instance = ReportingInstance.objects.create(
            cycle=cycle,
            report_family="CBD_NATIONAL_REPORT",
            report_label=report_label,
            version_label=version_label,
            reporting_period_start=period_start or cycle.start_date,
            reporting_period_end=period_end or cycle.end_date,
            report_title=(body.get("report_title") or f"{country_name} {report_label}").strip(),
            country_name=country_name,
            is_public=is_public,
            focal_point_org=getattr(request.user, "organisation", None),
            publishing_authority_org=getattr(request.user, "organisation", None),
            created_by=request.user,
            updated_by=request.user,
            status=ReportingStatus.DRAFT,
        )

        pack = resolve_cbd_pack()
        for section in pack.sections.filter(is_active=True).order_by("ordering", "code"):
            response_json = build_default_response_payload(section)
            if section.code == "section-i":
                response_json["report_label"] = report_label
                response_json["country_or_reporting_party_name"] = country_name
                response_json["public_availability"] = "public" if is_public else "internal"
            ReportTemplatePackResponse.objects.create(
                reporting_instance=instance,
                section=section,
                response_json=response_json,
                updated_by=request.user if request.user.is_authenticated else None,
            )
        record_audit_event(
            request.user,
            "reporting_instance_create",
            instance,
            metadata={
                "report_family": instance.report_family,
                "report_label": instance.report_label,
                "reporting_period_start": (
                    instance.reporting_period_start.isoformat() if instance.reporting_period_start else None
                ),
                "reporting_period_end": (
                    instance.reporting_period_end.isoformat() if instance.reporting_period_end else None
                ),
                "is_public": instance.is_public,
                "pack_code": pack.code,
            },
        )
        return Response(
            {
                "instance": {
                    "uuid": str(instance.uuid),
                    "cycle_code": instance.cycle.code,
                    "cycle_title": instance.cycle.title,
                    "report_family": instance.report_family,
                    "report_label": instance.report_label,
                    "version_label": instance.version_label,
                    "status": instance.status,
                    "is_public": instance.is_public,
                    "reporting_period_start": (
                        instance.reporting_period_start.isoformat() if instance.reporting_period_start else None
                    ),
                    "reporting_period_end": (
                        instance.reporting_period_end.isoformat() if instance.reporting_period_end else None
                    ),
                },
                "workspace_url": reverse("api_reporting_workspace_summary", kwargs={"instance_uuid": instance.uuid}),
            },
            status=status.HTTP_201_CREATED,
        )

    queryset = (
        ReportingInstance.objects.select_related("cycle", "frozen_by")
        .order_by("-cycle__start_date", "-created_at", "uuid")
    )
    rows = []
    for instance in queryset:
        if not _require_instance_scope(request.user, instance):
            continue
        readiness = get_instance_readiness(instance, request.user)
        rows.append(
            {
                "uuid": str(instance.uuid),
                "cycle_code": instance.cycle.code,
                "cycle_title": instance.cycle.title,
                "report_family": instance.report_family,
                "report_label": instance.report_label,
                "version_label": instance.version_label,
                "reporting_period_start": (
                    instance.reporting_period_start.isoformat() if instance.reporting_period_start else None
                ),
                "reporting_period_end": (
                    instance.reporting_period_end.isoformat() if instance.reporting_period_end else None
                ),
                "is_public": bool(instance.is_public),
                "status": instance.status,
                "frozen_at": instance.frozen_at.isoformat() if instance.frozen_at else None,
                "readiness_status": readiness.get("status", "unknown"),
                "readiness_score": readiness.get("score"),
            }
        )
    return Response({"instances": rows})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_nr7_summary(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    if not _require_instance_scope(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    validation = build_nr7_validation_summary(instance=instance, user=request.user)
    preview = build_nr7_preview_payload(instance=instance, user=request.user)
    map_layers = filter_spatial_layers_for_user(
        SpatialLayer.objects.filter(is_active=True).select_related("indicator"),
        request.user,
    ).order_by("theme", "title", "name", "layer_code")
    links = {
        "sections_overview": reverse("nbms_app:reporting_instance_sections", kwargs={"instance_uuid": instance.uuid}),
        "section_i": reverse("nbms_app:reporting_instance_section_i", kwargs={"instance_uuid": instance.uuid}),
        "section_ii": reverse("nbms_app:reporting_instance_section_ii", kwargs={"instance_uuid": instance.uuid}),
        "section_iii": reverse("nbms_app:reporting_instance_section_iii", kwargs={"instance_uuid": instance.uuid}),
        "section_iv_goals": reverse("nbms_app:reporting_instance_section_iv_goals", kwargs={"instance_uuid": instance.uuid}),
        "section_iv_targets": reverse("nbms_app:reporting_instance_section_iv", kwargs={"instance_uuid": instance.uuid}),
        "section_v": reverse("nbms_app:reporting_instance_section_v", kwargs={"instance_uuid": instance.uuid}),
        "pdf_export": reverse("api_reporting_nr7_pdf", kwargs={"instance_uuid": instance.uuid}),
    }
    return Response(
        {
            "instance": {
                "uuid": str(instance.uuid),
                "cycle_code": instance.cycle.code,
                "cycle_title": instance.cycle.title,
                "version_label": instance.version_label,
                "status": instance.status,
                "frozen_at": instance.frozen_at.isoformat() if instance.frozen_at else None,
            },
            "validation": validation,
            "preview_payload": preview["preview_payload"],
            "preview_error": preview["preview_error"],
            "map_layers": [
                {
                    "layer_code": layer.layer_code,
                    "title": layer.title or layer.name,
                    "caption": layer.description,
                    "provenance": {
                        "source_type": layer.source_type,
                        "data_ref": layer.data_ref,
                        "attribution": layer.attribution,
                        "license": layer.license,
                    },
                    "export_ready": bool(layer.export_approved),
                }
                for layer in map_layers
            ],
            "links": links,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_nr7_pdf(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    if not _require_instance_scope(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        pdf_bytes = render_nr7_pdf_bytes(instance=instance, user=request.user)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="nr7-{instance.uuid}.pdf"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_summary(request, instance_uuid):
    instance = get_object_or_404(
        ReportingInstance.objects.select_related("cycle", "focal_point_org", "publishing_authority_org"),
        uuid=instance_uuid,
    )
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    pack = resolve_cbd_pack()
    workflow = ensure_workflow_instance(instance)
    _sections = list(pack.sections.filter(is_active=True).order_by("ordering", "code"))
    responses = (
        ReportTemplatePackResponse.objects.filter(reporting_instance=instance, section__pack=pack)
        .select_related("section", "updated_by")
        .prefetch_related("revisions")
        .order_by("section__ordering", "section__code")
    )
    response_map = {row.section.code: row for row in responses}
    section_rows = []
    for section in _sections:
        row = response_map.get(section.code)
        if row is None:
            row = ReportTemplatePackResponse.objects.create(
                reporting_instance=instance,
                section=section,
                response_json=build_default_response_payload(section),
                updated_by=request.user if request.user.is_authenticated else None,
            )
            ensure_initial_revision(section_response=row, author=request.user)
        section_rows.append(_serialize_section_response(row))

    validation = build_pack_validation(pack=pack, instance=instance, user=request.user)
    payload = build_cbd_report_payload(instance=instance)
    latest_dossier = instance.dossier_artifacts.order_by("-created_at", "-id").first()
    approvals = {
        row.section.code: row
        for row in workflow.section_approvals.select_related("section", "approved_by").order_by("section__ordering", "section__code")
    }
    latest_context = (
        ReportContext.objects.filter(
            reporting_instance=instance,
            user=request.user if request.user.is_authenticated else None,
        )
        .order_by("-updated_at", "-id")
        .first()
    )
    return Response(
        {
            "instance": {
                "uuid": str(instance.uuid),
                "cycle_code": instance.cycle.code if instance.cycle_id else "",
                "cycle_title": instance.cycle.title if instance.cycle_id else "",
                "report_family": instance.report_family,
                "report_label": instance.report_label,
                "version_label": instance.version_label,
                "reporting_period_start": (
                    instance.reporting_period_start.isoformat() if instance.reporting_period_start else None
                ),
                "reporting_period_end": (
                    instance.reporting_period_end.isoformat() if instance.reporting_period_end else None
                ),
                "report_title": instance.report_title,
                "country_name": instance.country_name,
                "status": instance.status,
                "is_public": bool(instance.is_public),
                "focal_point_org": instance.focal_point_org.name if instance.focal_point_org_id else "",
                "publishing_authority_org": (
                    instance.publishing_authority_org.name if instance.publishing_authority_org_id else ""
                ),
                "finalized_at": instance.finalized_at.isoformat() if instance.finalized_at else None,
                "final_content_hash": instance.final_content_hash,
            },
            "pack": {
                "code": pack.code,
                "title": pack.title,
                "version": pack.version,
            },
            "sections": section_rows,
            "section_approvals": [
                {
                    "section_code": section.code,
                    "approved": bool(approvals.get(section.code) and approvals[section.code].approved),
                    "approved_by": approvals[section.code].approved_by.username if approvals.get(section.code) and approvals[section.code].approved_by_id else None,
                    "approved_at": (
                        approvals[section.code].approved_at.isoformat()
                        if approvals.get(section.code) and approvals[section.code].approved_at
                        else None
                    ),
                }
                for section in _sections
            ],
            "workflow": {
                "uuid": str(workflow.uuid),
                "status": workflow.status,
                "current_step": workflow.current_step,
                "locked": workflow.locked,
                "latest_content_hash": workflow.latest_content_hash,
                "actions": [
                    {
                        "uuid": str(row.uuid),
                        "action_type": row.action_type,
                        "actor": row.actor.username if row.actor_id else None,
                        "comment": row.comment,
                        "created_at": row.created_at.isoformat(),
                    }
                    for row in workflow.actions.select_related("actor").order_by("-created_at", "-id")[:25]
                ],
            },
            "signoff_records": [
                {
                    "uuid": str(row.uuid),
                    "signer": row.signer.username if row.signer_id else None,
                    "signer_role": row.signer_role,
                    "body": row.body,
                    "state_from": row.state_from,
                    "state_to": row.state_to,
                    "signed_at": row.signed_at.isoformat() if row.signed_at else None,
                    "comment": row.comment,
                    "snapshot_hash_pointer": row.snapshot_hash_pointer,
                }
                for row in instance.signoff_records.select_related("signer").order_by("-signed_at", "-created_at")[:40]
            ],
            "validation": validation,
            "preview_payload": payload,
            "latest_dossier": read_dossier_manifest(latest_dossier) if latest_dossier else None,
            "context": {
                "filters_json": latest_context.filters_json if latest_context else {},
                "context_hash": latest_context.context_hash if latest_context else "",
            },
            "capabilities": user_capabilities(request.user),
        }
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_section(request, instance_uuid, section_code):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    _pack, _section, response_row = _get_cbd_pack_response(instance, section_code)

    if request.method == "GET":
        ensure_narrative_block(
            instance=instance,
            section_code=section_code,
            block_key="main",
            title=_section.title,
            user=request.user,
        )
        narrative_rows = list_section_narrative_blocks(instance=instance, section_code=section_code)
        payload = _serialize_section_response(response_row)
        payload["schema_json"] = _section.schema_json
        payload["narrative_blocks"] = [
            {
                "uuid": str(row.uuid),
                "section_code": row.section_code,
                "block_key": row.block_key,
                "title": row.title,
                "storage_path": row.storage_path,
                "current_version": row.current_version,
                "current_content_hash": row.current_content_hash,
                "html_snapshot": row.html_snapshot,
                "text_snapshot": row.text_snapshot,
            }
            for row in narrative_rows
        ]
        return Response(payload)

    if not _can_edit_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    body = request.data or {}
    base_version = int(body.get("base_version") or response_row.current_version or 1)
    if base_version != int(response_row.current_version or 1):
        return Response(
            {"detail": "Version conflict. Reload section and retry."},
            status=status.HTTP_409_CONFLICT,
        )
    suggestion_mode = bool(body.get("suggestion_mode"))
    response_json = body.get("response_json") or {}
    if not isinstance(response_json, dict):
        return Response({"detail": "response_json must be an object."}, status=status.HTTP_400_BAD_REQUEST)
    if suggestion_mode:
        patch_json = body.get("patch_json")
        if not isinstance(patch_json, dict):
            previous = response_row.response_json or {}
            patch_json = {}
            for key in sorted(set(previous.keys()) | set(response_json.keys())):
                if previous.get(key) != response_json.get(key):
                    patch_json[key] = response_json.get(key)
        suggestion = create_suggested_change(
            section_response=response_row,
            user=request.user,
            base_version=base_version,
            patch_json=patch_json,
            rationale=(body.get("rationale") or "").strip(),
        )
        return Response(
            {
                "mode": "suggestion",
                "suggested_change_uuid": str(suggestion.uuid),
                "status": suggestion.status,
            },
            status=status.HTTP_201_CREATED,
        )

    revision = append_revision(
        section_response=response_row,
        content=response_json,
        author=request.user,
        note="direct_edit",
    )
    if section_code == "section-i":
        instance.country_name = (
            response_json.get("country_or_reporting_party_name")
            or response_json.get("country_name")
            or instance.country_name
        )
        label_value = str(response_json.get("report_label") or instance.report_label).strip().upper()
        if label_value in {"NR7", "NR8"}:
            instance.report_label = label_value
        public_value = str(response_json.get("public_availability") or "").strip().lower()
        if public_value in {"public", "internal"}:
            instance.is_public = public_value == "public"
        instance.updated_by = request.user
        instance.save(update_fields=["country_name", "report_label", "is_public", "updated_by", "updated_at"])
    record_audit_event(
        request.user,
        "report_section_update",
        response_row,
        metadata={
            "instance_uuid": str(instance.uuid),
            "section_code": section_code,
            "revision_uuid": str(revision.uuid),
            "version": revision.version,
        },
    )
    return Response(_serialize_section_response(response_row))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_context(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "POST":
        context = persist_report_context(
            instance=instance,
            user=request.user,
            session_key=getattr(request.session, "session_key", "") or "",
            filters=request.data.get("context") or request.data,
        )
        return Response(
            {
                "context": context.filters_json,
                "context_hash": context.context_hash,
            }
        )

    context = (
        ReportContext.objects.filter(
            reporting_instance=instance,
            user=request.user if request.user.is_authenticated else None,
        )
        .order_by("-updated_at", "-id")
        .first()
    )
    return Response(
        {
            "context": context.filters_json if context else {},
            "context_hash": context.context_hash if context else "",
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_section_preview(request, instance_uuid, section_code):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    _pack, section, response_row = _get_cbd_pack_response(instance, section_code)
    context_filters = normalize_context_filters(request.GET.get("context"))
    narrative = render_section_narrative(
        instance=instance,
        section_code=section_code,
        context_filters=context_filters,
    )
    html = _section_preview_html(
        section_title=section.title,
        response_json=response_row.response_json or {},
        narrative_html=narrative.get("rendered_html") or "",
    )
    return Response(
        {
            "section_code": section_code,
            "html": html,
            "resolved_values_manifest": narrative.get("resolved_values_manifest", []),
            "context_hash": narrative.get("context_hash", ""),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_section_charts(request, instance_uuid, section_code):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    context_filters = normalize_context_filters(request.GET.get("context"))
    context_row = persist_report_context(
        instance=instance,
        user=request.user,
        session_key=getattr(request.session, "session_key", "") or "",
        filters=context_filters,
    )
    payload = build_section_chart_specs(
        instance=instance,
        section_code=section_code,
        context_filters=context_row.filters_json,
    )
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_section_narrative_render(request, instance_uuid, section_code):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    ensure_narrative_block(
        instance=instance,
        section_code=section_code,
        block_key="main",
        title=f"{section_code.upper()} Narrative",
        user=request.user,
    )
    context_filters = normalize_context_filters(request.GET.get("context"))
    context_row = persist_report_context(
        instance=instance,
        user=request.user,
        session_key=getattr(request.session, "session_key", "") or "",
        filters=context_filters,
    )
    payload = render_section_narrative(
        instance=instance,
        section_code=section_code,
        context_filters=context_row.filters_json,
    )
    return Response(payload)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_section_narrative_blocks(request, instance_uuid, section_code):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    if request.method == "POST":
        if not _can_edit_report_instance(request.user, instance):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        body = request.data or {}
        block_key = (body.get("block_key") or "main").strip() or "main"
        title = (body.get("title") or f"{section_code.upper()} Narrative").strip()
        block = ensure_narrative_block(
            instance=instance,
            section_code=section_code,
            block_key=block_key,
            title=title,
            user=request.user,
        )
        content_b64 = body.get("docx_base64")
        content_text = body.get("content_text")
        if content_b64:
            try:
                content_bytes = base64.b64decode(content_b64)
            except Exception:  # noqa: BLE001
                return Response({"detail": "Invalid docx_base64 payload."}, status=status.HTTP_400_BAD_REQUEST)
            upsert_narrative_block_content(block=block, content_bytes=content_bytes, user=request.user, note="api_upsert")
        elif content_text is not None:
            content_bytes = build_docx_bytes_from_text(title=title, text=str(content_text))
            upsert_narrative_block_content(block=block, content_bytes=content_bytes, user=request.user, note="api_text_upsert")

        record_audit_event(
            request.user,
            "report_narrative_block_upsert",
            block,
            metadata={
                "instance_uuid": str(instance.uuid),
                "section_code": section_code,
                "block_key": block.block_key,
                "version": block.current_version,
            },
        )

    ensure_narrative_block(
        instance=instance,
        section_code=section_code,
        block_key="main",
        title=f"{section_code.upper()} Narrative",
        user=request.user,
    )
    rows = list_section_narrative_blocks(instance=instance, section_code=section_code)
    return Response(
        {
            "blocks": [
                {
                    "uuid": str(row.uuid),
                    "section_code": row.section_code,
                    "block_key": row.block_key,
                    "title": row.title,
                    "storage_path": row.storage_path,
                    "current_version": row.current_version,
                    "current_content_hash": row.current_content_hash,
                    "html_snapshot": row.html_snapshot,
                    "text_snapshot": row.text_snapshot,
                }
                for row in rows
            ]
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_section_narrative_editor_config(request, instance_uuid, section_code, block_key):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    block = ensure_narrative_block(
        instance=instance,
        section_code=section_code,
        block_key=block_key,
        title=f"{section_code.upper()} Narrative",
        user=request.user,
    )
    document_url = request.build_absolute_uri(
        reverse(
            "api_reporting_workspace_section_narrative_block_document",
            args=[instance.uuid, section_code, block_key],
        )
    )
    callback_url = request.build_absolute_uri(
        reverse("api_reporting_workspace_onlyoffice_callback", args=[block.uuid])
    )
    document_server_url = (getattr(settings, "ONLYOFFICE_DOCUMENT_SERVER_PUBLIC_URL", "") or "").strip()
    return Response(
        {
            "editor_config": {
                "documentType": "word",
                "documentServerUrl": document_server_url,
                "document": {
                    "fileType": "docx",
                    "key": block.onlyoffice_document_key or f"{block.uuid}-{block.current_version}",
                    "title": f"{instance.report_label}-{section_code}-{block_key}.docx",
                    "url": document_url,
                },
                "editorConfig": {
                    "callbackUrl": callback_url,
                    "lang": "en",
                    "mode": "edit",
                    "user": {
                        "id": str(request.user.id),
                        "name": request.user.get_username(),
                    },
                },
                "type": "desktop",
            }
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_section_narrative_block_document(request, instance_uuid, section_code, block_key):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    block = get_object_or_404(
        ReportNarrativeBlock.objects.filter(reporting_instance=instance, section_code=section_code),
        block_key=block_key,
    )
    if not block.storage_path:
        return Response({"detail": "No narrative document available."}, status=status.HTTP_404_NOT_FOUND)
    file_handle = default_storage.open(block.storage_path, mode="rb")
    response = FileResponse(
        file_handle,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{instance.report_label}-{section_code}-{block_key}.docx"'
    )
    response["ETag"] = block.current_content_hash
    return response


@api_view(["POST"])
@permission_classes([AllowAny])
def api_reporting_workspace_onlyoffice_callback(request, block_uuid):
    block = get_object_or_404(ReportNarrativeBlock, uuid=block_uuid)
    body = request.data or {}
    status_value = int(body.get("status") or 0)
    # ONLYOFFICE callback save statuses (2, 6) carry a downloadable URL.
    if status_value in {2, 6} and body.get("url"):
        update_narrative_block_from_callback(block=block, callback_payload=body)
        record_audit_event(
            None,
            "report_narrative_block_callback",
            block,
            metadata={
                "status": status_value,
                "block_uuid": str(block.uuid),
                "section_code": block.section_code,
            },
        )
    return Response({"error": 0})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_generate_section_iii(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_edit_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    _pack, _section, response_row = _get_cbd_pack_response(instance, "section-iii")
    targets = scoped_national_targets(instance, request.user).order_by("code", "id")
    rows = []
    for target in targets:
        rows.append(
            {
                "national_target_uuid": str(target.uuid),
                "national_target_code": target.code,
                "national_target_title": target.title,
                "actions_taken": "",
                "progress_level": "unknown",
                "progress_summary_outcomes": "",
                "challenges_and_future_approaches": "",
                "headline_indicator_data": [],
                "binary_indicator_responses": [],
                "component_indicators": [],
                "effectiveness_examples": "",
                "sdg_other_agreements": "",
            }
        )
    payload = dict(response_row.response_json or {})
    payload["target_progress_rows"] = rows
    revision = append_revision(
        section_response=response_row,
        content=payload,
        author=request.user,
        note="generate_section_iii_skeleton",
    )
    return Response(
        {
            "section_code": "section-iii",
            "target_count": len(rows),
            "revision_uuid": str(revision.uuid),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_recompute_section_iv(request, instance_uuid):
    # Backward-compatible alias retained for existing clients.
    return _refresh_section_iv_rollup(request, instance_uuid)


def _refresh_section_iv_rollup(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_edit_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    _pack, _section, response_row = _get_cbd_pack_response(instance, "section-iv")
    _pack_iii, _section_iii, section_iii = _get_cbd_pack_response(instance, "section-iii")
    target_rows = (section_iii.response_json or {}).get("target_progress_rows") or []
    goal_rows = []
    grouped = defaultdict(list)
    for row in target_rows:
        target_code = str(row.get("national_target_code") or "")
        if target_code:
            grouped[target_code[:1]].append(row)
    framework_goals = scoped_framework_targets(instance, request.user).select_related("goal", "framework")
    for framework_target in framework_goals.order_by("framework__code", "code"):
        goal = framework_target.goal
        if not goal:
            continue
        key = goal.code
        rows = grouped.get(key, [])
        goal_rows.append(
            {
                "framework_goal_code": goal.code,
                "framework_goal_title": goal.title,
                "summary_national_progress": " ".join(
                    (str(item.get("progress_summary_outcomes") or "").strip() for item in rows if item)
                ).strip(),
                "selected_headline_binary_indicators": [],
                "selected_component_indicators": [],
                "sources_of_data": [],
                "curated_override": "",
            }
        )
    payload = dict(response_row.response_json or {})
    payload["goal_progress_rows"] = goal_rows
    revision = append_revision(
        section_response=response_row,
        content=payload,
        author=request.user,
        note="refresh_section_iv_rollup",
    )
    return Response(
        {
            "section_code": "section-iv",
            "goal_count": len(goal_rows),
            "revision_uuid": str(revision.uuid),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_refresh_section_iv(request, instance_uuid):
    return _refresh_section_iv_rollup(request, instance_uuid)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_section_history(request, instance_uuid, section_code):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    _pack, _section, response_row = _get_cbd_pack_response(instance, section_code)
    revisions = list(
        response_row.revisions.select_related("author").order_by("-version", "-id")
    )
    diff_from = request.GET.get("from")
    diff_to = request.GET.get("to")
    diff_payload = None
    if diff_from and diff_to:
        from_row = next((row for row in revisions if str(row.version) == str(diff_from)), None)
        to_row = next((row for row in revisions if str(row.version) == str(diff_to)), None)
        if from_row and to_row:
            from_content = from_row.content_snapshot or {}
            to_content = to_row.content_snapshot or {}
            changed_keys = sorted(
                key
                for key in set(from_content.keys()) | set(to_content.keys())
                if from_content.get(key) != to_content.get(key)
            )
            diff_payload = {
                "from_version": from_row.version,
                "to_version": to_row.version,
                "changed_keys": changed_keys,
            }
    return Response(
        {
            "section_code": section_code,
            "current_version": response_row.current_version,
            "revisions": [
                {
                    "uuid": str(row.uuid),
                    "version": row.version,
                    "author": row.author.username if row.author_id else None,
                    "content_hash": row.content_hash,
                    "parent_hash": row.parent_hash,
                    "note": row.note,
                    "created_at": row.created_at.isoformat(),
                }
                for row in revisions
            ],
            "diff": diff_payload,
        }
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_section_comments(request, instance_uuid, section_code):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    _pack, _section, response_row = _get_cbd_pack_response(instance, section_code)

    if request.method == "POST":
        if not _can_edit_report_instance(request.user, instance):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        body = request.data or {}
        thread_uuid = (body.get("thread_uuid") or "").strip()
        body_text = (body.get("body") or "").strip()
        if not body_text:
            return Response({"detail": "Comment body is required."}, status=status.HTTP_400_BAD_REQUEST)
        if thread_uuid:
            thread = get_object_or_404(
                ReportCommentThread.objects.filter(section_response=response_row),
                uuid=thread_uuid,
            )
        else:
            json_path = (body.get("json_path") or "").strip()
            object_uuid = (body.get("object_uuid") or "").strip()
            field_name = (body.get("field_name") or "").strip()
            if field_name and not json_path:
                json_path = field_name
            if not json_path and not (object_uuid and field_name):
                return Response(
                    {"detail": "json_path is required when creating a thread."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            thread = ReportCommentThread.objects.create(
                section_response=response_row,
                json_path=json_path,
                object_uuid=object_uuid or None,
                field_name=field_name,
                created_by=request.user,
            )
        comment = ReportComment.objects.create(
            thread=thread,
            author=request.user,
            body=body_text,
        )
        record_audit_event(
            request.user,
            "report_comment_create",
            response_row,
            metadata={
                "thread_uuid": str(thread.uuid),
                "comment_uuid": str(comment.uuid),
                "json_path": thread.json_path,
            },
        )

    threads = (
        ReportCommentThread.objects.filter(section_response=response_row)
        .select_related("created_by", "resolved_by")
        .prefetch_related("comments__author")
        .order_by("-created_at", "-id")
    )
    return Response(
        {
            "threads": [
                {
                    "uuid": str(thread.uuid),
                    "json_path": thread.json_path,
                    "status": thread.status,
                    "object_uuid": str(thread.object_uuid) if thread.object_uuid else None,
                    "field_name": thread.field_name,
                    "created_by": thread.created_by.username if thread.created_by_id else None,
                    "created_at": thread.created_at.isoformat(),
                    "resolved_at": thread.resolved_at.isoformat() if thread.resolved_at else None,
                    "resolved_by": thread.resolved_by.username if thread.resolved_by_id else None,
                    "comments": [
                        {
                            "uuid": str(comment.uuid),
                            "author": comment.author.username if comment.author_id else None,
                            "body": comment.body,
                            "created_at": comment.created_at.isoformat(),
                        }
                        for comment in thread.comments.all().order_by("created_at", "id")
                    ],
                }
                for thread in threads
            ]
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_comment_thread_status(request, instance_uuid, section_code, thread_uuid):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_edit_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    _pack, _section, response_row = _get_cbd_pack_response(instance, section_code)
    thread = get_object_or_404(
        ReportCommentThread.objects.filter(section_response=response_row),
        uuid=thread_uuid,
    )
    new_status = (request.data.get("status") or "").strip().lower()
    if new_status not in {ReportCommentThreadStatus.OPEN, ReportCommentThreadStatus.RESOLVED}:
        return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)
    thread.status = new_status
    if new_status == ReportCommentThreadStatus.RESOLVED:
        thread.resolved_at = timezone.now()
        thread.resolved_by = request.user
    else:
        thread.resolved_at = None
        thread.resolved_by = None
    thread.save(update_fields=["status", "resolved_at", "resolved_by", "updated_at"])
    record_audit_event(
        request.user,
        "report_comment_thread_status",
        response_row,
        metadata={"thread_uuid": str(thread.uuid), "status": thread.status},
    )
    return Response({"thread_uuid": str(thread.uuid), "status": thread.status})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_section_suggestions(request, instance_uuid, section_code):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    _pack, _section, response_row = _get_cbd_pack_response(instance, section_code)

    if request.method == "POST":
        if not _can_edit_report_instance(request.user, instance):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        base_version = int(request.data.get("base_version") or response_row.current_version or 1)
        patch_json = request.data.get("patch_json") or request.data.get("diff_patch") or {}
        object_uuid = (request.data.get("object_uuid") or "").strip()
        field_name = (request.data.get("field_name") or "").strip()
        if object_uuid and field_name:
            suggestion = ReportSuggestedChange.objects.create(
                section_response=response_row,
                object_uuid=object_uuid,
                field_name=field_name,
                base_version=base_version,
                patch_json=patch_json if isinstance(patch_json, dict) else {},
                diff_patch=patch_json if isinstance(patch_json, dict) else {},
                old_value_hash=(request.data.get("old_value_hash") or "").strip(),
                proposed_value=request.data.get("proposed_value") if request.data.get("proposed_value") is not None else {},
                rationale=(request.data.get("rationale") or "").strip(),
                created_by=request.user if request.user.is_authenticated else None,
                status=SuggestedChangeStatus.PROPOSED,
            )
            record_audit_event(
                request.user,
                "report_suggestion_create",
                response_row,
                metadata={
                    "section_response_uuid": str(response_row.uuid),
                    "suggested_change_uuid": str(suggestion.uuid),
                    "object_uuid": object_uuid,
                    "field_name": field_name,
                    "base_version": base_version,
                },
            )
        else:
            suggestion = create_suggested_change(
                section_response=response_row,
                user=request.user,
                base_version=base_version,
                patch_json=patch_json,
                rationale=(request.data.get("rationale") or "").strip(),
            )
        return Response(
            {"uuid": str(suggestion.uuid), "status": suggestion.status},
            status=status.HTTP_201_CREATED,
        )

    suggestions = (
        ReportSuggestedChange.objects.filter(section_response=response_row)
        .select_related("created_by", "decided_by")
        .order_by("-created_at", "-id")
    )
    return Response(
        {
            "suggestions": [
                {
                    "uuid": str(row.uuid),
                    "object_uuid": str(row.object_uuid) if row.object_uuid else None,
                    "field_name": row.field_name,
                    "base_version": row.base_version,
                    "patch_json": row.patch_json,
                    "diff_patch": row.diff_patch,
                    "old_value_hash": row.old_value_hash,
                    "proposed_value": row.proposed_value,
                    "rationale": row.rationale,
                    "status": row.status,
                    "created_by": row.created_by.username if row.created_by_id else None,
                    "created_at": row.created_at.isoformat(),
                    "decided_by": row.decided_by.username if row.decided_by_id else None,
                    "reviewer": row.decided_by.username if row.decided_by_id else None,
                    "decided_at": row.decided_at.isoformat() if row.decided_at else None,
                    "decision_note": row.decision_note,
                }
                for row in suggestions
            ]
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_suggestion_decide(request, instance_uuid, section_code, suggestion_uuid):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_edit_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    _pack, _section, response_row = _get_cbd_pack_response(instance, section_code)
    suggestion = get_object_or_404(
        ReportSuggestedChange.objects.filter(section_response=response_row),
        uuid=suggestion_uuid,
    )
    action = (request.data.get("action") or "").strip().lower()
    if action not in {"accept", "reject"}:
        return Response({"detail": "action must be accept or reject."}, status=status.HTTP_400_BAD_REQUEST)
    suggestion, revision = decide_suggested_change(
        suggestion=suggestion,
        user=request.user,
        accept=(action == "accept"),
        note=(request.data.get("note") or "").strip(),
    )
    return Response(
        {
            "uuid": str(suggestion.uuid),
            "status": suggestion.status,
            "revision_uuid": str(revision.uuid) if revision else None,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_workflow(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    workflow = ensure_workflow_instance(instance)
    return Response(
        {
            "workflow": {
                "uuid": str(workflow.uuid),
                "status": workflow.status,
                "current_step": workflow.current_step,
                "locked": workflow.locked,
                "latest_content_hash": workflow.latest_content_hash,
                "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
                "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            },
            "section_approvals": [
                {
                    "section_code": row.section.code,
                    "approved": row.approved,
                    "approved_by": row.approved_by.username if row.approved_by_id else None,
                    "approved_at": row.approved_at.isoformat() if row.approved_at else None,
                    "note": row.note,
                }
                for row in workflow.section_approvals.select_related("section", "approved_by").order_by(
                    "section__ordering",
                    "section__code",
                )
            ],
            "actions": [
                {
                    "uuid": str(row.uuid),
                    "action_type": row.action_type,
                    "actor": row.actor.username if row.actor_id else None,
                    "comment": row.comment,
                    "payload_hash": row.payload_hash,
                    "created_at": row.created_at.isoformat(),
                }
                for row in workflow.actions.select_related("actor").order_by("-created_at", "-id")
            ],
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_workflow_action(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    action = (request.data.get("action") or "").strip().lower()
    section_code = (request.data.get("section_code") or "").strip()
    comment = (request.data.get("comment") or "").strip()
    context_filters = normalize_context_filters(request.data.get("context"))
    resolved_manifest = []
    if any(str(value or "").strip() for value in context_filters.values()):
        pack = resolve_cbd_pack()
        for section in pack.sections.filter(is_active=True).order_by("ordering", "code"):
            rendered = render_section_narrative(
                instance=instance,
                section_code=section.code,
                context_filters=context_filters,
            )
            resolved_manifest.extend(rendered.get("resolved_values_manifest", []))
    try:
        workflow, workflow_action = transition_report_workflow(
            instance=instance,
            user=request.user,
            action=action,
            comment=comment,
            section_code=section_code,
            context_filters=context_filters,
            resolved_values_manifest=resolved_manifest,
        )
    except PermissionDenied as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(
        {
            "workflow_uuid": str(workflow.uuid),
            "workflow_status": workflow.status,
            "current_step": workflow.current_step,
            "instance_status": instance.status,
            "action_uuid": str(workflow_action.uuid),
        }
    )


def _report_export_allowed(user, instance):
    if instance.is_public and instance.status in {
        ReportingStatus.SUBMITTED,
        ReportingStatus.RELEASED,
        ReportingStatus.PUBLIC_RELEASED,
    }:
        return True
    return _can_view_report_instance(user, instance)


@api_view(["GET"])
@permission_classes([AllowAny])
def api_reporting_workspace_export_pdf(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    if not _report_export_allowed(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    context_filters = _resolve_export_context(instance, request.user, request.GET.get("context"))
    payload = build_cbd_report_payload(instance=instance)
    payload, manifest = _attach_context_rendering(payload, instance, context_filters)
    pdf_bytes = render_cbd_pdf_bytes(payload=payload)
    artifact = store_report_export_artifact(
        instance=instance,
        generated_by=request.user,
        format_name=ReportExportArtifact.FORMAT_PDF,
        content_bytes=pdf_bytes,
        metadata={
            "api": "workspace_export_pdf",
            "report_label": instance.report_label,
            "context_filters": context_filters,
            "resolved_values_count": len(manifest),
        },
    )
    record_audit_event(
        request.user if getattr(request.user, "is_authenticated", False) else None,
        "report_export_pdf",
        instance,
        metadata={
            "artifact_uuid": str(artifact.uuid),
            "report_label": instance.report_label,
            "context_filters": context_filters,
            "resolved_values_count": len(manifest),
        },
    )
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{instance.report_label.lower()}-report-{instance.uuid}.pdf"'
    response["ETag"] = artifact.content_hash
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def api_reporting_workspace_export_docx(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    if not _report_export_allowed(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    context_filters = _resolve_export_context(instance, request.user, request.GET.get("context"))
    payload = build_cbd_report_payload(instance=instance)
    payload, manifest = _attach_context_rendering(payload, instance, context_filters)
    docx_bytes = render_cbd_docx_bytes(payload=payload)
    artifact = store_report_export_artifact(
        instance=instance,
        generated_by=request.user,
        format_name=ReportExportArtifact.FORMAT_DOCX,
        content_bytes=docx_bytes,
        metadata={
            "api": "workspace_export_docx",
            "report_label": instance.report_label,
            "context_filters": context_filters,
            "resolved_values_count": len(manifest),
        },
    )
    record_audit_event(
        request.user if getattr(request.user, "is_authenticated", False) else None,
        "report_export_docx",
        instance,
        metadata={
            "artifact_uuid": str(artifact.uuid),
            "report_label": instance.report_label,
            "context_filters": context_filters,
            "resolved_values_count": len(manifest),
        },
    )
    response = HttpResponse(
        docx_bytes,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    response["Content-Disposition"] = f'attachment; filename="{instance.report_label.lower()}-report-{instance.uuid}.docx"'
    response["ETag"] = artifact.content_hash
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def api_reporting_workspace_export_json(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    if not _report_export_allowed(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    context_filters = _resolve_export_context(instance, request.user, request.GET.get("context"))
    payload = build_cbd_report_payload(instance=instance)
    payload, manifest = _attach_context_rendering(payload, instance, context_filters)
    json_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    artifact = store_report_export_artifact(
        instance=instance,
        generated_by=request.user,
        format_name=ReportExportArtifact.FORMAT_JSON,
        content_bytes=json_bytes,
        metadata={
            "api": "workspace_export_json",
            "report_label": instance.report_label,
            "context_filters": context_filters,
            "resolved_values_count": len(manifest),
        },
    )
    record_audit_event(
        request.user if getattr(request.user, "is_authenticated", False) else None,
        "report_export_json",
        instance,
        metadata={
            "artifact_uuid": str(artifact.uuid),
            "report_label": instance.report_label,
            "context_filters": context_filters,
            "resolved_values_count": len(manifest),
        },
    )
    response = HttpResponse(json_bytes, content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="{instance.report_label.lower()}-report-{instance.uuid}.json"'
    response["ETag"] = artifact.content_hash
    return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_generate_dossier(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _report_export_allowed(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    workflow = ensure_workflow_instance(instance)
    linked_action = workflow.actions.order_by("-created_at", "-id").first()
    raw_context = None
    try:
        raw_context = (request.data or {}).get("context")
    except (UnsupportedMediaType, ParseError, AttributeError):
        raw_context = None
    context_filters = _resolve_export_context(instance, request.user, raw_context)
    dossier = generate_reporting_dossier(
        instance=instance,
        user=request.user,
        linked_action=linked_action,
        context_filters=context_filters,
    )
    return Response(
        {
            "dossier": read_dossier_manifest(dossier),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_reporting_workspace_latest_dossier(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _report_export_allowed(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    dossier = instance.dossier_artifacts.order_by("-created_at", "-id").first()
    if not dossier:
        return Response({"detail": "No dossier generated yet."}, status=status.HTTP_404_NOT_FOUND)
    if request.GET.get("download") == "1":
        file_handle = default_storage.open(dossier.storage_path, mode="rb")
        response = FileResponse(file_handle, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="report-dossier-{instance.uuid}.zip"'
        response["ETag"] = dossier.content_hash
        return response
    return Response({"dossier": read_dossier_manifest(dossier)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_ort_validation(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    pack = resolve_cbd_pack()
    validation = build_pack_validation(pack=pack, instance=instance, user=request.user)
    blockers = [item for item in validation.get("qa_items", []) if item.get("severity") == "BLOCKER"]
    return Response(
        {
            "contract": "nbms.cbd_national_report.v1",
            "overall_valid": len(blockers) == 0,
            "blocking_issues": blockers,
            "validation": validation,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_create_nr8_from_nr7(request, instance_uuid):
    source = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    if not _can_edit_report_instance(request.user, source):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    if source.report_label != "NR7":
        return Response({"detail": "Carry-forward source must be an NR7 instance."}, status=status.HTTP_400_BAD_REQUEST)

    cycle_code = "NR8"
    cycle, _ = ReportingCycle.objects.update_or_create(
        code=cycle_code,
        defaults={
            "title": "Eighth National Report",
            "start_date": source.reporting_period_end or source.cycle.end_date,
            "end_date": source.reporting_period_end or source.cycle.end_date,
            "due_date": source.cycle.due_date,
            "default_language": source.cycle.default_language,
            "allowed_languages": source.cycle.allowed_languages,
            "is_active": True,
        },
    )
    instance = ReportingInstance.objects.create(
        cycle=cycle,
        report_family=source.report_family,
        report_label="NR8",
        version_label="v1",
        reporting_period_start=source.reporting_period_end,
        reporting_period_end=source.reporting_period_end,
        report_title=(source.report_title or "").replace("NR7", "NR8") or f"{source.country_name} NR8",
        country_name=source.country_name,
        focal_point_org=source.focal_point_org,
        publishing_authority_org=source.publishing_authority_org,
        is_public=source.is_public,
        status=ReportingStatus.DRAFT,
        created_by=request.user if request.user.is_authenticated else None,
        updated_by=request.user if request.user.is_authenticated else None,
        notes=f"Carry-forward from NR7 instance {source.uuid}.",
    )

    source_rows = {
        row.section.code: row
        for row in ReportTemplatePackResponse.objects.filter(reporting_instance=source).select_related("section")
    }
    pack = resolve_cbd_pack()
    for section in pack.sections.filter(is_active=True).order_by("ordering", "code"):
        source_row = source_rows.get(section.code)
        response_json = _deep_clone(source_row.response_json if source_row else build_default_response_payload(section))
        response_json["_carry_forward_from_instance"] = str(source.uuid)
        response_json["_carry_forward_needs_review"] = True
        if section.code == "section-i":
            response_json["report_label"] = "NR8"
        new_row = ReportTemplatePackResponse.objects.create(
            reporting_instance=instance,
            section=section,
            response_json=response_json,
            updated_by=request.user if request.user.is_authenticated else None,
            current_version=1,
            current_content_hash=payload_hash(response_json),
        )
        ensure_initial_revision(section_response=new_row, author=request.user)

    for row in ReportNarrativeBlock.objects.filter(reporting_instance=source):
        new_block = ensure_narrative_block(
            instance=instance,
            section_code=row.section_code,
            block_key=row.block_key,
            title=row.title,
            user=request.user,
        )
        if row.storage_path and default_storage.exists(row.storage_path):
            with default_storage.open(row.storage_path, mode="rb") as fh:
                content_bytes = fh.read()
            upsert_narrative_block_content(
                block=new_block,
                content_bytes=content_bytes,
                user=request.user,
                note="carry_forward_from_nr7",
            )

    record_audit_event(
        request.user,
        "report_carry_forward_nr8_from_nr7",
        instance,
        metadata={
            "source_instance_uuid": str(source.uuid),
            "target_instance_uuid": str(instance.uuid),
        },
    )
    return Response(
        {
            "source_instance_uuid": str(source.uuid),
            "new_instance_uuid": str(instance.uuid),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_workspace_diff(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _can_view_report_instance(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    from_uuid = (request.GET.get("from_instance_uuid") or "").strip()
    if not from_uuid:
        return Response({"detail": "from_instance_uuid is required."}, status=status.HTTP_400_BAD_REQUEST)
    baseline = get_object_or_404(ReportingInstance, uuid=from_uuid)
    if not _can_view_report_instance(request.user, baseline):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    current_rows = {
        row.section.code: row.response_json or {}
        for row in ReportTemplatePackResponse.objects.filter(reporting_instance=instance).select_related("section")
    }
    baseline_rows = {
        row.section.code: row.response_json or {}
        for row in ReportTemplatePackResponse.objects.filter(reporting_instance=baseline).select_related("section")
    }
    section_codes = sorted(set(current_rows.keys()) | set(baseline_rows.keys()))
    section_diffs = []
    for code in section_codes:
        before = baseline_rows.get(code) or {}
        after = current_rows.get(code) or {}
        field_changes = []
        for key in sorted(set(before.keys()) | set(after.keys())):
            if before.get(key) != after.get(key):
                field_changes.append(
                    {
                        "field_name": key,
                        "before": before.get(key),
                        "after": after.get(key),
                    }
                )
        section_diffs.append(
            {
                "section_code": code,
                "changed": bool(field_changes),
                "field_changes": field_changes,
            }
        )

    narrative_diffs = []
    current_blocks = ReportNarrativeBlock.objects.filter(reporting_instance=instance)
    for block in current_blocks:
        baseline_block = ReportNarrativeBlock.objects.filter(
            reporting_instance=baseline,
            section_code=block.section_code,
            block_key=block.block_key,
        ).first()
        before_text = baseline_block.text_snapshot if baseline_block else ""
        after_text = block.text_snapshot or ""
        if before_text == after_text:
            continue
        diff_lines = list(
            difflib.unified_diff(
                before_text.splitlines(),
                after_text.splitlines(),
                lineterm="",
            )
        )
        narrative_diffs.append(
            {
                "section_code": block.section_code,
                "block_key": block.block_key,
                "changed": True,
                "summary": {
                    "added_lines": len([line for line in diff_lines if line.startswith("+") and not line.startswith("+++")]),
                    "removed_lines": len([line for line in diff_lines if line.startswith("-") and not line.startswith("---")]),
                },
                "diff_excerpt": diff_lines[:80],
            }
        )

    change_summary_lines = []
    for section in section_diffs:
        if section["changed"]:
            change_summary_lines.append(
                f"{section['section_code']}: {len(section['field_changes'])} structured field changes."
            )
    for narrative in narrative_diffs:
        change_summary_lines.append(
            (
                f"{narrative['section_code']} narrative ({narrative['block_key']}): "
                f"+{narrative['summary']['added_lines']} / -{narrative['summary']['removed_lines']} lines."
            )
        )

    return Response(
        {
            "baseline_instance_uuid": str(baseline.uuid),
            "instance_uuid": str(instance.uuid),
            "section_diffs": section_diffs,
            "narrative_diffs": narrative_diffs,
            "change_summary": "\n".join(change_summary_lines),
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_reporting_public_view(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    if not instance.is_public:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    if instance.status not in {ReportingStatus.SUBMITTED, ReportingStatus.RELEASED, ReportingStatus.PUBLIC_RELEASED}:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    payload = build_cbd_report_payload(instance=instance)
    return Response(
        {
            "instance": {
                "uuid": str(instance.uuid),
                "report_title": instance.report_title,
                "country_name": instance.country_name,
                "cycle_code": instance.cycle.code if instance.cycle_id else "",
                "status": instance.status,
            },
            "payload": payload,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_discovery_search(request):
    search = (request.GET.get("search") or "").strip()
    limit = _parse_positive_int(request.GET.get("limit"), default=8, minimum=1, maximum=25)
    if len(search) < 2:
        return Response(
            {
                "search": search,
                "counts": {"indicators": 0, "targets": 0, "datasets": 0},
                "indicators": [],
                "targets": [],
                "datasets": [],
            }
        )

    indicator_qs = _indicator_base_queryset(request.user).filter(
        Q(code__icontains=search)
        | Q(title__icontains=search)
        | Q(computation_notes__icontains=search)
        | Q(national_target__code__icontains=search)
        | Q(national_target__title__icontains=search)
    )
    target_qs = filter_queryset_for_user(
        NationalTarget.objects.select_related("organisation"),
        request.user,
        perm="nbms_app.view_nationaltarget",
    ).filter(
        Q(code__icontains=search)
        | Q(title__icontains=search)
        | Q(description__icontains=search)
    )
    dataset_qs = filter_queryset_for_user(
        Dataset.objects.select_related("organisation", "created_by").annotate(
            latest_release_date=Max("releases__release_date")
        ),
        request.user,
        perm="nbms_app.view_dataset",
    ).filter(
        Q(dataset_code__icontains=search)
        | Q(title__icontains=search)
        | Q(description__icontains=search)
    )

    indicator_rows = list(indicator_qs.order_by("title", "code", "uuid")[:limit])
    target_rows = list(target_qs.order_by("code", "title", "uuid")[:limit])
    dataset_rows = list(dataset_qs.order_by("title", "dataset_code", "uuid")[:limit])

    return Response(
        {
            "search": search,
            "counts": {
                "indicators": indicator_qs.count(),
                "targets": target_qs.count(),
                "datasets": dataset_qs.count(),
            },
            "indicators": [_indicator_payload(row) for row in indicator_rows],
            "targets": [
                {
                    "uuid": str(row.uuid),
                    "code": row.code,
                    "title": row.title,
                    "status": row.status,
                    "sensitivity": row.sensitivity,
                    "organisation": row.organisation.name if row.organisation_id else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in target_rows
            ],
            "datasets": [
                {
                    "uuid": str(row.uuid),
                    "code": row.dataset_code,
                    "title": row.title,
                    "status": row.status,
                    "sensitivity": row.sensitivity,
                    "organisation": row.organisation.name if row.organisation_id else None,
                    "release_date": (
                        row.latest_release_date.isoformat()
                        if getattr(row, "latest_release_date", None)
                        else None
                    ),
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in dataset_rows
            ],
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_indicator_list(request):
    user = request.user
    queryset = _indicator_base_queryset(user)

    search = (request.GET.get("search") or "").strip()
    if search:
        queryset = queryset.filter(
            Q(code__icontains=search)
            | Q(title__icontains=search)
            | Q(computation_notes__icontains=search)
            | Q(national_target__code__icontains=search)
            | Q(national_target__title__icontains=search)
        )

    framework = (request.GET.get("framework") or "").strip()
    if framework:
        queryset = queryset.filter(
            framework_indicator_links__framework_indicator__framework__code__iexact=framework,
            framework_indicator_links__is_active=True,
        )

    framework_target = (request.GET.get("framework_target") or "").strip()
    if framework_target:
        queryset = queryset.filter(
            framework_indicator_links__framework_indicator__framework_target__code__iexact=framework_target,
            framework_indicator_links__is_active=True,
        )

    realm = (request.GET.get("realm") or "").strip()
    if realm:
        queryset = queryset.filter(
            Q(coverage_geography__icontains=realm)
            | Q(spatial_coverage__icontains=realm)
            | Q(indicator_type__iexact=realm)
        )

    status_filter = (request.GET.get("status") or request.GET.get("publication_state") or "").strip()
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    sensitivity = (request.GET.get("sensitivity") or "").strip()
    if sensitivity:
        queryset = queryset.filter(sensitivity=sensitivity)

    method_readiness = (request.GET.get("method_readiness") or "").strip().lower()
    if method_readiness:
        queryset = queryset.filter(method_profiles__is_active=True, method_profiles__readiness_state=method_readiness)

    geography = (request.GET.get("geography") or "").strip()
    if geography:
        queryset = queryset.filter(
            Q(coverage_geography__icontains=geography) | Q(spatial_coverage__icontains=geography)
        )

    year_from = request.GET.get("year_from")
    if year_from:
        try:
            year_from_int = int(year_from)
            queryset = queryset.filter(Q(coverage_time_end_year__isnull=True) | Q(coverage_time_end_year__gte=year_from_int))
        except ValueError:
            pass
    year_to = request.GET.get("year_to")
    if year_to:
        try:
            year_to_int = int(year_to)
            queryset = queryset.filter(Q(coverage_time_start_year__isnull=True) | Q(coverage_time_start_year__lte=year_to_int))
        except ValueError:
            pass

    sort = (request.GET.get("sort") or "title").strip().lower()
    if sort == "recently_updated":
        queryset = queryset.order_by("-updated_at", "title", "uuid")
    elif sort == "relevance" and search:
        queryset = queryset.order_by("title", "code", "uuid")
    else:
        queryset = queryset.order_by("title", "code", "uuid")

    queryset = queryset.distinct()
    total = queryset.count()
    page = _parse_positive_int(request.GET.get("page"), 1, minimum=1, maximum=100000)
    page_size = _parse_positive_int(request.GET.get("page_size"), 20, minimum=1, maximum=100)
    start = (page - 1) * page_size
    end = start + page_size
    rows = list(queryset[start:end])

    facets = {
        "frameworks": list(
            IndicatorFrameworkIndicatorLink.objects.filter(indicator__in=queryset, is_active=True)
            .values("framework_indicator__framework__code")
            .annotate(total=Count("id"))
            .order_by("framework_indicator__framework__code")
        ),
        "statuses": list(
            queryset.values("status").annotate(total=Count("id")).order_by("status")
        ),
        "sensitivities": list(
            queryset.values("sensitivity").annotate(total=Count("id")).order_by("sensitivity")
        ),
        "method_readiness": list(
            IndicatorMethodProfile.objects.filter(indicator__in=queryset, is_active=True)
            .values("readiness_state")
            .annotate(total=Count("id"))
            .order_by("readiness_state")
        ),
    }

    return Response(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": [_indicator_payload(item) for item in rows],
            "facets": facets,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_indicator_detail(request, indicator_uuid):
    queryset = _indicator_base_queryset(request.user)
    indicator = get_object_or_404(queryset, uuid=indicator_uuid)

    methodology_links = (
        IndicatorMethodologyVersionLink.objects.filter(indicator=indicator, is_active=True)
        .select_related("methodology_version", "methodology_version__methodology")
        .order_by("-is_primary", "methodology_version__effective_date", "methodology_version__version")
    )
    evidence_links = (
        IndicatorEvidenceLink.objects.filter(indicator=indicator)
        .select_related("evidence")
        .order_by("evidence__title")
    )
    series = (
        indicator_data_series_for_user(request.user)
        .filter(indicator=indicator)
        .order_by("title", "uuid")
    )
    points_qs = (
        indicator_data_points_for_user(request.user)
        .filter(series__in=series)
        .select_related("programme_run")
        .order_by("-year", "-updated_at", "-id")
    )
    latest_point = points_qs.first()
    latest_pipeline_point = points_qs.exclude(programme_run__isnull=True).first()
    method_profiles = (
        IndicatorMethodProfile.objects.filter(indicator=indicator, is_active=True)
        .order_by("method_type", "implementation_key", "uuid")
    )
    input_requirement = (
        IndicatorInputRequirement.objects.filter(indicator=indicator)
        .prefetch_related("required_map_layers", "required_map_sources")
        .first()
    )
    required_layers = list(input_requirement.required_map_layers.all().order_by("layer_code", "id")) if input_requirement else []
    required_sources = list(input_requirement.required_map_sources.all().order_by("code", "id")) if input_requirement else []
    available_layers = filter_spatial_layers_for_user(
        SpatialLayer.objects.filter(id__in=[row.id for row in required_layers]),
        request.user,
    )
    available_layer_ids = set(available_layers.values_list("id", flat=True))

    layer_requirements = []
    for row in required_layers:
        is_available = row.id in available_layer_ids
        latest_run = row.latest_ingestion_run
        layer_requirements.append(
            {
                "layer_code": row.layer_code,
                "title": row.title or row.name,
                "available": is_available,
                "sensitivity": row.sensitivity,
                "consent_required": row.consent_required,
                "last_ingestion_status": latest_run.status if latest_run else None,
                "last_ingestion_rows": latest_run.rows_ingested if latest_run else None,
                "last_ingestion_at": latest_run.finished_at.isoformat() if latest_run and latest_run.finished_at else None,
            }
        )

    source_requirements = []
    for row in required_sources:
        source_requirements.append(
            {
                "code": row.code,
                "title": row.title,
                "status": row.last_status,
                "last_sync_at": row.last_sync_at.isoformat() if row.last_sync_at else None,
                "last_feature_count": row.last_feature_count,
                "requires_token": row.requires_token,
                "enabled_by_default": row.enabled_by_default,
            }
        )

    readiness_items = [
        *(item.get("available", False) for item in layer_requirements),
        *(
            item.get("status") in {"ready", "skipped"} and item.get("last_feature_count", 0) >= 0
            for item in source_requirements
        ),
    ]
    spatial_readiness = {
        "overall_ready": bool(readiness_items) and all(readiness_items),
        "layer_requirements": layer_requirements,
        "source_requirements": source_requirements,
        "disaggregation_expectations_json": (
            input_requirement.disaggregation_expectations_json if input_requirement else {}
        ),
        "cadence": input_requirement.cadence if input_requirement else "",
        "notes": input_requirement.notes if input_requirement else "",
        "last_checked_at": input_requirement.last_checked_at.isoformat() if input_requirement and input_requirement.last_checked_at else None,
    }
    pipeline = {
        "data_last_refreshed_at": latest_point.updated_at.isoformat() if latest_point else None,
        "latest_year": latest_point.year if latest_point else None,
        "latest_pipeline_run_uuid": (
            str(latest_pipeline_point.programme_run.uuid)
            if latest_pipeline_point and latest_pipeline_point.programme_run_id
            else None
        ),
        "latest_pipeline_run_status": (
            latest_pipeline_point.programme_run.status
            if latest_pipeline_point and latest_pipeline_point.programme_run_id
            else None
        ),
    }
    latest_series = latest_point.series if latest_point else series.first()
    release_workflow = get_release_workflow_state(latest_series) if latest_series else {
        "status": None,
        "requires_data_steward_review": False,
        "itsc_method_approved": False,
        "sense_check_attested": False,
        "sense_check_attested_by": None,
        "sense_check_attested_at": None,
    }
    registry_requirement = getattr(indicator, "registry_coverage_requirement", None)
    registry_counts = {
        "ecosystems": filter_queryset_for_user(EcosystemType.objects.all(), request.user).count(),
        "taxa": filter_queryset_for_user(TaxonConcept.objects.all(), request.user).count(),
        "ias_profiles": filter_queryset_for_user(AlienTaxonProfile.objects.all(), request.user).count(),
    }
    if registry_requirement:
        registry_checks = [
            {
                "key": "ecosystems",
                "required": registry_requirement.require_ecosystem_registry,
                "minimum": registry_requirement.min_ecosystem_count,
                "available": registry_counts["ecosystems"],
            },
            {
                "key": "taxa",
                "required": registry_requirement.require_taxon_registry,
                "minimum": registry_requirement.min_taxon_count,
                "available": registry_counts["taxa"],
            },
            {
                "key": "ias_profiles",
                "required": registry_requirement.require_ias_registry,
                "minimum": registry_requirement.min_ias_count,
                "available": registry_counts["ias_profiles"],
            },
        ]
    else:
        registry_checks = [
            {"key": "ecosystems", "required": False, "minimum": 0, "available": registry_counts["ecosystems"]},
            {"key": "taxa", "required": False, "minimum": 0, "available": registry_counts["taxa"]},
            {"key": "ias_profiles", "required": False, "minimum": 0, "available": registry_counts["ias_profiles"]},
        ]
    registry_overall_ready = all(
        (not row["required"]) or row["available"] >= row["minimum"]
        for row in registry_checks
    )
    registry_readiness = {
        "overall_ready": registry_overall_ready,
        "checks": registry_checks,
        "notes": registry_requirement.notes if registry_requirement else "",
        "last_checked_at": (
            registry_requirement.last_checked_at.isoformat() if registry_requirement and registry_requirement.last_checked_at else None
        ),
    }
    used_by_programmes = filter_monitoring_programmes_for_user(
        MonitoringProgramme.objects.filter(indicator_links__indicator=indicator, indicator_links__is_active=True).distinct(),
        request.user,
    ).order_by("programme_code", "id")
    used_by_targets = (
        IndicatorFrameworkIndicatorLink.objects.filter(indicator=indicator, is_active=True)
        .select_related("framework_indicator", "framework_indicator__framework_target", "framework_indicator__framework_target__framework")
        .order_by("framework_indicator__framework_target__framework__code", "framework_indicator__framework_target__code", "id")
    )
    used_by_graph = {
        "indicator": {"uuid": str(indicator.uuid), "code": indicator.code, "title": indicator.title},
        "framework_targets": [
            {
                "framework_code": row.framework_indicator.framework_target.framework.code if row.framework_indicator and row.framework_indicator.framework_target_id else None,
                "target_code": row.framework_indicator.framework_target.code if row.framework_indicator and row.framework_indicator.framework_target_id else None,
                "target_title": row.framework_indicator.framework_target.title if row.framework_indicator and row.framework_indicator.framework_target_id else None,
            }
            for row in used_by_targets
            if row.framework_indicator and row.framework_indicator.framework_target_id
        ],
        "programmes": [
            {
                "uuid": str(programme.uuid),
                "programme_code": programme.programme_code,
                "title": programme.title,
            }
            for programme in used_by_programmes
        ],
        "report_products": [
            {
                "code": row.code,
                "title": row.title,
                "version": row.version,
            }
            for row in ReportProductTemplate.objects.filter(is_active=True).order_by("code", "id")
        ],
    }
    indicator_payload = _indicator_payload(indicator)
    pipeline["next_expected_update_on"] = indicator_payload.get("next_expected_update_on")
    pipeline["pipeline_maturity"] = _pipeline_maturity(
        indicator_payload.get("method_readiness_state"),
        pipeline.get("latest_pipeline_run_status"),
    )
    pipeline["readiness_status"] = indicator_payload.get("readiness_status")
    pipeline["readiness_score"] = indicator_payload.get("readiness_score")
    pipeline["release_workflow"] = release_workflow

    return Response(
        {
            "indicator": indicator_payload,
            "narrative": {
                "summary": indicator.computation_notes,
                "limitations": indicator.limitations,
                "spatial_coverage": indicator.spatial_coverage,
                "temporal_coverage": indicator.temporal_coverage,
            },
            "methodologies": [
                {
                    "methodology_code": link.methodology_version.methodology.methodology_code,
                    "methodology_title": link.methodology_version.methodology.title,
                    "version": link.methodology_version.version,
                    "effective_date": (
                        link.methodology_version.effective_date.isoformat()
                        if link.methodology_version.effective_date
                        else None
                    ),
                    "is_primary": link.is_primary,
                }
                for link in methodology_links
            ],
            "evidence": [
                {
                    "uuid": str(link.evidence.uuid),
                    "title": link.evidence.title,
                    "evidence_type": link.evidence.evidence_type,
                    "source_url": link.evidence.source_url,
                }
                for link in evidence_links
            ],
            "series": [
                {
                    "uuid": str(item.uuid),
                    "title": item.title,
                    "unit": item.unit,
                    "value_type": item.value_type,
                    "status": item.status,
                    "sensitivity": item.sensitivity,
                }
                for item in series
            ],
            "method_profiles": [
                {
                    "uuid": str(profile.uuid),
                    "method_type": profile.method_type,
                    "implementation_key": profile.implementation_key,
                    "readiness_state": profile.readiness_state,
                    "readiness_notes": profile.readiness_notes,
                    "last_success_at": profile.last_success_at.isoformat() if profile.last_success_at else None,
                }
                for profile in method_profiles
            ],
            "spatial_readiness": spatial_readiness,
            "registry_readiness": registry_readiness,
            "pipeline": pipeline,
            "used_by_graph": used_by_graph,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_indicator_datasets(request, indicator_uuid):
    queryset = _indicator_base_queryset(request.user)
    indicator = get_object_or_404(queryset, uuid=indicator_uuid)
    links = (
        IndicatorDatasetLink.objects.filter(indicator=indicator)
        .select_related("dataset", "dataset__organisation")
        .order_by("dataset__title", "dataset__uuid")
    )
    datasets = filter_queryset_for_user(
        Dataset.objects.filter(id__in=[link.dataset_id for link in links]).select_related("organisation"),
        request.user,
        perm="nbms_app.view_dataset",
    )
    dataset_ids = set(datasets.values_list("id", flat=True))
    return Response(
        {
            "indicator_uuid": str(indicator.uuid),
            "datasets": [
                {
                    "uuid": str(link.dataset.uuid),
                    "title": link.dataset.title,
                    "status": link.dataset.status,
                    "sensitivity": link.dataset.sensitivity,
                    "organisation": link.dataset.organisation.name if link.dataset.organisation_id else None,
                    "note": link.note,
                }
                for link in links
                if link.dataset_id in dataset_ids
            ],
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_indicator_series_summary(request, indicator_uuid):
    queryset = _indicator_base_queryset(request.user)
    indicator = get_object_or_404(queryset, uuid=indicator_uuid)
    agg = (request.GET.get("agg") or "year").strip().lower()
    geography = (request.GET.get("geography") or "").strip().lower()
    year_filter = request.GET.get("year")

    series_qs = indicator_data_series_for_user(request.user).filter(indicator=indicator)
    points_qs = (
        indicator_data_points_for_user(request.user)
        .filter(series__in=series_qs)
        .select_related("spatial_unit", "spatial_layer", "series")
        .order_by("year", "id")
    )
    if year_filter:
        try:
            points_qs = points_qs.filter(year=int(year_filter))
        except ValueError:
            pass

    grouped = defaultdict(list)
    for point in points_qs:
        if geography:
            disagg_text = str(point.disaggregation or "").lower()
            if geography not in disagg_text:
                continue
        if agg == "province":
            disagg = point.disaggregation or {}
            key = (
                disagg.get("province_code")
                or disagg.get("province")
                or (point.spatial_unit.unit_code if point.spatial_unit_id else "")
                or "UNKNOWN"
            )
        elif agg == "year":
            key = point.year
        else:
            key = point.series_id
        grouped[key].append(point)

    results = []
    for key in sorted(grouped, key=lambda item: str(item)):
        points = grouped[key]
        numeric_values = [float(item.value_numeric) for item in points if item.value_numeric is not None]
        results.append(
            {
                "bucket": key,
                "count": len(points),
                "numeric_mean": (sum(numeric_values) / len(numeric_values)) if numeric_values else None,
                "values": [
                    {
                        "year": item.year,
                        "value_numeric": float(item.value_numeric) if item.value_numeric is not None else None,
                        "value_text": item.value_text,
                        "disaggregation": item.disaggregation,
                        "spatial_resolution": item.spatial_resolution or item.series.spatial_resolution,
                        "spatial_unit": (
                            {
                                "uuid": str(item.spatial_unit.uuid),
                                "unit_code": item.spatial_unit.unit_code,
                                "name": item.spatial_unit.name,
                            }
                            if item.spatial_unit_id
                            else None
                        ),
                        "spatial_layer": (
                            {
                                "uuid": str(item.spatial_layer.uuid),
                                "layer_code": item.spatial_layer.layer_code,
                                "title": item.spatial_layer.title or item.spatial_layer.name,
                            }
                            if item.spatial_layer_id
                            else None
                        ),
                    }
                    for item in points
                ],
            }
        )

    return Response(
        {
            "indicator_uuid": str(indicator.uuid),
            "aggregation": agg,
            "results": results,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_indicator_map(request, indicator_uuid):
    indicator = get_object_or_404(_indicator_base_queryset(request.user), uuid=indicator_uuid)
    series_qs = indicator_data_series_for_user(request.user).filter(indicator=indicator).order_by("title", "uuid")
    points_qs = (
        indicator_data_points_for_user(request.user)
        .filter(series__in=series_qs, value_numeric__isnull=False)
        .select_related("spatial_unit", "spatial_layer", "programme_run")
        .order_by("year", "id")
    )
    year_param = request.GET.get("year")
    selected_year = None
    if year_param:
        try:
            selected_year = int(year_param)
        except ValueError:
            selected_year = None
    if selected_year is None:
        latest_point = points_qs.order_by("-year", "-id").first()
        selected_year = latest_point.year if latest_point else None
    if selected_year is None:
        return Response(
            {
                "indicator_uuid": str(indicator.uuid),
                "indicator_code": indicator.code,
                "year": None,
                "type": "FeatureCollection",
                "features": [],
            }
        )
    points_qs = points_qs.filter(year=selected_year)

    value_by_province = defaultdict(list)
    run_uuid_by_province = {}
    for point in points_qs:
        disagg = point.disaggregation or {}
        province_code = (
            disagg.get("province_code")
            or disagg.get("province")
            or (point.spatial_unit.unit_code if point.spatial_unit_id else "")
            or "UNKNOWN"
        )
        value_by_province[province_code].append(float(point.value_numeric))
        if province_code not in run_uuid_by_province and point.programme_run_id:
            run_uuid_by_province[province_code] = str(point.programme_run.uuid)
    mean_by_province = {
        code: (sum(values) / len(values)) if values else None
        for code, values in value_by_province.items()
    }

    requested_layer = (request.GET.get("layer_code") or "").strip()
    requirement = (
        IndicatorInputRequirement.objects.filter(indicator=indicator).prefetch_related("required_map_layers").first()
    )
    candidate_codes = []
    if requested_layer:
        candidate_codes.append(requested_layer)
    if requirement:
        candidate_codes.extend(
            requirement.required_map_layers.filter(theme__iexact="Admin").order_by("layer_code", "id").values_list(
                "layer_code", flat=True
            )
        )
        candidate_codes.extend(
            requirement.required_map_layers.order_by("layer_code", "id").values_list("layer_code", flat=True)
        )
    candidate_codes.extend(["ZA_PROVINCES_NE", "ZA_PROVINCES"])
    candidate_codes = [item for item in dict.fromkeys(candidate_codes) if item]

    layer = (
        filter_spatial_layers_for_user(SpatialLayer.objects.filter(layer_code__in=candidate_codes), request.user)
        .order_by("layer_code", "id")
        .first()
    )
    if not layer:
        return Response({"detail": "No accessible admin layer found for indicator map."}, status=status.HTTP_404_NOT_FOUND)

    bbox = parse_bbox(request.GET.get("bbox"))
    limit = _parse_positive_int(request.GET.get("limit"), 5000, minimum=1, maximum=5000)
    _, payload = spatial_feature_collection(
        user=request.user,
        layer_code=layer.layer_code,
        bbox=bbox,
        limit=limit,
        offset=0,
    )
    for feature in payload.get("features", []):
        props = feature.get("properties") or {}
        province_code = (
            props.get("province_code")
            or props.get("province")
            or props.get("feature_key")
            or props.get("feature_id")
            or "UNKNOWN"
        )
        value = mean_by_province.get(str(province_code))
        props["indicator_code"] = indicator.code
        props["indicator_year"] = selected_year
        props["indicator_value"] = value
        props["indicator_value_unit"] = "%"
        props["pipeline_run_uuid"] = run_uuid_by_province.get(str(province_code))
        feature["properties"] = props

    return Response(
        {
            "indicator_uuid": str(indicator.uuid),
            "indicator_code": indicator.code,
            "year": selected_year,
            "layer_code": layer.layer_code,
            **payload,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_indicator_validation(request, indicator_uuid):
    queryset = _indicator_base_queryset(request.user)
    indicator = get_object_or_404(queryset, uuid=indicator_uuid)
    series_qs = indicator_data_series_for_user(request.user).filter(indicator=indicator).order_by("title", "uuid")
    checks = []
    for series in series_qs:
        points = list(
            indicator_data_points_for_user(request.user)
            .filter(series=series)
            .order_by("year", "id")
        )
        state = "ok"
        notes = []
        if not points:
            state = "blocked"
            notes.append("No datapoints available.")
        elif len(points) < 2:
            state = "warning"
            notes.append("Only one datapoint available.")
        if series.value_type == "numeric" and any(point.value_numeric is None for point in points):
            state = "warning" if state == "ok" else state
            notes.append("Some datapoints are missing numeric values.")
        checks.append(
            {
                "series_uuid": str(series.uuid),
                "series_title": series.title,
                "state": state,
                "notes": notes or ["Validation passed."],
            }
        )
    return Response(
        {
            "indicator_uuid": str(indicator.uuid),
            "overall_state": "blocked"
            if any(item["state"] == "blocked" for item in checks)
            else ("warning" if any(item["state"] == "warning" for item in checks) else "ok"),
            "checks": checks,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_indicator_methods(request, indicator_uuid):
    indicator = get_object_or_404(_indicator_base_queryset(request.user), uuid=indicator_uuid)
    profiles = (
        IndicatorMethodProfile.objects.filter(indicator=indicator, is_active=True)
        .order_by("method_type", "implementation_key", "uuid")
    )
    profile_ids = list(profiles.values_list("id", flat=True))
    recent_runs = (
        IndicatorMethodRun.objects.filter(profile_id__in=profile_ids)
        .select_related("profile", "requested_by")
        .order_by("-created_at", "-id")[:40]
    )
    runs_by_profile = defaultdict(list)
    for run in recent_runs:
        runs_by_profile[run.profile_id].append(run)
    return Response(
        {
            "indicator_uuid": str(indicator.uuid),
            "profiles": [
                {
                    "uuid": str(profile.uuid),
                    "method_type": profile.method_type,
                    "implementation_key": profile.implementation_key,
                    "summary": profile.summary,
                    "required_inputs_json": profile.required_inputs_json,
                    "disaggregation_requirements_json": profile.disaggregation_requirements_json,
                    "readiness_state": profile.readiness_state,
                    "readiness_notes": profile.readiness_notes,
                    "last_run_at": profile.last_run_at.isoformat() if profile.last_run_at else None,
                    "last_success_at": profile.last_success_at.isoformat() if profile.last_success_at else None,
                    "recent_runs": [
                        {
                            "uuid": str(run.uuid),
                            "status": run.status,
                            "started_at": run.started_at.isoformat() if run.started_at else None,
                            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                            "requested_by": run.requested_by.username if run.requested_by_id else None,
                        }
                        for run in runs_by_profile.get(profile.id, [])
                    ],
                }
                for profile in profiles
            ],
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_indicator_method_run(request, indicator_uuid, profile_uuid):
    indicator = get_object_or_404(_indicator_base_queryset(request.user), uuid=indicator_uuid)
    profile = get_object_or_404(
        IndicatorMethodProfile.objects.filter(indicator=indicator, is_active=True),
        uuid=profile_uuid,
    )
    if not _can_run_indicator_methods(request.user):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    params = request.data.get("params") or {}
    use_cache = bool(request.data.get("use_cache", True))
    run = run_method_profile(profile=profile, user=request.user, params=params, use_cache=use_cache)
    return Response(
        {
            "run_uuid": str(run.uuid),
            "status": run.status,
            "output_json": run.output_json,
            "error_message": run.error_message,
            "profile_uuid": str(profile.uuid),
            "indicator_uuid": str(indicator.uuid),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_indicator_transition(request, indicator_uuid):
    queryset = filter_queryset_for_user(
        Indicator.objects.select_related("national_target", "organisation", "created_by"),
        request.user,
    )
    indicator = get_object_or_404(queryset, uuid=indicator_uuid)
    action = (request.data.get("action") or "").strip().lower()
    note = (request.data.get("note") or "").strip()
    try:
        if action == "submit":
            submit_for_review(indicator, request.user)
        elif action == "approve":
            approve(indicator, request.user, note=note)
        elif action == "reject":
            reject(indicator, request.user, note=note)
        elif action == "publish":
            if not IndicatorEvidenceLink.objects.filter(indicator=indicator).exists():
                return Response(
                    {"detail": "Evidence is required before publishing an indicator."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            publish(indicator, request.user)
        else:
            return Response({"detail": "Unsupported action."}, status=status.HTTP_400_BAD_REQUEST)
    except PermissionDenied as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:  # noqa: BLE001
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    indicator.refresh_from_db()
    return Response({"status": indicator.status, "indicator_uuid": str(indicator.uuid)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_indicator_release_transition(request, series_uuid):
    queryset = filter_queryset_for_user(
        IndicatorDataSeries.objects.select_related("indicator", "organisation", "created_by"),
        request.user,
        perm="nbms_app.view_indicatordataseries",
    )
    series = get_object_or_404(queryset, uuid=series_uuid)
    action = (request.data.get("action") or "").strip().lower()
    note = (request.data.get("note") or "").strip()
    try:
        if action == "submit":
            sense_check_attested = _parse_bool(request.data.get("sense_check_attested"), default=False)
            submit_indicator_release(
                series,
                request.user,
                note=note,
                sense_check_attested=sense_check_attested,
            )
        elif action == "approve":
            approve_indicator_release(series, request.user, note=note)
        else:
            return Response({"detail": "Unsupported action."}, status=status.HTTP_400_BAD_REQUEST)
    except PermissionDenied as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    series.refresh_from_db()
    return Response(
        {
            "series_uuid": str(series.uuid),
            "status": series.status,
            "workflow": get_release_workflow_state(series),
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_spatial_layers(request):
    layers = filter_spatial_layers_for_user(
        SpatialLayer.objects.select_related("indicator"),
        request.user,
    ).order_by("name", "slug")
    return Response(
        {
            "layers": [
                {
                    "uuid": str(layer.uuid),
                    "name": layer.name,
                    "slug": layer.slug,
                    "description": layer.description,
                    "source_type": layer.source_type,
                    "sensitivity": layer.sensitivity,
                    "is_public": layer.is_public,
                    "default_style_json": layer.default_style_json,
                    "indicator": {
                        "uuid": str(layer.indicator.uuid),
                        "code": layer.indicator.code,
                        "title": layer.indicator.title,
                    }
                    if layer.indicator_id
                    else None,
                }
                for layer in layers
            ]
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_spatial_layer_features(request, slug):
    bbox = parse_bbox(request.GET.get("bbox"))
    province = (request.GET.get("province") or "").strip()
    indicator = (request.GET.get("indicator") or "").strip()
    year = request.GET.get("year")
    limit = _parse_positive_int(request.GET.get("limit"), 1000, minimum=1, maximum=5000)
    parsed_year = None
    if year:
        try:
            parsed_year = int(year)
        except ValueError:
            parsed_year = None

    layer, payload = spatial_feature_collection(
        user=request.user,
        layer_slug=slug,
        bbox=bbox,
        province=province or None,
        indicator=indicator or None,
        year=parsed_year,
        limit=limit,
    )
    if not layer:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_template_pack_list(request):
    packs = ReportTemplatePack.objects.filter(is_active=True).order_by("mea_code", "code")
    return Response(
        {
            "packs": [
                {
                    "uuid": str(pack.uuid),
                    "code": pack.code,
                    "title": pack.title,
                    "mea_code": pack.mea_code,
                    "version": pack.version,
                    "description": pack.description,
                    "section_count": pack.sections.filter(is_active=True).count(),
                }
                for pack in packs
            ]
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_template_pack_sections(request, pack_code):
    pack = get_object_or_404(ReportTemplatePack.objects.filter(is_active=True), code=pack_code)
    sections = pack.sections.filter(is_active=True).order_by("ordering", "code")
    return Response(
        {
            "pack": {
                "code": pack.code,
                "title": pack.title,
                "mea_code": pack.mea_code,
                "version": pack.version,
            },
            "sections": [
                {
                    "uuid": str(section.uuid),
                    "code": section.code,
                    "title": section.title,
                    "ordering": section.ordering,
                    "schema_json": section.schema_json,
                }
                for section in sections
            ],
        }
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_template_pack_instance_responses(request, pack_code, instance_uuid):
    pack = get_object_or_404(ReportTemplatePack.objects.filter(is_active=True), code=pack_code)
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _require_instance_scope(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "POST":
        section_code = (request.data.get("section_code") or "").strip()
        response_json = request.data.get("response_json") or {}
        if not isinstance(response_json, dict):
            return Response(
                {"detail": "response_json must be a JSON object."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        section = get_object_or_404(
            ReportTemplatePackSection.objects.filter(pack=pack, is_active=True),
            code=section_code,
        )
        response, _created = ReportTemplatePackResponse.objects.update_or_create(
            reporting_instance=instance,
            section=section,
            defaults={"response_json": response_json, "updated_by": request.user},
        )
        return Response(
            {
                "uuid": str(response.uuid),
                "section_code": section.code,
                "response_json": response.response_json,
            }
        )

    sections = pack.sections.filter(is_active=True).order_by("ordering", "code")
    responses = (
        ReportTemplatePackResponse.objects.filter(reporting_instance=instance, section__pack=pack)
        .select_related("section", "updated_by")
        .order_by("section__ordering", "section__code")
    )
    response_map = {row.section.code: row for row in responses}
    return Response(
        {
            "pack": {
                "code": pack.code,
                "title": pack.title,
                "mea_code": pack.mea_code,
            },
            "instance_uuid": str(instance.uuid),
            "responses": [
                {
                    "section_code": section.code,
                    "section_title": section.title,
                    "response_json": (
                        response_map[section.code].response_json
                        if section.code in response_map
                        else _default_pack_response_payload(section)
                    ),
                    "updated_by": (
                        response_map[section.code].updated_by.username
                        if section.code in response_map and response_map[section.code].updated_by
                        else None
                    ),
                    "updated_at": (
                        response_map[section.code].updated_at.isoformat()
                        if section.code in response_map
                        else None
                    ),
                }
                for section in sections
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_template_pack_validate(request, pack_code, instance_uuid):
    pack = get_object_or_404(ReportTemplatePack.objects.filter(is_active=True), code=pack_code)
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _require_instance_scope(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    validation = build_pack_validation(pack=pack, instance=instance, user=request.user)
    return Response(validation)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_template_pack_pdf(request, pack_code, instance_uuid):
    pack = get_object_or_404(ReportTemplatePack.objects.filter(is_active=True), code=pack_code)
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _require_instance_scope(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    try:
        pdf_bytes = render_pack_pdf_bytes(pack=pack, instance=instance, user=request.user)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    filename = f"{pack.code}_{instance.uuid}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_template_pack_export(request, pack_code, instance_uuid):
    pack = get_object_or_404(ReportTemplatePack.objects.filter(is_active=True), code=pack_code)
    instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
    if not _require_instance_scope(request.user, instance):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    exporter = resolve_pack_exporter(pack)
    if not exporter:
        return Response({"detail": "No exporter registered for this pack."}, status=status.HTTP_400_BAD_REQUEST)
    payload = exporter(instance, request.user)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_report_product_list(request):
    seed_default_report_products()
    templates = ReportProductTemplate.objects.filter(is_active=True).order_by("code")
    return Response(
        {
            "report_products": [
                {
                    "uuid": str(template.uuid),
                    "code": template.code,
                    "title": template.title,
                    "version": template.version,
                    "description": template.description,
                }
                for template in templates
            ]
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_report_product_preview(request, product_code):
    template = get_object_or_404(ReportProductTemplate.objects.filter(is_active=True), code=product_code)
    instance_uuid = (request.GET.get("instance_uuid") or "").strip()
    instance = None
    if instance_uuid:
        instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
        if not _require_instance_scope(request.user, instance):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    payload = build_report_product_payload(template=template, instance=instance, user=request.user)
    html = render_report_product_html(template=template, payload=payload)
    run = generate_report_product_run(template=template, instance=instance, user=request.user)
    return Response(
        {
            "template": {
                "code": template.code,
                "title": template.title,
                "version": template.version,
            },
            "payload": payload,
            "html_preview": html,
            "run_uuid": str(run.uuid),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_report_product_html(request, product_code):
    template = get_object_or_404(ReportProductTemplate.objects.filter(is_active=True), code=product_code)
    instance_uuid = (request.GET.get("instance_uuid") or "").strip()
    instance = None
    if instance_uuid:
        instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
        if not _require_instance_scope(request.user, instance):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    payload = build_report_product_payload(template=template, instance=instance, user=request.user)
    html = render_report_product_html(template=template, payload=payload)
    return HttpResponse(html, content_type="text/html; charset=utf-8")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_report_product_pdf(request, product_code):
    template = get_object_or_404(ReportProductTemplate.objects.filter(is_active=True), code=product_code)
    instance_uuid = (request.GET.get("instance_uuid") or "").strip()
    instance = None
    if instance_uuid:
        instance = get_object_or_404(ReportingInstance, uuid=instance_uuid)
        if not _require_instance_scope(request.user, instance):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    payload = build_report_product_payload(template=template, instance=instance, user=request.user)
    try:
        pdf_bytes = render_report_product_pdf_bytes(template=template, payload=payload)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    filename = f"{template.code}_{instance.uuid if instance else 'global'}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_report_product_runs(request):
    queryset = ReportProductRun.objects.select_related("template", "reporting_instance", "generated_by").order_by(
        "-created_at",
        "-id",
    )[:50]
    if not (is_system_admin(request.user) or getattr(request.user, "is_staff", False)):
        queryset = queryset.filter(generated_by=request.user)
    return Response(
        {
            "runs": [
                {
                    "uuid": str(row.uuid),
                    "template_code": row.template.code,
                    "status": row.status,
                    "reporting_instance_uuid": str(row.reporting_instance.uuid) if row.reporting_instance_id else None,
                    "generated_by": row.generated_by.username if row.generated_by_id else None,
                    "generated_at": row.generated_at.isoformat() if row.generated_at else None,
                    "created_at": row.created_at.isoformat(),
                }
                for row in queryset
            ]
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_registry_ecosystems(request):
    queryset = filter_queryset_for_user(
        EcosystemType.objects.select_related("organisation", "get_node").order_by("ecosystem_code", "name", "uuid"),
        request.user,
    )
    biome = (request.GET.get("biome") or "").strip()
    if biome:
        queryset = queryset.filter(biome__icontains=biome)
    bioregion = (request.GET.get("bioregion") or "").strip()
    if bioregion:
        queryset = queryset.filter(bioregion__icontains=bioregion)
    version = (request.GET.get("version") or "").strip()
    if version:
        queryset = queryset.filter(vegmap_version__icontains=version)
    get_efg = (request.GET.get("get_efg") or "").strip()
    if get_efg:
        queryset = queryset.filter(
            Q(get_node__code__icontains=get_efg) | Q(typology_crosswalks__get_node__code__icontains=get_efg)
        ).distinct()
    threat_category = (request.GET.get("threat_category") or "").strip()
    if threat_category:
        queryset = queryset.filter(risk_assessments__category__iexact=threat_category).distinct()

    page_size = _parse_positive_int(request.GET.get("page_size"), default=25, minimum=1, maximum=100)
    page = _parse_positive_int(request.GET.get("page"), default=1, minimum=1, maximum=10000)
    total = queryset.count()
    start = (page - 1) * page_size
    results = queryset[start : start + page_size]

    return Response(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": [
                {
                    "uuid": str(row.uuid),
                    "ecosystem_code": row.ecosystem_code,
                    "name": row.name,
                    "realm": row.realm,
                    "biome": row.biome,
                    "bioregion": row.bioregion,
                    "vegmap_version": row.vegmap_version,
                    "get_node": row.get_node.code if row.get_node_id else None,
                    "status": row.status,
                    "sensitivity": row.sensitivity,
                    "qa_status": row.qa_status,
                    "organisation": row.organisation.name if row.organisation_id else None,
                    "updated_at": row.updated_at.isoformat(),
                }
                for row in results
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_registry_ecosystem_detail(request, ecosystem_uuid):
    queryset = filter_queryset_for_user(EcosystemType.objects.select_related("organisation", "get_node"), request.user)
    ecosystem = get_object_or_404(queryset, uuid=ecosystem_uuid)
    crosswalks = (
        EcosystemTypologyCrosswalk.objects.filter(ecosystem_type=ecosystem)
        .select_related("get_node", "reviewed_by")
        .order_by("-is_primary", "-confidence", "get_node__level", "get_node__code", "id")
    )
    risk_assessments = (
        EcosystemRiskAssessment.objects.filter(ecosystem_type=ecosystem)
        .select_related("assessor", "reviewed_by")
        .order_by("-assessment_year", "assessment_scope", "id")
    )
    return Response(
        {
            "ecosystem": {
                "uuid": str(ecosystem.uuid),
                "ecosystem_code": ecosystem.ecosystem_code,
                "name": ecosystem.name,
                "realm": ecosystem.realm,
                "biome": ecosystem.biome,
                "bioregion": ecosystem.bioregion,
                "vegmap_version": ecosystem.vegmap_version,
                "vegmap_source_id": ecosystem.vegmap_source_id,
                "description": ecosystem.description,
                "get_node": ecosystem.get_node.code if ecosystem.get_node_id else None,
                "status": ecosystem.status,
                "sensitivity": ecosystem.sensitivity,
                "qa_status": ecosystem.qa_status,
                "organisation": ecosystem.organisation.name if ecosystem.organisation_id else None,
                "updated_at": ecosystem.updated_at.isoformat(),
            },
            "crosswalks": [
                {
                    "uuid": str(row.uuid),
                    "get_code": row.get_node.code,
                    "get_level": row.get_node.level,
                    "get_label": row.get_node.label,
                    "confidence": row.confidence,
                    "review_status": row.review_status,
                    "is_primary": row.is_primary,
                    "evidence": row.evidence,
                    "reviewed_by": row.reviewed_by.username if row.reviewed_by_id else None,
                    "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
                }
                for row in crosswalks
            ],
            "risk_assessments": [
                {
                    "uuid": str(row.uuid),
                    "assessment_year": row.assessment_year,
                    "assessment_scope": row.assessment_scope,
                    "category": row.category,
                    "criterion_a": row.criterion_a,
                    "criterion_b": row.criterion_b,
                    "criterion_c": row.criterion_c,
                    "criterion_d": row.criterion_d,
                    "criterion_e": row.criterion_e,
                    "review_status": row.review_status,
                    "assessor": row.assessor.username if row.assessor_id else None,
                    "reviewed_by": row.reviewed_by.username if row.reviewed_by_id else None,
                    "updated_at": row.updated_at.isoformat(),
                }
                for row in risk_assessments
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_registry_taxa(request):
    queryset = filter_queryset_for_user(TaxonConcept.objects.select_related("organisation").order_by("scientific_name", "taxon_code"), request.user)
    rank = (request.GET.get("rank") or "").strip()
    if rank:
        queryset = queryset.filter(taxon_rank__iexact=rank)
    status_filter = (request.GET.get("status") or "").strip()
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    source = (request.GET.get("source") or "").strip()
    if source:
        queryset = queryset.filter(primary_source_system__icontains=source)
    has_voucher = (request.GET.get("has_voucher") or "").strip().lower()
    if has_voucher in {"true", "false"}:
        queryset = queryset.filter(has_national_voucher_specimen=(has_voucher == "true"))
    native = (request.GET.get("native") or "").strip().lower()
    if native in {"true", "false"}:
        queryset = queryset.filter(is_native=(native == "true"))
    endemic = (request.GET.get("endemic") or "").strip().lower()
    if endemic in {"true", "false"}:
        queryset = queryset.filter(is_endemic=(endemic == "true"))
    search = (request.GET.get("search") or "").strip()
    if search:
        queryset = queryset.filter(
            Q(scientific_name__icontains=search)
            | Q(canonical_name__icontains=search)
            | Q(taxon_code__icontains=search)
            | Q(family__icontains=search)
            | Q(genus__icontains=search)
        )

    page_size = _parse_positive_int(request.GET.get("page_size"), default=25, minimum=1, maximum=100)
    page = _parse_positive_int(request.GET.get("page"), default=1, minimum=1, maximum=10000)
    total = queryset.count()
    start = (page - 1) * page_size
    results = queryset[start : start + page_size]

    return Response(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": [
                {
                    "uuid": str(row.uuid),
                    "taxon_code": row.taxon_code,
                    "scientific_name": row.scientific_name,
                    "canonical_name": row.canonical_name,
                    "taxon_rank": row.taxon_rank,
                    "taxonomic_status": row.taxonomic_status,
                    "kingdom": row.kingdom,
                    "family": row.family,
                    "genus": row.genus,
                    "is_native": row.is_native,
                    "is_endemic": row.is_endemic,
                    "has_national_voucher_specimen": row.has_national_voucher_specimen,
                    "voucher_specimen_count": row.voucher_specimen_count,
                    "primary_source_system": row.primary_source_system,
                    "status": row.status,
                    "sensitivity": row.sensitivity,
                    "qa_status": row.qa_status,
                    "organisation": row.organisation.name if row.organisation_id else None,
                    "updated_at": row.updated_at.isoformat(),
                }
                for row in results
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_registry_taxon_detail(request, taxon_uuid):
    queryset = filter_queryset_for_user(TaxonConcept.objects.select_related("organisation"), request.user)
    taxon = get_object_or_404(queryset, uuid=taxon_uuid)

    names = TaxonName.objects.filter(taxon=taxon).order_by("-is_preferred", "name_type", "name", "id")
    source_records = TaxonSourceRecord.objects.filter(taxon=taxon).order_by("-retrieved_at", "source_system", "id")
    vouchers_qs = filter_queryset_for_user(
        SpecimenVoucher.objects.filter(taxon=taxon).select_related("organisation").order_by("-event_date", "occurrence_id", "id"),
        request.user,
    )
    can_view_sensitive = _can_view_sensitive_locality(request.user)

    voucher_rows = []
    for row in vouchers_qs:
        hide_locality = bool(row.has_sensitive_locality and not can_view_sensitive)
        voucher_rows.append(
            {
                "uuid": str(row.uuid),
                "occurrence_id": row.occurrence_id,
                "institution_code": row.institution_code,
                "collection_code": row.collection_code,
                "catalog_number": row.catalog_number,
                "basis_of_record": row.basis_of_record,
                "event_date": row.event_date.isoformat() if row.event_date else None,
                "country_code": row.country_code,
                "locality": "Restricted locality" if hide_locality else row.locality,
                "decimal_latitude": None if hide_locality else float(row.decimal_latitude) if row.decimal_latitude is not None else None,
                "decimal_longitude": None if hide_locality else float(row.decimal_longitude) if row.decimal_longitude is not None else None,
                "has_sensitive_locality": row.has_sensitive_locality,
                "sensitivity": row.sensitivity,
                "status": row.status,
            }
        )

    return Response(
        {
            "taxon": {
                "uuid": str(taxon.uuid),
                "taxon_code": taxon.taxon_code,
                "scientific_name": taxon.scientific_name,
                "canonical_name": taxon.canonical_name,
                "taxon_rank": taxon.taxon_rank,
                "taxonomic_status": taxon.taxonomic_status,
                "classification": {
                    "kingdom": taxon.kingdom,
                    "phylum": taxon.phylum,
                    "class_name": taxon.class_name,
                    "order": taxon.order,
                    "family": taxon.family,
                    "genus": taxon.genus,
                    "species": taxon.species,
                },
                "gbif_taxon_key": taxon.gbif_taxon_key,
                "gbif_usage_key": taxon.gbif_usage_key,
                "gbif_accepted_taxon_key": taxon.gbif_accepted_taxon_key,
                "is_native": taxon.is_native,
                "is_endemic": taxon.is_endemic,
                "has_national_voucher_specimen": taxon.has_national_voucher_specimen,
                "voucher_specimen_count": taxon.voucher_specimen_count,
                "primary_source_system": taxon.primary_source_system,
                "status": taxon.status,
                "sensitivity": taxon.sensitivity,
                "qa_status": taxon.qa_status,
                "organisation": taxon.organisation.name if taxon.organisation_id else None,
                "updated_at": taxon.updated_at.isoformat(),
            },
            "names": [
                {
                    "uuid": str(row.uuid),
                    "name": row.name,
                    "name_type": row.name_type,
                    "language": row.language,
                    "is_preferred": row.is_preferred,
                }
                for row in names
            ],
            "source_records": [
                {
                    "uuid": str(row.uuid),
                    "source_system": row.source_system,
                    "source_ref": row.source_ref,
                    "source_url": row.source_url,
                    "retrieved_at": row.retrieved_at.isoformat(),
                    "payload_hash": row.payload_hash,
                    "licence": row.licence,
                    "citation": row.citation,
                    "is_primary": row.is_primary,
                }
                for row in source_records
            ],
            "vouchers": voucher_rows,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_registry_ias(request):
    queryset = filter_queryset_for_user(
        AlienTaxonProfile.objects.select_related("taxon", "organisation").order_by("taxon__scientific_name", "country_code", "id"),
        request.user,
    )
    stage = (request.GET.get("stage") or "").strip().lower()
    if stage:
        queryset = queryset.filter(degree_of_establishment_code=stage)
    pathway = (request.GET.get("pathway") or "").strip().lower()
    if pathway:
        queryset = queryset.filter(pathway_code=pathway)
    habitat = (request.GET.get("habitat") or "").strip().lower()
    if habitat:
        queryset = queryset.filter(habitat_types_json__icontains=habitat)
    eicat = (request.GET.get("eicat") or "").strip().upper()
    if eicat:
        queryset = queryset.filter(eicat_assessments__category=eicat).distinct()
    seicat = (request.GET.get("seicat") or "").strip().upper()
    if seicat:
        queryset = queryset.filter(seicat_assessments__category=seicat).distinct()
    search = (request.GET.get("search") or "").strip()
    if search:
        queryset = queryset.filter(
            Q(taxon__scientific_name__icontains=search)
            | Q(taxon__canonical_name__icontains=search)
            | Q(taxon__taxon_code__icontains=search)
        )

    page_size = _parse_positive_int(request.GET.get("page_size"), default=25, minimum=1, maximum=100)
    page = _parse_positive_int(request.GET.get("page"), default=1, minimum=1, maximum=10000)
    total = queryset.count()
    start = (page - 1) * page_size
    results = queryset[start : start + page_size]

    return Response(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": [
                {
                    "uuid": str(row.uuid),
                    "taxon_uuid": str(row.taxon.uuid),
                    "taxon_code": row.taxon.taxon_code,
                    "scientific_name": row.taxon.scientific_name,
                    "country_code": row.country_code,
                    "establishment_means_code": row.establishment_means_code,
                    "degree_of_establishment_code": row.degree_of_establishment_code,
                    "pathway_code": row.pathway_code,
                    "is_invasive": row.is_invasive,
                    "regulatory_status": row.regulatory_status,
                    "latest_eicat": (
                        row.eicat_assessments.order_by("-assessed_on", "-id").values_list("category", flat=True).first()
                    ),
                    "latest_seicat": (
                        row.seicat_assessments.order_by("-assessed_on", "-id").values_list("category", flat=True).first()
                    ),
                    "status": row.status,
                    "sensitivity": row.sensitivity,
                    "qa_status": row.qa_status,
                    "updated_at": row.updated_at.isoformat(),
                }
                for row in results
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_registry_ias_detail(request, profile_uuid):
    queryset = filter_queryset_for_user(
        AlienTaxonProfile.objects.select_related("taxon", "organisation"),
        request.user,
    )
    profile = get_object_or_404(queryset, uuid=profile_uuid)

    checklist_rows = IASCountryChecklistRecord.objects.filter(taxon=profile.taxon).order_by("country_code", "source_identifier", "id")
    eicat_rows = EICATAssessment.objects.filter(profile=profile).select_related("assessed_by", "reviewed_by").order_by("-assessed_on", "id")
    seicat_rows = SEICATAssessment.objects.filter(profile=profile).select_related("assessed_by", "reviewed_by").order_by("-assessed_on", "id")

    return Response(
        {
            "profile": {
                "uuid": str(profile.uuid),
                "taxon_uuid": str(profile.taxon.uuid),
                "taxon_code": profile.taxon.taxon_code,
                "scientific_name": profile.taxon.scientific_name,
                "country_code": profile.country_code,
                "establishment_means_code": profile.establishment_means_code,
                "establishment_means_label": profile.establishment_means_label,
                "degree_of_establishment_code": profile.degree_of_establishment_code,
                "degree_of_establishment_label": profile.degree_of_establishment_label,
                "pathway_code": profile.pathway_code,
                "pathway_label": profile.pathway_label,
                "habitat_types_json": profile.habitat_types_json,
                "regulatory_status": profile.regulatory_status,
                "is_invasive": profile.is_invasive,
                "status": profile.status,
                "sensitivity": profile.sensitivity,
                "qa_status": profile.qa_status,
                "updated_at": profile.updated_at.isoformat(),
            },
            "checklist_records": [
                {
                    "uuid": str(row.uuid),
                    "source_dataset": row.source_dataset,
                    "source_identifier": row.source_identifier,
                    "country_code": row.country_code,
                    "is_alien": row.is_alien,
                    "is_invasive": row.is_invasive,
                    "establishment_means_code": row.establishment_means_code,
                    "degree_of_establishment_code": row.degree_of_establishment_code,
                    "pathway_code": row.pathway_code,
                    "retrieved_at": row.retrieved_at.isoformat() if row.retrieved_at else None,
                }
                for row in checklist_rows
            ],
            "eicat_assessments": [
                {
                    "uuid": str(row.uuid),
                    "category": row.category,
                    "mechanisms_json": row.mechanisms_json,
                    "impact_scope": row.impact_scope,
                    "confidence": row.confidence,
                    "review_status": row.review_status,
                    "assessed_on": row.assessed_on.isoformat() if row.assessed_on else None,
                    "assessed_by": row.assessed_by.username if row.assessed_by_id else None,
                    "reviewed_by": row.reviewed_by.username if row.reviewed_by_id else None,
                }
                for row in eicat_rows
            ],
            "seicat_assessments": [
                {
                    "uuid": str(row.uuid),
                    "category": row.category,
                    "wellbeing_constituents_json": row.wellbeing_constituents_json,
                    "activity_change_narrative": row.activity_change_narrative,
                    "confidence": row.confidence,
                    "review_status": row.review_status,
                    "assessed_on": row.assessed_on.isoformat() if row.assessed_on else None,
                    "assessed_by": row.assessed_by.username if row.assessed_by_id else None,
                    "reviewed_by": row.reviewed_by.username if row.reviewed_by_id else None,
                }
                for row in seicat_rows
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_registry_gold_summaries(request):
    kind = (request.GET.get("kind") or "").strip().lower() or "ecosystems"
    model = _registry_gold_model(kind)
    if model is None:
        return Response({"detail": "Unsupported registry summary kind."}, status=status.HTTP_400_BAD_REQUEST)

    queryset = filter_queryset_for_user(model.objects.select_related("organisation"), request.user)

    snapshot_date = (request.GET.get("snapshot_date") or "").strip()
    if snapshot_date:
        queryset = queryset.filter(snapshot_date=snapshot_date)
    else:
        latest = latest_snapshot_date(model)
        if latest:
            queryset = queryset.filter(snapshot_date=latest)

    organisation_id = (request.GET.get("organisation_id") or "").strip()
    if organisation_id.isdigit():
        queryset = queryset.filter(organisation_id=int(organisation_id))

    if kind in {"ecosystems", "ias"}:
        dimension = (request.GET.get("dimension") or "").strip().lower()
        if dimension:
            queryset = queryset.filter(dimension=dimension)

    limit = _parse_positive_int(request.GET.get("limit"), default=200, minimum=1, maximum=1000)
    rows = _registry_gold_payload(kind, queryset, limit)
    return Response(
        {
            "kind": kind,
            "count": queryset.count(),
            "rows": rows,
        }
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def api_registry_object_evidence(request, object_type, object_uuid):
    try:
        _target, obj = get_registry_object(object_type=object_type, object_uuid=object_uuid, user=request.user)
    except Exception:  # noqa: BLE001
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response({"evidence_links": list_registry_evidence_links(obj=obj, user=request.user)})

    if not _can_manage_registry_workflows(request.user):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    evidence_uuid = (request.data.get("evidence_uuid") or "").strip()
    if not evidence_uuid:
        return Response({"detail": "evidence_uuid is required."}, status=status.HTTP_400_BAD_REQUEST)
    note = request.data.get("note") or ""
    try:
        link = link_registry_evidence(obj=obj, evidence_uuid=evidence_uuid, user=request.user, note=note)
    except PermissionDenied:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(
        {
            "link": {
                "uuid": str(link.uuid),
                "evidence_uuid": str(link.evidence.uuid),
                "title": link.evidence.title,
                "notes": link.notes,
            }
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_registry_transition(request, object_type, object_uuid):
    if not _can_manage_registry_workflows(request.user):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    action = (request.data.get("action") or "").strip().lower()
    note = request.data.get("note") or ""
    evidence_uuids = request.data.get("evidence_uuids") or []
    if not isinstance(evidence_uuids, list):
        return Response({"detail": "evidence_uuids must be a list."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        obj = transition_registry_object(
            object_type=object_type,
            object_uuid=object_uuid,
            action=action,
            user=request.user,
            note=note,
            evidence_uuids=evidence_uuids,
        )
    except PermissionDenied:
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:  # noqa: BLE001
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(
        {
            "object_uuid": str(obj.uuid),
            "status": obj.status,
            "review_status": getattr(obj, "review_status", ""),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_programme_templates(request):
    queryset = ProgrammeTemplate.objects.filter(is_active=True).select_related("organisation").order_by(
        "domain",
        "template_code",
        "id",
    )
    domain = (request.GET.get("domain") or "").strip().lower()
    if domain:
        queryset = queryset.filter(domain=domain)
    template_codes = list(queryset.values_list("template_code", flat=True))
    linked_programmes = {
        row["programme_code"]: str(row["uuid"])
        for row in MonitoringProgramme.objects.filter(programme_code__in=template_codes, is_active=True).values(
            "programme_code",
            "uuid",
        )
    }
    return Response(
        {
            "templates": [
                {
                    "uuid": str(row.uuid),
                    "template_code": row.template_code,
                    "title": row.title,
                    "description": row.description,
                    "domain": row.domain,
                    "pipeline_definition_json": row.pipeline_definition_json,
                    "required_outputs_json": row.required_outputs_json,
                    "status": row.status,
                    "sensitivity": row.sensitivity,
                    "qa_status": row.qa_status,
                    "organisation": row.organisation.name if row.organisation_id else None,
                    "updated_at": row.updated_at.isoformat(),
                    "linked_programme_uuid": linked_programmes.get(row.template_code),
                }
                for row in queryset
            ]
        }
    )
