"""
Base settings.
"""

import logging
import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = BASE_DIR / "src"

env = environ.Env()
if os.environ.get("DJANGO_READ_DOT_ENV_FILE", "1").lower() in ("1", "true", "yes"):
    environ.Env.read_env(str(BASE_DIR / ".env"))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ENVIRONMENT = env("ENVIRONMENT", default="dev").lower()

logger = logging.getLogger(__name__)

_default_hosts = ["localhost", "127.0.0.1", "0.0.0.0"]
ALLOWED_HOSTS = [h.strip() for h in env.list("DJANGO_ALLOWED_HOSTS", default=_default_hosts) if h.strip()]

_default_csrf = [
    "http://localhost",
    "http://127.0.0.1",
    "http://0.0.0.0",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=_default_csrf) if o.strip()]
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in env.list("CORS_ALLOWED_ORIGINS", default=[]) if origin.strip()]
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=True)
_cors_headers_default = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CORS_ALLOW_HEADERS = [header.strip().lower() for header in env.list("CORS_ALLOW_HEADERS", default=_cors_headers_default)]

ENABLE_GIS = env.bool("ENABLE_GIS", default=False)

GIS_APPS = ["django.contrib.gis"] if ENABLE_GIS else []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    *GIS_APPS,
    "django.contrib.sites",
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "django_filters",
    "guardian",
    "storages",
    "django_otp",
    "django_otp.plugins.otp_static",
    "django_otp.plugins.otp_totp",
    "two_factor",
    "nbms_app.apps.NbmsAppConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "nbms_app.middleware_request_id.RequestIDMiddleware",
    "django.middleware.common.CommonMiddleware",
    "nbms_app.middleware.RateLimitMiddleware",
    "nbms_app.middleware_metrics.MetricsMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "nbms_app.middleware_request_logging.RequestLoggingMiddleware",
    "nbms_app.middleware_security.SessionSecurityMiddleware",
    "nbms_app.middleware_security.SecurityHeadersMiddleware",
    "nbms_app.middleware_audit.AuditContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_otp.middleware.OTPMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "nbms_app.context_processors.reporting_instance_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


DATABASE_URL = env("DATABASE_URL", default="")
if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
        )
    }
else:
    db_name = env("NBMS_DB_NAME", default=env("POSTGRES_DB", default="nbms_project_db2"))
    db_user = env("NBMS_DB_USER", default=env("POSTGRES_USER", default="nbms_user"))
    db_password = env("NBMS_DB_PASSWORD", default=env("POSTGRES_PASSWORD", default=""))
    db_host = env("POSTGRES_HOST", default="localhost")
    db_port = env("POSTGRES_PORT", default="5432")
    test_db_name = env("NBMS_TEST_DB_NAME", default=env("POSTGRES_TEST_DB", default="test_nbms_project_db2"))
    DATABASES = {
        "default": {
            "ENGINE": env("DJANGO_DB_ENGINE", default="django.contrib.gis.db.backends.postgis"),
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
            "TEST": {"NAME": test_db_name},
        }
    }

if ENABLE_GIS and DATABASES["default"]["ENGINE"].startswith("django.db.backends.postgresql"):
    DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"
if not ENABLE_GIS and DATABASES["default"]["ENGINE"].startswith("django.contrib.gis"):
    DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"


AUTH_USER_MODEL = "nbms_app.User"
SITE_ID = 1
AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", default="Africa/Johannesburg")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int("DATA_UPLOAD_MAX_MEMORY_SIZE", default=10 * 1024 * 1024)
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int("FILE_UPLOAD_MAX_MEMORY_SIZE", default=5 * 1024 * 1024)
DATA_UPLOAD_MAX_NUMBER_FIELDS = env.int("DATA_UPLOAD_MAX_NUMBER_FIELDS", default=2000)

EVIDENCE_MAX_FILE_SIZE = env.int("EVIDENCE_MAX_FILE_SIZE", default=25 * 1024 * 1024)
EVIDENCE_ALLOWED_EXTENSIONS = [
    ext.strip().lower()
    for ext in env(
        "EVIDENCE_ALLOWED_EXTENSIONS",
        default=".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt",
    ).split(",")
    if ext.strip()
]

