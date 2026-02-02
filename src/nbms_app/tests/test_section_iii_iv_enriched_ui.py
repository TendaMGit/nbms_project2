import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from nbms_app.models import (
    Framework,
    FrameworkTarget,
    LifecycleStatus,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
    SectionIIINationalTargetProgress,
    SectionIVFrameworkTargetProgress,
)
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from nbms_app.services.instance_approvals import approve_for_instance


pytestmark = pytest.mark.django_db


def _create_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-III-IV-UI",
        title="Cycle III/IV UI",
        start_date="2025-01-01",
        end_date="2025-12-31",
        due_date="2026-01-31",
        is_active=True,
    )
    return ReportingInstance.objects.create(cycle=cycle)


def _create_staff_user(org, username):
    user = User.objects.create_user(
        username=username,
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=ROLE_DATA_STEWARD)
    user.groups.add(group)
    return user


def test_section_iii_enriched_fields_persist(client):
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org, "staff-iii")
    instance = _create_instance()
    target = NationalTarget.objects.create(
        code="NT-1",
        title="Target 1",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    approve_for_instance(instance, target, user)

    client.force_login(user)
    resp = client.post(
        reverse("nbms_app:reporting_instance_section_iii_edit", args=[instance.uuid, target.uuid]),
        data={
            "progress_status": "in_progress",
            "progress_level": "on_track",
            "summary": "Progress summary",
            "actions_taken": "Actions",
            "outcomes": "Outcomes",
            "challenges_and_approaches": "Challenges",
            "effectiveness_examples": "Examples",
            "sdg_and_other_agreements": "SDGs",
            "support_needed": "Support",
        },
    )
    assert resp.status_code == 302
    entry = SectionIIINationalTargetProgress.objects.get(reporting_instance=instance, national_target=target)
    assert entry.progress_level == "on_track"
    assert entry.challenges_and_approaches == "Challenges"


def test_section_iv_enriched_fields_persist(client):
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org, "staff-iv")
    instance = _create_instance()

    target = NationalTarget.objects.create(
        code="NT-2",
        title="Target 2",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    approve_for_instance(instance, target, user)

    framework = Framework.objects.create(code="GBF", title="GBF")
    framework_target = FrameworkTarget.objects.create(
        framework=framework,
        code="T-2",
        title="Framework Target 2",
    )
    NationalTargetFrameworkTargetLink.objects.create(
        national_target=target,
        framework_target=framework_target,
    )

    client.force_login(user)
    resp = client.post(
        reverse("nbms_app:reporting_instance_section_iv_edit", args=[instance.uuid, framework_target.uuid]),
        data={
            "progress_status": "in_progress",
            "progress_level": "on_track",
            "summary": "Progress summary",
            "actions_taken": "Actions",
            "outcomes": "Outcomes",
            "challenges_and_approaches": "Challenges",
            "effectiveness_examples": "Examples",
            "sdg_and_other_agreements": "SDGs",
            "support_needed": "Support",
        },
    )
    assert resp.status_code == 302
    entry = SectionIVFrameworkTargetProgress.objects.get(reporting_instance=instance, framework_target=framework_target)
    assert entry.progress_level == "on_track"
    assert entry.challenges_and_approaches == "Challenges"
