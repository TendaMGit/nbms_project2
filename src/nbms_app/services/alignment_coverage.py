from collections import defaultdict
from datetime import timezone as dt_timezone

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone

from nbms_app.models import (
    ConsentRecord,
    ConsentStatus,
    Indicator,
    IndicatorFrameworkIndicatorLink,
    LifecycleStatus,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
)
from nbms_app.services.alignment import (
    filter_indicator_framework_links_for_user,
    filter_target_framework_links_for_user,
)
from nbms_app.services.authorization import filter_queryset_for_user, is_system_admin
from nbms_app.services.consent import requires_consent
from nbms_app.services.instance_approvals import approved_queryset
from nbms_app.services.section_progress import scoped_national_targets


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


def _sort_items(items):
    return sorted(items, key=lambda obj: (obj.code or "", obj.title or "", str(obj.uuid)))


def _consent_granted_uuids(instance, model):
    if not instance:
        return set()
    content_type = ContentType.objects.get_for_model(model)
    return set(
        ConsentRecord.objects.filter(
            content_type=content_type,
            status=ConsentStatus.GRANTED,
        )
        .filter(Q(reporting_instance=instance) | Q(reporting_instance__isnull=True))
        .values_list("object_uuid", flat=True)
    )


def _apply_consent_filter(instance, items, consent_granted):
    filtered = []
    for obj in items:
        if not requires_consent(obj) or obj.uuid in consent_granted:
            filtered.append(obj)
    return filtered


def _percent(part, total):
    if not total:
        return 0.0
    return round((part / total) * 100, 1)