EXPORT_REQUIRE_SECTIONS = env.bool("EXPORT_REQUIRE_SECTIONS", default=False)
EXPORT_REQUIRE_READINESS = env.bool("EXPORT_REQUIRE_READINESS", default=False)

ONLYOFFICE_ENABLED = env.bool("ONLYOFFICE_ENABLED", default=False)
ONLYOFFICE_DOCUMENT_SERVER_URL = env("ONLYOFFICE_DOCUMENT_SERVER_URL", default="http://onlyoffice")
ONLYOFFICE_DOCUMENT_SERVER_PUBLIC_URL = env(
    "ONLYOFFICE_DOCUMENT_SERVER_PUBLIC_URL",
    default="http://localhost:8082",
)
ONLYOFFICE_JWT_SECRET = env("ONLYOFFICE_JWT_SECRET", default="")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if ENABLE_GIS and os.name == "nt":
    gdal_path = env("GDAL_LIBRARY_PATH", default=None)
    geos_path = env("GEOS_LIBRARY_PATH", default=None)
    if gdal_path:
        GDAL_LIBRARY_PATH = gdal_path
    if geos_path:
        GEOS_LIBRARY_PATH = geos_path

if ENABLE_GIS and env("DJANGO_DB_ENGINE", default="") == "django.contrib.gis.db.backends.spatialite":
    os.environ.setdefault("SPATIALITE_LIBRARY_PATH", env("SPATIALITE_LIBRARY_PATH", default="mod_spatialite"))

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@nbms.local")

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("DRF_THROTTLE_ANON", default="120/min"),
        "user": env("DRF_THROTTLE_USER", default="600/min"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "NBMS Platform API",
    "DESCRIPTION": "NBMS platform baseline with PostGIS and governance controls.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"


_use_s3_env = env("USE_S3", default=None)
if _use_s3_env is None:
    _use_s3_env = env("USE_S3_STORAGE", default="0")
USE_S3 = _use_s3_env.lower() in ("1", "true", "yes")
USE_S3_STORAGE = USE_S3
AWS_S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default="http://localhost:9000")
AWS_ACCESS_KEY_ID = env("S3_ACCESS_KEY", default="minioadmin")
AWS_SECRET_ACCESS_KEY = env("S3_SECRET_KEY", default="minioadmin")
AWS_STORAGE_BUCKET_NAME = env("S3_BUCKET", default="nbms-media")
AWS_S3_REGION_NAME = env("S3_REGION", default="us-east-1")
AWS_S3_ADDRESSING_STYLE = env("S3_ADDRESSING_STYLE", default="path")
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False

if USE_S3:
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


LOG_LEVEL = env("DJANGO_LOG_LEVEL", default="INFO")
LOG_JSON = env.bool("DJANGO_LOG_JSON", default=False)
LOGGING_FORMATTER = "json" if LOG_JSON else "plain"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "nbms_app.logging_utils.RequestIdLogFilter",
        },
        "sensitive_data": {
            "()": "nbms_app.logging_utils.SensitiveDataFilter",
        },
    },
    "formatters": {
        "plain": {
            "format": (
                "%(asctime)s %(levelname)s %(name)s "
                "[request_id=%(request_id)s user_id=%(user_id)s method=%(method)s "
                "path=%(path)s status=%(status_code)s latency_ms=%(latency_ms)s] %(message)s"
            ),
        },
        "json": {
            "()": "nbms_app.logging_utils.JsonLogFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_id", "sensitive_data"],
            "formatter": LOGGING_FORMATTER,
        }
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "nbms.request": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

SENTRY_DSN = env("SENTRY_DSN", default="")
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", default=ENVIRONMENT)
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0)
SENTRY_PROFILES_SAMPLE_RATE = env.float("SENTRY_PROFILES_SAMPLE_RATE", default=0.0)
SENTRY_SEND_DEFAULT_PII = env.bool("SENTRY_SEND_DEFAULT_PII", default=False)
SENTRY_RELEASE = env("SENTRY_RELEASE", default="")

