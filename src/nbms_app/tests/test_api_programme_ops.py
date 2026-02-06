import json

import pytest
from django.urls import reverse

from nbms_app.models import (
    MonitoringProgramme,
    MonitoringProgrammeRun,
    MonitoringProgrammeSteward,
    Organisation,
    ProgrammeRunStatus,
    ProgrammeStewardRole,
    SensitivityClass,
    User,
)


pytestmark = pytest.mark.django_db


def _make_programme(*, code, lead_org, title="Programme", sensitivity=None, is_active=True, rules=None):
    return MonitoringProgramme.objects.create(
        programme_code=code,
        title=title,
        lead_org=lead_org,
        sensitivity_class=sensitivity,
        is_active=is_active,
        refresh_cadence="manual",
        scheduler_enabled=False,
        pipeline_definition_json={
            "steps": [
                {"key": "ingest", "type": "ingest"},
                {"key": "validate", "type": "validate"},
            ]
        },
        data_quality_rules_json=rules or {"minimum_dataset_links": 0, "minimum_indicator_links": 0},
    )


def test_programme_list_requires_authentication(client):
    response = client.get(reverse("api_programme_list"))
    assert response.status_code in {401, 403}


def test_programme_list_and_detail_apply_abac_no_leak(client):
    public_sensitivity = SensitivityClass.objects.create(
        sensitivity_code="PUB",
        sensitivity_name="Public",
        access_level_default="public",
        consent_required_default=False,
        is_active=True,
    )
    internal_sensitivity = SensitivityClass.objects.create(
        sensitivity_code="INT",
        sensitivity_name="Internal",
        access_level_default="internal",
        consent_required_default=False,
        is_active=True,
    )
    org_a = Organisation.objects.create(name="Org A", org_code="ORG-A")
    org_b = Organisation.objects.create(name="Org B", org_code="ORG-B")
    org_c = Organisation.objects.create(name="Org C", org_code="ORG-C")
    public_programme = _make_programme(
        code="PROG-PUBLIC",
        title="Public Programme",
        lead_org=org_a,
        sensitivity=public_sensitivity,
    )
    restricted_programme = _make_programme(
        code="PROG-INT",
        title="Internal Programme",
        lead_org=org_b,
        sensitivity=internal_sensitivity,
    )

    user = User.objects.create_user(username="viewer", password="pass12345", organisation=org_c)
    assert client.login(username="viewer", password="pass12345")

    list_response = client.get(reverse("api_programme_list"))
    assert list_response.status_code == 200
    codes = [item["programme_code"] for item in list_response.json()["programmes"]]
    assert "PROG-PUBLIC" in codes
    assert "PROG-INT" not in codes

    detail_response = client.get(reverse("api_programme_detail", args=[restricted_programme.uuid]))
    assert detail_response.status_code == 404

    public_detail = client.get(reverse("api_programme_detail", args=[public_programme.uuid]))
    assert public_detail.status_code == 200
    assert public_detail.json()["programme"]["programme_code"] == "PROG-PUBLIC"


def test_programme_run_create_allows_steward_assignment(client):
    org_lead = Organisation.objects.create(name="Lead Org", org_code="LEAD")
    org_other = Organisation.objects.create(name="Other Org", org_code="OTHER")
    programme = _make_programme(code="PROG-RUN", lead_org=org_lead, rules={"minimum_dataset_links": 0, "minimum_indicator_links": 0})
    user = User.objects.create_user(username="operator", password="pass12345", organisation=org_other)
    MonitoringProgrammeSteward.objects.create(
        programme=programme,
        user=user,
        role=ProgrammeStewardRole.OPERATOR,
        is_active=True,
    )
    assert client.login(username="operator", password="pass12345")

    response = client.post(
        reverse("api_programme_run_create", args=[programme.uuid]),
        data=json.dumps({"run_type": "full", "dry_run": True, "execute_now": True}),
        content_type="application/json",
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["run_type"] == "full"
    assert payload["status"] in {ProgrammeRunStatus.SUCCEEDED, ProgrammeRunStatus.BLOCKED}
    run = MonitoringProgrammeRun.objects.get(uuid=payload["uuid"])
    assert run.requested_by == user


def test_programme_run_create_forbidden_for_read_only_user(client):
    public_sensitivity = SensitivityClass.objects.create(
        sensitivity_code="PUB2",
        sensitivity_name="Public 2",
        access_level_default="public",
        consent_required_default=False,
        is_active=True,
    )
    org_owner = Organisation.objects.create(name="Owner Org", org_code="OWN")
    org_viewer = Organisation.objects.create(name="Viewer Org", org_code="VIEW")
    programme = _make_programme(code="PROG-RO", lead_org=org_owner, sensitivity=public_sensitivity)
    user = User.objects.create_user(username="readonly", password="pass12345", organisation=org_viewer)
    assert client.login(username="readonly", password="pass12345")

    response = client.post(
        reverse("api_programme_run_create", args=[programme.uuid]),
        data=json.dumps({"run_type": "full"}),
        content_type="application/json",
    )
    assert response.status_code == 403


def test_programme_run_rerun_endpoint_executes_again(client):
    org = Organisation.objects.create(name="Run Org", org_code="RUN")
    programme = _make_programme(code="PROG-RERUN", lead_org=org, rules={"minimum_dataset_links": 0, "minimum_indicator_links": 0})
    user = User.objects.create_user(username="runner", password="pass12345", organisation=org)
    assert client.login(username="runner", password="pass12345")

    create_response = client.post(
        reverse("api_programme_run_create", args=[programme.uuid]),
        data=json.dumps({"run_type": "ingest", "execute_now": False}),
        content_type="application/json",
    )
    assert create_response.status_code == 201
    run_uuid = create_response.json()["uuid"]
    run = MonitoringProgrammeRun.objects.get(uuid=run_uuid)
    assert run.status == ProgrammeRunStatus.QUEUED

    rerun_response = client.post(
        reverse("api_programme_run_detail", args=[run.uuid]),
        data=json.dumps({}),
        content_type="application/json",
    )
    assert rerun_response.status_code == 200
    run.refresh_from_db()
    assert run.status in {ProgrammeRunStatus.SUCCEEDED, ProgrammeRunStatus.BLOCKED}
