import secrets

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET
from prometheus_client import CONTENT_TYPE_LATEST

from nbms_app.services.authorization import is_system_admin
from nbms_app.services.metrics import render_prometheus, update_db_pool_metrics


def _token_allowed(request):
    token = settings.METRICS_TOKEN
    if not token:
        return False
    header = request.META.get("HTTP_AUTHORIZATION", "")
    header_token = ""
    if header.startswith("Bearer "):
        header_token = header.split("Bearer ", 1)[1].strip()
    if header_token and secrets.compare_digest(header_token, token):
        return True
    if getattr(settings, "METRICS_ALLOW_QUERY_TOKEN", False):
        query_token = (request.GET.get("token") or "").strip()
        if query_token and secrets.compare_digest(query_token, token):
            return True
    return False


@require_GET
def metrics(request):
    update_db_pool_metrics()
    if request.user.is_authenticated and is_system_admin(request.user):
        return HttpResponse(render_prometheus(), content_type=CONTENT_TYPE_LATEST)
    if _token_allowed(request):
        return HttpResponse(render_prometheus(), content_type=CONTENT_TYPE_LATEST)
    return HttpResponseForbidden("Forbidden")
