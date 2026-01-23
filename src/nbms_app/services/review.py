import json

from django.db.models import Q

from nbms_app.models import (
    Dataset,
    DatasetRelease,
    Evidence,
    Indicator,
    IndicatorFrameworkIndicatorLink,
    NationalTargetFrameworkTargetLink,
    SectionIIINationalTargetProgress,
    SectionIVFrameworkTargetProgress,
)
from nbms_app.services.alignment import (
    filter_indicator_framework_links_for_user,
    filter_target_framework_links_for_user,
)
from nbms_app.services.authorization import filter_queryset_for_user
from nbms_app.services.consent import consent_is_granted, requires_consent
from nbms_app.services.indicator_data import (
    binary_indicator_responses_for_user,
    indicator_data_points_for_user,
    indicator_data_series_for_user,
)
from nbms_app.services.instance_approvals import approved_queryset
from nbms_app.services.readiness import compute_reporting_readiness, get_instance_readiness
from nbms_app.services.section_progress import scoped_framework_targets, scoped_national_targets


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
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return _StrictUserProxy(user)
    return user


def _abac_queryset(queryset, user):
    return filter_queryset_for_user(queryset, _strict_user(user))


def _allowed_series_queryset(instance, user):
    approved_indicator_ids = approved_queryset(instance, Indicator).values_list("id", flat=True)
    series_qs = indicator_data_series_for_user(_strict_user(user), instance).select_related(
        "framework_indicator",
        "indicator",
    )
    return series_qs.filter(Q(indicator_id__in=approved_indicator_ids) | Q(indicator__isnull=True))


def _allowed_binary_queryset(instance, user):
    return binary_indicator_responses_for_user(_strict_user(user), instance).select_related(
        "question",
        "question__framework_indicator",
    )


def _allowed_evidence(instance, user):
    evidence_qs = _abac_queryset(approved_queryset(instance, Evidence), user)
    allowed = []
    for item in evidence_qs:
        if not requires_consent(item) or consent_is_granted(instance, item):
            allowed.append(item)
    return allowed


def _allowed_dataset_releases(instance, user):
    dataset_qs = _abac_queryset(approved_queryset(instance, Dataset), user)
    releases = DatasetRelease.objects.filter(dataset__in=dataset_qs).select_related("dataset")
    allowed = []
    for release in releases:
        if not requires_consent(release) or consent_is_granted(instance, release):
            allowed.append(release)
    return allowed


def build_instance_review_summary(instance, user):
    strict_user = _strict_user(user)
    readiness = get_instance_readiness(instance, strict_user)
    catalog_readiness = compute_reporting_readiness(instance.uuid, scope="selected", user=strict_user)

    scoped_targets = scoped_national_targets(instance, strict_user)
    section_iii_entries = SectionIIINationalTargetProgress.objects.filter(
        reporting_instance=instance,
        national_target__in=scoped_targets,
    )
    section_iii_target_ids = set(section_iii_entries.values_list("national_target_id", flat=True))
    missing_targets = list(
        scoped_targets.exclude(id__in=section_iii_target_ids).order_by("code")
    )

    scoped_framework = scoped_framework_targets(instance, strict_user)
    section_iv_entries = SectionIVFrameworkTargetProgress.objects.filter(
        reporting_instance=instance,
        framework_target__in=scoped_framework,
    )
    section_iv_target_ids = set(section_iv_entries.values_list("framework_target_id", flat=True))
    missing_framework_targets = list(
        scoped_framework.exclude(id__in=section_iv_target_ids).order_by("code")
    )

    referenced_series = _allowed_series_queryset(instance, strict_user).filter(
        Q(section_iii_progress_entries__in=section_iii_entries)
        | Q(section_iv_progress_entries__in=section_iv_entries)
    ).distinct()
    referenced_series_ids = set(referenced_series.values_list("id", flat=True))

    referenced_binary = _allowed_binary_queryset(instance, strict_user).filter(
        Q(section_iii_progress_entries__in=section_iii_entries)
        | Q(section_iv_progress_entries__in=section_iv_entries)
    ).distinct()

    series_with_points = indicator_data_points_for_user(strict_user, instance).filter(
        series_id__in=referenced_series_ids
    )
    series_with_points_count = (
        series_with_points.values_list("series_id", flat=True).distinct().count()
    )

    target_links = filter_target_framework_links_for_user(
        NationalTargetFrameworkTargetLink.objects.filter(national_target__in=scoped_targets),
        strict_user,
    )
    mapped_target_ids = set(target_links.values_list("national_target_id", flat=True))
    mapped_targets_count = scoped_targets.filter(id__in=mapped_target_ids).count()

    indicator_ids = referenced_series.exclude(indicator_id__isnull=True).values_list(
        "indicator_id",
        flat=True,
    ).distinct()
    indicator_links = filter_indicator_framework_links_for_user(
        IndicatorFrameworkIndicatorLink.objects.filter(indicator_id__in=indicator_ids),
        strict_user,
    )
    mapped_indicator_ids = set(indicator_links.values_list("indicator_id", flat=True))
    mapped_indicators_count = len(mapped_indicator_ids)

    readiness_summary = {
        "score": readiness.get("readiness_score", 0),
        "band": readiness.get("readiness_band", "red"),
        "blockers": readiness.get("blockers", []),
        "warnings": readiness.get("warnings", []),
        "catalog_readiness": {
            "overall_ready": catalog_readiness.get("summary", {}).get("overall_ready"),
            "blocking_gap_count": catalog_readiness.get("summary", {}).get("blocking_gap_count"),
            "top_blockers": catalog_readiness.get("diagnostics", {}).get("top_blockers", []),
        },
    }

    coverage = {
        "section_iii": {
            "total": scoped_targets.count(),
            "completed": len(section_iii_target_ids),
            "missing": max(0, scoped_targets.count() - len(section_iii_target_ids)),
        },
        "section_iv": {
            "total": scoped_framework.count(),
            "completed": len(section_iv_target_ids),
            "missing": max(0, scoped_framework.count() - len(section_iv_target_ids)),
        },
    }

    indicator_coverage = {
        "referenced_series": referenced_series.count(),
        "series_with_points": series_with_points_count,
        "referenced_binary_responses": referenced_binary.count(),
    }

    mapping_coverage = {
        "targets_mapped": mapped_targets_count,
        "targets_total": scoped_targets.count(),
        "indicators_mapped": mapped_indicators_count,
        "indicators_total": len(indicator_ids),
    }

    return {
        "readiness": readiness_summary,
        "coverage": coverage,
        "indicator_coverage": indicator_coverage,
        "mapping_coverage": mapping_coverage,
        "missing_targets": missing_targets,
        "missing_framework_targets": missing_framework_targets,
    }


