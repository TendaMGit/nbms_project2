from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse


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
