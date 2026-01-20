import json
import uuid
from datetime import date, datetime, timezone as py_timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import override_settings

from nbms_app.exports.ort_nr7_narrative import build_ort_nr7_narrative_payload
from nbms_app.models import (
    NationalTarget,
    Organisation,
    ReportSectionResponse,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
)
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from nbms_app.services.instance_approvals import approve_for_instance


pytestmark = pytest.mark.django_db


def _seed_templates_and_rules():
    call_command("seed_report_templates")
    call_command("seed_validation_rules")


def _create_cycle_and_instance(*, cycle_uuid, instance_uuid):
    cycle = ReportingCycle.objects.create(
        uuid=cycle_uuid,
        code="CYCLE-1",
        title="Cycle 1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    instance = ReportingInstance.objects.create(
        uuid=instance_uuid,
        cycle=cycle,
        version_label="v1",
    )
    return cycle, instance


def _create_user(org, username, staff=False):
    return User.objects.create_user(
        username=username,
        password="pass1234",
        organisation=org,
        is_staff=staff,
    )


def _create_section_response(instance, user, code, content):
    template = ReportSectionTemplate.objects.get(code=code)
    return ReportSectionResponse.objects.create(
        reporting_instance=instance,
        template=template,
        response_json=content,
        updated_by=user,
    )


def _seed_required_responses(instance, user):
    _create_section_response(instance, user, "section-i", {"summary": "Section I narrative"})
    _create_section_response(instance, user, "section-ii", {"policy_measures": "Section II narrative"})
    _create_section_response(instance, user, "section-iii", {"progress_overview": "Section III narrative"})
    _create_section_response(instance, user, "section-iv", {"support_needs": "Section IV narrative"})
    _create_section_response(
        instance,
        user,
        "section-v",
        {"annex_notes": "Section V notes", "references": "Section V references"},
    )
    _create_section_response(
        instance,
        user,
        "section-other-information",
        {
            "additional_information": "Annex info",
            "additional_documents": [{"url": "https://example.com/doc", "name": "Annex doc"}],
        },
    )


@override_settings(EXPORT_REQUIRE_SECTIONS=True, LANGUAGE_CODE="en")
def test_ort_nr7_narrative_export_happy_path_gated_and_deterministic():
    _seed_templates_and_rules()
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "staff", staff=True)
    instance_uuid = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    cycle_uuid = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    _, instance = _create_cycle_and_instance(cycle_uuid=cycle_uuid, instance_uuid=instance_uuid)
    _seed_required_responses(instance, user)

    fixed_time = datetime(2026, 1, 20, 10, 0, 0, tzinfo=py_timezone.utc)
    with patch("nbms_app.exports.ort_nr7_narrative.timezone.now", return_value=fixed_time):
        payload = build_ort_nr7_narrative_payload(instance=instance, user=user)

    fixture_path = Path("src/nbms_app/tests/fixtures/exports/ort_nr7_narrative_expected.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert payload == expected


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_ort_nr7_narrative_export_blocks_missing_required_section():
    _seed_templates_and_rules()
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "staff", staff=True)
    _, instance = _create_cycle_and_instance(
        cycle_uuid=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaab"),
        instance_uuid=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbc"),
    )
    _create_section_response(instance, user, "section-i", {"summary": "Section I narrative"})

    with pytest.raises(ValidationError):
        build_ort_nr7_narrative_payload(instance=instance, user=user)


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_ort_nr7_narrative_export_blocks_missing_consent_for_sensitive_approved_item():
    _seed_templates_and_rules()
    org = Organisation.objects.create(name="Org A")
    admin = _create_user(org, "admin", staff=True)
    _, instance = _create_cycle_and_instance(
        cycle_uuid=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaac"),
        instance_uuid=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbd"),
    )
    _seed_required_responses(instance, admin)

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
        build_ort_nr7_narrative_payload(instance=instance, user=admin)


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_ort_nr7_narrative_export_abac_no_leak():
    _seed_templates_and_rules()
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    user_a = _create_user(org_a, "steward-a")
    user_b = _create_user(org_b, "steward-b")
    group = Group.objects.create(name=ROLE_DATA_STEWARD)
    user_a.groups.add(group)
    user_b.groups.add(group)
    _, instance = _create_cycle_and_instance(
        cycle_uuid=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaad"),
        instance_uuid=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbe"),
    )
    _seed_required_responses(instance, user_a)

    target = NationalTarget.objects.create(
        code="NT-PRIVATE",
        title="Target Private",
        organisation=org_a,
        created_by=user_a,
        sensitivity=SensitivityLevel.INTERNAL,
        status="published",
    )
    approve_for_instance(instance, target, user_a)

    payload = build_ort_nr7_narrative_payload(instance=instance, user=user_b)
    assert "NT-PRIVATE" not in json.dumps(payload)
