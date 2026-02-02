import csv

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

from nbms_app.models import (
    Indicator,
    IndicatorReportingCapability,
    IndicatorUpdateFrequency,
    LifecycleStatus,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
)
from nbms_app.services.readiness import get_instance_readiness
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from django.contrib.auth.models import Group
from nbms_app.models import User
from nbms_app.services.instance_approvals import approve_for_instance


pytestmark = pytest.mark.django_db


def _create_staff_user(org, username="staff-meta"):
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
        code="CYCLE-META",
        title="Cycle META",
        start_date="2025-01-01",
        end_date="2025-12-31",
        due_date="2026-01-31",
        is_active=True,
    )
    return ReportingInstance.objects.create(cycle=cycle)


def test_indicator_reporting_metadata_validation():
    org = Organisation.objects.create(name="Org A")
    target = NationalTarget.objects.create(
        code="NT-1",
        title="Target 1",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )

    indicator = Indicator(
        code="IND-1",
        title="Indicator 1",
        national_target=target,
        indicator_type=NationalIndicatorType.NATIONAL,
        reporting_capability=IndicatorReportingCapability.NO,
        reporting_no_reason_codes=[],
    )
    with pytest.raises(ValidationError):
        indicator.full_clean()

    indicator.reporting_capability = IndicatorReportingCapability.YES
    indicator.reporting_no_reason_codes = ["no_data"]
    with pytest.raises(ValidationError):
        indicator.full_clean()

    indicator.reporting_capability = IndicatorReportingCapability.UNKNOWN
    indicator.reporting_no_reason_codes = []
    indicator.coverage_time_start_year = 2025
    indicator.coverage_time_end_year = 2024
    with pytest.raises(ValidationError):
        indicator.full_clean()


def test_indicator_import_export_roundtrip(tmp_path):
    org = Organisation.objects.create(name="Org A", org_code="ORG-A")
    target = NationalTarget.objects.create(
        code="NT-1",
        title="Target 1",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    indicator = Indicator.objects.create(
        code="IND-1",
        title="Indicator 1",
        national_target=target,
        indicator_type=NationalIndicatorType.NATIONAL,
        reporting_capability=IndicatorReportingCapability.YES,
        update_frequency=IndicatorUpdateFrequency.ANNUAL,
        organisation=org,
        sensitivity=SensitivityLevel.PUBLIC,
        status=LifecycleStatus.PUBLISHED,
    )

    export_path = tmp_path / "indicator_export.csv"
    call_command(
        "reference_catalog_export",
        "--entity",
        "indicator",
        "--out",
        str(export_path),
    )
    assert export_path.exists()

    with export_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert rows
    row = rows[0]
    assert row["indicator_code"] == "IND-1"
    assert row["reporting_capability"] == "yes"

    row["reporting_capability"] = "no"
    row["reporting_no_reason_codes"] = "no_data"

    import_path = tmp_path / "indicator_import.csv"
    with import_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerow(row)

    call_command(
        "reference_catalog_import",
        "--entity",
        "indicator",
        "--file",
        str(import_path),
    )
    indicator.refresh_from_db()
    assert indicator.reporting_capability == IndicatorReportingCapability.NO
    assert indicator.reporting_no_reason_codes == ["no_data"]


def test_readiness_includes_reporting_capability_counts():
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org)
    instance = _create_instance()
    target = NationalTarget.objects.create(
        code="NT-1",
        title="Target 1",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    indicator = Indicator.objects.create(
        code="IND-1",
        title="Indicator 1",
        national_target=target,
        indicator_type=NationalIndicatorType.NATIONAL,
        reporting_capability=IndicatorReportingCapability.PARTIAL,
        organisation=org,
        sensitivity=SensitivityLevel.PUBLIC,
        status=LifecycleStatus.PUBLISHED,
    )
    approve_for_instance(instance, indicator, user)

    readiness = get_instance_readiness(instance, user)
    reporting_counts = readiness["details"]["indicator_reporting_capability"]
    assert reporting_counts["total"] == 1
    assert reporting_counts["by_capability"].get("partial") == 1
