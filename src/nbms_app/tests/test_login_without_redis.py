import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse


pytestmark = pytest.mark.django_db


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-login-cache",
        }
    },
    SESSION_ENGINE="django.contrib.sessions.backends.db",
)
def test_login_works_without_redis(client):
    User = get_user_model()
    User.objects.create_user(username="alice", password="pass1234")

    login_url = reverse("two_factor:login")
    response = client.get(login_url)
    assert response.status_code == 200

    response = client.post(
        login_url,
        {
            "auth-username": "alice",
            "auth-password": "pass1234",
            "login_view-current_step": "auth",
        },
    )
    assert response.status_code in {302, 303}
    assert "_auth_user_id" in client.session


def test_cache_fallback_when_redis_unreachable(monkeypatch):
    from config.settings import base as base_settings
    import redis

    monkeypatch.setenv("USE_REDIS", "1")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6399/0")
    monkeypatch.setattr(base_settings, "DEBUG", True)
    monkeypatch.setattr(base_settings, "ENVIRONMENT", "dev")

    class _FakeRedis:
        def ping(self):
            raise redis.ConnectionError("redis down")

    monkeypatch.setattr(redis.Redis, "from_url", lambda *args, **kwargs: _FakeRedis())

    caches = base_settings._build_cache_settings()
    assert caches["default"]["BACKEND"].endswith("LocMemCache")
