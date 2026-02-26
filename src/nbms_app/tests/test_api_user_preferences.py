import json

import pytest
from django.urls import reverse

from nbms_app.models import Organisation, User, UserPreference


pytestmark = pytest.mark.django_db


def _create_user(username):
    org = Organisation.objects.create(name=f"{username}-org", org_code=f"{username.upper()}-ORG")
    return User.objects.create_user(
        username=username,
        password="Pass_12345",
        organisation=org,
        is_staff=True,
    )


def test_me_preferences_requires_authentication(client):
    response = client.get(reverse("api_me_preferences"))
    assert response.status_code in {401, 403}


def test_me_preferences_get_bootstraps_defaults(client):
    user = _create_user("pref-user")
    client.force_login(user)

    response = client.get(reverse("api_me_preferences"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["theme_id"] == "fynbos"
    assert payload["theme_mode"] == "light"
    assert payload["density"] == "comfortable"
    assert payload["default_geography"]["type"] == "national"
    assert payload["saved_filters"]["indicators"] == []
    assert payload["watchlist"]["reports"] == []
    assert UserPreference.objects.filter(user=user).exists()


def test_me_preferences_put_updates_profile(client):
    user = _create_user("pref-updater")
    client.force_login(user)

    response = client.put(
        reverse("api_me_preferences"),
        data=json.dumps(
            {
                "theme_id": "high_contrast",
                "theme_mode": "dark",
                "density": "compact",
                "default_geography": {"type": "province", "code": "ZA-WC"},
                "saved_filters": {"indicators": [], "registries": [], "downloads": []},
                "watchlist": {
                    "indicators": ["ind-001"],
                    "registries": [],
                    "reports": ["rep-001"],
                },
                "dashboard_layout": {"cards": ["updated", "due_soon"]},
            },
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["theme_id"] == "high_contrast"
    assert payload["theme_mode"] == "dark"
    assert payload["density"] == "compact"
    assert payload["default_geography"]["type"] == "province"
    assert payload["default_geography"]["code"] == "ZA-WC"
    assert payload["dashboard_layout"]["cards"] == ["updated", "due_soon"]


def test_watchlist_add_and_remove(client):
    user = _create_user("watch-user")
    client.force_login(user)

    add_response = client.post(
        reverse("api_me_preferences_watchlist_add"),
        data=json.dumps({"namespace": "indicators", "uuid": "indicator-001"}),
        content_type="application/json",
    )
    assert add_response.status_code == 200
    assert add_response.json()["watchlist"]["indicators"] == ["indicator-001"]

    # Duplicate add should remain unique.
    second_add = client.post(
        reverse("api_me_preferences_watchlist_add"),
        data=json.dumps({"namespace": "indicators", "uuid": "indicator-001"}),
        content_type="application/json",
    )
    assert second_add.status_code == 200
    assert second_add.json()["watchlist"]["indicators"] == ["indicator-001"]

    remove_response = client.post(
        reverse("api_me_preferences_watchlist_remove"),
        data=json.dumps({"namespace": "indicators", "uuid": "indicator-001"}),
        content_type="application/json",
    )
    assert remove_response.status_code == 200
    assert remove_response.json()["watchlist"]["indicators"] == []


def test_saved_filter_create_and_delete(client):
    user = _create_user("saved-filter-user")
    client.force_login(user)

    create_response = client.post(
        reverse("api_me_preferences_saved_filters"),
        data=json.dumps(
            {
                "namespace": "indicators",
                "name": "Due soon",
                "params": {"search": "forest", "due_soon": True},
                "pinned": True,
            }
        ),
        content_type="application/json",
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    entry_id = payload["entry"]["id"]
    assert payload["entry"]["name"] == "Due soon"
    assert payload["saved_filters"]["indicators"][0]["id"] == entry_id

    delete_response = client.delete(reverse("api_me_preferences_saved_filter_delete", args=[entry_id]))
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
    assert delete_response.json()["saved_filters"]["indicators"] == []


def test_preferences_are_isolated_per_user(client):
    user_a = _create_user("pref-a")
    user_b = _create_user("pref-b")

    client.force_login(user_a)
    update_response = client.put(
        reverse("api_me_preferences"),
        data=json.dumps({"theme_id": "dark_pro"}),
        content_type="application/json",
    )
    assert update_response.status_code == 200

    client.force_login(user_b)
    user_b_response = client.get(reverse("api_me_preferences"))
    assert user_b_response.status_code == 200
    assert user_b_response.json()["theme_id"] == "fynbos"
