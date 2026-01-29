import re

from django.apps import apps

from nbms_app.services.audit import audit_sensitive_access
from nbms_app.services.request_context import reset_current_request, set_current_request

_ADMIN_CHANGE_RE = re.compile(r"^/admin/(?P<app>[^/]+)/(?P<model>[^/]+)/(?P<pk>[^/]+)/change/?")


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_current_request(request)
        try:
            response = self.get_response(request)
            if request.method in {"GET", "HEAD"}:
                match = _ADMIN_CHANGE_RE.match(request.path or "")
                if match:
                    app_label = match.group("app")
                    model_name = match.group("model")
                    pk = match.group("pk")
                    try:
                        model = apps.get_model(app_label, model_name)
                    except LookupError:
                        model = None
                    if model:
                        obj = model.objects.filter(pk=pk).first()
                        if obj:
                            audit_sensitive_access(request, obj, action="admin_view")
            return response
        finally:
            reset_current_request(token)
