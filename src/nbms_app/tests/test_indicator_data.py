from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import IntegrityError, transaction

from nbms_app.models import (
    BinaryIndicatorQuestion,
    BinaryIndicatorResponse,
    Framework,
    FrameworkIndicator,
    FrameworkIndicatorType,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    LifecycleStatus,
    NationalTarget,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
)
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from nbms_app.services.consent import ConsentStatus, set_consent_status
from nbms_app.services.indicator_data import (
    filter_indicator_data_points_for_user,
    filter_indicator_data_series_for_user,
)


pytestmark = pytest.mark.django_db


def _create_user(org, username):
    user = User.objects.create_user(
        username=username,
        password="pass1234",
        organisation=org,
    )
    group, _ = Group.objects.get_or_create(name=ROLE_DATA_STEWARD)
    user.groups.add(group)
    return user


def _create_indicator(org, user, code="IND-1", target_code="NT-1"):
    target = NationalTarget.objects.create(
        code=target_code,
        title="Target",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    return Indicator.objects.create(
        code=code,
        title="Indicator",
        national_target=target,
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )


def test_indicator_data_series_constraints():
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "user-a")
    indicator = _create_indicator(org, user)
    framework = Framework.objects.create(code="GBF", title="GBF")
    framework_indicator = FrameworkIndicator.objects.create(
        framework=framework,
        code="BIN-1",
        title="Binary",
        indicator_type=FrameworkIndicatorType.BINARY,
    )

    series = IndicatorDataSeries.objects.create(
        indicator=indicator,
        title="Series",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
        organisation=org,
        created_by=user,
    )
    assert series.indicator_id == indicator.id

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IndicatorDataSeries.objects.create(
                indicator=indicator,
                title="Dup",
                status=LifecycleStatus.PUBLISHED,
                sensitivity=SensitivityLevel.INTERNAL,
            )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IndicatorDataSeries.objects.create(
                indicator=indicator,
                framework_indicator=framework_indicator,
                title="Invalid",
            )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IndicatorDataSeries.objects.create(title="Missing identity")


def test_indicator_data_abac_no_leak():
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    user_a = _create_user(org_a, "user-a")
    user_b = _create_user(org_b, "user-b")
    indicator = _create_indicator(org_a, user_a, code="IND-PRIVATE", target_code="NT-PRIVATE")

    series = IndicatorDataSeries.objects.create(
        indicator=indicator,
        title="Series",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
        organisation=org_a,
        created_by=user_a,
    )
    point = IndicatorDataPoint.objects.create(
        series=series,
        year=2020,
        value_numeric=Decimal("1.23"),
    )

    visible_series_for_b = filter_indicator_data_series_for_user(IndicatorDataSeries.objects.all(), user_b)
    visible_points_for_b = filter_indicator_data_points_for_user(IndicatorDataPoint.objects.all(), user_b)
    assert series not in visible_series_for_b
    assert point not in visible_points_for_b

    visible_series_for_a = filter_indicator_data_series_for_user(IndicatorDataSeries.objects.all(), user_a)
    visible_points_for_a = filter_indicator_data_points_for_user(IndicatorDataPoint.objects.all(), user_a)
    assert series in visible_series_for_a
    assert point in visible_points_for_a


def test_indicator_data_sensitive_requires_consent():
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "user-a")
    indicator = _create_indicator(org, user, code="IND-SENS", target_code="NT-SENS")
    series = IndicatorDataSeries.objects.create(
        indicator=indicator,
        title="Sensitive series",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.IPLC_SENSITIVE,
        organisation=org,
        created_by=user,
    )
    IndicatorDataPoint.objects.create(series=series, year=2021, value_numeric=Decimal("2.5"))

    cycle = ReportingCycle.objects.create(
        code="CYCLE-1",
        title="Cycle",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    instance = ReportingInstance.objects.create(cycle=cycle)

    visible_before = filter_indicator_data_series_for_user(
        IndicatorDataSeries.objects.all(), user, instance=instance
    )
    assert series not in visible_before

    set_consent_status(instance, series, user, ConsentStatus.GRANTED, note="ok")
    visible_after = filter_indicator_data_series_for_user(
        IndicatorDataSeries.objects.all(), user, instance=instance
    )
    assert series in visible_after


def test_binary_indicator_response_unique_per_instance_question():
    framework = Framework.objects.create(code="GBF", title="GBF")
    indicator = FrameworkIndicator.objects.create(
        framework=framework,
        code="BIN-1",
        title="Binary",
        indicator_type=FrameworkIndicatorType.BINARY,
    )
    question = BinaryIndicatorQuestion.objects.create(
        framework_indicator=indicator,
        group_key="binaryResponseTarget1",
        question_key="1_1",
        question_text="target1_question_1",
    )
    cycle = ReportingCycle.objects.create(
        code="CYCLE-1",
        title="Cycle",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    instance = ReportingInstance.objects.create(cycle=cycle)

    BinaryIndicatorResponse.objects.create(
        reporting_instance=instance,
        question=question,
        response=["yes"],
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            BinaryIndicatorResponse.objects.create(
                reporting_instance=instance,
                question=question,
                response=["no"],
            )


def test_seed_binary_indicator_questions_idempotent():
    call_command("seed_binary_indicator_questions")
    initial_count = BinaryIndicatorQuestion.objects.count()
    call_command("seed_binary_indicator_questions")
    assert BinaryIndicatorQuestion.objects.count() == initial_count
    assert initial_count > 0
