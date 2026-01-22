import json
import uuid
from datetime import date, datetime, timezone as py_timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import override_settings

from nbms_app.exports.ort_nr7_v2 import build_ort_nr7_v2_payload
from nbms_app.models import (
    BinaryIndicatorQuestion,
    BinaryIndicatorResponse,
    Framework,
    FrameworkIndicator,
    FrameworkIndicatorType,
    FrameworkTarget,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    LifecycleStatus,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    ProgressStatus,
    ReportSectionResponse,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    SectionIIINationalTargetProgress,
    SectionIVFrameworkTargetProgress,
    SensitivityLevel,
    User,
    Evidence,
    Dataset,
    DatasetRelease,
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


def _create_framework_stack(org, user):
    framework = Framework.objects.create(
        uuid=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        code="GBF",
        title="Global Biodiversity Framework",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    framework_target = FrameworkTarget.objects.create(
        uuid=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        framework=framework,
        code="T2",
        title="Restore ecosystems",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    framework_indicator = FrameworkIndicator.objects.create(
        uuid=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        framework=framework,
        code="BIN-1",
        title="Binary indicator",
        indicator_type=FrameworkIndicatorType.BINARY,
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    return framework, framework_target, framework_indicator


@override_settings(EXPORT_REQUIRE_SECTIONS=True, LANGUAGE_CODE="en")
def test_ort_nr7_v2_happy_path_golden():
    _seed_templates_and_rules()
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "staff", staff=True)
    instance_uuid = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    cycle_uuid = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    _, instance = _create_cycle_and_instance(cycle_uuid=cycle_uuid, instance_uuid=instance_uuid)
    _seed_required_responses(instance, user)

    target = NationalTarget.objects.create(
        uuid=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        code="NT-1",
        title="National Target 1",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    indicator = Indicator.objects.create(
        uuid=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        code="IND-1",
        title="Indicator 1",
        national_target=target,
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    evidence = Evidence.objects.create(
        uuid=uuid.UUID("aaaaaaaa-1111-2222-3333-444444444444"),
        title="Evidence 1",
        evidence_type="report",
        source_url="https://example.com/evidence",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    dataset = Dataset.objects.create(
        uuid=uuid.UUID("bbbbbbbb-1111-2222-3333-444444444444"),
        title="Dataset 1",
        description="Dataset description",
        methodology="Dataset methodology",
        source_url="https://example.com/dataset",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    release = DatasetRelease.objects.create(
        uuid=uuid.UUID("cccccccc-1111-2222-3333-444444444444"),
        dataset=dataset,
        version="v1",
        release_date=date(2025, 6, 1),
        snapshot_title="Dataset 1",
        snapshot_description="Dataset description",
        snapshot_methodology="Dataset methodology",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )

    framework, framework_target, framework_indicator = _create_framework_stack(org, user)
    NationalTargetFrameworkTargetLink.objects.create(national_target=target, framework_target=framework_target)

    series = IndicatorDataSeries.objects.create(
        uuid=uuid.UUID("66666666-6666-6666-6666-666666666666"),
        indicator=indicator,
        title="Series 1",
        unit="ha",
        value_type="numeric",
        methodology="Method",
        source_notes="Source notes",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
        organisation=org,
        created_by=user,
    )
    IndicatorDataPoint.objects.create(
        uuid=uuid.UUID("77777777-7777-7777-7777-777777777777"),
        series=series,
        year=2020,
        value_numeric=Decimal("1.500000"),
        disaggregation={"sex": "all"},
        dataset_release=release,
        source_url="https://example.com/source",
        footnote="Footnote A",
    )
    IndicatorDataPoint.objects.create(
        uuid=uuid.UUID("88888888-8888-8888-8888-888888888888"),
        series=series,
        year=2021,
        value_numeric=Decimal("2.500000"),
        disaggregation={"sex": "all"},
    )

    question = BinaryIndicatorQuestion.objects.create(
        uuid=uuid.UUID("99999999-9999-9999-9999-999999999999"),
        framework_indicator=framework_indicator,
        group_key="group-1",
        question_key="q1",
        question_text="Is the target on track?",
        question_type="option",
        options=["yes", "no"],
        sort_order=1,
    )
    response = BinaryIndicatorResponse.objects.create(
        uuid=uuid.UUID("ffffffff-1111-2222-3333-444444444444"),
        reporting_instance=instance,
        question=question,
        response=["yes"],
        comments="On track",
    )

    approve_for_instance(instance, target, user)
    approve_for_instance(instance, indicator, user)
    approve_for_instance(instance, evidence, user)
    approve_for_instance(instance, dataset, user)

    section_iii = SectionIIINationalTargetProgress.objects.create(
        uuid=uuid.UUID("dddddddd-1111-2222-3333-444444444444"),
        reporting_instance=instance,
        national_target=target,
        progress_status=ProgressStatus.IN_PROGRESS,
        summary="Section III summary",
        actions_taken="Actions taken",
        outcomes="Outcomes",
        challenges="Challenges",
        support_needed="Support needed",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
    )
    section_iii.indicator_data_series.add(series)
    section_iii.binary_indicator_responses.add(response)
    section_iii.evidence_items.add(evidence)
    section_iii.dataset_releases.add(release)

    section_iv = SectionIVFrameworkTargetProgress.objects.create(
        uuid=uuid.UUID("eeeeeeee-1111-2222-3333-444444444444"),
        reporting_instance=instance,
        framework_target=framework_target,
        progress_status=ProgressStatus.IN_PROGRESS,
        summary="Section IV summary",
        actions_taken="Actions taken",
        outcomes="Outcomes",
        challenges="Challenges",
        support_needed="Support needed",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
    )
    section_iv.indicator_data_series.add(series)
    section_iv.binary_indicator_responses.add(response)
    section_iv.evidence_items.add(evidence)
    section_iv.dataset_releases.add(release)

    fixed_time = datetime(2026, 1, 20, 10, 0, 0, tzinfo=py_timezone.utc)
    with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=fixed_time):
        payload = build_ort_nr7_v2_payload(instance=instance, user=user)

    fixture_path = Path("src/nbms_app/tests/fixtures/exports/ort_nr7_v2_expected.json")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert payload == expected


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_ort_nr7_v2_blocks_missing_progress_when_required():
    _seed_templates_and_rules()
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "staff", staff=True)
    _, instance = _create_cycle_and_instance(
        cycle_uuid=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaab"),
        instance_uuid=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbc"),
    )
    _seed_required_responses(instance, user)

    target = NationalTarget.objects.create(
        code="NT-REQ",
        title="Target Required",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    approve_for_instance(instance, target, user)

    framework, framework_target, _ = _create_framework_stack(org, user)
    NationalTargetFrameworkTargetLink.objects.create(national_target=target, framework_target=framework_target)

    SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target,
        progress_status=ProgressStatus.IN_PROGRESS,
        summary="Section III summary",
    )

    with pytest.raises(ValidationError):
        build_ort_nr7_v2_payload(instance=instance, user=user)


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_ort_nr7_v2_blocks_references_not_export_eligible():
    _seed_templates_and_rules()
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "staff", staff=True)
    _, instance = _create_cycle_and_instance(
        cycle_uuid=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaac"),
        instance_uuid=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbd"),
    )
    _seed_required_responses(instance, user)

    target = NationalTarget.objects.create(
        code="NT-REF",
        title="Target Ref",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    approve_for_instance(instance, target, user)

    framework, framework_target, _ = _create_framework_stack(org, user)
    NationalTargetFrameworkTargetLink.objects.create(national_target=target, framework_target=framework_target)

    hidden_indicator = Indicator.objects.create(
        code="IND-UNAPPROVED",
        title="Indicator Unapproved",
        national_target=target,
        organisation=org,
        created_by=user,
        status=LifecycleStatus.DRAFT,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    series = IndicatorDataSeries.objects.create(
        indicator=hidden_indicator,
        title="Hidden series",
        unit="ha",
        value_type="numeric",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
        organisation=org,
        created_by=user,
    )

    SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target,
        progress_status=ProgressStatus.IN_PROGRESS,
        summary="Section III summary",
    ).indicator_data_series.add(series)

    SectionIVFrameworkTargetProgress.objects.create(
        reporting_instance=instance,
        framework_target=framework_target,
        progress_status=ProgressStatus.IN_PROGRESS,
        summary="Section IV summary",
    )

    with pytest.raises(ValidationError):
        build_ort_nr7_v2_payload(instance=instance, user=user)


@override_settings(EXPORT_REQUIRE_SECTIONS=True)
def test_ort_nr7_v2_abac_no_leak_cross_org():
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
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    approve_for_instance(instance, target, user_a)

    payload = build_ort_nr7_v2_payload(instance=instance, user=user_b)
    assert "NT-PRIVATE" not in json.dumps(payload)
