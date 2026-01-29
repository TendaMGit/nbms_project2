from django.apps import apps
from django.db.models.signals import post_delete, post_save

from nbms_app.models import AuditEvent
from nbms_app.services.audit import audit_is_suppressed, record_event
from nbms_app.services.request_context import get_current_request


def _should_audit_model(model):
    return model._meta.app_label == "nbms_app" and model is not AuditEvent


def _base_metadata(instance):
    metadata = {}
    for field in ("status", "sensitivity", "access_level", "is_active"):
        if hasattr(instance, field):
            metadata[field] = getattr(instance, field)
    return metadata


def _resolve_actor(instance, request):
    if request and getattr(request, "user", None) and request.user.is_authenticated:
        return request.user
    return getattr(instance, "created_by", None)


def _audit_save(sender, instance, created, **kwargs):
    if audit_is_suppressed():
        return
    request = get_current_request()
    actor = _resolve_actor(instance, request)
    action = f"{'create' if created else 'update'}_{sender.__name__.lower()}"
    record_event(actor, action, obj=instance, metadata=_base_metadata(instance), request=request)


def _audit_delete(sender, instance, **kwargs):
    if audit_is_suppressed():
        return
    request = get_current_request()
    actor = _resolve_actor(instance, request)
    action = f"delete_{sender.__name__.lower()}"
    record_event(actor, action, obj=instance, metadata=_base_metadata(instance), request=request)


def _register_model_signals(model):
    post_save.connect(
        _audit_save,
        sender=model,
        dispatch_uid=f"audit_post_save_{model.__name__}",
        weak=False,
    )
    post_delete.connect(
        _audit_delete,
        sender=model,
        dispatch_uid=f"audit_post_delete_{model.__name__}",
        weak=False,
    )


for _model in apps.get_models():
    if _should_audit_model(_model):
        _register_model_signals(_model)
