import os

from celery.schedules import crontab
from flask_caching.backends.rediscache import RedisCache


def _bool_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("SUPERSET_SECRET_KEY", "")
SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "")
SUPERSET_WEBSERVER_PORT = int(os.getenv("SUPERSET_PORT", "8088"))
TALISMAN_ENABLED = False
ENABLE_PROXY_FIX = _bool_env("ENABLE_PROXY_FIX", "true")
FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "EMBEDDED_SUPERSET": True,
}
GUEST_ROLE_NAME = "Stakeholder Viewer"
WTF_CSRF_ENABLED = True
ROW_LIMIT = 5000
SQL_MAX_ROW = 100000
CONTENT_SECURITY_POLICY_WARNING = False

_broker_url = os.getenv("CELERY_BROKER_URL", "redis://superset_redis:6379/0")
_result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://superset_redis:6379/1")
_cache_redis_url = os.getenv("CACHE_REDIS_URL", "redis://superset_redis:6379/2")
_rate_limit_storage = os.getenv("RATELIMIT_STORAGE_URI", "redis://superset_redis:6379/4")


class CeleryConfig:
    broker_url = _broker_url
    result_backend = _result_backend
    imports = (
        "superset.sql_lab",
        "superset.tasks.scheduler",
        "superset.tasks.thumbnails",
    )
    task_acks_late = False
    worker_prefetch_multiplier = 1
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=0, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": _cache_redis_url,
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_cache_",
}
DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": _cache_redis_url,
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_data_",
}
FILTER_STATE_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": _cache_redis_url,
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_filters_",
}
EXPLORE_FORM_DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": _cache_redis_url,
    "CACHE_DEFAULT_TIMEOUT": 86400,
    "CACHE_KEY_PREFIX": "superset_explore_",
}
RESULTS_BACKEND = RedisCache(host="superset_redis", port=6379, key_prefix="superset_results")
GLOBAL_ASYNC_QUERIES_REDIS_CONFIG = {
    "host": "superset_redis",
    "port": 6379,
    "db": 3,
    "ssl": False,
}
RATELIMIT_STORAGE_URI = _rate_limit_storage
