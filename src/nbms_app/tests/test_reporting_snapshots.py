from datetime import date, datetime, timezone as py_timezone
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse
from django.test import override_settings

from nbms_app.models import (
    Indicator,
    LifecycleStatus,
    NationalTarget,
    Organisation,
    ProgressStatus,
    ReportSectionResponse,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    SectionIIINationalTargetProgress,
    SensitivityLevel,
    User,
)
from nbms_app.services.instance_approvals import approve_for_instance
from nbms_app.services.snapshots import create_reporting_snapshot


pytestmark = pytest.mark.django_db


def _seed_templates_and_rules():
    call_command("seed_report_templates")
    call_command("seed_validation_rules")


def _create_cycle_and_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-1",
        title="Cycle 1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    instance = ReportingInstance.objects.create(
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
        {"additional_information": "Annex info"},
    )


def _setup_exportable_instance():
    _seed_templates_and_rules()
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "staff", staff=True)
    _, instance = _create_cycle_and_instance()
    _seed_required_responses(instance, user)

    target = NationalTarget.objects.create(
        code="NT-1",
        title="National Target 1",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    indicator = Indicator.objects.create(
        code="IND-1",
        title="Indicator 1",
        national_target=target,
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )

    approve_for_instance(instance, target, user)
    approve_for_instance(instance, indicator, user)

    progress = SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target,
        progress_status=ProgressStatus.IN_PROGRESS,
        summary="Initial summary",
    )
    return instance, user, progress


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_snapshot_creation_requires_export_eligibility():
    _seed_templates_and_rules()
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "staff", staff=True)
    _, instance = _create_cycle_and_instance()

    with pytest.raises(ValidationError):
        create_reporting_snapshot(instance=instance, user=user)


@override_settings(EXPORT_REQUIRE_SECTIONS=True, LANGUAGE_CODE="en")
def test_snapshot_hash_deterministic_and_idempotent():
    instance, user, _ = _setup_exportable_instance()
    fixed_time = datetime(2026, 1, 22, 12, 0, 0, tzinfo=py_timezone.utc)

    with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=fixed_time):
        snapshot_a = create_reporting_snapshot(instance=instance, user=user)
        snapshot_b = create_reporting_snapshot(instance=instance, user=user)

    assert snapshot_a.uuid == snapshot_b.uuid
    assert snapshot_a.payload_hash == snapshot_b.payload_hash


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_snapshot_captures_readiness_report():
    instance, user, _ = _setup_exportable_instance()
    snapshot = create_reporting_snapshot(instance=instance, user=user)

    assert "summary" in snapshot.readiness_report_json
    assert snapshot.readiness_overall_ready == snapshot.readiness_report_json["summary"].get("overall_ready")
    assert (
        snapshot.readiness_blocking_gap_count
        == snapshot.readiness_report_json["summary"].get("blocking_gap_count")
    )


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_snapshot_immutable():
    instance, user, _ = _setup_exportable_instance()
    fixed_time = datetime(2026, 1, 22, 12, 0, 0, tzinfo=py_timezone.utc)

    with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=fixed_time):
        snapshot = create_reporting_snapshot(instance=instance, user=user)

    snapshot.payload_hash = "x" * 64
    with pytest.raises(ValidationError):
        snapshot.save()


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_snapshot_access_control_no_staff_bypass_of_abac(client):
    _seed_templates_and_rules()
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    user_a = _create_user(org_a, "staff-a", staff=True)
    user_b = _create_user(org_b, "staff-b", staff=True)
    _, instance = _create_cycle_and_instance()
    _seed_required_responses(instance, user_a)

    target = NationalTarget.objects.create(
        code="NT-A",
        title="National Target A",
        organisation=org_a,
        created_by=user_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    indicator = Indicator.objects.create(
        code="IND-A",
        title="Indicator A",
        national_target=target,
        organisation=org_a,
        created_by=user_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    approve_for_instance(instance, target, user_a)
    approve_for_instance(instance, indicator, user_a)

    SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target,
        progress_status=ProgressStatus.IN_PROGRESS,
        summary="Summary",
    )

    fixed_time = datetime(2026, 1, 22, 12, 0, 0, tzinfo=py_timezone.utc)
    with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=fixed_time):
        create_reporting_snapshot(instance=instance, user=user_a)

    url = reverse("nbms_app:reporting_instance_snapshots", args=[instance.uuid])

    client.force_login(user_b)
    response = client.get(url)
    assert response.status_code == 403

    client.force_login(user_a)
    response = client.get(url)
    assert response.status_code == 200


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_snapshot_diff_detects_controlled_change(client):
    instance, user, progress = _setup_exportable_instance()
    time_a = datetime(2026, 1, 22, 12, 0, 0, tzinfo=py_timezone.utc)
    time_b = datetime(2026, 1, 22, 13, 0, 0, tzinfo=py_timezone.utc)

    with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=time_a):
        snapshot_a = create_reporting_snapshot(instance=instance, user=user)

    progress.summary = "Updated summary"
    progress.save(update_fields=["summary"])

    with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=time_b):
        snapshot_b = create_reporting_snapshot(instance=instance, user=user)

    url = reverse("nbms_app:reporting_instance_snapshot_diff", args=[instance.uuid])
    client.force_login(user)
    response = client.get(url, {"a": snapshot_a.uuid, "b": snapshot_b.uuid})
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "NT-1" in content
