from django.contrib.auth.models import AnonymousUser
from django.db.models import Q

from nbms_app.models import LifecycleStatus, SensitivityLevel

ROLE_ADMIN = "Admin"
ROLE_SECRETARIAT = "Secretariat"
ROLE_DATA_STEWARD = "Data Steward"
ROLE_INDICATOR_LEAD = "Indicator Lead"
ROLE_CONTRIBUTOR = "Contributor"
ROLE_VIEWER = "Viewer"
ROLE_SECURITY_OFFICER = "Security Officer"
ROLE_COMMUNITY_REPRESENTATIVE = "Community Representative"


def user_has_role(user, *roles):
    if not user or isinstance(user, AnonymousUser):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.groups.filter(name__in=roles).exists()


def can_view_object(user, obj):
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True

    if not user or isinstance(user, AnonymousUser):
        return obj.status == LifecycleStatus.PUBLISHED and obj.sensitivity == SensitivityLevel.PUBLIC

    if user_has_role(user, ROLE_SECURITY_OFFICER):
        return True

    if getattr(obj, "created_by_id", None) == user.id:
        return True

    if obj.status == LifecycleStatus.PUBLISHED:
        if obj.sensitivity == SensitivityLevel.PUBLIC:
            return True
        if obj.sensitivity in {SensitivityLevel.INTERNAL, SensitivityLevel.RESTRICTED}:
            return obj.organisation_id == getattr(user, "organisation_id", None)
        if obj.sensitivity == SensitivityLevel.IPLC_SENSITIVE:
            return obj.organisation_id == getattr(user, "organisation_id", None) and user_has_role(
                user, ROLE_COMMUNITY_REPRESENTATIVE
            )

    if user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD):
        return obj.organisation_id == getattr(user, "organisation_id", None)

    return False


def can_edit_object(user, obj):
    if not user or isinstance(user, AnonymousUser):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    if user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD):
        return obj.organisation_id == getattr(user, "organisation_id", None)
    return getattr(obj, "created_by_id", None) == user.id


def filter_queryset_for_user(queryset, user):
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
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

        if user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD):
            org_role_q = Q(organisation_id=org_id)

        if user_has_role(user, ROLE_COMMUNITY_REPRESENTATIVE):
            iplc_q = Q(
                organisation_id=org_id,
                status=LifecycleStatus.PUBLISHED,
                sensitivity=SensitivityLevel.IPLC_SENSITIVE,
            )

    return queryset.filter(public_q | creator_q | org_published_q | org_role_q | iplc_q)
