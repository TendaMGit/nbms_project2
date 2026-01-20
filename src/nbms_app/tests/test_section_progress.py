from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from nbms_app.models import (
    Framework,
    FrameworkTarget,
    LifecycleStatus,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SectionIIINationalTargetProgress,
    SectionIVFrameworkTargetProgress,
    SensitivityLevel,
    User,
)
from nbms_app.services.instance_approvals import approve_for_instance
from nbms_app.services.readiness import get_instance_readiness
from nbms_app.services.section_progress import scoped_framework_targets, scoped_national_targets
from nbms_app.services.authorization import ROLE_DATA_STEWARD


pytestmark = pytest.mark.django_db


def _create_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-III-IV",
        title="Cycle III/IV",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
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


def test_section_iii_progress_unique_per_instance_target():
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org, "staff-a")
    instance = _create_instance()
    target = NationalTarget.objects.create(
        code="NT-1",
        title="Target 1",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )

    SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SectionIIINationalTargetProgress.objects.create(
                reporting_instance=instance,
                national_target=target,
            )


def test_section_iv_progress_unique_per_instance_target():
    framework = Framework.objects.create(code="GBF", title="GBF")
    framework_target = FrameworkTarget.objects.create(
        framework=framework,
        code="T1",
        title="Target 1",
    )
    instance = _create_instance()

    SectionIVFrameworkTargetProgress.objects.create(
        reporting_instance=instance,
        framework_target=framework_target,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SectionIVFrameworkTargetProgress.objects.create(
                reporting_instance=instance,
                framework_target=framework_target,
            )


def test_freeze_blocks_post_edit(client):
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org, "staff-a")
    instance = _create_instance()
    target = NationalTarget.objects.create(
        code="NT-FREEZE",
        title="Frozen target",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    approve_for_instance(instance, target, user)
    instance.frozen_at = timezone.now()
    instance.save(update_fields=["frozen_at"])

    client.force_login(user)
    resp = client.post(
        reverse("nbms_app:reporting_instance_section_iii_edit", args=[instance.uuid, target.uuid]),
        data={"summary": "Should not save"},
    )
    assert resp.status_code == 403
    assert SectionIIINationalTargetProgress.objects.filter(
        reporting_instance=instance,
        national_target=target,
    ).count() == 0


def test_out_of_scope_target_rejected_on_create_and_edit(client):
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org, "staff-a")
    instance = _create_instance()
    target_in_scope = NationalTarget.objects.create(
        code="NT-IN",
        title="In scope",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    target_out = NationalTarget.objects.create(
        code="NT-OUT",
        title="Out of scope",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    approve_for_instance(instance, target_in_scope, user)

    client.force_login(user)
    resp = client.get(
        reverse("nbms_app:reporting_instance_section_iii_edit", args=[instance.uuid, target_out.uuid])
    )
    assert resp.status_code == 404
    resp = client.post(
        reverse("nbms_app:reporting_instance_section_iii_edit", args=[instance.uuid, target_out.uuid]),
        data={"summary": "Should not save"},
    )
    assert resp.status_code == 404


def test_cross_org_no_leak_on_list_and_detail(client):
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    staff_a = _create_staff_user(org_a, "staff-a")
    staff_b = _create_staff_user(org_b, "staff-b")
    instance = _create_instance()
    target = NationalTarget.objects.create(
        code="NT-A",
        title="Target A",
        organisation=org_a,
        created_by=staff_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    approve_for_instance(instance, target, staff_a)

    client.force_login(staff_b)
    resp = client.get(reverse("nbms_app:reporting_instance_section_iii", args=[instance.uuid]))
    assert resp.status_code == 403
    resp = client.get(
        reverse("nbms_app:reporting_instance_section_iii_edit", args=[instance.uuid, target.uuid])
    )
    assert resp.status_code == 403


def test_progress_reference_abac_no_leak():
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    staff_a = _create_staff_user(org_a, "staff-a")
    user_b = User.objects.create_user(
        username="user-b",
        password="pass1234",
        organisation=org_b,
    )
    instance = _create_instance()
    target = NationalTarget.objects.create(
        code="NT-PRIVATE",
        title="Private target",
        organisation=org_a,
        created_by=staff_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    approve_for_instance(instance, target, staff_a)

    framework = Framework.objects.create(code="GBF", title="GBF")
    framework_target = FrameworkTarget.objects.create(
        framework=framework,
        code="T2",
        title="Target 2",
    )
    NationalTargetFrameworkTargetLink.objects.create(
        national_target=target,
        framework_target=framework_target,
    )

    assert target in scoped_national_targets(instance, staff_a)
    assert framework_target in scoped_framework_targets(instance, staff_a)

    assert target not in scoped_national_targets(instance, user_b)
    assert framework_target not in scoped_framework_targets(instance, user_b)


def test_readiness_requires_progress_entries_for_scoped_targets():
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org, "staff-a")
    instance = _create_instance()
    call_command("seed_validation_rules")

    target = NationalTarget.objects.create(
        code="NT-READY",
        title="Ready target",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    approve_for_instance(instance, target, user)

    framework = Framework.objects.create(code="GBF", title="GBF")
    framework_target = FrameworkTarget.objects.create(
        framework=framework,
        code="T3",
        title="Target 3",
    )
    NationalTargetFrameworkTargetLink.objects.create(
        national_target=target,
        framework_target=framework_target,
    )

    readiness = get_instance_readiness(instance, user)
    assert readiness["details"]["progress"]["section_iii_missing"] == 1
    assert readiness["details"]["progress"]["section_iv_missing"] == 1

    SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target,
        summary="Progress summary",
    )
    SectionIVFrameworkTargetProgress.objects.create(
        reporting_instance=instance,
        framework_target=framework_target,
        summary="Framework progress summary",
    )

    readiness = get_instance_readiness(instance, user)
    assert readiness["details"]["progress"]["section_iii_missing"] == 0
    assert readiness["details"]["progress"]["section_iv_missing"] == 0
