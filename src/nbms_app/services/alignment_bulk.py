from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q

from nbms_app.models import (
    ConsentRecord,
    ConsentStatus,
    Framework,
    FrameworkIndicator,
    FrameworkTarget,
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
from nbms_app.services.alignment_coverage import compute_alignment_coverage, get_selected_targets_and_indicators
from nbms_app.services.alignment_ordering import (
    order_indicator_links_queryset,
    order_queryset_by_code_title_uuid,
    order_queryset_by_framework_code_title_uuid,
    order_target_links_queryset,
)
from nbms_app.services.authorization import filter_queryset_for_user
from nbms_app.services.consent import requires_consent


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


def _apply_consent_queryset(instance, queryset, model):
    if not instance:
        return queryset.none()
    consent_granted = _consent_granted_uuids(instance, model)
    ids = []
    for obj in queryset:
        if not requires_consent(obj) or obj.uuid in consent_granted:
            ids.append(obj.id)
    return queryset.filter(id__in=ids)


def visible_frameworks_for_user(user):
    frameworks = filter_queryset_for_user(
        Framework.objects.filter(status=LifecycleStatus.PUBLISHED),
        user,
        perm="nbms_app.view_framework",
    )
    return order_queryset_by_code_title_uuid(frameworks)


def visible_framework_targets_for_user(*, instance, user, framework_code=None, query=None):
    queryset = filter_queryset_for_user(
        FrameworkTarget.objects.filter(status=LifecycleStatus.PUBLISHED).select_related("framework"),
        user,
        perm="nbms_app.view_frameworktarget",
    )
    if framework_code:
        queryset = queryset.filter(framework__code=framework_code)
    if query:
        queryset = queryset.filter(Q(code__icontains=query) | Q(title__icontains=query))
    queryset = order_queryset_by_framework_code_title_uuid(queryset)
    queryset = _apply_consent_queryset(instance, queryset, FrameworkTarget)
    return order_queryset_by_framework_code_title_uuid(queryset)


def visible_framework_indicators_for_user(*, instance, user, framework_code=None, query=None):
    queryset = filter_queryset_for_user(
        FrameworkIndicator.objects.filter(status=LifecycleStatus.PUBLISHED).select_related("framework"),
        user,
        perm="nbms_app.view_frameworkindicator",
    )
    if framework_code:
        queryset = queryset.filter(framework__code=framework_code)
    if query:
        queryset = queryset.filter(Q(code__icontains=query) | Q(title__icontains=query))
    queryset = order_queryset_by_framework_code_title_uuid(queryset)
    queryset = _apply_consent_queryset(instance, queryset, FrameworkIndicator)
    return order_queryset_by_framework_code_title_uuid(queryset)


def selected_targets_and_indicators(instance, user):
    targets_qs, indicators_qs, _source = get_selected_targets_and_indicators(instance=instance, user=user)
    return targets_qs, indicators_qs


def orphan_targets_for_instance(instance, user, query=None):
    coverage = compute_alignment_coverage(user=user, instance=instance, scope="selected", include_details=False)
    orphans = coverage["orphans"]["national_targets_unmapped"]
    if not query:
        return orphans
    query = query.strip().lower()
    return [
        item
        for item in orphans
        if query in (item.get("code") or "").lower() or query in (item.get("title") or "").lower()
    ]


def orphan_indicators_for_instance(instance, user, query=None):
    coverage = compute_alignment_coverage(user=user, instance=instance, scope="selected", include_details=False)
    orphans = coverage["orphans"]["indicators_unmapped"]
    if not query:
        return orphans
    query = query.strip().lower()
    return [
        item
        for item in orphans
        if query in (item.get("code") or "").lower() or query in (item.get("title") or "").lower()
    ]


def visible_orphan_targets_queryset(instance, user, orphan_items):
    uuids = [item["uuid"] for item in orphan_items]
    queryset = filter_queryset_for_user(
        NationalTarget.objects.filter(uuid__in=uuids, status=LifecycleStatus.PUBLISHED).select_related(
            "organisation",
            "created_by",
        ),
        user,
        perm="nbms_app.view_nationaltarget",
    )
    queryset = order_queryset_by_code_title_uuid(queryset)
    return _apply_consent_queryset(instance, queryset, NationalTarget)


def visible_orphan_indicators_queryset(instance, user, orphan_items):
    uuids = [item["uuid"] for item in orphan_items]
    queryset = filter_queryset_for_user(
        Indicator.objects.filter(uuid__in=uuids, status=LifecycleStatus.PUBLISHED).select_related(
            "national_target",
            "organisation",
            "created_by",
        ),
        user,
        perm="nbms_app.view_indicator",
    )
    queryset = order_queryset_by_code_title_uuid(queryset)
    return _apply_consent_queryset(instance, queryset, Indicator)


def visible_selected_targets_queryset(instance, user):
    targets_qs, _indicators_qs, _source = get_selected_targets_and_indicators(instance=instance, user=user)
    targets_qs = order_queryset_by_code_title_uuid(targets_qs)
    return _apply_consent_queryset(instance, targets_qs, NationalTarget)


def visible_selected_indicators_queryset(instance, user):
    _targets_qs, indicators_qs, _source = get_selected_targets_and_indicators(instance=instance, user=user)
    indicators_qs = order_queryset_by_code_title_uuid(indicators_qs)
    return _apply_consent_queryset(instance, indicators_qs, Indicator)


def visible_target_links_for_instance(instance, user):
    targets_qs, _indicators_qs, _source = get_selected_targets_and_indicators(instance=instance, user=user)
    links = NationalTargetFrameworkTargetLink.objects.filter(
        national_target__in=targets_qs,
        is_active=True,
    ).select_related("framework_target", "framework_target__framework", "national_target")
    links = filter_target_framework_links_for_user(links, user)
    target_consent = _consent_granted_uuids(instance, NationalTarget)
    framework_consent = _consent_granted_uuids(instance, FrameworkTarget)
    allowed_ids = [
        link.id
        for link in links
        if (not requires_consent(link.national_target) or link.national_target.uuid in target_consent)
        and (
            not requires_consent(link.framework_target)
            or link.framework_target.uuid in framework_consent
        )
    ]
    links = NationalTargetFrameworkTargetLink.objects.filter(id__in=allowed_ids).select_related(
        "framework_target",
        "framework_target__framework",
        "national_target",
    )
    return order_target_links_queryset(links)


def visible_indicator_links_for_instance(instance, user):
    _targets_qs, indicators_qs, _source = get_selected_targets_and_indicators(instance=instance, user=user)
    links = IndicatorFrameworkIndicatorLink.objects.filter(
        indicator__in=indicators_qs,
        is_active=True,
    ).select_related("framework_indicator", "framework_indicator__framework", "indicator")
    links = filter_indicator_framework_links_for_user(links, user)
    indicator_consent = _consent_granted_uuids(instance, Indicator)
    framework_consent = _consent_granted_uuids(instance, FrameworkIndicator)
    allowed_ids = [
        link.id
        for link in links
        if (not requires_consent(link.indicator) or link.indicator.uuid in indicator_consent)
        and (
            not requires_consent(link.framework_indicator)
            or link.framework_indicator.uuid in framework_consent
        )
    ]
    links = IndicatorFrameworkIndicatorLink.objects.filter(id__in=allowed_ids).select_related(
        "framework_indicator",
        "framework_indicator__framework",
        "indicator",
    )
    return order_indicator_links_queryset(links)


def bulk_link_targets(
    *,
    instance,
    user,
    targets,
    framework_targets,
    relation_type,
    confidence=None,
    notes="",
    source="",
):
    if not targets or not framework_targets:
        return {"created": 0, "skipped": 0, "failed": 0}

    allowed_target_ids = {item.id for item in targets}
    allowed_framework_ids = {item.id for item in framework_targets}

    existing_links = NationalTargetFrameworkTargetLink.objects.filter(
        national_target_id__in=allowed_target_ids,
        framework_target_id__in=allowed_framework_ids,
    ).select_related("national_target", "framework_target")
    existing_map = {(link.national_target_id, link.framework_target_id): link for link in existing_links}

    created = 0
    skipped = 0
    failed = 0
    with transaction.atomic():
        for target in targets:
            for framework_target in framework_targets:
                key = (target.id, framework_target.id)
                link = existing_map.get(key)
                if link:
                    if link.is_active:
                        skipped += 1
                        continue
                    link.is_active = True
                    link.relation_type = relation_type
                    link.confidence = confidence
                    link.notes = notes or ""
                    link.source = source or ""
                    link.save(update_fields=["is_active", "relation_type", "confidence", "notes", "source"])
                    created += 1
                    continue
                try:
                    NationalTargetFrameworkTargetLink.objects.create(
                        national_target=target,
                        framework_target=framework_target,
                        relation_type=relation_type,
                        confidence=confidence,
                        notes=notes or "",
                        source=source or "",
                        is_active=True,
                    )
                    created += 1
                except Exception:  # noqa: BLE001
                    failed += 1

    return {"created": created, "skipped": skipped, "failed": failed}


def bulk_link_indicators(
    *,
    instance,
    user,
    indicators,
    framework_indicators,
    relation_type,
    confidence=None,
    notes="",
    source="",
):
    if not indicators or not framework_indicators:
        return {"created": 0, "skipped": 0, "failed": 0}

    allowed_indicator_ids = {item.id for item in indicators}
    allowed_framework_ids = {item.id for item in framework_indicators}

    existing_links = IndicatorFrameworkIndicatorLink.objects.filter(
        indicator_id__in=allowed_indicator_ids,
        framework_indicator_id__in=allowed_framework_ids,
    ).select_related("indicator", "framework_indicator")
    existing_map = {(link.indicator_id, link.framework_indicator_id): link for link in existing_links}

    created = 0
    skipped = 0
    failed = 0
    with transaction.atomic():
        for indicator in indicators:
            for framework_indicator in framework_indicators:
                key = (indicator.id, framework_indicator.id)
                link = existing_map.get(key)
                if link:
                    if link.is_active:
                        skipped += 1
                        continue
                    link.is_active = True
                    link.relation_type = relation_type
                    link.confidence = confidence
                    link.notes = notes or ""
                    link.source = source or ""
                    link.save(update_fields=["is_active", "relation_type", "confidence", "notes", "source"])
                    created += 1
                    continue
                try:
                    IndicatorFrameworkIndicatorLink.objects.create(
                        indicator=indicator,
                        framework_indicator=framework_indicator,
                        relation_type=relation_type,
                        confidence=confidence,
                        notes=notes or "",
                        source=source or "",
                        is_active=True,
                    )
                    created += 1
                except Exception:  # noqa: BLE001
                    failed += 1

    return {"created": created, "skipped": skipped, "failed": failed}


def bulk_archive_target_links(*, user, links):
    if not links:
        return 0
    with transaction.atomic():
        updated = NationalTargetFrameworkTargetLink.objects.filter(id__in=[link.id for link in links]).update(
            is_active=False
        )
    return updated


def bulk_archive_indicator_links(*, user, links):
    if not links:
        return 0
    with transaction.atomic():
        updated = IndicatorFrameworkIndicatorLink.objects.filter(id__in=[link.id for link in links]).update(
            is_active=False
        )
    return updated
