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

SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False").lower() == "true"
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False").lower() == "true"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

