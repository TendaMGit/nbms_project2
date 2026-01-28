from django.contrib.auth.models import AnonymousUser
from django.db.models import Q

from nbms_app.models import AccessLevel
from nbms_app.services.authorization import is_system_admin


def _is_privileged(user):
    if not user or isinstance(user, AnonymousUser):
        return False
    if is_system_admin(user):
        return True
    return False


def filter_organisations_for_user(queryset, user):
    if _is_privileged(user):
        return queryset
    if not user or isinstance(user, AnonymousUser):
        return queryset.none()
    org_id = getattr(user, "organisation_id", None)
    if not org_id:
        return queryset.none()
    return queryset.filter(id=org_id)


def filter_data_agreements_for_user(queryset, user):
    if _is_privileged(user):
        return queryset
    if not user or isinstance(user, AnonymousUser):
        return queryset.none()
    org_id = getattr(user, "organisation_id", None)
    if not org_id:
        return queryset.none()
    return queryset.filter(parties__id=org_id, is_active=True).distinct()


def filter_sensitivity_classes_for_user(queryset, user):
    if _is_privileged(user):
        return queryset
    if not user or isinstance(user, AnonymousUser):
        return queryset.none()
    return queryset.filter(is_active=True)


def filter_dataset_catalog_for_user(queryset, user):
    if _is_privileged(user):
        return queryset
    if not user or isinstance(user, AnonymousUser):
        return queryset.filter(access_level=AccessLevel.PUBLIC, is_active=True)
    org_id = getattr(user, "organisation_id", None)
    if not org_id:
        return queryset.filter(access_level=AccessLevel.PUBLIC, is_active=True)
    public_q = Q(access_level=AccessLevel.PUBLIC)
    internal_q = Q(access_level=AccessLevel.INTERNAL, custodian_org_id=org_id) | Q(
        access_level=AccessLevel.INTERNAL, producer_org_id=org_id
    )
    restricted_q = Q(access_level=AccessLevel.RESTRICTED, custodian_org_id=org_id) | Q(
        access_level=AccessLevel.RESTRICTED, producer_org_id=org_id
    )
    return queryset.filter(is_active=True).filter(public_q | internal_q | restricted_q)


def filter_monitoring_programmes_for_user(queryset, user):
    if _is_privileged(user):
        return queryset
    if not user or isinstance(user, AnonymousUser):
        return queryset.filter(
            sensitivity_class__access_level_default=AccessLevel.PUBLIC,
            is_active=True,
        )
    org_id = getattr(user, "organisation_id", None)
    if not org_id:
        return queryset.filter(
            sensitivity_class__access_level_default=AccessLevel.PUBLIC,
            is_active=True,
        )
    public_q = Q(sensitivity_class__access_level_default=AccessLevel.PUBLIC)
    org_q = Q(lead_org_id=org_id) | Q(partners__id=org_id)
    return queryset.filter(is_active=True).filter(public_q | org_q).distinct()


def filter_methodologies_for_user(queryset, user):
    if _is_privileged(user):
        return queryset
    if not user or isinstance(user, AnonymousUser):
        return queryset.filter(owner_org__isnull=True, is_active=True)
    org_id = getattr(user, "organisation_id", None)
    if not org_id:
        return queryset.filter(owner_org__isnull=True, is_active=True)
    return queryset.filter(is_active=True).filter(Q(owner_org_id=org_id) | Q(owner_org__isnull=True))


def can_edit_dataset_catalog(user, dataset):
    if _is_privileged(user):
        return True
    if not user or isinstance(user, AnonymousUser):
        return False
    org_id = getattr(user, "organisation_id", None)
    return org_id and org_id in {dataset.custodian_org_id, dataset.producer_org_id}


def can_edit_monitoring_programme(user, programme):
    if _is_privileged(user):
        return True
    if not user or isinstance(user, AnonymousUser):
        return False
    org_id = getattr(user, "organisation_id", None)
    if not org_id:
        return False
    partner_ids = set(programme.partners.values_list("id", flat=True))
    return org_id == programme.lead_org_id or org_id in partner_ids


def can_edit_methodology(user, methodology):
    if _is_privileged(user):
        return True
    if not user or isinstance(user, AnonymousUser):
        return False
    org_id = getattr(user, "organisation_id", None)
    return bool(org_id and org_id == methodology.owner_org_id)


def can_edit_data_agreement(user, agreement):
    if _is_privileged(user):
        return True
    if not user or isinstance(user, AnonymousUser):
        return False
    org_id = getattr(user, "organisation_id", None)
    if not org_id:
        return False
    return agreement.parties.filter(id=org_id).exists()


def can_edit_sensitivity_class(user, sensitivity_class):
    return _is_privileged(user)
