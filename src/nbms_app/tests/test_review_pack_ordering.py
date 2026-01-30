import json
import os
from datetime import date
from pathlib import Path

import pytest
from django.contrib.auth.models import Group

from nbms_app.models import (
    Framework,
    FrameworkTarget,
    Indicator,
    IndicatorDataSeries,
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
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from nbms_app.services.instance_approvals import approve_for_instance
from nbms_app.services.review import build_review_pack_context


pytestmark = pytest.mark.django_db


GOLDEN_PATH = Path("src/nbms_app/tests/golden/review_pack_order_minimal.json")


def _create_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-1",
        title="Cycle 1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    return ReportingInstance.objects.create(cycle=cycle, version_label="v1")


def _create_user(org, username):
    user = User.objects.create_user(
        username=username,
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=ROLE_DATA_STEWARD)
    user.groups.add(group)
    return user


@pytest.mark.django_db
def test_review_pack_ordering_minimal():
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "steward")
    instance = _create_instance()

    target_b = NationalTarget.objects.create(
        code="T2",
        title="Target 2",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    target_a = NationalTarget.objects.create(
        code="T1",
        title="Target 1",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )

    indicator_b = Indicator.objects.create(
        code="I2",
        title="Indicator 2",
        national_target=target_a,
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    indicator_a = Indicator.objects.create(
        code="I1",
        title="Indicator 1",
        national_target=target_a,
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )

    approve_for_instance(instance, target_a, user)
    approve_for_instance(instance, target_b, user)
    approve_for_instance(instance, indicator_a, user)
    approve_for_instance(instance, indicator_b, user)

    framework = Framework.objects.create(code="GBF", title="GBF", status=LifecycleStatus.PUBLISHED)
    fw_target_b = FrameworkTarget.objects.create(
        framework=framework,
        code="F2",
        title="Framework Target 2",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    fw_target_a = FrameworkTarget.objects.create(
        framework=framework,
        code="F1",
        title="Framework Target 1",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    NationalTargetFrameworkTargetLink.objects.create(national_target=target_a, framework_target=fw_target_a)
    NationalTargetFrameworkTargetLink.objects.create(national_target=target_b, framework_target=fw_target_b)

    section_iii_a = SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target_a,
        summary="Progress A",
    )
    SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target_b,
        summary="Progress B",
    )
    SectionIVFrameworkTargetProgress.objects.create(
        reporting_instance=instance,
        framework_target=fw_target_b,
        summary="Framework Progress B",
    )
    SectionIVFrameworkTargetProgress.objects.create(
        reporting_instance=instance,
        framework_target=fw_target_a,
        summary="Framework Progress A",
    )

    series_b = IndicatorDataSeries.objects.create(
        indicator=indicator_b,
        title="Series B",
        unit="ha",
        value_type="numeric",
        methodology="Method",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        organisation=org,
        created_by=user,
    )
    series_a = IndicatorDataSeries.objects.create(
        indicator=indicator_a,
        title="Series A",
        unit="ha",
        value_type="numeric",
        methodology="Method",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        organisation=org,
        created_by=user,
    )
    section_iii_a.indicator_data_series.add(series_b, series_a)

    context = build_review_pack_context(instance, user)
    section_iii_codes = [item["entry"].national_target.code for item in context["section_iii_items"]]
    section_iv_codes = [item["entry"].framework_target.code for item in context["section_iv_items"]]
    indicator_codes = [
        item["series"].indicator.code
        for item in context["section_iii_items"][0]["series_items"]
        if item["series"].indicator_id
    ]

    payload = {
        "section_iii_targets": section_iii_codes,
        "section_iv_framework_targets": section_iv_codes,
        "indicator_codes": indicator_codes,
    }

    if os.getenv("UPDATE_GOLDEN") == "1":
        GOLDEN_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        assert True
        return

    expected = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert payload == expected
