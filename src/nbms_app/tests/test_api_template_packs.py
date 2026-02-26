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
    section_codes = [item["code"] for item in sections]
    assert section_codes == [
        "section_1_institutional",
        "section_2_narrative",
        "section_3_implementation_indicators",
        "section_4_annex_targets",
    ]

    save_response = client.post(
        reverse("api_template_pack_instance_responses", args=["ramsar_v1", instance.uuid]),
        {
            "section_code": sections[0]["code"],
            "response_json": {
                "reporting_party": "South Africa",
                "administrative_authority": "DFFE",
                "national_focal_point_name": "Jane Doe",
                "national_focal_point_email": "jane@example.org",
            },
        },
        content_type="application/json",
    )
    assert save_response.status_code == 200

    section_three = next(item for item in sections if item["code"] == "section_3_implementation_indicators")
    questions = section_three["schema_json"]["fields"][0]["question_catalog"]
    questionnaire_response = [
        {
            "question_code": row["code"],
            "question_title": row["title"],
            "response": "partial",
            "notes": "Seeded for API test",
            "linked_indicator_codes": ["GBF-H-A1-ZA"],
            "linked_programme_codes": ["NBMS-CORE-PROGRAMME"],
            "linked_evidence_uuids": [],
        }
        for row in questions
    ]
    save_questionnaire = client.post(
        reverse("api_template_pack_instance_responses", args=["ramsar_v1", instance.uuid]),
        {
            "section_code": "section_3_implementation_indicators",
            "response_json": {"implementation_questions": questionnaire_response},
        },
        content_type="application/json",
    )
    assert save_questionnaire.status_code == 200

    get_response = client.get(
        reverse("api_template_pack_instance_responses", args=["ramsar_v1", instance.uuid]),
    )
    assert get_response.status_code == 200
    payload = get_response.json()
    first = payload["responses"][0]
    assert first["section_code"] == sections[0]["code"]
    assert first["response_json"]["reporting_party"] == "South Africa"

    validation_response = client.get(
        reverse("api_template_pack_validate", args=["ramsar_v1", instance.uuid]),
    )
    assert validation_response.status_code == 200
    validation_payload = validation_response.json()
    assert validation_payload["pack_code"] == "ramsar_v1"
    assert isinstance(validation_payload["qa_items"], list)

    pdf_response = client.get(
        reverse("api_template_pack_pdf", args=["ramsar_v1", instance.uuid]),
    )
    assert pdf_response.status_code == 200
    assert pdf_response["Content-Type"] == "application/pdf"
    assert len(pdf_response.content) > 100

    export_response = client.get(
        reverse("api_template_pack_export", args=["ramsar_v1", instance.uuid]),
    )
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["schema"] == "nbms.mea.ramsar_v1.v1"
    implementation = next(
        item for item in export_payload["sections"] if item["code"] == "section_3_implementation_indicators"
    )
    assert implementation["response"]["implementation_questions"][0]["response"] == "partial"
