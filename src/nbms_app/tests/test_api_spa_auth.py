import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from nbms_app.models import Organisation, User
from nbms_app.services.authorization import ROLE_DATA_STEWARD


pytestmark = pytest.mark.django_db


def test_api_auth_me_requires_authentication(client):
    response = client.get(reverse("api_auth_me"))
    assert response.status_code in {401, 403}


def test_api_auth_me_returns_profile_and_capabilities(client):
    org = Organisation.objects.create(name="Org A", org_code="ORG-A")
    user = User.objects.create_user(
        username="api-user",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=ROLE_DATA_STEWARD)
    user.groups.add(group)
    client.force_login(user)

    response = client.get(reverse("api_auth_me"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "api-user"
    assert payload["organisation"]["name"] == "Org A"
    assert payload["capabilities"]["is_staff"] is True


def test_api_auth_csrf_returns_token(client):
    response = client.get(reverse("api_auth_csrf"))
    assert response.status_code == 200
    payload = response.json()
    assert "csrfToken" in payload
    assert payload["csrfToken"]


def test_api_help_sections_exposes_help_dictionary(client):
    response = client.get(reverse("api_help_sections"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"]
    assert "section_i" in payload["sections"]
