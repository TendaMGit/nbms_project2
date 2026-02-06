from collections import defaultdict
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from nbms_app.models import (
    AuditEvent,
    Dataset,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorDatasetLink,
    IndicatorEvidenceLink,
    IndicatorFrameworkIndicatorLink,
    IndicatorMethodologyVersionLink,
    InstanceExportApproval,
    LifecycleStatus,
    ReportTemplatePack,
    ReportTemplatePackResponse,
    ReportTemplatePackSection,
    ReportingInstance,
    ReportingStatus,
    SpatialLayer,
    SensitivityLevel,
)
from nbms_app.section_help import SECTION_FIELD_HELP
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
from nbms_app.services.indicator_data import indicator_data_points_for_user, indicator_data_series_for_user
from nbms_app.services.section_progress import scoped_national_targets
from nbms_app.services.spatial_access import (
    filter_spatial_layers_for_user,
    parse_bbox,
    spatial_feature_collection,
)
from nbms_app.services.template_pack_registry import resolve_pack_exporter
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


def _default_pack_response_payload(section):
    schema_fields = section.schema_json.get("fields", [])
    return {field.get("key"): "" for field in schema_fields if field.get("key")}


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
