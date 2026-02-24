import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured


def _reload_prod_settings():
    import config.settings.base as base
    import config.settings.prod as prod

    importlib.reload(base)
    return importlib.reload(prod)


def test_prod_secure_defaults_are_enabled(monkeypatch):
    monkeypatch.setenv("DJANGO_READ_DOT_ENV_FILE", "0")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "prod-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp-prod-settings.sqlite3")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.org")
    monkeypatch.setenv("DJANGO_CSRF_TRUSTED_ORIGINS", "https://example.org")
    for key in (
        "SECURE_SSL_REDIRECT",
        "SESSION_COOKIE_SECURE",
        "CSRF_COOKIE_SECURE",
        "SECURE_HSTS_SECONDS",
        "SECURE_PROXY_SSL_HEADER",
    ):
        monkeypatch.delenv(key, raising=False)

    prod = _reload_prod_settings()

    assert prod.DEBUG is False
    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
    assert prod.SECURE_HSTS_SECONDS == 31536000
    assert prod.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert prod.X_FRAME_OPTIONS == "DENY"
    assert "default-src 'self'" in prod.CONTENT_SECURITY_POLICY
    assert prod.SESSION_COOKIE_NAME == "nbms_sessionid"
    assert prod.SESSION_COOKIE_AGE == 43200
    assert prod.USE_X_FORWARDED_HOST is True
    assert prod.USE_X_FORWARDED_PORT is True
    assert prod.SECURE_REFERRER_POLICY == "strict-origin-when-cross-origin"
    assert "geolocation=()" in prod.PERMISSIONS_POLICY


def test_prod_proxy_ssl_header_parsing(monkeypatch):
    monkeypatch.setenv("DJANGO_READ_DOT_ENV_FILE", "0")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "prod-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp-prod-settings.sqlite3")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.org")
    monkeypatch.setenv("DJANGO_CSRF_TRUSTED_ORIGINS", "https://example.org")
    monkeypatch.setenv("SECURE_PROXY_SSL_HEADER", "HTTP_X_FORWARDED_PROTO,https")

    prod = _reload_prod_settings()

    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")


def test_prod_fails_fast_when_database_url_missing(monkeypatch):
    monkeypatch.setenv("DJANGO_READ_DOT_ENV_FILE", "0")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "prod-secret")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.org")
    monkeypatch.setenv("DJANGO_CSRF_TRUSTED_ORIGINS", "https://example.org")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ImproperlyConfigured, match="DATABASE_URL must be set for production."):
        _reload_prod_settings()


def test_prod_rejects_cors_wildcard(monkeypatch):
    monkeypatch.setenv("DJANGO_READ_DOT_ENV_FILE", "0")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "prod-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp-prod-settings.sqlite3")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.org")
    monkeypatch.setenv("DJANGO_CSRF_TRUSTED_ORIGINS", "https://example.org")
    monkeypatch.setenv("CORS_ALLOW_ALL_ORIGINS", "true")

    with pytest.raises(ImproperlyConfigured, match="CORS_ALLOW_ALL_ORIGINS cannot be enabled in production."):
        _reload_prod_settings()
