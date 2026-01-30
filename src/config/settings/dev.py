"""Development settings."""

import os

from .base import *  # noqa: F403

DEBUG = True

if not SECRET_KEY:  # noqa: F405
    SECRET_KEY = "dev-not-for-production"  # noqa: F405

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]  # noqa: F405

# Default to local-memory cache for Windows-first dev when Redis isn't configured.
if not os.environ.get("REDIS_URL"):
    CACHES = {  # noqa: F405
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "nbms-dev-cache",
        }
    }

