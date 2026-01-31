"""Development settings."""

from .base import *  # noqa: F403

DEBUG = True

if not SECRET_KEY:  # noqa: F405
    SECRET_KEY = "dev-not-for-production"  # noqa: F405

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]  # noqa: F405

# Keep sessions in the DB for dev to avoid Redis dependency.
SESSION_ENGINE = "django.contrib.sessions.backends.db"

