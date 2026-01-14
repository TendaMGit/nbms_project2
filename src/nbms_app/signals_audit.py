from django.db.models.signals import post_save
from django.dispatch import receiver

from nbms_app.models import Indicator, NationalTarget
from nbms_app.services.audit import record_audit_event


def _track_changes(sender, instance, created, **kwargs):
    if created:
        return
    if not instance.pk:
        return
    action = f"update_{sender.__name__.lower()}"
    metadata = {"status": instance.status, "sensitivity": instance.sensitivity}
    record_audit_event(getattr(instance, "created_by", None), action, instance, metadata=metadata)


@receiver(post_save, sender=NationalTarget)
def audit_nationaltarget_update(sender, instance, created, **kwargs):
    _track_changes(sender, instance, created, **kwargs)


@receiver(post_save, sender=Indicator)
def audit_indicator_update(sender, instance, created, **kwargs):
    _track_changes(sender, instance, created, **kwargs)
