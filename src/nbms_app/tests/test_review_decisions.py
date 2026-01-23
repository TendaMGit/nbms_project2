import uuid
from datetime import date, datetime, timezone as py_timezone
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

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
    ReviewDecisionStatus,
    SectionIIINationalTargetProgress,
    SensitivityLevel,
    User,
)
from nbms_app.services.instance_approvals import approve_for_instance
from nbms_app.services.review_decisions import create_review_decision
from nbms_app.services.snapshots import create_reporting_snapshot


pytestmark = pytest.mark.django_db


def _seed_templates_and_rules():
    call_command("seed_report_templates")
    call_command("seed_validation_rules")


def _create_cycle_and_instance(code=None):
    cycle_code = code or f"CYCLE-{uuid.uuid4().hex[:6].upper()}"
    cycle = ReportingCycle.objects.create(
        code=cycle_code,
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
def test_review_decision_requires_snapshot():
    instance, user, _ = _setup_exportable_instance()
    with pytest.raises(ValidationError):
        create_review_decision(
            instance=instance,
            snapshot=None,
            user=user,
            decision=ReviewDecisionStatus.APPROVED,
            notes="",
        )


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_review_decision_requires_instance_abac(client):
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
        snapshot = create_reporting_snapshot(instance=instance, user=user_a)

    list_url = reverse("nbms_app:reporting_instance_review_decisions", args=[instance.uuid])
    create_url = reverse("nbms_app:reporting_instance_review_decision_create", args=[instance.uuid])

    client.force_login(user_b)
    response = client.get(list_url)
    assert response.status_code == 403
    response = client.post(
        create_url,
        {"decision": ReviewDecisionStatus.CHANGES_REQUESTED, "snapshot_uuid": snapshot.uuid},
    )
    assert response.status_code == 403


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_review_decision_snapshot_must_belong_to_instance():
    instance, user, progress = _setup_exportable_instance()
    fixed_time = datetime(2026, 1, 22, 12, 0, 0, tzinfo=py_timezone.utc)
    with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=fixed_time):
        snapshot_a = create_reporting_snapshot(instance=instance, user=user)

    _, other_instance = _create_cycle_and_instance()
    _seed_required_responses(other_instance, user)
    target = progress.national_target
    indicator = Indicator.objects.filter(national_target=target).first()
    approve_for_instance(other_instance, target, user)
    if indicator:
        approve_for_instance(other_instance, indicator, user)
    SectionIIINationalTargetProgress.objects.create(
        reporting_instance=other_instance,
        national_target=target,
        progress_status=ProgressStatus.IN_PROGRESS,
        summary="Other instance summary",
    )
    with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=fixed_time):
        snapshot_b = create_reporting_snapshot(instance=other_instance, user=user)

    with pytest.raises(ValidationError):
        create_review_decision(
            instance=instance,
            snapshot=snapshot_b,
            user=user,
            decision=ReviewDecisionStatus.CHANGES_REQUESTED,
            notes="",
        )

    create_review_decision(
        instance=instance,
        snapshot=snapshot_a,
        user=user,
        decision=ReviewDecisionStatus.CHANGES_REQUESTED,
        notes="",
    )


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_approve_requires_frozen_and_latest_snapshot():
    instance, user, progress = _setup_exportable_instance()
    time_a = datetime(2026, 1, 22, 12, 0, 0, tzinfo=py_timezone.utc)
    time_b = datetime(2026, 1, 22, 13, 0, 0, tzinfo=py_timezone.utc)

    with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=time_a):
        snapshot_a = create_reporting_snapshot(instance=instance, user=user)

    progress.summary = "Updated summary"
    progress.save(update_fields=["summary"])

    with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=time_b):
        snapshot_b = create_reporting_snapshot(instance=instance, user=user)

    with pytest.raises(ValidationError):
        create_review_decision(
            instance=instance,
            snapshot=snapshot_a,
            user=user,
            decision=ReviewDecisionStatus.APPROVED,
            notes="",
        )

    with pytest.raises(ValidationError):
        create_review_decision(
            instance=instance,
            snapshot=snapshot_b,
            user=user,
            decision=ReviewDecisionStatus.APPROVED,
            notes="",
        )

    instance.frozen_at = timezone.now()
    instance.frozen_by = user
    instance.save(update_fields=["frozen_at", "frozen_by"])

    create_review_decision(
        instance=instance,
        snapshot=snapshot_b,
        user=user,
        decision=ReviewDecisionStatus.APPROVED,
        notes="",
    )


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_review_decision_immutable():
    instance, user, _ = _setup_exportable_instance()
    fixed_time = datetime(2026, 1, 22, 12, 0, 0, tzinfo=py_timezone.utc)
    with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=fixed_time):
        snapshot = create_reporting_snapshot(instance=instance, user=user)

    decision = create_review_decision(
        instance=instance,
        snapshot=snapshot,
        user=user,
        decision=ReviewDecisionStatus.CHANGES_REQUESTED,
        notes="Initial notes",
    )
    decision.notes = "Updated notes"
    with pytest.raises(ValidationError):
        decision.save()


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_review_dashboard_shows_current_decision(client):
    instance, user, _ = _setup_exportable_instance()
    fixed_time = datetime(2026, 1, 22, 12, 0, 0, tzinfo=py_timezone.utc)
    with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=fixed_time):
        snapshot = create_reporting_snapshot(instance=instance, user=user)

    create_review_decision(
        instance=instance,
        snapshot=snapshot,
        user=user,
        decision=ReviewDecisionStatus.CHANGES_REQUESTED,
        notes="Needs updates",
    )

    url = reverse("nbms_app:reporting_instance_review", args=[instance.uuid])
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200
    assert "Changes requested" in response.content.decode("utf-8")
