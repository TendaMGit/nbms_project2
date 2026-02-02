import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from nbms_app.models import Organisation, ReportingCycle, ReportingInstance, User, SectionIReportContext
from nbms_app.services.authorization import ROLE_DATA_STEWARD


pytestmark = pytest.mark.django_db


def _create_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-I",
        title="Cycle I",
        start_date="2025-01-01",
        end_date="2025-12-31",
        due_date="2026-01-31",
        is_active=True,
    )
    return ReportingInstance.objects.create(cycle=cycle)


def _create_staff_user(org, username="staff-i"):
    user = User.objects.create_user(
        username=username,
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=ROLE_DATA_STEWARD)
    user.groups.add(group)
    return user


def test_section_i_access_and_freeze(client):
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org)
    instance = _create_instance()

    client.force_login(user)
    resp = client.get(reverse("nbms_app:reporting_instance_section_i", args=[instance.uuid]))
    assert resp.status_code == 200

    instance.frozen_at = timezone.now()
    instance.save(update_fields=["frozen_at"])
    resp = client.post(
        reverse("nbms_app:reporting_instance_section_i", args=[instance.uuid]),
        data={"reporting_party_name": "South Africa", "submission_language": "English"},
    )
    assert resp.status_code == 403
    assert SectionIReportContext.objects.filter(reporting_instance=instance).count() == 0


def test_section_i_requires_staff(client):
    org = Organisation.objects.create(name="Org A")
    user = User.objects.create_user(
        username="nonstaff-i",
        password="pass1234",
        organisation=org,
        is_staff=False,
    )
    instance = _create_instance()

    client.force_login(user)
    resp = client.get(reverse("nbms_app:reporting_instance_section_i", args=[instance.uuid]))
    assert resp.status_code in (302, 403)
