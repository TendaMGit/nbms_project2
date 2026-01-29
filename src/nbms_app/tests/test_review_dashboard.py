import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.urls import reverse

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


def _create_user(org, username, staff=False, steward=False):
    user = User.objects.create_user(
        username=username,
        password="pass1234",
        organisation=org,
        is_staff=staff,
    )
    if steward or staff:
        group, _ = Group.objects.get_or_create(name=ROLE_DATA_STEWARD)
        user.groups.add(group)
    return user


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


def _create_framework_stack(org, user):
    framework = Framework.objects.create(
        code="GBF",
        title="Global Biodiversity Framework",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    framework_target = FrameworkTarget.objects.create(
        framework=framework,
        code="T2",
        title="Restore ecosystems",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    framework_indicator = FrameworkIndicator.objects.create(
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


def test_review_dashboard_staff_only_and_instance_abac(client):
    _seed_templates_and_rules()
    org = Organisation.objects.create(name="Org A")
    _, instance = _create_cycle_and_instance()
    staff_user = _create_user(org, "staff", staff=True)
    non_staff = _create_user(org, "viewer", staff=False)

    url = reverse("nbms_app:reporting_instance_review", args=[instance.uuid])

    client.force_login(non_staff)
    response = client.get(url)
    assert response.status_code == 302

    client.force_login(staff_user)
    response = client.get(url)
    assert response.status_code == 200


def test_review_dashboard_abac_no_leak_cross_org(client):
    _seed_templates_and_rules()
    org_a = Organisation.objects.create(name="Org A")
    org_b = Organisation.objects.create(name="Org B")
    _, instance = _create_cycle_and_instance()
    user_a = _create_user(org_a, "user-a", staff=True)
    user_b = _create_user(org_b, "user-b", staff=True)

    group, _ = Group.objects.get_or_create(name=ROLE_DATA_STEWARD)
    user_a.groups.add(group)
    user_b.groups.add(group)

    target_a = NationalTarget.objects.create(
        code="NT-A",
        title="Target A",
        organisation=org_a,
        created_by=user_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    target_b = NationalTarget.objects.create(
        code="NT-B",
        title="Target B",
        organisation=org_b,
        created_by=user_b,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    approve_for_instance(instance, target_a, user_a)
    approve_for_instance(instance, target_b, user_b)

    url = reverse("nbms_app:reporting_instance_review", args=[instance.uuid])
    client.force_login(user_b)
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "NT-B" in content
    assert "NT-A" not in content


def test_review_pack_v2_renders_progress_and_embedded_indicator_tables(client):
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
        sensitivity=SensitivityLevel.PUBLIC,
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
    evidence = Evidence.objects.create(
        title="Evidence 1",
        evidence_type="report",
        source_url="https://example.com/evidence",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    dataset = Dataset.objects.create(
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

    _, framework_target, framework_indicator = _create_framework_stack(org, user)
    NationalTargetFrameworkTargetLink.objects.create(national_target=target, framework_target=framework_target)

    series = IndicatorDataSeries.objects.create(
        indicator=indicator,
        title="Series 1",
        unit="ha",
        value_type="numeric",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
        organisation=org,
        created_by=user,
    )
    IndicatorDataPoint.objects.create(
        series=series,
        year=2020,
        value_numeric=Decimal("1.500000"),
        disaggregation={"sex": "all"},
        dataset_release=release,
    )

    question = BinaryIndicatorQuestion.objects.create(
        framework_indicator=framework_indicator,
        group_key="group-1",
        question_key="q1",
        question_text="Is the target on track?",
        question_type="option",
        options=["yes", "no"],
        sort_order=1,
    )
    response = BinaryIndicatorResponse.objects.create(
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
        reporting_instance=instance,
        national_target=target,
        progress_status=ProgressStatus.IN_PROGRESS,
        summary="Section III summary",
    )
    section_iii.indicator_data_series.add(series)
    section_iii.binary_indicator_responses.add(response)
    section_iii.evidence_items.add(evidence)
    section_iii.dataset_releases.add(release)

    section_iv = SectionIVFrameworkTargetProgress.objects.create(
        reporting_instance=instance,
        framework_target=framework_target,
        progress_status=ProgressStatus.IN_PROGRESS,
        summary="Section IV summary",
    )
    section_iv.indicator_data_series.add(series)
    section_iv.binary_indicator_responses.add(response)
    section_iv.evidence_items.add(evidence)
    section_iv.dataset_releases.add(release)

    url = reverse("nbms_app:reporting_instance_review_pack_v2", args=[instance.uuid])
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Series 1" in content
    assert "2020" in content
    assert "1.500000" in content
    assert "Is the target on track?" in content


def test_review_pack_v2_deterministic_ordering(client):
    _seed_templates_and_rules()
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "staff", staff=True)
    _, instance = _create_cycle_and_instance()
    _seed_required_responses(instance, user)

    target_b = NationalTarget.objects.create(
        code="NT-2",
        title="Target 2",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    target_a = NationalTarget.objects.create(
        code="NT-1",
        title="Target 1",
        organisation=org,
        created_by=user,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    approve_for_instance(instance, target_a, user)
    approve_for_instance(instance, target_b, user)

    SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target_b,
        progress_status=ProgressStatus.IN_PROGRESS,
        summary="B summary",
    )
    SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target_a,
        progress_status=ProgressStatus.IN_PROGRESS,
        summary="A summary",
    )

    url = reverse("nbms_app:reporting_instance_review_pack_v2", args=[instance.uuid])
    client.force_login(user)
    response = client.get(url)
    content = response.content.decode("utf-8")
    assert content.find("NT-1 - Target 1") < content.find("NT-2 - Target 2")


def test_review_links_to_export_v2_endpoint(client):
    _seed_templates_and_rules()
    org = Organisation.objects.create(name="Org A")
    user = _create_user(org, "staff", staff=True)
    _, instance = _create_cycle_and_instance()

    url = reverse("nbms_app:reporting_instance_review", args=[instance.uuid])
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200
    export_url = reverse("nbms_app:export_ort_nr7_v2_instance", args=[instance.uuid])
    assert export_url in response.content.decode("utf-8")
