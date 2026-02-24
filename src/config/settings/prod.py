"""Production settings."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

def _require_env(name):
    value = env(name, default="").strip()  # noqa: F405
    if not value:
        raise ImproperlyConfigured(f"{name} must be set for production.")
    return value


_require_env("DJANGO_SECRET_KEY")
_require_env("DATABASE_URL")

ALLOWED_HOSTS = [host.strip() for host in env.list("DJANGO_ALLOWED_HOSTS", default=[]) if host.strip()]  # noqa: F405
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set for production.")

CSRF_TRUSTED_ORIGINS = [  # noqa: F405
    origin.strip() for origin in env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[]) if origin.strip()
]
if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured("DJANGO_CSRF_TRUSTED_ORIGINS must be set for production.")

if CORS_ALLOW_ALL_ORIGINS:  # noqa: F405
    raise ImproperlyConfigured("CORS_ALLOW_ALL_ORIGINS cannot be enabled in production.")

if any(origin == "*" for origin in CORS_ALLOWED_ORIGINS):  # noqa: F405
    raise ImproperlyConfigured("CORS_ALLOWED_ORIGINS cannot contain wildcard entries in production.")

def _bool_env(name, default):
    return env.bool(name, default=default)  # noqa: F405


SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = _bool_env("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = _bool_env("SECURE_HSTS_PRELOAD", False)
SECURE_SSL_REDIRECT = _bool_env("SECURE_SSL_REDIRECT", True)
SECURE_REDIRECT_EXEMPT = [pattern for pattern in env.list("SECURE_REDIRECT_EXEMPT", default=[]) if pattern]  # noqa: F405
SESSION_COOKIE_SECURE = _bool_env("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = _bool_env("CSRF_COOKIE_SECURE", True)

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = _bool_env("CSRF_COOKIE_HTTPONLY", True)
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="Lax")  # noqa: F405
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="Lax")  # noqa: F405
CSRF_COOKIE_NAME = env("CSRF_COOKIE_NAME", default="csrftoken")  # noqa: F405
CSRF_USE_SESSIONS = _bool_env("CSRF_USE_SESSIONS", False)

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", default="strict-origin-when-cross-origin")  # noqa: F405
SECURE_CROSS_ORIGIN_OPENER_POLICY = env("SECURE_CROSS_ORIGIN_OPENER_POLICY", default="same-origin")  # noqa: F405
X_FRAME_OPTIONS = env("X_FRAME_OPTIONS", default="DENY")  # noqa: F405
PERMISSIONS_POLICY = env(
    "PERMISSIONS_POLICY",
    default="geolocation=(), camera=(), microphone=(), payment=()",
)  # noqa: F405

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
CONTENT_SECURITY_POLICY = env("CONTENT_SECURITY_POLICY", default=_csp_default)  # noqa: F405
CONTENT_SECURITY_POLICY_REPORT_ONLY = _bool_env("CONTENT_SECURITY_POLICY_REPORT_ONLY", False)

SESSION_COOKIE_NAME = env("SESSION_COOKIE_NAME", default="nbms_sessionid")  # noqa: F405
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=60 * 60 * 12)  # noqa: F405
SESSION_EXPIRE_AT_BROWSER_CLOSE = _bool_env("SESSION_EXPIRE_AT_BROWSER_CLOSE", False)
SESSION_SAVE_EVERY_REQUEST = _bool_env("SESSION_SAVE_EVERY_REQUEST", False)
USE_X_FORWARDED_HOST = _bool_env("USE_X_FORWARDED_HOST", True)
USE_X_FORWARDED_PORT = _bool_env("USE_X_FORWARDED_PORT", True)

_proxy_header = env("SECURE_PROXY_SSL_HEADER", default="HTTP_X_FORWARDED_PROTO,https").strip()  # noqa: F405
if _proxy_header:
    if "," not in _proxy_header:
        raise ImproperlyConfigured("SECURE_PROXY_SSL_HEADER must use 'HEADER,VALUE' format.")
    header, value = [part.strip() for part in _proxy_header.split(",", 1)]
    if not header or not value:
        raise ImproperlyConfigured("SECURE_PROXY_SSL_HEADER must use 'HEADER,VALUE' format.")
    SECURE_PROXY_SSL_HEADER = (header, value)

