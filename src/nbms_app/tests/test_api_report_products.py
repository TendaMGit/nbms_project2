from datetime import date

import pytest
from django.core.management import call_command
from django.urls import reverse

from nbms_app.models import Organisation, ReportingCycle, ReportingInstance, User


pytestmark = pytest.mark.django_db


def _create_staff():
    org = Organisation.objects.create(name="Org Report", org_code="ORG-REPORT")
    return User.objects.create_user(
        username="report_staff",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )


def _create_instance():
    cycle = ReportingCycle.objects.create(
        code="REPORT-PRODUCT-CYCLE",
        title="Report Product Cycle",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    return ReportingInstance.objects.create(cycle=cycle, version_label="v1")


def test_report_product_endpoints(client):
    call_command("seed_report_products")
    call_command("seed_indicator_workflow_v1")
    user = _create_staff()
    instance = _create_instance()
    client.force_login(user)

    list_response = client.get(reverse("api_report_product_list"))
    assert list_response.status_code == 200
    items = list_response.json()["report_products"]
    assert {item["code"] for item in items} >= {"nba_v1", "gmo_v1", "invasive_v1"}

    preview_response = client.get(
        reverse("api_report_product_preview", args=["nba_v1"]),
        {"instance_uuid": str(instance.uuid)},
    )
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["template"]["code"] == "nba_v1"
    assert preview_payload["payload"]["schema"] == "nbms.report_product.nba_v1.v1"
    assert preview_payload["run_uuid"]

    html_response = client.get(
        reverse("api_report_product_html", args=["nba_v1"]),
        {"instance_uuid": str(instance.uuid)},
    )
    assert html_response.status_code == 200
    assert "text/html" in html_response["Content-Type"]

    pdf_response = client.get(
        reverse("api_report_product_pdf", args=["nba_v1"]),
        {"instance_uuid": str(instance.uuid)},
    )
    assert pdf_response.status_code == 200
    assert pdf_response["Content-Type"] == "application/pdf"
    assert len(pdf_response.content) > 100

    runs_response = client.get(reverse("api_report_product_runs"))
    assert runs_response.status_code == 200
    assert runs_response.json()["runs"]
