from collections import defaultdict
from datetime import timezone as dt_timezone

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone

from nbms_app.models import (
    ConsentRecord,
    ConsentStatus,
    DatasetRelease,
    FrameworkIndicator,
    FrameworkTarget,
    FrameworkIndicatorType,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorDatasetLink,
    IndicatorFrameworkIndicatorLink,
    LifecycleStatus,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
)
from nbms_app.services.alignment import filter_indicator_framework_links_for_user, filter_target_framework_links_for_user
from nbms_app.services.alignment_coverage import get_selected_targets_and_indicators
from nbms_app.services.alignment_ordering import sort_dicts, sort_model_items
from nbms_app.services.authorization import filter_queryset_for_user, is_system_admin
from nbms_app.services.consent import requires_consent
from nbms_app.services.indicator_data import indicator_data_series_for_user
from nbms_app.services.instance_approvals import approved_queryset


class _StrictUserProxy:
    def __init__(self, user):
        self._user = user

    def __getattr__(self, name):
        if name in {"is_staff", "is_superuser"}:
            return False
        return getattr(self._user, name)


def _strict_user(user):
    if not user:
        return user
    if is_system_admin(user):
        return user
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return _StrictUserProxy(user)
    return user


def _consent_granted_uuids(instance, model):
    content_type = ContentType.objects.get_for_model(model)
    qs = ConsentRecord.objects.filter(content_type=content_type, status=ConsentStatus.GRANTED)
    if instance:
        qs = qs.filter(Q(reporting_instance=instance) | Q(reporting_instance__isnull=True))
    else:
        qs = qs.filter(reporting_instance__isnull=True)
    return set(qs.values_list("object_uuid", flat=True))


def _apply_consent_filter(items, consent_granted):
    filtered = []
    for obj in items:
        if not requires_consent(obj) or obj.uuid in consent_granted:
            filtered.append(obj)
    return filtered


def _percent(part, total):
    if not total:
        return 0.0
    return round((part / total) * 100, 1)


def _indicator_level_value(value):
    if not value:
        return None
    return str(value).lower().strip()


def _reporting_capability_value(indicator):
    return str(getattr(indicator, "reporting_capability", "") or "").lower().strip()


