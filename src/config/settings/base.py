"""
Base settings.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = BASE_DIR / "src"

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"

_default_hosts = "localhost,127.0.0.1,0.0.0.0"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", _default_hosts).split(",") if h.strip()]

_default_csrf = "http://localhost,http://127.0.0.1,http://0.0.0.0"
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", _default_csrf).split(",") if o.strip()
]

ENABLE_GIS = os.environ.get("ENABLE_GIS", "true").lower() == "true"

GIS_APPS = ["django.contrib.gis"] if ENABLE_GIS else []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
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
    "nbms_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
        )
    }
else:
    db_name = os.environ.get("NBMS_DB_NAME", os.environ.get("POSTGRES_DB", "nbms_project_db2"))
    db_user = os.environ.get("NBMS_DB_USER", os.environ.get("POSTGRES_USER", "nbms_user"))
    db_password = os.environ.get("NBMS_DB_PASSWORD", os.environ.get("POSTGRES_PASSWORD", ""))
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    test_db_name = os.environ.get("NBMS_TEST_DB_NAME", os.environ.get("POSTGRES_TEST_DB", "test_nbms_project_db2"))
    DATABASES = {
        "default": {
            "ENGINE": os.environ.get("DJANGO_DB_ENGINE", "django.contrib.gis.db.backends.postgis"),
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
            "TEST": {"NAME": test_db_name},
        }
    }

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
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Africa/Johannesburg")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if ENABLE_GIS and os.name == "nt":
    gdal_path = os.environ.get("GDAL_LIBRARY_PATH")
    geos_path = os.environ.get("GEOS_LIBRARY_PATH")
    if gdal_path:
        GDAL_LIBRARY_PATH = gdal_path
    if geos_path:
        GEOS_LIBRARY_PATH = geos_path

if ENABLE_GIS and os.environ.get("DJANGO_DB_ENGINE") == "django.contrib.gis.db.backends.spatialite":
    os.environ.setdefault("SPATIALITE_LIBRARY_PATH", os.environ.get("SPATIALITE_LIBRARY_PATH", "mod_spatialite"))

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
}

SPECTACULAR_SETTINGS = {
    "TITLE": "NBMS Platform API",
    "DESCRIPTION": "NBMS platform baseline with PostGIS and governance controls.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"


USE_S3_STORAGE = os.environ.get("USE_S3_STORAGE", "true").lower() == "true"
AWS_S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000")
AWS_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_KEY", "minioadmin")
AWS_STORAGE_BUCKET_NAME = os.environ.get("S3_BUCKET", "nbms-media")
AWS_S3_REGION_NAME = os.environ.get("S3_REGION", "us-east-1")
AWS_S3_ADDRESSING_STYLE = os.environ.get("S3_ADDRESSING_STYLE", "path")
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False

if USE_S3_STORAGE:
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


LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {"django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False}},
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    }
}


LOGIN_URL = "two_factor:login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"


GUARDIAN_RENDER_403 = True
GUARDIAN_RENDER_404 = False
ANONYMOUS_USER_NAME = None