if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
            send_default_pii=SENTRY_SEND_DEFAULT_PII,
            environment=SENTRY_ENVIRONMENT,
            release=SENTRY_RELEASE or None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sentry initialization skipped: %s", exc)

def _bool_env(value):
    return str(value).lower() in ("1", "true", "yes")


def _should_use_redis():
    explicit = env("USE_REDIS", default=None)
    if explicit is not None:
        return _bool_env(explicit)
    cache_backend = env("CACHE_BACKEND", default="").lower()
    if cache_backend == "redis":
        return True
    return False


def _build_cache_settings():
    redis_url = env("REDIS_URL", default="redis://localhost:6379/0")
    use_redis = _should_use_redis()
    allow_fallback = DEBUG or ENVIRONMENT in ("dev", "test")

    if use_redis and allow_fallback:
        try:
            import redis

            redis.Redis.from_url(redis_url).ping()
        except Exception:  # noqa: BLE001
            logger.warning("Redis unreachable; falling back to LocMemCache for dev/test.")
            use_redis = False

    if use_redis:
        return {
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": redis_url,
            }
        }

    return {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "nbms-local-cache",
        }
    }


CACHES = _build_cache_settings()

RATE_LIMITS = {
    "login": {
        "rate": env("RATE_LIMIT_LOGIN", default="5/300"),
        "methods": ["POST"],
        "paths": ["/accounts/login/", "/account/login/"],
    },
    "password_reset": {
        "rate": env("RATE_LIMIT_PASSWORD_RESET", default="5/300"),
        "methods": ["POST"],
        "paths": ["/accounts/password_reset/"],
    },
    "workflow": {
        "rate": env("RATE_LIMIT_WORKFLOW", default="10/60"),
        "methods": ["POST"],
        "paths": ["/manage/review-queue/"],
        "actions": ["approve", "reject", "publish", "archive"],
    },
    "exports": {
        "rate": env("RATE_LIMIT_EXPORTS", default="20/60"),
        "methods": ["POST", "GET"],
        "paths": [
            "/exports/",
            "/api/template-packs/",
            "/api/indicators/",
            "/api/spatial/layers/",
        ],
    },
    "public_api": {
        "rate": env("RATE_LIMIT_PUBLIC_API", default="600/60"),
        "methods": ["GET"],
        "paths": [
            "/api/indicators",
            "/api/spatial/layers",
            "/api/ogc",
            "/api/tiles",
            "/api/help/sections",
        ],
    },
    "spatial_heavy": {
        "rate": env("RATE_LIMIT_SPATIAL_HEAVY", default="120/60"),
        "methods": ["GET"],
        "paths": ["/api/ogc/collections/", "/api/tiles/"],
    },
    "metrics": {
        "rate": env("RATE_LIMIT_METRICS", default="30/60"),
        "methods": ["GET"],
        "paths": ["/metrics/", "/api/system/health"],
    },
}

METRICS_TOKEN = env("METRICS_TOKEN", default="")
METRICS_ALLOW_QUERY_TOKEN = env.bool("METRICS_ALLOW_QUERY_TOKEN", default=False)
HEALTHCHECK_SKIP_MIGRATION_CHECK = env.bool("HEALTHCHECK_SKIP_MIGRATION_CHECK", default=False)

BIRDIE_BASE_URL = env("BIRDIE_BASE_URL", default="")
BIRDIE_API_TOKEN = env("BIRDIE_API_TOKEN", default="")
BIRDIE_TIMEOUT_SECONDS = env.int("BIRDIE_TIMEOUT_SECONDS", default=20)
BIRDIE_USE_FIXTURE = env.bool("BIRDIE_USE_FIXTURE", default=True)

LOGIN_URL = "two_factor:login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"


GUARDIAN_RENDER_403 = True
GUARDIAN_RENDER_404 = False
ANONYMOUS_USER_NAME = None

