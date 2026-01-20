import pytest
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction

from nbms_app.models import (
    Framework,
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    IndicatorFrameworkIndicatorLink,
    LifecycleStatus,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    SensitivityLevel,
    User,
)
from nbms_app.services.alignment import (
    filter_indicator_framework_links_for_user,
    filter_target_framework_links_for_user,
)
from nbms_app.services.authorization import ROLE_DATA_STEWARD


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


def _create_framework_bundle():
    framework = Framework.objects.create(code="GBF", title="GBF")
    framework_target = FrameworkTarget.objects.create(
        framework=framework,
        code="T2",
        title="Target 2",
    )
    framework_indicator = FrameworkIndicator.objects.create(
        framework=framework,
        code="IND-1",
        title="Indicator 1",
    )
    return framework_target, framework_indicator


def test_alignment_links_unique_constraints():
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "user-a")
    framework_target, framework_indicator = _create_framework_bundle()

    target = NationalTarget.objects.create(
        code="NT-1",
        title="Target 1",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    indicator = Indicator.objects.create(
        code="IND-NT-1",
        title="Indicator 1",
        national_target=target,
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )

    NationalTargetFrameworkTargetLink.objects.create(
        national_target=target,
        framework_target=framework_target,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            NationalTargetFrameworkTargetLink.objects.create(
                national_target=target,
                framework_target=framework_target,
            )

    IndicatorFrameworkIndicatorLink.objects.create(
        indicator=indicator,
        framework_indicator=framework_indicator,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IndicatorFrameworkIndicatorLink.objects.create(
                indicator=indicator,
                framework_indicator=framework_indicator,
            )


def test_alignment_links_abac_no_leak():
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    user_a = _create_user(org_a, "user-a")
    user_b = _create_user(org_b, "user-b")
    framework_target, framework_indicator = _create_framework_bundle()

    target = NationalTarget.objects.create(
        code="NT-PRIVATE",
        title="Private Target",
        organisation=org_a,
        created_by=user_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    indicator = Indicator.objects.create(
        code="IND-PRIVATE",
        title="Private Indicator",
        national_target=target,
        organisation=org_a,
        created_by=user_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )

    target_link = NationalTargetFrameworkTargetLink.objects.create(
        national_target=target,
        framework_target=framework_target,
    )
    indicator_link = IndicatorFrameworkIndicatorLink.objects.create(
        indicator=indicator,
        framework_indicator=framework_indicator,
    )

    visible_targets_for_b = filter_target_framework_links_for_user(
        NationalTargetFrameworkTargetLink.objects.all(),
        user_b,
    )
    visible_indicators_for_b = filter_indicator_framework_links_for_user(
        IndicatorFrameworkIndicatorLink.objects.all(),
        user_b,
    )
    assert target_link not in visible_targets_for_b
    assert indicator_link not in visible_indicators_for_b

    visible_targets_for_a = filter_target_framework_links_for_user(
        NationalTargetFrameworkTargetLink.objects.all(),
        user_a,
    )
    visible_indicators_for_a = filter_indicator_framework_links_for_user(
        IndicatorFrameworkIndicatorLink.objects.all(),
        user_a,
    )
    assert target_link in visible_targets_for_a
    assert indicator_link in visible_indicators_for_a
