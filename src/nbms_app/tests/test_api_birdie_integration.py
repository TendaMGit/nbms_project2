from datetime import date

import pytest
from django.core.management import call_command
from django.urls import reverse

from nbms_app.models import IntegrationDataAsset, Organisation, ReportingCycle, ReportingInstance, User


pytestmark = pytest.mark.django_db


def _create_staff():
    org, _ = Organisation.objects.get_or_create(name="South African National Biodiversity Institute", org_code="SANBI")
    return User.objects.create_user(
        username="birdie_staff",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )


def _create_instance():
    cycle = ReportingCycle.objects.create(
        code="BIRDIE-CYCLE",
        title="Birdie Cycle",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    return ReportingInstance.objects.create(cycle=cycle, version_label="v1")


def test_birdie_seed_and_dashboard_api(client):
    call_command("seed_programme_ops_v1")
    call_command("seed_birdie_integration")
    user = _create_staff()
    _create_instance()
    client.force_login(user)

    response = client.get(reverse("api_birdie_dashboard"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["programme"]["programme_code"] == "NBMS-BIRDIE-INTEGRATION"
    assert payload["site_reports"]
    assert payload["species_reports"]
    assert payload["map_layers"]
    assert payload["provenance"]

    bronze_assets = IntegrationDataAsset.objects.filter(source_system="BIRDIE", layer="bronze")
    assert bronze_assets.count() >= 3


def test_birdie_dashboard_requires_auth(client):
    response = client.get(reverse("api_birdie_dashboard"))
    assert response.status_code in {401, 403}
