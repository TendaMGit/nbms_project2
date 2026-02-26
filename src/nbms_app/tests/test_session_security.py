import pytest
from django.urls import reverse

from nbms_app.models import Organisation, User


pytestmark = pytest.mark.django_db


def test_authenticated_session_rekeys_once(client):
    org = Organisation.objects.create(name="Org", org_code="ORG")
    user = User.objects.create_user(username="session-user", password="pass1234", organisation=org)
    client.force_login(user)
    initial_session_key = client.session.session_key

    first_response = client.get(reverse("nbms_app:home"))
    first_session_key = client.session.session_key
    second_response = client.get(reverse("nbms_app:home"))
    second_session_key = client.session.session_key

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_session_key != initial_session_key
    assert second_session_key == first_session_key
