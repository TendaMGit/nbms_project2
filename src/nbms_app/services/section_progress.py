from django.contrib.auth.models import AnonymousUser
from django.db.models import Q

from nbms_app.models import (
    FrameworkTarget,
    Indicator,
    LifecycleStatus,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    SensitivityLevel,
)
from nbms_app.services.authorization import ROLE_SECURITY_OFFICER, user_has_role
from nbms_app.services.instance_approvals import approved_queryset


def _filter_queryset_for_user_strict(queryset, user):
    if getattr(user, "is_superuser", False):
        return queryset

    if not user or isinstance(user, AnonymousUser):
        return queryset.filter(status=LifecycleStatus.PUBLISHED, sensitivity=SensitivityLevel.PUBLIC)

    if user_has_role(user, ROLE_SECURITY_OFFICER):
        return queryset

    public_q = Q(status=LifecycleStatus.PUBLISHED, sensitivity=SensitivityLevel.PUBLIC)
    creator_q = Q(created_by_id=user.id)
    org_id = getattr(user, "organisation_id", None)

    org_published_q = Q()
    org_role_q = Q()
    iplc_q = Q()

    if org_id:
        org_published_q = Q(
            organisation_id=org_id,
            status=LifecycleStatus.PUBLISHED,
            sensitivity__in=[SensitivityLevel.INTERNAL, SensitivityLevel.RESTRICTED],
        )
        if user_has_role(user, "Secretariat", "Data Steward"):
            org_role_q = Q(organisation_id=org_id)
        if user_has_role(user, "Community Representative"):
            iplc_q = Q(
                organisation_id=org_id,
                status=LifecycleStatus.PUBLISHED,
                sensitivity=SensitivityLevel.IPLC_SENSITIVE,
            )

    return queryset.filter(public_q | creator_q | org_published_q | org_role_q | iplc_q)


def scoped_national_targets(instance, user):
    if not instance:
        return NationalTarget.objects.none()

    visible = _filter_queryset_for_user_strict(
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

    visible = _filter_queryset_for_user_strict(
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
