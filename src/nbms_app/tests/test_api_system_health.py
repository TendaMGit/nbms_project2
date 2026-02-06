import pytest
from django.urls import reverse

from nbms_app.models import AuditEvent, Organisation, User


pytestmark = pytest.mark.django_db


def test_system_health_requires_authentication(client):
    response = client.get(reverse("api_system_health"))
    assert response.status_code in {401, 403}


def test_system_health_forbids_non_staff(client):
    org = Organisation.objects.create(name="Org", org_code="ORG")
    user = User.objects.create_user(username="viewer", password="pass1234", organisation=org)
    client.force_login(user)

    response = client.get(reverse("api_system_health"))
    assert response.status_code == 403


def test_system_health_staff_receives_status_and_recent_failures(client):
    org = Organisation.objects.create(name="Org", org_code="ORG")
    user = User.objects.create_user(
        username="operator",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    AuditEvent.objects.create(
        actor=user,
        action="export_reject",
        event_type="export_reject",
        object_type="ExportPackage",
        object_id="1",
        metadata={"status": "draft"},
    )
    client.force_login(user)

    response = client.get(reverse("api_system_health"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_status"] in {"ok", "degraded"}
    assert [service["service"] for service in payload["services"]] == ["database", "storage", "cache"]
    assert "recent_failures" in payload
