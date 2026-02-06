from datetime import date

import pytest
from django.urls import reverse

from nbms_app.models import Organisation, ReportingCycle, ReportingInstance, User


pytestmark = pytest.mark.django_db


def _make_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-NR7",
        title="NR7 Cycle",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    return ReportingInstance.objects.create(cycle=cycle, version_label="v1")


def test_reporting_instances_api_requires_staff_scope(client):
    instance = _make_instance()
    org = Organisation.objects.create(name="Org A", org_code="ORG-A")
    user = User.objects.create_user(username="viewer", password="pass1234", organisation=org)
    client.force_login(user)

    response = client.get(reverse("api_reporting_instances"))
    assert response.status_code == 403

    user.is_staff = True
    user.save(update_fields=["is_staff"])
    response = client.get(reverse("api_reporting_instances"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["instances"][0]["uuid"] == str(instance.uuid)


def test_nr7_summary_api_returns_validation_and_links(client):
    instance = _make_instance()
    org = Organisation.objects.create(name="Org B", org_code="ORG-B")
    staff = User.objects.create_user(
        username="staff",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    client.force_login(staff)

    response = client.get(reverse("api_reporting_nr7_summary", kwargs={"instance_uuid": instance.uuid}))
    assert response.status_code == 200
    payload = response.json()
    assert payload["instance"]["uuid"] == str(instance.uuid)
    assert "validation" in payload
    assert "qa_items" in payload["validation"]
    assert payload["links"]["section_i"].endswith(f"/reporting/instances/{instance.uuid}/section-i/")


def test_nr7_pdf_export_endpoint_returns_pdf(client):
    instance = _make_instance()
    org = Organisation.objects.create(name="Org C", org_code="ORG-C")
    staff = User.objects.create_user(
        username="pdf-staff",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    client.force_login(staff)

    response = client.get(reverse("api_reporting_nr7_pdf", kwargs={"instance_uuid": instance.uuid}))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