def compute_alignment_coverage(
    *,
    user,
    instance,
    scope="selected",
    framework_codes=None,
    include_details=True,
):
    """
    Compute alignment coverage for a reporting instance.

    Scopes:
    - selected: items currently selected for the instance (approvals/section progress),
      aligned with export readiness expectations.
    - all: all visible registry items for the user (ABAC filtered).

    Notes:
    - Totals reflect ABAC + consent filters for the requesting user.
    - When framework_codes is provided, mapping status is evaluated against those frameworks only.
    """
    if not instance:
        raise ValueError("Instance is required.")
    if scope not in {"selected", "all"}:
        raise ValueError("Invalid scope.")

    strict_user = _strict_user(user)
    framework_codes = [code for code in (framework_codes or []) if code]
    framework_filter = set(framework_codes) if framework_codes else None

    if scope == "selected":
        targets_qs = scoped_national_targets(instance, strict_user)
        indicators_qs = approved_queryset(instance, Indicator).filter(status=LifecycleStatus.PUBLISHED)
        indicators_qs = filter_queryset_for_user(
            indicators_qs.select_related("national_target", "organisation", "created_by"),
            user,
            perm="nbms_app.view_indicator",
        )
    else:
        targets_qs = filter_queryset_for_user(
            NationalTarget.objects.select_related("organisation", "created_by")
            .filter(status=LifecycleStatus.PUBLISHED)
            .order_by("code"),
            user,
            perm="nbms_app.view_nationaltarget",
        )
        indicators_qs = filter_queryset_for_user(
            Indicator.objects.select_related("national_target", "organisation", "created_by")
            .filter(status=LifecycleStatus.PUBLISHED)
            .order_by("code"),
            user,
            perm="nbms_app.view_indicator",
        )

    targets = _sort_items(list(targets_qs))
    indicators = _sort_items(list(indicators_qs))

    target_consent = _consent_granted_uuids(instance, NationalTarget)
    indicator_consent = _consent_granted_uuids(instance, Indicator)

    targets = _apply_consent_filter(instance, targets, target_consent)
    indicators = _apply_consent_filter(instance, indicators, indicator_consent)

    target_links = NationalTargetFrameworkTargetLink.objects.filter(
        national_target__in=targets,
        is_active=True,
    ).select_related("framework_target", "framework_target__framework", "national_target")
    target_links = filter_target_framework_links_for_user(target_links, strict_user)
    if framework_filter:
        target_links = target_links.filter(framework_target__framework__code__in=framework_filter)
    target_links = target_links.order_by(
        "framework_target__framework__code",
        "framework_target__code",
        "framework_target__title",
        "framework_target__uuid",
    )

    indicator_links = IndicatorFrameworkIndicatorLink.objects.filter(
        indicator__in=indicators,
        is_active=True,
    ).select_related("framework_indicator", "framework_indicator__framework", "indicator")
    indicator_links = filter_indicator_framework_links_for_user(indicator_links, strict_user)
    if framework_filter:
        indicator_links = indicator_links.filter(framework_indicator__framework__code__in=framework_filter)
    indicator_links = indicator_links.order_by(
        "framework_indicator__framework__code",
        "framework_indicator__code",
        "framework_indicator__title",
        "framework_indicator__uuid",
    )

    target_links_map = defaultdict(list)
    for link in target_links:
        target_links_map[link.national_target_id].append(link)

    indicator_links_map = defaultdict(list)
    for link in indicator_links:
        indicator_links_map[link.indicator_id].append(link)

    mapped_target_ids = set(target_links_map.keys())
    mapped_indicator_ids = set(indicator_links_map.keys())

    orphans_targets = []
    orphans_indicators = []
    target_details = []
    indicator_details = []

    for target in targets:
        links = target_links_map.get(target.id, [])
        if not links:
            orphans_targets.append(
                {"uuid": str(target.uuid), "code": target.code, "title": target.title}
            )
        if include_details:
            linked_framework_targets = [
                {
                    "uuid": str(link.framework_target.uuid),
                    "code": link.framework_target.code,
                    "title": link.framework_target.title,
                    "framework_code": link.framework_target.framework.code,
                }
                for link in links
            ]
            target_details.append(
                {
                    "uuid": str(target.uuid),
                    "code": target.code,
                    "title": target.title,
                    "mapped": bool(links),
                    "linked_framework_targets": linked_framework_targets,
                }
            )

    for indicator in indicators:
        links = indicator_links_map.get(indicator.id, [])
        if not links:
            orphans_indicators.append(
                {"uuid": str(indicator.uuid), "code": indicator.code, "title": indicator.title}
            )
        if include_details:
            linked_framework_indicators = [
                {
                    "uuid": str(link.framework_indicator.uuid),
                    "code": link.framework_indicator.code,
                    "title": link.framework_indicator.title,
                    "framework_code": link.framework_indicator.framework.code,
                }
                for link in links
            ]
            indicator_details.append(
                {
                    "uuid": str(indicator.uuid),
                    "code": indicator.code,
                    "title": indicator.title,
                    "mapped": bool(links),
                    "linked_framework_indicators": linked_framework_indicators,
                }
            )

    framework_stats = {}
    for link in target_links:
        framework = link.framework_target.framework
        data = framework_stats.setdefault(
            framework.code,
            {
                "framework_code": framework.code,
                "framework_title": framework.title,
                "targets": {"mapped_links": 0, "distinct_framework_targets_used": set()},
                "indicators": {"mapped_links": 0, "distinct_framework_indicators_used": set()},
            },
        )
        data["targets"]["mapped_links"] += 1
        data["targets"]["distinct_framework_targets_used"].add(link.framework_target_id)

    for link in indicator_links:
        framework = link.framework_indicator.framework
        data = framework_stats.setdefault(
            framework.code,
            {
                "framework_code": framework.code,
                "framework_title": framework.title,
                "targets": {"mapped_links": 0, "distinct_framework_targets_used": set()},
                "indicators": {"mapped_links": 0, "distinct_framework_indicators_used": set()},
            },
        )
        data["indicators"]["mapped_links"] += 1
        data["indicators"]["distinct_framework_indicators_used"].add(link.framework_indicator_id)

    by_framework = []
    for data in framework_stats.values():
        by_framework.append(
            {
                "framework_code": data["framework_code"],
                "framework_title": data["framework_title"],
                "targets": {
                    "mapped_links": data["targets"]["mapped_links"],
                    "distinct_framework_targets_used": len(data["targets"]["distinct_framework_targets_used"]),
                },
                "indicators": {
                    "mapped_links": data["indicators"]["mapped_links"],
                    "distinct_framework_indicators_used": len(
                        data["indicators"]["distinct_framework_indicators_used"]
                    ),
                },
            }
        )
    by_framework = sorted(by_framework, key=lambda item: (item["framework_code"], item["framework_title"]))

    target_mapped = sum(1 for target in targets if target.id in mapped_target_ids)
    indicator_mapped = sum(1 for indicator in indicators if indicator.id in mapped_indicator_ids)

    generated_at = timezone.now().astimezone(dt_timezone.utc).isoformat()

    return {
        "instance_uuid": str(instance.uuid),
        "scope": scope,
        "generated_at": generated_at,
        "filters": {"framework_codes": sorted(framework_filter) if framework_filter else None},
        "notes": [
            "Metrics reflect your access permissions (ABAC/consent).",
            "Items you cannot access are excluded from totals.",
        ],
        "summary": {
            "national_targets": {
                "total": len(targets),
                "mapped": target_mapped,
                "unmapped": len(targets) - target_mapped,
                "pct_mapped": _percent(target_mapped, len(targets)),
            },
            "indicators": {
                "total": len(indicators),
                "mapped": indicator_mapped,
                "unmapped": len(indicators) - indicator_mapped,
                "pct_mapped": _percent(indicator_mapped, len(indicators)),
            },
        },
        "by_framework": by_framework,
        "orphans": {
            "national_targets_unmapped": orphans_targets,
            "indicators_unmapped": orphans_indicators,
        },
        "coverage_details": {
            "national_targets": target_details if include_details else [],
            "indicators": indicator_details if include_details else [],
        },
    }
