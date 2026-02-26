import logging
import time

logger = logging.getLogger("nbms.request")


def _user_id_from_request(request):
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return None
    return getattr(user, "id", None)


class RequestLoggingMiddleware:
    """Emit one structured access log event per request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = None
        try:
            response = self.get_response(request)
            return response
        except Exception:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "request.failed",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status_code": 500,
                    "latency_ms": latency_ms,
                    "user_id": _user_id_from_request(request),
                },
            )
            raise
        finally:
            if response is not None:
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                logger.info(
                    "request.completed",
                    extra={
                        "method": request.method,
                        "path": request.path,
                        "status_code": response.status_code,
                        "latency_ms": latency_ms,
                        "user_id": _user_id_from_request(request),
                    },
                )
