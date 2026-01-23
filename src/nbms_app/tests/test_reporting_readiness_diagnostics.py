import csv

import pytest
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext

from nbms_app.models import (
    DatasetCatalog,
    Framework,
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorFrameworkIndicatorLink,
    LifecycleStatus,
    Methodology,
    MethodologyIndicatorLink,
    MethodologyVersion,
    MonitoringProgramme,
    NationalTarget,
    Organisation,
    ProgrammeDatasetLink,
    ProgrammeIndicatorLink,
    ReportingCycle,
    ReportingInstance,
    ReportingStatus,
    SectionIIINationalTargetProgress,
    SensitivityLevel,
    User,
)
from nbms_app.services.readiness import compute_reporting_readiness


pytestmark = pytest.mark.django_db


def _base_instance():
    org = Organisation.objects.create(name="Org A", org_code="ORG-A")
    user = User.objects.create_user(username="user-a", password="pass1234", organisation=org)
    cycle = ReportingCycle.objects.create(
        code="CYCLE-1",
        title="Cycle 1",
        start_date="2025-01-01",
        end_date="2025-12-31",
        due_date="2026-01-01",
        is_active=True,
    )
    instance = ReportingInstance.objects.create(
        cycle=cycle,
        version_label="v1",
        status=ReportingStatus.DRAFT,
    )
    target = NationalTarget.objects.create(
        code="NT-1",
        title="Target 1",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    indicator = Indicator.objects.create(
        code="IND-1",
        title="Indicator 1",
        national_target=target,
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    return org, user, instance, target, indicator


def _attach_full_chain(indicator, org):
    framework = Framework.objects.create(code="GBF", title="GBF")
    framework_target = FrameworkTarget.objects.create(framework=framework, code="T1", title="Target 1")
    framework_indicator = FrameworkIndicator.objects.create(
        framework=framework,
        code="IND-G-1",
        title="Indicator G1",
        framework_target=framework_target,
    )
    IndicatorFrameworkIndicatorLink.objects.create(
        indicator=indicator,
        framework_indicator=framework_indicator,
    )

    programme = MonitoringProgramme.objects.create(
        programme_code="PRG-1",
        title="Programme 1",
        lead_org=org,
    )
    ProgrammeIndicatorLink.objects.create(programme=programme, indicator=indicator)

    dataset = DatasetCatalog.objects.create(
        dataset_code="DS-1",
        title="Dataset 1",
        custodian_org=org,
        access_level="internal",
    )
    ProgrammeDatasetLink.objects.create(programme=programme, dataset=dataset)

    methodology = Methodology.objects.create(
        methodology_code="METH-1",
        title="Method 1",
        owner_org=org,
    )
    MethodologyIndicatorLink.objects.create(methodology=methodology, indicator=indicator)

    return methodology, dataset


def test_completeness_full_chain_ready():
    org, user, instance, target, indicator = _base_instance()
    methodology, _ = _attach_full_chain(indicator, org)
    MethodologyVersion.objects.create(methodology=methodology, version="1.0", is_active=True)

    series = IndicatorDataSeries.objects.create(indicator=indicator, title="Series 1", unit="count")
    IndicatorDataPoint.objects.create(series=series, year=2020, value_numeric=10)
    progress = SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target,
    )
    progress.indicator_data_series.add(series)

    result = compute_reporting_readiness(instance.uuid, scope="all")
    assert result["summary"]["overall_ready"] is True
    entry = result["per_indicator"][0]
    assert entry["blockers"] == []
    assert entry["missing"] == []


def test_missing_methodology_version_blocks():
    org, user, instance, target, indicator = _base_instance()
    _attach_full_chain(indicator, org)

    result = compute_reporting_readiness(instance.uuid, scope="all")
    entry = result["per_indicator"][0]
    assert "NO_METHOD_VERSION" in entry["missing"]
    assert "NO_METHOD_VERSION" in entry["blockers"]


def test_consent_required_blocks():
    org, user, instance, target, indicator = _base_instance()
    methodology, dataset = _attach_full_chain(indicator, org)
    MethodologyVersion.objects.create(methodology=methodology, version="1.0", is_active=True)
    dataset.consent_required = True
    dataset.save(update_fields=["consent_required"])

    result = compute_reporting_readiness(instance.uuid, scope="all")
    entry = result["per_indicator"][0]
    assert entry["flags"]["consent_blocked"] is True
    assert "CONSENT_REQUIRED" in entry["blockers"]


def test_csv_output_format(tmp_path):
    org, user, instance, target, indicator = _base_instance()
    _attach_full_chain(indicator, org)
    out_path = tmp_path / "readiness.csv"

    call_command(
        "reporting_readiness",
        instance=str(instance.uuid),
        format="csv",
        output=str(out_path),
    )

    with out_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames is not None
    assert "indicator_code" in reader.fieldnames
    assert rows


def test_readiness_query_count_under_threshold():
    org = Organisation.objects.create(name="Org Perf", org_code="ORG-PERF")
    user = User.objects.create_user(username="perf", password="pass1234", organisation=org)
    cycle = ReportingCycle.objects.create(
        code="CYCLE-PERF",
        title="Cycle Perf",
        start_date="2025-01-01",
        end_date="2025-12-31",
        due_date="2026-01-01",
        is_active=True,
    )
    instance = ReportingInstance.objects.create(
        cycle=cycle,
        version_label="v1",
        status=ReportingStatus.DRAFT,
    )
    target = NationalTarget.objects.create(
        code="NT-PERF",
        title="Target Perf",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )

    framework = Framework.objects.create(code="GBF-PERF", title="GBF Perf")
    framework_target = FrameworkTarget.objects.create(framework=framework, code="T-P1", title="Target Perf")
    framework_indicator = FrameworkIndicator.objects.create(
        framework=framework,
        code="IND-PERF",
        title="Indicator Perf",
        framework_target=framework_target,
    )

    programme = MonitoringProgramme.objects.create(
        programme_code="PRG-PERF",
        title="Programme Perf",
        lead_org=org,
    )
    dataset = DatasetCatalog.objects.create(
        dataset_code="DS-PERF",
        title="Dataset Perf",
        custodian_org=org,
        access_level="internal",
    )
    ProgrammeDatasetLink.objects.create(programme=programme, dataset=dataset)

    methodology = Methodology.objects.create(
        methodology_code="METH-PERF",
        title="Method Perf",
        owner_org=org,
    )
    MethodologyVersion.objects.create(methodology=methodology, version="1.0", is_active=True)

    progress = SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target,
    )

    for idx in range(25):
        indicator = Indicator.objects.create(
            code=f"IND-P{idx}",
            title=f"Indicator {idx}",
            national_target=target,
            organisation=org,
            created_by=user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        IndicatorFrameworkIndicatorLink.objects.create(
            indicator=indicator,
            framework_indicator=framework_indicator,
        )
        ProgrammeIndicatorLink.objects.create(programme=programme, indicator=indicator)
        MethodologyIndicatorLink.objects.create(methodology=methodology, indicator=indicator)
        series = IndicatorDataSeries.objects.create(indicator=indicator, title="Series", unit="count")
        IndicatorDataPoint.objects.create(series=series, year=2020, value_numeric=10)
        progress.indicator_data_series.add(series)

    with CaptureQueriesContext(connection) as ctx:
        compute_reporting_readiness(instance.uuid, scope="all", user=user)

    assert len(ctx) <= 70
