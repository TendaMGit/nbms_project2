import pytest
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

from nbms_app.models import (
    ConsentRecord,
    ConsentStatus,
    Dataset,
    DatasetRelease,
    Framework,
    FrameworkIndicator,
    FrameworkIndicatorType,
    FrameworkTarget,
    Indicator,
    IndicatorDataSeries,
    IndicatorDatasetLink,
    IndicatorFrameworkIndicatorLink,
    LifecycleStatus,
    NationalTarget,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
)
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from nbms_app.services.hl21_1 import compute_hl21_1_gap_analysis


pytestmark = pytest.mark.django_db


def _create_staff_user(org, username="staff-hl21"):
    user = User.objects.create_user(
        username=username,
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=ROLE_DATA_STEWARD)
    user.groups.add(group)
    return user


def _create_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-HL21",
        title="Cycle HL21",
        start_date="2025-01-01",
        end_date="2025-12-31",
        due_date="2026-01-31",
        is_active=True,
    )
    return ReportingInstance.objects.create(cycle=cycle)


def _create_framework():
    return Framework.objects.create(code="GBF", title="GBF", status=LifecycleStatus.PUBLISHED)


def _create_framework_target(framework, code="T-1"):
    return FrameworkTarget.objects.create(
        framework=framework,
        code=code,
        title=f"Target {code}",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )


def _create_framework_indicator(framework, target, code, org=None, sensitivity=SensitivityLevel.PUBLIC):
    return FrameworkIndicator.objects.create(
        framework=framework,
        framework_target=target,
        code=code,
        title=f"Indicator {code}",
        indicator_type=FrameworkIndicatorType.HEADLINE,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=sensitivity,
        organisation=org,
    )


def _create_national_target(org, code="NT-1", sensitivity=SensitivityLevel.PUBLIC):
    return NationalTarget.objects.create(
        code=code,
        title=f"National {code}",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=sensitivity,
    )


def _create_national_indicator(org, target, code="NIND-1", sensitivity=SensitivityLevel.PUBLIC):
    return Indicator.objects.create(
        code=code,
        title=f"National indicator {code}",
        national_target=target,
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=sensitivity,
    )


def test_selected_scope_without_progress_returns_zero():
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org)
    instance = _create_instance()
    framework = _create_framework()
    target = _create_framework_target(framework)
    _create_framework_indicator(framework, target, "H1")

    output = compute_hl21_1_gap_analysis(
        user=user,
        instance=instance,
        scope="selected",
        framework_code="GBF",
    )
    assert output["summary"]["coverage_only"]["total_headline_indicators"] == 0


def test_scope_all_ordering_and_mapping():
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org)
    framework = _create_framework()
    target = _create_framework_target(framework)

    fi1 = _create_framework_indicator(framework, target, "H1")
    fi10 = _create_framework_indicator(framework, target, "H10")
    fi2 = _create_framework_indicator(framework, target, "H2")

    nt = _create_national_target(org)
    indicator = _create_national_indicator(org, nt)
    IndicatorFrameworkIndicatorLink.objects.create(
        indicator=indicator,
        framework_indicator=fi1,
        is_active=True,
    )

    output = compute_hl21_1_gap_analysis(user=user, scope="all", framework_code="GBF")
    summary = output["summary"]["coverage_only"]
    assert summary["total_headline_indicators"] == 3
    assert summary["addressed_count"] == 1

    codes = [item["framework_indicator_code"] for item in output["headline_indicators"]]
    assert codes == ["H1", "H10", "H2"]


def test_abac_hidden_indicator_does_not_count():
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    user = _create_staff_user(org_a)
    framework = _create_framework()
    target = _create_framework_target(framework)
    fi = _create_framework_indicator(framework, target, "H1")

    nt_b = _create_national_target(org_b, code="NT-B", sensitivity=SensitivityLevel.INTERNAL)
    indicator_b = _create_national_indicator(org_b, nt_b, code="NIND-B", sensitivity=SensitivityLevel.INTERNAL)
    IndicatorFrameworkIndicatorLink.objects.create(
        indicator=indicator_b,
        framework_indicator=fi,
        is_active=True,
    )

    output = compute_hl21_1_gap_analysis(user=user, scope="all", framework_code="GBF")
    summary = output["summary"]["coverage_only"]
    assert summary["total_headline_indicators"] == 1
    assert summary["addressed_count"] == 0
    assert output["headline_indicators"][0]["mapped_national_indicators"] == []


def test_consent_required_framework_indicator_excluded():
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org)
    instance = _create_instance()
    framework = _create_framework()
    target = _create_framework_target(framework)
    fi = _create_framework_indicator(
        framework, target, "H1", org=org, sensitivity=SensitivityLevel.IPLC_SENSITIVE
    )

    output = compute_hl21_1_gap_analysis(
        user=user,
        instance=instance,
        scope="all",
        framework_code="GBF",
    )
    assert output["summary"]["coverage_only"]["total_headline_indicators"] == 0

    ConsentRecord.objects.create(
        content_type=ContentType.objects.get_for_model(FrameworkIndicator),
        object_uuid=fi.uuid,
        reporting_instance=instance,
        status=ConsentStatus.GRANTED,
    )
    output = compute_hl21_1_gap_analysis(
        user=user,
        instance=instance,
        scope="all",
        framework_code="GBF",
    )
    assert output["summary"]["coverage_only"]["total_headline_indicators"] == 1


def test_reportability_from_data_series_and_dataset_release():
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org)
    framework = _create_framework()
    target = _create_framework_target(framework)
    fi = _create_framework_indicator(framework, target, "H1")

    nt = _create_national_target(org)
    indicator = _create_national_indicator(org, nt)
    IndicatorFrameworkIndicatorLink.objects.create(
        indicator=indicator,
        framework_indicator=fi,
        is_active=True,
    )

    IndicatorDataSeries.objects.create(
        indicator=indicator,
        title="Series",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        organisation=org,
    )
    dataset = Dataset.objects.create(
        title="Dataset",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    release = DatasetRelease.objects.create(
        dataset=dataset,
        version="v1",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    IndicatorDatasetLink.objects.create(indicator=indicator, dataset=dataset)

    output = compute_hl21_1_gap_analysis(user=user, scope="all", framework_code="GBF")
    item = output["headline_indicators"][0]
    assert item["reportable"] is True
    assert "data_series" in item["reportability_sources"]
    assert "dataset_release" in item["reportability_sources"]


def test_command_outputs_files(tmp_path):
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org)
    framework = _create_framework()
    target = _create_framework_target(framework)
    _create_framework_indicator(framework, target, "H1")

    call_command(
        "hl21_1_gap_analysis",
        "--user",
        user.username,
        "--format",
        "csv",
        "--out-dir",
        str(tmp_path),
    )
    assert (tmp_path / "hl21_1_summary.csv").exists()
    assert (tmp_path / "hl21_1_headline_indicators.csv").exists()
    assert (tmp_path / "hl21_1_by_target.csv").exists()
