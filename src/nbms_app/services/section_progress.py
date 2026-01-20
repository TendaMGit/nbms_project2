from django.db.models import Q

from nbms_app.models import FrameworkTarget, Indicator, LifecycleStatus, NationalTarget, NationalTargetFrameworkTargetLink
from nbms_app.services.authorization import filter_queryset_for_user
from nbms_app.services.instance_approvals import approved_queryset


def scoped_national_targets(instance, user):
    if not instance:
        return NationalTarget.objects.none()

    visible = filter_queryset_for_user(
        NationalTarget.objects.select_related("organisation", "created_by"),
        user,
    ).filter(status=LifecycleStatus.PUBLISHED)

    approved_targets = approved_queryset(instance, NationalTarget).values_list("uuid", flat=True)
    approved_indicator_targets = approved_queryset(instance, Indicator).values_list("national_target_id", flat=True)

    return (
        visible.filter(Q(uuid__in=approved_targets) | Q(id__in=approved_indicator_targets))
        .distinct()
        .order_by("code")
    )


def scoped_framework_targets(instance, user):
    if not instance:
        return FrameworkTarget.objects.none()

    visible = filter_queryset_for_user(
        FrameworkTarget.objects.select_related("framework", "organisation", "created_by"),
        user,
    ).filter(status=LifecycleStatus.PUBLISHED)

    national_targets = scoped_national_targets(instance, user)
    if not national_targets.exists():
        return visible.none()

    framework_target_ids = NationalTargetFrameworkTargetLink.objects.filter(
        national_target__in=national_targets
    ).values_list("framework_target_id", flat=True)

    return visible.filter(id__in=framework_target_ids).distinct().order_by("framework__code", "code")
