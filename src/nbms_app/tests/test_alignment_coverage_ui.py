from datetime import date

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nbms_app.models import (
    ApprovalDecision,
    Framework,
    FrameworkTarget,
    InstanceExportApproval,
    LifecycleStatus,
    NationalTarget,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
)


pytestmark = pytest.mark.django_db


def _create_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-1",
        title="Cycle 1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    return ReportingInstance.objects.create(cycle=cycle, version_label="v1")


def _approve(instance, obj):
    InstanceExportApproval.objects.create(
        reporting_instance=instance,
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_uuid=obj.uuid,
        decision=ApprovalDecision.APPROVED,
        approval_scope="export",
    )


def test_alignment_coverage_access_control(client):
    org = Organisation.objects.create(name="Org A")
    instance = _create_instance()

    user = User.objects.create_user(username="user", password="pass1234", organisation=org)
    client.force_login(user)
    resp = client.get(reverse("nbms_app:reporting_instance_review", args=[instance.uuid]))
    assert resp.status_code in {302, 403}
    resp = client.get(reverse("nbms_app:reporting_instance_alignment_coverage", args=[instance.uuid]))
    assert resp.status_code in {302, 403}

    staff = User.objects.create_user(
        username="staff",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    client.force_login(staff)
    resp = client.get(reverse("nbms_app:reporting_instance_review", args=[instance.uuid]))
    assert resp.status_code == 200
    resp = client.get(reverse("nbms_app:reporting_instance_alignment_coverage", args=[instance.uuid]))
    assert resp.status_code == 200


def test_alignment_coverage_panel_zero_selected(client):
    org = Organisation.objects.create(name="Org A")
    staff = User.objects.create_user(
        username="staff",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    instance = _create_instance()

    client.force_login(staff)
    resp = client.get(reverse("nbms_app:reporting_instance_review", args=[instance.uuid]))
    assert resp.status_code == 200
    assert "Alignment coverage" in resp.content.decode()
    assert "No selected items yet" in resp.content.decode()


def test_alignment_coverage_view_all_lists_orphans(client):
    org = Organisation.objects.create(name="Org A")
    staff = User.objects.create_user(
        username="staff",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    instance = _create_instance()

    target = NationalTarget.objects.create(
        code="NT-1",
        title="Target",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    _approve(instance, target)

    client.force_login(staff)
    resp = client.get(reverse("nbms_app:reporting_instance_alignment_coverage", args=[instance.uuid]))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "National targets unmapped" in content
    assert "NT-1" in content


def test_alignment_coverage_no_hidden_link_leak(client):
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    staff = User.objects.create_user(
        username="staff",
        password="pass1234",
        organisation=org_a,
        is_staff=True,
    )
    instance = _create_instance()

    target = NationalTarget.objects.create(
        code="NT-1",
        title="Target",
        organisation=org_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    _approve(instance, target)

    framework = Framework.objects.create(code="GBF", title="GBF", status=LifecycleStatus.PUBLISHED)
    hidden_fw_target = FrameworkTarget.objects.create(
        framework=framework,
        code="T-HIDDEN",
        title="Hidden",
        organisation=org_b,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    target.framework_target_links.create(framework_target=hidden_fw_target)

    client.force_login(staff)
    resp = client.get(reverse("nbms_app:reporting_instance_alignment_coverage", args=[instance.uuid]))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "NT-1" in content
    assert "T-HIDDEN" not in content
