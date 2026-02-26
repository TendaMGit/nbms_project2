import time

from nbms_app.services.metrics import observe_http_request, update_db_pool_metrics


class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            route = "unresolved"
            resolver_match = getattr(request, "resolver_match", None)
            if resolver_match is not None and getattr(resolver_match, "route", None):
                route = resolver_match.route
            elapsed = time.perf_counter() - started
            observe_http_request(
                method=request.method,
                route=route or request.path,
                status_code=500,
                duration_seconds=elapsed,
            )
            raise
        route = "unresolved"
        resolver_match = getattr(request, "resolver_match", None)
        if resolver_match is not None and getattr(resolver_match, "route", None):
            route = resolver_match.route
        elapsed = time.perf_counter() - started
        observe_http_request(
            method=request.method,
            route=(route or request.path),
            status_code=response.status_code,
            duration_seconds=elapsed,
        )
        update_db_pool_metrics()
        return response
