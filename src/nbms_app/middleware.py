from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


def _get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _parse_rate(rate):
    if not rate:
        return None
    parts = rate.split("/")
    if len(parts) != 2:
        return None
    try:
        count = int(parts[0])
    except (TypeError, ValueError):
        return None
    window = parts[1].strip().lower()
    if window.isdigit():
        return count, int(window)
    if window in {"s", "sec", "second"}:
        return count, 1
    if window in {"m", "min", "minute"}:
        return count, 60
    if window in {"h", "hr", "hour"}:
        return count, 3600
    return None


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = getattr(settings, "RATE_LIMITS", {})

    def __call__(self, request):
        response = self._check_limits(request)
        if response:
            return response
        return self.get_response(request)

    def _check_limits(self, request):
        for name, config in self.rate_limits.items():
            if not self._match_config(request, config):
                continue

            parsed = _parse_rate(config.get("rate"))
            if not parsed:
                continue

            max_requests, window = parsed
            key = f"rl:{name}:{_get_client_ip(request)}:{request.method}:{request.path}"
            allowed = self._allow_request(key, max_requests, window)
            if not allowed:
                response = HttpResponse("Too Many Requests", status=429)
                response["Retry-After"] = str(window)
                return response
        return None

    def _match_config(self, request, config):
        methods = config.get("methods", ["POST"])
        if request.method not in methods:
            return False
        paths = config.get("paths", [])
        if not any(request.path.startswith(path) for path in paths):
            return False
        actions = config.get("actions")
        if actions and not any(f"/{action}/" in request.path for action in actions):
            return False
        return True

    def _allow_request(self, key, max_requests, window):
        added = cache.add(key, 1, timeout=window)
        if added:
            return True
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=window)
            return True
        if count > max_requests:
            return False
        return True
