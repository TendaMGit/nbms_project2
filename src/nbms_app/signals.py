from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from nbms_app.models import Indicator, NationalTarget
from nbms_app.services.authorization import ROLE_DATA_STEWARD, ROLE_SECRETARIAT


def _assign_perms_to_groups(obj, perm_base):
    groups = Group.objects.filter(name__in=[ROLE_SECRETARIAT, ROLE_DATA_STEWARD])
    for group in groups:
        assign_perm(f"view_{perm_base}", group, obj)
        assign_perm(f"change_{perm_base}", group, obj)


def _assign_perms_to_creator(obj, perm_base):
    if getattr(obj, "created_by", None):
        assign_perm(f"view_{perm_base}", obj.created_by, obj)
        assign_perm(f"change_{perm_base}", obj.created_by, obj)


@receiver(post_save, sender=NationalTarget)
def grant_nationaltarget_perms(sender, instance, created, **kwargs):
    if not created:
        return
    _assign_perms_to_creator(instance, "nationaltarget")
    _assign_perms_to_groups(instance, "nationaltarget")


@receiver(post_save, sender=Indicator)
def grant_indicator_perms(sender, instance, created, **kwargs):
    if not created:
        return
    _assign_perms_to_creator(instance, "indicator")
    _assign_perms_to_groups(instance, "indicator")
