"""Production settings."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set for production.")

if not DATABASES["default"].get("PASSWORD"):  # noqa: F405
    raise ImproperlyConfigured("POSTGRES_PASSWORD must be set for production.")

if not ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set for production.")

def _bool_env(name, default):
    fallback = "true" if default else "false"
    return os.environ.get(name, fallback).lower() == "true"


SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _bool_env("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = _bool_env("SECURE_HSTS_PRELOAD", False)
SECURE_SSL_REDIRECT = _bool_env("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = _bool_env("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = _bool_env("CSRF_COOKIE_SECURE", True)

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = _bool_env("CSRF_COOKIE_HTTPONLY", True)
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.environ.get("CSRF_COOKIE_SAMESITE", "Lax")

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = os.environ.get("SECURE_REFERRER_POLICY", "same-origin")
SECURE_CROSS_ORIGIN_OPENER_POLICY = os.environ.get("SECURE_CROSS_ORIGIN_OPENER_POLICY", "same-origin")
X_FRAME_OPTIONS = os.environ.get("X_FRAME_OPTIONS", "DENY")

_csp_default = " ".join(
    [
        "default-src 'self';",
        "script-src 'self';",
        "style-src 'self' 'unsafe-inline';",
        "img-src 'self' data: blob: https://tile.openstreetmap.org;",
        "font-src 'self' data:;",
        "connect-src 'self';",
        "object-src 'none';",
        "base-uri 'self';",
        "frame-ancestors 'none';",
        "form-action 'self';",
    ]
)
CONTENT_SECURITY_POLICY = os.environ.get("CONTENT_SECURITY_POLICY", _csp_default)
CONTENT_SECURITY_POLICY_REPORT_ONLY = _bool_env("CONTENT_SECURITY_POLICY_REPORT_ONLY", False)

SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "nbms_sessionid")
SESSION_COOKIE_AGE = int(os.environ.get("SESSION_COOKIE_AGE", str(60 * 60 * 12)))
SESSION_EXPIRE_AT_BROWSER_CLOSE = _bool_env("SESSION_EXPIRE_AT_BROWSER_CLOSE", False)
SESSION_SAVE_EVERY_REQUEST = _bool_env("SESSION_SAVE_EVERY_REQUEST", False)

_proxy_header = os.environ.get("SECURE_PROXY_SSL_HEADER", "").strip()
if _proxy_header:
    if "," not in _proxy_header:
        raise ImproperlyConfigured("SECURE_PROXY_SSL_HEADER must use 'HEADER,VALUE' format.")
    header, value = [part.strip() for part in _proxy_header.split(",", 1)]
    if not header or not value:
        raise ImproperlyConfigured("SECURE_PROXY_SSL_HEADER must use 'HEADER,VALUE' format.")
    SECURE_PROXY_SSL_HEADER = (header, value)