def _stable_json(value):
    return json.dumps(value or {}, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _sort_series_key(series):
    framework_code = series.framework_indicator.code if series.framework_indicator_id else ""
    indicator_code = series.indicator.code if series.indicator_id else str(series.uuid)
    return (framework_code, indicator_code)


def build_review_pack_context(instance, user):
    strict_user = _strict_user(user)
    scoped_targets = scoped_national_targets(instance, strict_user)
    scoped_framework = scoped_framework_targets(instance, strict_user)

    section_iii_entries = (
        SectionIIINationalTargetProgress.objects.filter(
            reporting_instance=instance,
            national_target__in=scoped_targets,
        )
        .select_related("national_target")
        .prefetch_related(
            "indicator_data_series",
            "binary_indicator_responses__question__framework_indicator",
            "evidence_items",
            "dataset_releases",
        )
        .order_by("national_target__code")
    )

    section_iv_entries = (
        SectionIVFrameworkTargetProgress.objects.filter(
            reporting_instance=instance,
            framework_target__in=scoped_framework,
        )
        .select_related("framework_target", "framework_target__framework")
        .prefetch_related(
            "indicator_data_series",
            "binary_indicator_responses__question__framework_indicator",
            "evidence_items",
            "dataset_releases",
        )
        .order_by("framework_target__code")
    )

    allowed_series = _allowed_series_queryset(instance, strict_user)
    allowed_series_ids = set(allowed_series.values_list("id", flat=True))

    allowed_binary = _allowed_binary_queryset(instance, strict_user)
    allowed_binary_ids = set(allowed_binary.values_list("id", flat=True))

    allowed_evidence = _allowed_evidence(instance, strict_user)
    allowed_evidence_ids = {item.id for item in allowed_evidence}

    allowed_releases = _allowed_dataset_releases(instance, strict_user)
    allowed_release_ids = {item.id for item in allowed_releases}

    points_qs = indicator_data_points_for_user(strict_user, instance).filter(series__in=allowed_series)
    points_qs = points_qs.filter(
        Q(dataset_release__isnull=True) | Q(dataset_release_id__in=allowed_release_ids)
    )
    points_by_series = {}
    for point in points_qs.order_by("year", "id"):
        points_by_series.setdefault(point.series_id, []).append(point)

    def build_entry_payload(entry):
        series = [item for item in entry.indicator_data_series.all() if item.id in allowed_series_ids]
        series = sorted(series, key=_sort_series_key)
        series_items = []
        for item in series:
            points = sorted(
                points_by_series.get(item.id, []),
                key=lambda point: (point.year, _stable_json(point.disaggregation)),
            )
            series_items.append({"series": item, "points": points})

        binary_responses = [
            item for item in entry.binary_indicator_responses.all() if item.id in allowed_binary_ids
        ]
        binary_responses = sorted(
            binary_responses,
            key=lambda item: (
                item.question.framework_indicator.code,
                item.question.group_key,
                item.question.question_key,
            ),
        )

        evidence_items = [
            item for item in entry.evidence_items.all() if item.id in allowed_evidence_ids
        ]
        evidence_items = sorted(evidence_items, key=lambda item: item.title)

        dataset_releases = [
            item for item in entry.dataset_releases.all() if item.id in allowed_release_ids
        ]
        dataset_releases = sorted(
            dataset_releases,
            key=lambda item: (item.dataset.title if item.dataset_id else "", item.version),
        )

        return {
            "entry": entry,
            "series_items": series_items,
            "binary_items": binary_responses,
            "evidence_items": evidence_items,
            "dataset_releases": dataset_releases,
        }

    section_iii_items = [build_entry_payload(entry) for entry in section_iii_entries]
    section_iv_items = [build_entry_payload(entry) for entry in section_iv_entries]

    return {
        "section_iii_items": section_iii_items,
        "section_iv_items": section_iv_items,
    }
