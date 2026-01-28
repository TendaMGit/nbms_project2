from nbms_app.models import (
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    IndicatorFrameworkIndicatorLink,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
)
from nbms_app.services.authorization import filter_queryset_for_user


def filter_target_framework_links_for_user(queryset, user):
    target_ids = filter_queryset_for_user(NationalTarget.objects.all(), user).values_list("id", flat=True)
    framework_target_ids = filter_queryset_for_user(FrameworkTarget.objects.all(), user).values_list("id", flat=True)
    return queryset.filter(
        national_target_id__in=target_ids,
        framework_target_id__in=framework_target_ids,
        is_active=True,
    )


def filter_indicator_framework_links_for_user(queryset, user):
    indicator_ids = filter_queryset_for_user(Indicator.objects.all(), user).values_list("id", flat=True)
    framework_indicator_ids = filter_queryset_for_user(
        FrameworkIndicator.objects.all(), user
    ).values_list("id", flat=True)
    return queryset.filter(
        indicator_id__in=indicator_ids,
        framework_indicator_id__in=framework_indicator_ids,
        is_active=True,
    )


def target_framework_links_for_user(user):
    return filter_target_framework_links_for_user(
        NationalTargetFrameworkTargetLink.objects.select_related("national_target", "framework_target"),
        user,
    )


def indicator_framework_links_for_user(user):
    return filter_indicator_framework_links_for_user(
        IndicatorFrameworkIndicatorLink.objects.select_related("indicator", "framework_indicator"),
        user,
    )
