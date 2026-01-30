import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType

from nbms_app.models import (
    ApprovalDecision,
    ConsentRecord,
    ConsentStatus,
    Framework,
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    IndicatorFrameworkIndicatorLink,
    InstanceExportApproval,
    LifecycleStatus,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
)
from nbms_app.services.alignment_coverage import compute_alignment_coverage
from nbms_app.services.authorization import ROLE_COMMUNITY_REPRESENTATIVE


pytestmark = pytest.mark.django_db


def _create_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-1",
        title="Cycle 1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    instance = ReportingInstance.objects.create(cycle=cycle, version_label="v1")
    return instance


def _approve(instance, obj):
    InstanceExportApproval.objects.create(
        reporting_instance=instance,
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_uuid=obj.uuid,
        decision=ApprovalDecision.APPROVED,
        approval_scope="export",
    )


def test_alignment_coverage_deterministic_ordering():
    org = Organisation.objects.create(name="Org A")
    user = User.objects.create_user(username="user", password="pass1234", organisation=org)
    instance = _create_instance()

    target_b = NationalTarget.objects.create(
        code="B",
        title="Target B",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    target_a = NationalTarget.objects.create(
        code="A",
        title="Target A",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    indicator_b = Indicator.objects.create(
        code="IND-2",
        title="Indicator B",
        national_target=target_b,
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    indicator_a = Indicator.objects.create(
        code="IND-1",
        title="Indicator A",
        national_target=target_a,
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )

    _approve(instance, target_a)
    _approve(instance, target_b)
    _approve(instance, indicator_a)
    _approve(instance, indicator_b)

    fw_a = Framework.objects.create(code="GBF", title="GBF", status=LifecycleStatus.PUBLISHED)
    fw_b = Framework.objects.create(code="SDG", title="SDG", status=LifecycleStatus.PUBLISHED)
    fw_target_b = FrameworkTarget.objects.create(
        framework=fw_b,
        code="T2",
        title="Target 2",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    fw_target_a = FrameworkTarget.objects.create(
        framework=fw_a,
        code="T1",
        title="Target 1",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    link_a = NationalTargetFrameworkTargetLink.objects.create(
        national_target=target_a,
        framework_target=fw_target_b,
    )
    link_b = NationalTargetFrameworkTargetLink.objects.create(
        national_target=target_a,
        framework_target=fw_target_a,
    )

    fw_indicator_a = FrameworkIndicator.objects.create(
        framework=fw_a,
        code="FI-1",
        title="Framework Indicator 1",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    IndicatorFrameworkIndicatorLink.objects.create(
        indicator=indicator_a,
        framework_indicator=fw_indicator_a,
    )

    coverage = compute_alignment_coverage(user=user, instance=instance, scope="selected")
    targets = coverage["coverage_details"]["national_targets"]
    assert [item["code"] for item in targets] == ["A", "B"]

    linked = targets[0]["linked_framework_targets"]
    assert [(item["framework_code"], item["code"]) for item in linked] == [
        ("GBF", "T1"),
        ("SDG", "T2"),
    ]


def test_alignment_coverage_abac_excludes_other_org():
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    user_b = User.objects.create_user(username="userb", password="pass1234", organisation=org_b)
    instance = _create_instance()

    public_target = NationalTarget.objects.create(
        code="PUB",
        title="Public",
        organisation=org_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    internal_target = NationalTarget.objects.create(
        code="INT",
        title="Internal",
        organisation=org_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    _approve(instance, public_target)
    _approve(instance, internal_target)

    coverage = compute_alignment_coverage(user=user_b, instance=instance, scope="selected")
    assert coverage["summary"]["national_targets"]["total"] == 1
    assert coverage["summary"]["national_targets"]["unmapped"] == 1
    assert coverage["orphans"]["national_targets_unmapped"][0]["code"] == "PUB"


def test_alignment_coverage_consent_filter():
    org = Organisation.objects.create(name="Org A")
    user = User.objects.create_user(username="user", password="pass1234", organisation=org)
    user.groups.add(Group.objects.create(name=ROLE_COMMUNITY_REPRESENTATIVE))
    instance = _create_instance()

    sensitive_target = NationalTarget.objects.create(
        code="IPLC",
        title="Sensitive",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.IPLC_SENSITIVE,
    )
    _approve(instance, sensitive_target)

    coverage = compute_alignment_coverage(user=user, instance=instance, scope="selected")
    assert coverage["summary"]["national_targets"]["total"] == 0

    ConsentRecord.objects.create(
        reporting_instance=instance,
        content_type=ContentType.objects.get_for_model(NationalTarget),
        object_uuid=sensitive_target.uuid,
        status=ConsentStatus.GRANTED,
    )
    coverage = compute_alignment_coverage(user=user, instance=instance, scope="selected")
    assert coverage["summary"]["national_targets"]["total"] == 1


def test_alignment_coverage_scope_selected_vs_all():
    org = Organisation.objects.create(name="Org A")
    user = User.objects.create_user(username="user", password="pass1234", organisation=org)
    instance = _create_instance()

    approved_target = NationalTarget.objects.create(
        code="APP",
        title="Approved",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    unapproved_target = NationalTarget.objects.create(
        code="ALL",
        title="All",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    _approve(instance, approved_target)

    selected = compute_alignment_coverage(user=user, instance=instance, scope="selected")
    all_scope = compute_alignment_coverage(user=user, instance=instance, scope="all")

    assert selected["summary"]["national_targets"]["total"] == 1
    assert all_scope["summary"]["national_targets"]["total"] == 2


def test_alignment_coverage_framework_breakdown():
    org = Organisation.objects.create(name="Org A")
    user = User.objects.create_user(username="user", password="pass1234", organisation=org)
    instance = _create_instance()

    target = NationalTarget.objects.create(
        code="NT-1",
        title="Target",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    indicator = Indicator.objects.create(
        code="IND-1",
        title="Indicator",
        national_target=target,
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    _approve(instance, target)
    _approve(instance, indicator)

    fw = Framework.objects.create(code="GBF", title="GBF", status=LifecycleStatus.PUBLISHED)
    fw_target = FrameworkTarget.objects.create(
        framework=fw,
        code="T1",
        title="Target 1",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    fw_indicator = FrameworkIndicator.objects.create(
        framework=fw,
        code="FI-1",
        title="Framework Indicator",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )

    NationalTargetFrameworkTargetLink.objects.create(
        national_target=target,
        framework_target=fw_target,
    )
    IndicatorFrameworkIndicatorLink.objects.create(
        indicator=indicator,
        framework_indicator=fw_indicator,
    )

    coverage = compute_alignment_coverage(user=user, instance=instance, scope="selected")
    by_framework = coverage["by_framework"]
    assert len(by_framework) == 1
    assert by_framework[0]["framework_code"] == "GBF"
    assert by_framework[0]["targets"]["mapped_links"] == 1
    assert by_framework[0]["targets"]["distinct_framework_targets_used"] == 1
    assert by_framework[0]["indicators"]["mapped_links"] == 1
    assert by_framework[0]["indicators"]["distinct_framework_indicators_used"] == 1
