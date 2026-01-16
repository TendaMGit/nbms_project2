import json
import uuid
from datetime import date, datetime, timezone as py_timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import override_settings

from nbms_app.exports.ort7nr import build_ort7nr_package
from nbms_app.models import (
    Indicator,
    NationalTarget,
    Organisation,
    ReportSectionResponse,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
    ValidationRuleSet,
    ValidationScope,
)
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from nbms_app.services.instance_approvals import approve_for_instance


pytestmark = pytest.mark.django_db


def _create_ruleset(user):
    return ValidationRuleSet.objects.create(
        code="7NR_DEFAULT",
        applies_to=ValidationScope.REPORT_TYPE,
        rules_json={"sections": {"required": ["I"]}},
        is_active=True,
        created_by=user,
    )


def _create_section_template():
    return ReportSectionTemplate.objects.create(
        code="section-i",
        title="Section I",
        ordering=1,
        schema_json={"required": True, "fields": [{"key": "summary", "required": True}]},
        is_active=True,
    )


def _create_response(instance, template, user):
    return ReportSectionResponse.objects.create(
        reporting_instance=instance,
        template=template,
        response_json={"summary": "Section I summary"},
        updated_by=user,
    )


def _create_cycle_and_instance(instance_uuid=None):
    cycle = ReportingCycle.objects.create(
        code="CYCLE-1",
        title="Cycle 1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    kwargs = {"cycle": cycle, "version_label": "v1"}
    if instance_uuid:
        kwargs["uuid"] = instance_uuid
    instance = ReportingInstance.objects.create(**kwargs)
    return cycle, instance


def _create_user(org, username, staff=False):
    user = User.objects.create_user(
        username=username,
        password="pass1234",
        organisation=org,
        is_staff=staff,
    )
    return user


@override_settings(EXPORT_REQUIRE_SECTIONS=True, LANGUAGE_CODE="en", NBMS_ORT_GOVERNMENT_ID="ZA")
def test_ort7nr_export_happy_path_matches_golden_file():
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "steward")
    user.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
    _create_ruleset(user)
    template = _create_section_template()
    instance_uuid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    _, instance = _create_cycle_and_instance(instance_uuid=instance_uuid)
    _create_response(instance, template, user)

    target_uuid = uuid.UUID("22222222-2222-2222-2222-222222222222")
    target = NationalTarget.objects.create(
        uuid=target_uuid,
        code="NT-1",
        title="Target 1",
        description="Target desc",
        organisation=org,
        created_by=user,
        sensitivity=SensitivityLevel.PUBLIC,
        status="published",
    )
    indicator = Indicator.objects.create(
        uuid=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        code="IND-1",
        title="Indicator 1",
        national_target=target,
        organisation=org,
        created_by=user,
        sensitivity=SensitivityLevel.PUBLIC,
        status="published",
    )

    approve_for_instance(instance, target, user)
    approve_for_instance(instance, indicator, user)

    fixed_time = datetime(2026, 1, 16, 12, 0, 0, tzinfo=py_timezone.utc)
    with patch("nbms_app.exports.ort7nr.timezone.now", return_value=fixed_time):
        payload = build_ort7nr_package(instance=instance, user=user)

    fixture_path = Path("src/nbms_app/tests/fixtures/ort7nr/minimal_expected.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert payload == expected


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_ort7nr_export_blocked_missing_required_section():
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "steward")
    user.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
    _create_ruleset(user)
    _create_section_template()
    _, instance = _create_cycle_and_instance()

    with pytest.raises(ValidationError):
        build_ort7nr_package(instance=instance, user=user)


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_ort7nr_export_blocked_missing_approvals():
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "steward")
    user.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
    _create_ruleset(user)
    template = _create_section_template()
    _, instance = _create_cycle_and_instance()
    _create_response(instance, template, user)

    NationalTarget.objects.create(
        code="NT-2",
        title="Target 2",
        organisation=org,
        created_by=user,
        sensitivity=SensitivityLevel.PUBLIC,
        status="published",
    )

    with pytest.raises(ValidationError):
        build_ort7nr_package(instance=instance, user=user)


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_ort7nr_export_blocked_missing_consent():
    org = Organisation.objects.create(name="Org A")
    admin = _create_user(org, "admin", staff=True)
    _create_ruleset(admin)
    template = _create_section_template()
    _, instance = _create_cycle_and_instance()
    _create_response(instance, template, admin)

    target = NationalTarget.objects.create(
        code="NT-IPLC",
        title="Target IPLC",
        organisation=org,
        created_by=admin,
        sensitivity=SensitivityLevel.IPLC_SENSITIVE,
        status="published",
    )
    approve_for_instance(instance, target, admin, admin_override=True)

    with pytest.raises(ValidationError):
        build_ort7nr_package(instance=instance, user=admin)


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_ort7nr_export_abac_non_leak():
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    user_a = _create_user(org_a, "steward-a")
    user_b = _create_user(org_b, "steward-b")
    group = Group.objects.create(name=ROLE_DATA_STEWARD)
    user_a.groups.add(group)
    user_b.groups.add(group)

    _create_ruleset(user_a)
    template = _create_section_template()
    _, instance = _create_cycle_and_instance()
    _create_response(instance, template, user_a)

    target = NationalTarget.objects.create(
        code="NT-PRIVATE",
        title="Target Private",
        organisation=org_a,
        created_by=user_a,
        sensitivity=SensitivityLevel.INTERNAL,
        status="published",
    )
    approve_for_instance(instance, target, user_a)

    payload = build_ort7nr_package(instance=instance, user=user_b)
    assert payload["documents"]["nationalTarget7"] == []
