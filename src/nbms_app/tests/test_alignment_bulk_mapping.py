from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nbms_app.models import (
    AlignmentRelationType,
    ApprovalDecision,
    Framework,
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    IndicatorDataSeries,
    IndicatorFrameworkIndicatorLink,
    InstanceExportApproval,
    LifecycleStatus,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SectionIIINationalTargetProgress,
    SensitivityLevel,
    User,
)
from nbms_app.services.authorization import ROLE_COMMUNITY_REPRESENTATIVE, ROLE_SECRETARIAT


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


def _create_staff_user(org, username="staff"):
    user = User.objects.create_user(
        username=username,
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=ROLE_SECRETARIAT)
    user.groups.add(group)
    return user


def _create_progress_entry(instance, target):
    return SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target,
        summary="Progress",
    )


def _approve(instance, obj):
    InstanceExportApproval.objects.create(
        reporting_instance=instance,
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_uuid=obj.uuid,
        decision=ApprovalDecision.APPROVED,
        approval_scope="export",
    )


def test_alignment_bulk_access_control(client):
    org = Organisation.objects.create(name="Org A")
    instance = _create_instance()

    user = User.objects.create_user(username="user", password="pass1234", organisation=org)
    client.force_login(user)
    resp = client.get(reverse("nbms_app:alignment_orphans_targets", args=[instance.uuid]))
    assert resp.status_code in {302, 403}

    staff = _create_staff_user(org)
    client.force_login(staff)
    resp = client.get(reverse("nbms_app:alignment_orphans_targets", args=[instance.uuid]))
    assert resp.status_code == 200


