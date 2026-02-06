import importlib


def _reload_prod_settings():
    import config.settings.base as base
    import config.settings.prod as prod

    importlib.reload(base)
    return importlib.reload(prod)


def test_prod_secure_defaults_are_enabled(monkeypatch):
    monkeypatch.setenv("DJANGO_SECRET_KEY", "prod-secret")
    monkeypatch.setenv("NBMS_DB_PASSWORD", "prod-db-password")
    for key in (
        "SECURE_SSL_REDIRECT",
        "SESSION_COOKIE_SECURE",
        "CSRF_COOKIE_SECURE",
        "SECURE_HSTS_SECONDS",
        "SECURE_PROXY_SSL_HEADER",
    ):
        monkeypatch.delenv(key, raising=False)

    prod = _reload_prod_settings()

    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
    assert prod.SECURE_HSTS_SECONDS == 31536000
    assert prod.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert prod.X_FRAME_OPTIONS == "DENY"


def test_prod_proxy_ssl_header_parsing(monkeypatch):
    monkeypatch.setenv("DJANGO_SECRET_KEY", "prod-secret")
    monkeypatch.setenv("NBMS_DB_PASSWORD", "prod-db-password")
    monkeypatch.setenv("SECURE_PROXY_SSL_HEADER", "HTTP_X_FORWARDED_PROTO,https")

    prod = _reload_prod_settings()

    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")