def compute_hl21_1_gap_analysis(
    *,
    user,
    instance=None,
    scope="selected",
    framework_code="GBF",
    indicator_level="headline",
    include_details=True,
    include_charts_data=True,
):
    """
    Compute interim HL21.1 gap analysis for GBF headline framework indicators.

    Variants produced:
    - coverage_only: headline framework indicator has >=1 mapped national indicator
    - coverage_reportability: coverage_only + evidence of reportability (series or dataset release or reporting_capability)

    Scope behavior:
    - selected (requires instance): selection uses Section III/IV progress -> approvals -> none
    - all: all visible registry items for the user (ABAC filtered)
    """
    if scope not in {"selected", "all"}:
        raise ValueError("Invalid scope.")
    if scope == "selected" and not instance:
        raise ValueError("Instance is required for selected scope.")

    strict_user = _strict_user(user)
    indicator_level = _indicator_level_value(indicator_level) or FrameworkIndicatorType.HEADLINE

    selection_source = None
    selected_targets = []
    selected_indicators = []

    if scope == "selected":
        targets_qs, indicators_qs, selection_source = get_selected_targets_and_indicators(
            instance=instance,
            user=user,
        )
        target_consent = _consent_granted_uuids(instance, NationalTarget)
        indicator_consent = _consent_granted_uuids(instance, Indicator)
        selected_targets = _apply_consent_filter(list(targets_qs), target_consent)
        selected_indicators = _apply_consent_filter(list(indicators_qs), indicator_consent)
    else:
        target_consent = _consent_granted_uuids(instance, NationalTarget)
        indicator_consent = _consent_granted_uuids(instance, Indicator)
        selected_targets = []
        selected_indicators = []

    framework_target_consent = _consent_granted_uuids(instance, FrameworkTarget)
    framework_indicator_consent = _consent_granted_uuids(instance, FrameworkIndicator)

    if scope == "selected":
        if not selected_targets:
            framework_indicators = []
        else:
            target_links = NationalTargetFrameworkTargetLink.objects.filter(
                national_target__in=selected_targets,
                is_active=True,
            ).select_related("framework_target", "framework_target__framework", "framework_target__goal")
            target_links = filter_target_framework_links_for_user(target_links, strict_user)
            target_links = [
                link
                for link in target_links
                if not requires_consent(link.framework_target)
                or link.framework_target.uuid in framework_target_consent
            ]
            framework_target_ids = {link.framework_target_id for link in target_links}
            framework_indicators_qs = FrameworkIndicator.objects.filter(
                framework_target_id__in=framework_target_ids,
                status=LifecycleStatus.PUBLISHED,
            ).select_related("framework", "framework_target", "framework_target__goal")
            if framework_code:
                framework_indicators_qs = framework_indicators_qs.filter(
                    framework__code=framework_code
                )
            if indicator_level:
                framework_indicators_qs = framework_indicators_qs.filter(
                    indicator_type=indicator_level
                )
            framework_indicators_qs = filter_queryset_for_user(
                framework_indicators_qs,
                user,
            )
            framework_indicators = _apply_consent_filter(
                list(framework_indicators_qs),
                framework_indicator_consent,
            )
    else:
        framework_indicators_qs = FrameworkIndicator.objects.filter(
            status=LifecycleStatus.PUBLISHED,
        ).select_related("framework", "framework_target", "framework_target__goal")
        if framework_code:
            framework_indicators_qs = framework_indicators_qs.filter(framework__code=framework_code)
        if indicator_level:
            framework_indicators_qs = framework_indicators_qs.filter(indicator_type=indicator_level)
        framework_indicators_qs = filter_queryset_for_user(
            framework_indicators_qs,
            user,
        )
        framework_indicators = _apply_consent_filter(
            list(framework_indicators_qs),
            framework_indicator_consent,
        )

    framework_indicators = sorted(
        framework_indicators,
        key=lambda item: (
            item.framework.code if item.framework_id else "",
            item.code or "",
            item.title or "",
            str(item.uuid),
        ),
    )

    if scope == "selected":
        indicators_qs = Indicator.objects.filter(id__in=[obj.id for obj in selected_indicators])
    else:
        indicators_qs = Indicator.objects.filter(status=LifecycleStatus.PUBLISHED).select_related(
            "national_target", "organisation", "created_by"
        )
    indicators_qs = filter_queryset_for_user(
        indicators_qs,
        user,
        perm="nbms_app.view_indicator",
    )
    indicators = _apply_consent_filter(list(indicators_qs), indicator_consent)
    indicators = sort_model_items(indicators)

    indicator_ids = [indicator.id for indicator in indicators]
    framework_indicator_ids = [indicator.id for indicator in framework_indicators]

    indicator_links = IndicatorFrameworkIndicatorLink.objects.filter(
        indicator_id__in=indicator_ids,
        framework_indicator_id__in=framework_indicator_ids,
        is_active=True,
    ).select_related(
        "indicator",
        "framework_indicator",
        "framework_indicator__framework",
        "framework_indicator__framework_target",
        "framework_indicator__framework_target__goal",
    )
    indicator_links = filter_indicator_framework_links_for_user(indicator_links, strict_user)
    if framework_code:
        indicator_links = indicator_links.filter(framework_indicator__framework__code=framework_code)
    if indicator_level:
        indicator_links = indicator_links.filter(framework_indicator__indicator_type=indicator_level)
    indicator_links = [
        link
        for link in indicator_links
        if not requires_consent(link.framework_indicator)
        or link.framework_indicator.uuid in framework_indicator_consent
    ]

    links_by_framework_indicator = defaultdict(list)
    for link in indicator_links:
        links_by_framework_indicator[link.framework_indicator_id].append(link)

    # Reportability sources
    series_qs = indicator_data_series_for_user(user, instance)
    if indicator_ids:
        series_qs = series_qs.filter(indicator_id__in=indicator_ids)
    series_consent = _consent_granted_uuids(instance, IndicatorDataSeries)
    series = _apply_consent_filter(list(series_qs), series_consent)
    series_indicator_ids = {item.indicator_id for item in series if item.indicator_id}

    releases_qs = DatasetRelease.objects.select_related("dataset")
    if instance and scope == "selected":
        releases_qs = approved_queryset(instance, DatasetRelease)
    releases_qs = filter_queryset_for_user(releases_qs, user)
    release_consent = _consent_granted_uuids(instance, DatasetRelease)
    releases = _apply_consent_filter(list(releases_qs), release_consent)
    release_ids = [release.id for release in releases]
    dataset_ids = {release.dataset_id for release in releases if release.dataset_id}

    indicator_ids_with_dataset_release = set()
    if dataset_ids:
        indicator_ids_with_dataset_release.update(
            IndicatorDatasetLink.objects.filter(
                indicator_id__in=indicator_ids,
                dataset_id__in=dataset_ids,
            ).values_list("indicator_id", flat=True)
        )
    if release_ids:
        indicator_ids_with_dataset_release.update(
            IndicatorDataPoint.objects.filter(
                series__indicator_id__in=indicator_ids,
                dataset_release_id__in=release_ids,
            ).values_list("series__indicator_id", flat=True)
        )

    indicator_reportability = {}
    indicator_reportability_sources = {}
    for indicator in indicators:
        sources = []
        if indicator.id in series_indicator_ids:
            sources.append("data_series")
        if indicator.id in indicator_ids_with_dataset_release:
            sources.append("dataset_release")
        capability = _reporting_capability_value(indicator)
        if capability in {"yes", "partial"}:
            sources.append("reporting_capability")
        indicator_reportability[indicator.id] = bool(sources)
        indicator_reportability_sources[indicator.id] = sources

    headline_items = []
    addressed_items = []
    not_addressed_items = []

    by_target_stats = {}
    for framework_indicator in framework_indicators:
        mapped_links = links_by_framework_indicator.get(framework_indicator.id, [])
        mapped_indicator_ids = {link.indicator_id for link in mapped_links}
        mapped_indicators = [indicator for indicator in indicators if indicator.id in mapped_indicator_ids]
        mapped_indicators = sort_model_items(mapped_indicators)

        addressed = bool(mapped_links)
        reportable_sources = set()
        reportable = False
        for indicator in mapped_indicators:
            if indicator_reportability.get(indicator.id):
                reportable = True
                reportable_sources.update(indicator_reportability_sources.get(indicator.id, []))

        mapped_indicator_dicts = []
        if include_details:
            mapped_indicator_dicts = [
                {"uuid": str(indicator.uuid), "code": indicator.code, "title": indicator.title}
                for indicator in mapped_indicators
            ]

        target = framework_indicator.framework_target
        target_code = target.code if target else ""
        target_title = target.title if target else ""
        goal = target.goal if target else None
        goal_code = goal.code if goal else ""

        item = {
            "framework_indicator_uuid": str(framework_indicator.uuid),
            "framework_indicator_code": framework_indicator.code,
            "framework_indicator_title": framework_indicator.title,
            "framework_target_code": target_code,
            "framework_target_title": target_title,
            "framework_goal_code": goal_code,
            "status": "addressed" if addressed else "not_addressed",
            "mapped_national_indicators": mapped_indicator_dicts,
            "reportable": reportable,
            "reportability_sources": sorted(reportable_sources),
        }
        headline_items.append(item)

        if addressed:
            addressed_items.append(item)
        else:
            not_addressed_items.append(item)

        target_key = (target.id if target else None)
        stats = by_target_stats.setdefault(
            target_key,
            {
                "framework_target_uuid": str(target.uuid) if target else None,
                "framework_target_code": target_code,
                "framework_target_title": target_title,
                "framework_goal_code": goal_code,
                "total": 0,
                "addressed": 0,
                "reportable": 0,
            },
        )
        stats["total"] += 1
        if addressed:
            stats["addressed"] += 1
        if reportable:
            stats["reportable"] += 1

    headline_items = sort_dicts(
        headline_items,
        "framework_indicator_code",
        "framework_indicator_title",
        "framework_indicator_uuid",
    )
    addressed_items = sort_dicts(
        addressed_items,
        "framework_indicator_code",
        "framework_indicator_title",
        "framework_indicator_uuid",
    )
    not_addressed_items = sort_dicts(
        not_addressed_items,
        "framework_indicator_code",
        "framework_indicator_title",
        "framework_indicator_uuid",
    )

    by_target = []
    for stats in by_target_stats.values():
        total = stats["total"]
        addressed = stats["addressed"]
        reportable = stats["reportable"]
        by_target.append(
            {
                "framework_target_uuid": stats["framework_target_uuid"],
                "framework_target_code": stats["framework_target_code"],
                "framework_target_title": stats["framework_target_title"],
                "framework_goal_code": stats["framework_goal_code"],
                "total": total,
                "addressed": addressed,
                "not_addressed": total - addressed,
                "addressed_pct": _percent(addressed, total),
                "reportable": reportable,
                "not_reportable": total - reportable,
                "reportable_pct": _percent(reportable, total),
            }
        )
    by_target = sort_dicts(by_target, "framework_target_code", "framework_target_title", "framework_target_uuid")

    total = len(framework_indicators)
    addressed_count = len(addressed_items)
    reportable_count = sum(1 for item in headline_items if item["reportable"])

    if scope == "selected":
        if selection_source == "progress":
            selection_note = "Selected scope derived from Section III/IV progress entries."
        elif selection_source == "approvals":
            selection_note = "Selected scope derived from instance export approvals."
        else:
            selection_note = "No Section III/IV progress or export approvals; selected totals are 0."
    else:
        selection_note = None

    notes = [
        "Metrics reflect your access permissions (ABAC/consent).",
        "Items you cannot access are excluded from totals.",
        "Reportability proxy uses visible data series, visible dataset releases, or indicator reporting_capability.",
    ]
    if selection_note:
        notes.append(selection_note)

    output = {
        "framework_code": framework_code,
        "indicator_level": indicator_level,
        "scope": scope,
        "instance_uuid": str(instance.uuid) if instance else None,
        "generated_at": timezone.now().astimezone(dt_timezone.utc).isoformat(),
        "definitions": {
            "coverage_only": "Headline framework indicator has at least one mapped national indicator.",
            "coverage_reportability": (
                "Headline framework indicator has a mapped national indicator and evidence of reportability "
                "(data series, dataset release, or reporting_capability)."
            ),
            "denominator": "Distinct headline framework indicators visible to the user within scope.",
        },
        "notes": notes,
        "summary": {
            "coverage_only": {
                "total_headline_indicators": total,
                "addressed_count": addressed_count,
                "not_addressed_count": total - addressed_count,
                "addressed_pct": _percent(addressed_count, total),
            },
            "coverage_reportability": {
                "total_headline_indicators": total,
                "reportable_count": reportable_count,
                "not_reportable_count": total - reportable_count,
                "reportable_pct": _percent(reportable_count, total),
            },
        },
        "by_target": by_target,
        "headline_indicators": headline_items,
        "lists": {
            "addressed": addressed_items,
            "not_addressed": not_addressed_items,
        },
    }

    if include_charts_data:
        output["charts"] = {
            "addressed_vs_not": {
                "addressed": addressed_count,
                "not_addressed": total - addressed_count,
            },
            "by_target": [
                {
                    "framework_target_code": item["framework_target_code"],
                    "addressed_pct": item["addressed_pct"],
                    "reportable_pct": item["reportable_pct"],
                }
                for item in by_target
            ],
        }

    return output
