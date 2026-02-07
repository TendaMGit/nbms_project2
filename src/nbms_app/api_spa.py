from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.db import connections
from django.db.models import Count, Q
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from nbms_app.models import (
    AuditEvent,
    BirdieModelOutput,
    BirdieSite,
    BirdieSpecies,
    Dataset,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorDatasetLink,
    IndicatorEvidenceLink,
    IndicatorFrameworkIndicatorLink,
    IndicatorMethodProfile,
    IndicatorMethodRun,
    IndicatorMethodologyVersionLink,
    InstanceExportApproval,
    LifecycleStatus,
    MonitoringProgramme,
    MonitoringProgrammeAlert,
    MonitoringProgrammeRun,
    MonitoringProgrammeRunStep,
    ProgrammeAlertState,
    ProgrammeRunStatus,
    ProgrammeRunType,
    ReportProductTemplate,
    ReportProductRun,
    ReportTemplatePack,
    ReportTemplatePackResponse,
    ReportTemplatePackSection,
    ReportingInstance,
    ReportingStatus,
    SpatialLayer,
    IntegrationDataAsset,
    SensitivityLevel,
)
from nbms_app.section_help import SECTION_FIELD_HELP, build_section_help_payload
from nbms_app.services.authorization import (
    ROLE_ADMIN,
    ROLE_DATA_STEWARD,
    ROLE_INDICATOR_LEAD,
    ROLE_SECRETARIAT,
    ROLE_SYSTEM_ADMIN,
    filter_queryset_for_user,
    is_system_admin,
    user_has_role,
)
from nbms_app.services.catalog_access import filter_monitoring_programmes_for_user
from nbms_app.services.indicator_data import indicator_data_points_for_user, indicator_data_series_for_user
from nbms_app.services.indicator_method_sdk import run_method_profile
from nbms_app.services.nr7_builder import (
    build_nr7_preview_payload,
    build_nr7_validation_summary,
    render_nr7_pdf_bytes,
)
from nbms_app.services.programme_ops import execute_programme_run, queue_programme_run, user_can_manage_programme
from nbms_app.services.readiness import get_instance_readiness
from nbms_app.services.section_progress import scoped_national_targets
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


def _capabilities(user):
    return {
        "is_staff": bool(getattr(user, "is_staff", False)),
        "is_system_admin": bool(is_system_admin(user)),
        "can_manage_exports": bool(user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN)),
        "can_review": bool(user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN)),
        "can_publish": bool(user_has_role(user, ROLE_SECRETARIAT, ROLE_ADMIN) or is_system_admin(user)),
        "can_edit_indicators": bool(
            user_has_role(user, ROLE_INDICATOR_LEAD, ROLE_DATA_STEWARD, ROLE_SECRETARIAT, ROLE_ADMIN)
            or is_system_admin(user)
        ),
    }


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
        "updated_at": indicator.updated_at.isoformat(),
        "tags": sorted(set(tags)),
        "method_readiness_state": readiness_state,
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
            "capabilities": _capabilities(user),
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_auth_csrf(request):
    token = get_token(request)
    return Response({"csrfToken": token})


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

    return Response(
        {
            "counts": counts,
            "approvals_queue": approvals_queue,
            "latest_published_updates": latest_updates,
            "data_quality_alerts": quality_alerts[:20],
            "published_by_framework_target": list(chart_by_target),
            "approvals_over_time": list(approvals_over_time),
            "trend_signals": trend_signals,
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
        .prefetch_related("steps")
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
        MonitoringProgrammeRun.objects.select_related("programme", "requested_by").prefetch_related("steps"),
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_reporting_instances(request):
    if not (is_system_admin(request.user) or getattr(request.user, "is_staff", False)):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

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
                "version_label": instance.version_label,
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
    method_profiles = (
        IndicatorMethodProfile.objects.filter(indicator=indicator, is_active=True)
        .order_by("method_type", "implementation_key", "uuid")
    )

    return Response(
        {
            "indicator": _indicator_payload(indicator),
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

    series_qs = indicator_data_series_for_user(request.user).filter(indicator=indicator)
    points_qs = indicator_data_points_for_user(request.user).filter(series__in=series_qs).order_by("year", "id")

    grouped = defaultdict(list)
    for point in points_qs:
        if geography:
            disagg_text = str(point.disaggregation or "").lower()
            if geography not in disagg_text:
                continue
        key = point.year if agg == "year" else point.series_id
        grouped[key].append(point)

    results = []
    for key in sorted(grouped):
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
