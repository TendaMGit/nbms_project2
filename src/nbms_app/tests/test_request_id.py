import re

import pytest
from django.urls import reverse


pytestmark = pytest.mark.django_db


def test_request_id_is_added_when_missing(client):
    response = client.get(reverse("nbms_app:health_db"))
    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)


def test_request_id_honours_incoming_header(client):
    response = client.get(reverse("nbms_app:health_db"), HTTP_X_REQUEST_ID="integration-probe-123")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "integration-probe-123"
