from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET

from nbms_app.services.metrics import render_prometheus


def _token_allowed(request):
    token = settings.METRICS_TOKEN
    if not token:
        return False
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if header.startswith("Bearer ") and header.split("Bearer ", 1)[1] == token:
        return True
    if request.GET.get("token") == token:
        return True
    return False


@require_GET
def metrics(request):
    if request.user.is_authenticated and request.user.is_staff:
        return HttpResponse(render_prometheus(), content_type="text/plain")
    if _token_allowed(request):
        return HttpResponse(render_prometheus(), content_type="text/plain")
    return HttpResponseForbidden("Forbidden")
