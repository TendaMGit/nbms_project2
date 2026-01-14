from django.http import HttpResponse

from nbms_app.services.metrics import inc_counter


class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except Exception:
            inc_counter("requests_total", labels={"status": "500"})
            raise
        inc_counter("requests_total", labels={"status": str(response.status_code)})
        return response
