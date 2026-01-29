from contextlib import contextmanager
from contextvars import ContextVar

from django.contrib.contenttypes.models import ContentType

from nbms_app.models import AccessLevel, AuditEvent, SensitivityLevel
from nbms_app.services.authorization import is_system_admin
from nbms_app.services.request_context import get_current_request


_audit_suppressed = ContextVar("audit_suppressed", default=False)
_sensitive_keys = {
    "geometry",
    "geom",
    "geojson",
    "wkt",
    "wkb",
    "coordinates",
    "latitude",
    "longitude",
    "lat",
    "lon",
    "location",
    "narrative",
    "note",
    "notes",
    "description",
    "summary",
    "text",
    "content",
    "comment",
    "comments",
    "response",
    "email",
    "phone",
    "address",
    "contact",
    "consent_document",
    "document",
    "file",
    "attachment",
    "payload",
}


@contextmanager
def suppress_audit_events():
    token = _audit_suppressed.set(True)
    try:
        yield
    finally:
        _audit_suppressed.reset(token)


def audit_is_suppressed():
    return bool(_audit_suppressed.get())


def _should_redact(key):
    if not key:
        return False
    key_lower = str(key).lower()
    return any(token in key_lower for token in _sensitive_keys)


def _sanitize_metadata(value):
    if value is None:
        return None
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if _should_redact(key):
                sanitized[key] = "[redacted]"
            else:
                sanitized[key] = _sanitize_metadata(item)
        return sanitized
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_metadata(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _request_metadata(request):
    if not request:
        return {}
    meta = request.META or {}
    forwarded = meta.get("HTTP_X_FORWARDED_FOR", "")
    ip_address = forwarded.split(",")[0].strip() if forwarded else meta.get("REMOTE_ADDR", "")
    session_key = ""
    try:
        session_key = request.session.session_key or ""
    except Exception:  # noqa: BLE001
        session_key = ""
    return {
        "request_path": request.path or "",
        "request_method": request.method or "",
        "ip_address": ip_address or "",
        "user_agent": meta.get("HTTP_USER_AGENT", "") or "",
        "session_key": session_key,
        "request_id": meta.get("HTTP_X_REQUEST_ID", "") or meta.get("HTTP_X_CORRELATION_ID", "") or "",
    }


def record_event(actor, event_type, obj=None, object_ref=None, metadata=None, request=None):
    request = request or get_current_request()
    if actor is None and request and getattr(request, "user", None) and request.user.is_authenticated:
        actor = request.user

    object_type = ""
    object_uuid = None
    object_id = ""
    content_type = None
    if obj is not None:
        object_type = obj.__class__.__name__
        object_uuid = getattr(obj, "uuid", None)
        object_id = str(getattr(obj, "pk", "")) if getattr(obj, "pk", None) is not None else ""
        content_type = ContentType.objects.get_for_model(obj.__class__)
    elif object_ref:
        object_type = object_ref.get("object_type", "")
        object_uuid = object_ref.get("object_uuid")
        object_id = str(object_ref.get("object_id", "") or "")
        content_type = object_ref.get("content_type")

    payload = dict(metadata or {})
    payload.setdefault("object_type", object_type)
    payload.setdefault("object_uuid", str(object_uuid) if object_uuid else "")
    payload = _sanitize_metadata(payload)

    request_meta = _request_metadata(request)
    AuditEvent.objects.create(
        actor=actor,
        action=event_type,
        event_type=event_type,
        content_type=content_type,
        object_type=object_type,
        object_id=object_id,
        object_uuid=object_uuid,
        metadata=payload,
        request_path=request_meta.get("request_path", ""),
        request_method=request_meta.get("request_method", ""),
        ip_address=request_meta.get("ip_address", ""),
        user_agent=request_meta.get("user_agent", ""),
        session_key=request_meta.get("session_key", ""),
        request_id=request_meta.get("request_id", ""),
    )


def record_audit_event(actor, action, obj, metadata=None, request=None):
    record_event(actor, action, obj=obj, metadata=metadata, request=request)


def _object_is_sensitive(obj):
    if obj is None:
        return False
    sensitivity = getattr(obj, "sensitivity", None)
    if sensitivity and sensitivity != SensitivityLevel.PUBLIC:
        return True
    access_level = getattr(obj, "access_level", None)
    if access_level and access_level != AccessLevel.PUBLIC:
        return True
    sensitivity_class = getattr(obj, "sensitivity_class", None)
    if sensitivity_class and getattr(sensitivity_class, "access_level_default", None) != AccessLevel.PUBLIC:
        return True
    return False


def audit_sensitive_access(request, obj, action="view"):
    if not request or not getattr(request, "user", None):
        return
    user = request.user
    if not getattr(user, "is_authenticated", False):
        return

    # avoid circular import at module load
    from nbms_app.services.consent import requires_consent  # noqa: WPS433

    is_sensitive = _object_is_sensitive(obj)
    consent_required = requires_consent(obj) if obj is not None else False
    if is_system_admin(user):
        event_type = "admin_view_sensitive" if (is_sensitive or consent_required) else "admin_view"
        record_event(
            user,
            event_type,
            obj=obj,
            metadata={
                "action": action,
                "sensitive": bool(is_sensitive),
                "consent_required": bool(consent_required),
            },
            request=request,
        )
        return

    if is_sensitive or consent_required:
        record_event(
            user,
            "view_sensitive",
            obj=obj,
            metadata={
                "action": action,
                "sensitive": bool(is_sensitive),
                "consent_required": bool(consent_required),
            },
            request=request,
        )


def audit_queryset_access(request, queryset, action="list"):
    if not request or not getattr(request, "user", None):
        return queryset
    if not getattr(request.user, "is_authenticated", False):
        return queryset
    items = list(queryset)
    for obj in items:
        audit_sensitive_access(request, obj, action=action)
    return items