def test_alignment_bulk_target_mapping_and_duplicates(client):
    org = Organisation.objects.create(name="Org A")
    instance = _create_instance()
    staff = _create_staff_user(org)

    target = NationalTarget.objects.create(
        code="NT-1",
        title="Target",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    _create_progress_entry(instance, target)

    framework = Framework.objects.create(code="GBF", title="GBF", status=LifecycleStatus.PUBLISHED)
    framework_target = FrameworkTarget.objects.create(
        framework=framework,
        code="T1",
        title="Target 1",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )

    client.force_login(staff)
    url = reverse("nbms_app:alignment_orphans_targets", args=[instance.uuid])
    payload = {
        "national_targets": [str(target.id)],
        "framework_targets": [str(framework_target.id)],
        "relation_type": AlignmentRelationType.CONTRIBUTES_TO,
        "confidence": 80,
        "notes": "Evidence based",
        "source": "https://example.com/source",
    }
    resp = client.post(url, payload)
    assert resp.status_code == 302
    link = NationalTargetFrameworkTargetLink.objects.get()
    assert link.confidence == 80
    assert link.notes == "Evidence based"
    assert link.source == "https://example.com/source"

    resp = client.post(url, payload)
    assert resp.status_code == 302
    assert NationalTargetFrameworkTargetLink.objects.count() == 1


def test_alignment_bulk_indicator_mapping_metadata(client):
    org = Organisation.objects.create(name="Org A")
    instance = _create_instance()
    staff = _create_staff_user(org)

    target = NationalTarget.objects.create(
        code="NT-2",
        title="Target",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    entry = _create_progress_entry(instance, target)
    indicator = Indicator.objects.create(
        code="IND-1",
        title="Indicator",
        national_target=target,
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    series = IndicatorDataSeries.objects.create(
        indicator=indicator,
        title="Series",
        unit="ha",
        value_type="numeric",
        methodology="Method",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        organisation=org,
        created_by=staff,
    )
    entry.indicator_data_series.add(series)

    framework = Framework.objects.create(code="GBF", title="GBF", status=LifecycleStatus.PUBLISHED)
    framework_indicator = FrameworkIndicator.objects.create(
        framework=framework,
        code="FI-1",
        title="Indicator 1",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )

    client.force_login(staff)
    url = reverse("nbms_app:alignment_orphans_indicators", args=[instance.uuid])
    payload = {
        "indicators": [str(indicator.id)],
        "framework_indicators": [str(framework_indicator.id)],
        "relation_type": AlignmentRelationType.CONTRIBUTES_TO,
        "confidence": 70,
        "notes": "Confidence",
        "source": "https://example.com/indicator",
    }
    resp = client.post(url, payload)
    assert resp.status_code == 302
    link = IndicatorFrameworkIndicatorLink.objects.get()
    assert link.confidence == 70
    assert link.notes == "Confidence"
    assert link.source == "https://example.com/indicator"


def test_alignment_bulk_abac_tampered_post_blocked(client):
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    instance = _create_instance()
    staff = _create_staff_user(org_b, username="staffb")

    target = NationalTarget.objects.create(
        code="NT-A",
        title="Target A",
        organisation=org_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    _create_progress_entry(instance, target)

    framework = Framework.objects.create(code="GBF", title="GBF", status=LifecycleStatus.PUBLISHED)
    framework_target = FrameworkTarget.objects.create(
        framework=framework,
        code="T1",
        title="Target 1",
        organisation=org_b,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )

    client.force_login(staff)
    url = reverse("nbms_app:alignment_orphans_targets", args=[instance.uuid])
    payload = {
        "national_targets": [str(target.id)],
        "framework_targets": [str(framework_target.id)],
        "relation_type": AlignmentRelationType.CONTRIBUTES_TO,
    }
    resp = client.post(url, payload)
    assert resp.status_code == 200
    assert NationalTargetFrameworkTargetLink.objects.count() == 0


def test_alignment_bulk_hidden_framework_not_leaked(client):
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    instance = _create_instance()
    staff = _create_staff_user(org_a)

    target = NationalTarget.objects.create(
        code="NT-LEAK",
        title="Target",
        organisation=org_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    _create_progress_entry(instance, target)

    framework = Framework.objects.create(code="GBF", title="GBF", status=LifecycleStatus.PUBLISHED)
    hidden_fw_target = FrameworkTarget.objects.create(
        framework=framework,
        code="T-HIDDEN",
        title="Hidden",
        organisation=org_b,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    NationalTargetFrameworkTargetLink.objects.create(
        national_target=target,
        framework_target=hidden_fw_target,
        relation_type=AlignmentRelationType.CONTRIBUTES_TO,
    )

    client.force_login(staff)
    url = reverse("nbms_app:alignment_orphans_targets", args=[instance.uuid])
    resp = client.get(url)
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "NT-LEAK" in content
    assert "T-HIDDEN" not in content


def test_alignment_bulk_consent_blocked(client):
    org = Organisation.objects.create(name="Org A")
    instance = _create_instance()
    staff = _create_staff_user(org)
    group, _ = Group.objects.get_or_create(name=ROLE_COMMUNITY_REPRESENTATIVE)
    staff.groups.add(group)

    target = NationalTarget.objects.create(
        code="NT-IPLC",
        title="Sensitive",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.IPLC_SENSITIVE,
    )
    _create_progress_entry(instance, target)

    framework = Framework.objects.create(code="GBF", title="GBF", status=LifecycleStatus.PUBLISHED)
    framework_target = FrameworkTarget.objects.create(
        framework=framework,
        code="T1",
        title="Target 1",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )

    client.force_login(staff)
    url = reverse("nbms_app:alignment_orphans_targets", args=[instance.uuid])
    payload = {
        "national_targets": [str(target.id)],
        "framework_targets": [str(framework_target.id)],
        "relation_type": AlignmentRelationType.CONTRIBUTES_TO,
    }
    resp = client.post(url, payload)
    assert resp.status_code == 200
    assert NationalTargetFrameworkTargetLink.objects.count() == 0


def test_alignment_bulk_ordering_lexicographic(client):
    org = Organisation.objects.create(name="Org A")
    instance = _create_instance()
    staff = _create_staff_user(org)

    targets = []
    for code in ["T1", "T10", "T2"]:
        target = NationalTarget.objects.create(
            code=code,
            title=f"Target {code}",
            organisation=org,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        _create_progress_entry(instance, target)
        targets.append(target)

    framework = Framework.objects.create(code="GBF", title="GBF", status=LifecycleStatus.PUBLISHED)
    for code in ["F1", "F10", "F2"]:
        FrameworkTarget.objects.create(
            framework=framework,
            code=code,
            title=f"Framework {code}",
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )

    client.force_login(staff)
    url = reverse("nbms_app:alignment_orphans_targets", args=[instance.uuid])
    resp = client.get(url)
    content = resp.content.decode()
    first = content.find("T1")
    second = content.find("T10")
    third = content.find("T2")
    assert 0 <= first < second < third

    f_first = content.find("F1")
    f_second = content.find("F10")
    f_third = content.find("F2")
    assert 0 <= f_first < f_second < f_third
