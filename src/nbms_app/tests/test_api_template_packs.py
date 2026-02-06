from datetime import date

import pytest
from django.core.management import call_command
from django.urls import reverse

from nbms_app.models import Organisation, ReportingCycle, ReportingInstance, User


pytestmark = pytest.mark.django_db


def _create_staff():
    org = Organisation.objects.create(name="Org A", org_code="ORG-A")
    user = User.objects.create_user(
        username="staff",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    return user


def _create_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-TP",
        title="Template Pack Cycle",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    return ReportingInstance.objects.create(cycle=cycle, version_label="v1")


def test_template_pack_runtime_endpoints(client):
    call_command("seed_mea_template_packs")
    user = _create_staff()
    instance = _create_instance()
    client.force_login(user)

    list_response = client.get(reverse("api_template_pack_list"))
    assert list_response.status_code == 200
    packs = list_response.json()["packs"]
    assert any(pack["code"] == "ramsar_v1" for pack in packs)

    section_response = client.get(reverse("api_template_pack_sections", args=["ramsar_v1"]))
    assert section_response.status_code == 200
    sections = section_response.json()["sections"]
    assert sections

    save_response = client.post(
        reverse("api_template_pack_instance_responses", args=["ramsar_v1", instance.uuid]),
        {"section_code": sections[0]["code"], "response_json": {"summary": "Wetland update"}},
        content_type="application/json",
    )
    assert save_response.status_code == 200

    get_response = client.get(
        reverse("api_template_pack_instance_responses", args=["ramsar_v1", instance.uuid]),
    )
    assert get_response.status_code == 200
    payload = get_response.json()
    first = payload["responses"][0]
    assert first["section_code"] == sections[0]["code"]
    assert first["response_json"]["summary"] == "Wetland update"

    export_response = client.get(
        reverse("api_template_pack_export", args=["ramsar_v1", instance.uuid]),
    )
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["schema"] == "nbms.mea.ramsar_v1.v1"
