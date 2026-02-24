from django.core.cache import cache
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

import pytest

from nbms_app.models import Organisation, User


pytestmark = pytest.mark.django_db


@override_settings(
    RATE_LIMITS={
        "test_public": {
            "rate": "2/60",
            "methods": ["GET"],
            "paths": ["/api/help/sections"],
        }
    }
)
def test_rate_limit_blocks_after_threshold(client):
    cache.clear()
    url = reverse("api_help_sections")
    first = client.get(url)
    second = client.get(url)
    blocked = client.get(url)

    assert first.status_code == 200
    assert second.status_code == 200
    assert blocked.status_code == 429
    assert blocked.headers.get("Retry-After") == "60"


@override_settings(
    RATE_LIMITS={
        "login_limit": {
            "rate": "2/60",
            "methods": ["POST"],
            "paths": ["/accounts/login/"],
        }
    }
)
def test_login_rate_limit_blocks_bruteforce_attempts(client):
    cache.clear()
    org = Organisation.objects.create(name="Org", org_code="ORG")
    User.objects.create_user(username="ratelimited-user", password="Pass_12345", organisation=org)
    login_url = reverse("login")
    payload = {"username": "ratelimited-user", "password": "wrong-password"}

    first = client.post(login_url, payload)
    second = client.post(login_url, payload)
    blocked = client.post(login_url, payload)

    assert first.status_code in {200, 302}
    assert second.status_code in {200, 302}
    assert blocked.status_code == 429
    assert blocked.headers.get("Retry-After") == "60"


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_CLASSES": [
            "rest_framework.throttling.AnonRateThrottle",
            "rest_framework.throttling.UserRateThrottle",
        ],
        "DEFAULT_THROTTLE_RATES": {"anon": "5/min", "user": "20/min"},
    }
)
def test_drf_throttle_configuration_is_present():
    throttles = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"]
    throttle_rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

    assert "rest_framework.throttling.AnonRateThrottle" in throttles
    assert "rest_framework.throttling.UserRateThrottle" in throttles
    assert throttle_rates["anon"] == "5/min"
    assert throttle_rates["user"] == "20/min"
