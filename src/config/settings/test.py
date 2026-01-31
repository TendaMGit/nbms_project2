"""Test settings."""

from .base import *  # noqa: F403

DEBUG = False

if not SECRET_KEY:  # noqa: F405
    SECRET_KEY = "test-secret-key"  # noqa: F405

ALLOWED_HOSTS = ["testserver"]  # noqa: F405

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Keep sessions in the DB for test runs to avoid Redis dependency.
SESSION_ENGINE = "django.contrib.sessions.backends.db"

TEST_RUNNER = "config.test_runner.NBMSTestRunner"
TEST_DISCOVER_ROOT = str(SRC_DIR)  # noqa: F405
TEST_DISCOVER_TOP_LEVEL = str(BASE_DIR)  # noqa: F405
TEST_DISCOVER_PATTERN = "test*.py"

LOGGING = LOGGING.copy()  # noqa: F405
LOGGING["loggers"] = {**LOGGING.get("loggers", {})}
LOGGING["loggers"]["django.request"] = {
    "handlers": ["console"],
    "level": "ERROR",
    "propagate": False,
}

