import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from nbms_app.models import Organisation, ReportingCycle, ReportingInstance, User
from nbms_app.services.authorization import ROLE_DATA_STEWARD


pytestmark = pytest.mark.django_db


def _create_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-II",
        title="Cycle II",
        start_date="2025-01-01",
        end_date="2025-12-31",
        due_date="2026-01-31",
        is_active=True,
    )
    return ReportingInstance.objects.create(cycle=cycle)


def _create_staff_user(org, username="staff-ii"):
    user = User.objects.create_user(
        username=username,
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=ROLE_DATA_STEWARD)
    user.groups.add(group)
    return user


def test_section_ii_requires_completion_date_when_no(client):
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org)
    instance = _create_instance()

    client.force_login(user)
    resp = client.post(
        reverse("nbms_app:reporting_instance_section_ii", args=[instance.uuid]),
        data={
            "nbsap_updated_status": "no",
            "stakeholders_involved": "no",
            "nbsap_adopted_status": "no",
            "nbsap_adopted_other_text": "Not adopted",
            "nbsap_expected_adoption_date": "2026-12-31",
            "monitoring_system_description": "Monitoring system",
        },
    )
    assert resp.status_code == 200
    assert "nbsap_expected_completion_date" in resp.context["form"].errors


def test_section_ii_requires_stakeholder_other_text(client):
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org)
    instance = _create_instance()

    client.force_login(user)
    resp = client.post(
        reverse("nbms_app:reporting_instance_section_ii", args=[instance.uuid]),
        data={
            "nbsap_updated_status": "yes",
            "stakeholders_involved": "yes",
            "stakeholder_groups": ["other"],
            "stakeholder_groups_other_text": "",
            "nbsap_adopted_status": "no",
            "nbsap_adopted_other_text": "Not adopted",
            "nbsap_expected_adoption_date": "2026-12-31",
            "monitoring_system_description": "Monitoring system",
        },
    )
    assert resp.status_code == 200
    assert "stakeholder_groups_other_text" in resp.context["form"].errors


def test_section_ii_requires_adoption_specify_when_other(client):
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org)
    instance = _create_instance()

    client.force_login(user)
    resp = client.post(
        reverse("nbms_app:reporting_instance_section_ii", args=[instance.uuid]),
        data={
            "nbsap_updated_status": "yes",
            "stakeholders_involved": "no",
            "nbsap_adopted_status": "other",
            "nbsap_expected_adoption_date": "",
            "monitoring_system_description": "Monitoring system",
        },
    )
    assert resp.status_code == 200
    assert "nbsap_adopted_other_text" in resp.context["form"].errors
    assert "nbsap_expected_adoption_date" in resp.context["form"].errors
