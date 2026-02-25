from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError

from nbms_app.models import (
    AuditEvent,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorMethodologyVersionLink,
    LifecycleStatus,
    Methodology,
    MethodologyStatus,
    MethodologyVersion,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    SensitivityLevel,
    User,
)
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from nbms_app.services.indicator_release_workflow import (
    approve_indicator_release,
    submit_indicator_release,
)


pytestmark = pytest.mark.django_db


def _seed_release_stack(
    *,
    series_sensitivity=SensitivityLevel.PUBLIC,
    method_status=MethodologyStatus.ACTIVE,
    approval_body="ITSC methods panel approved",
):
    org = Organisation.objects.create(name="Release Org", org_code="REL-ORG")
    contributor = User.objects.create_user(
        username="contributor_release",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    steward = User.objects.create_user(
        username="steward_release",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    steward_group, _ = Group.objects.get_or_create(name=ROLE_DATA_STEWARD)
    steward.groups.add(steward_group)

    target = NationalTarget.objects.create(
        code="NT-REL",
        title="Release Target",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        created_by=contributor,
    )
    indicator = Indicator.objects.create(
        code="IND-REL",
        title="Release Indicator",
        national_target=target,
        indicator_type=NationalIndicatorType.OTHER,
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        created_by=contributor,
    )
    methodology = Methodology.objects.create(
        methodology_code="METH-REL",
        title="Release Method",
        owner_org=org,
    )
    methodology_version = MethodologyVersion.objects.create(
        methodology=methodology,
        version="1.0",
        status=method_status,
        approval_body=approval_body,
        is_active=True,
    )
    IndicatorMethodologyVersionLink.objects.create(
        indicator=indicator,
        methodology_version=methodology_version,
        is_primary=True,
        is_active=True,
    )
    series = IndicatorDataSeries.objects.create(
        indicator=indicator,
        title="Release Series",
        unit="index",
        value_type="numeric",
        organisation=org,
        created_by=contributor,
        status=LifecycleStatus.DRAFT,
        sensitivity=series_sensitivity,
    )
    IndicatorDataPoint.objects.create(
        series=series,
        year=2025,
        value_numeric=Decimal("12.5"),
        disaggregation={"province": "ALL"},
    )
    return {"org": org, "contributor": contributor, "steward": steward, "series": series}


def test_release_submit_requires_itsc_approved_method():
    stack = _seed_release_stack(
        method_status=MethodologyStatus.DRAFT,
        approval_body="Draft review pending",
    )
    series = stack["series"]
    contributor = stack["contributor"]

    with pytest.raises(ValidationError, match="ITSC-approved method version"):
        submit_indicator_release(series, contributor, sense_check_attested=True, note="submit")

    series.refresh_from_db()
    assert series.status == LifecycleStatus.DRAFT


def test_non_sensitive_release_fast_path_publishes_with_attestation_and_audit():
    stack = _seed_release_stack(series_sensitivity=SensitivityLevel.PUBLIC)
    series = stack["series"]
    contributor = stack["contributor"]

    submit_indicator_release(
        series,
        contributor,
        sense_check_attested=True,
        note="checked and ready",
    )

    series.refresh_from_db()
    assert series.status == LifecycleStatus.PUBLISHED
    assert series.sense_check_attested is True
    assert series.sense_check_attested_by == contributor
    assert series.sense_check_attested_at is not None

    actions = set(
        AuditEvent.objects.filter(
            object_type="IndicatorDataSeries",
            object_uuid=series.uuid,
        ).values_list("action", flat=True)
    )
    assert "indicator_release_submit" in actions
    assert "indicator_release_publish_fast_path" in actions


def test_sensitive_release_routes_to_steward_queue_before_publish():
    stack = _seed_release_stack(series_sensitivity=SensitivityLevel.RESTRICTED)
    series = stack["series"]
    contributor = stack["contributor"]
    steward = stack["steward"]

    submit_indicator_release(series, contributor, sense_check_attested=True, note="contains restricted rows")
    series.refresh_from_db()
    assert series.status == LifecycleStatus.PENDING_REVIEW

    with pytest.raises(PermissionDenied):
        approve_indicator_release(series, contributor, note="attempted self-approval")

    approve_indicator_release(series, steward, note="steward approved")
    series.refresh_from_db()
    assert series.status == LifecycleStatus.PUBLISHED

    actions = set(
        AuditEvent.objects.filter(
            object_type="IndicatorDataSeries",
            object_uuid=series.uuid,
        ).values_list("action", flat=True)
    )
    assert "indicator_release_submit" in actions
    assert "indicator_release_steward_approve" in actions
