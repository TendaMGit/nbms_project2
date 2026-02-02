import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError

from nbms_app.models import (
    BinaryIndicatorGroup,
    BinaryIndicatorGroupResponse,
    BinaryIndicatorQuestion,
    BinaryIndicatorResponse,
    NbsapStatus,
    ReportingCycle,
    ReportingInstance,
    ReportingStatus,
    SectionIINBSAPStatus,
    StakeholderInvolvement,
)


pytestmark = pytest.mark.django_db


def _make_instance():
    cycle = ReportingCycle.objects.create(
        code="TEST-CYCLE",
        title="Test Cycle",
        start_date="2025-01-01",
        end_date="2025-12-31",
        due_date="2026-01-31",
        is_active=True,
    )
    return ReportingInstance.objects.create(
        cycle=cycle,
        version_label="v1",
        status=ReportingStatus.DRAFT,
    )


def test_section_ii_requires_expected_completion_when_in_progress():
    instance = _make_instance()
    status = SectionIINBSAPStatus(
        reporting_instance=instance,
        nbsap_updated_status=NbsapStatus.IN_PROGRESS,
        stakeholders_involved=StakeholderInvolvement.NO,
        nbsap_adopted_status=NbsapStatus.NO,
        nbsap_adopted_other_text="Not adopted",
        monitoring_system_description="Monitoring system.",
    )
    with pytest.raises(ValidationError):
        status.full_clean()


def test_section_ii_requires_expected_completion_when_no():
    instance = _make_instance()
    status = SectionIINBSAPStatus(
        reporting_instance=instance,
        nbsap_updated_status=NbsapStatus.NO,
        stakeholders_involved=StakeholderInvolvement.NO,
        nbsap_adopted_status=NbsapStatus.NO,
        nbsap_adopted_other_text="Not adopted",
        monitoring_system_description="Monitoring system.",
    )
    with pytest.raises(ValidationError):
        status.full_clean()


def test_section_ii_requires_stakeholder_groups_when_involved():
    instance = _make_instance()
    status = SectionIINBSAPStatus(
        reporting_instance=instance,
        nbsap_updated_status=NbsapStatus.YES,
        stakeholders_involved=StakeholderInvolvement.YES,
        stakeholder_groups=[],
        nbsap_adopted_status=NbsapStatus.NO,
        nbsap_adopted_other_text="Not adopted",
        monitoring_system_description="Monitoring system.",
    )
    with pytest.raises(ValidationError):
        status.full_clean()


def test_section_ii_requires_other_text_when_other_selected():
    instance = _make_instance()
    status = SectionIINBSAPStatus(
        reporting_instance=instance,
        nbsap_updated_status=NbsapStatus.OTHER,
        nbsap_updated_other_text="",
        stakeholders_involved=StakeholderInvolvement.YES,
        stakeholder_groups=["other"],
        stakeholder_groups_other_text="",
        nbsap_adopted_status=NbsapStatus.OTHER,
        nbsap_adopted_other_text="",
        nbsap_expected_adoption_date=None,
        monitoring_system_description="Monitoring system.",
    )
    with pytest.raises(ValidationError):
        status.full_clean()


def test_section_ii_requires_adoption_mechanism_when_adopted():
    instance = _make_instance()
    status = SectionIINBSAPStatus(
        reporting_instance=instance,
        nbsap_updated_status=NbsapStatus.YES,
        stakeholders_involved=StakeholderInvolvement.NO,
        nbsap_adopted_status=NbsapStatus.YES,
        nbsap_adoption_mechanism="",
        monitoring_system_description="Monitoring system.",
    )
    with pytest.raises(ValidationError):
        status.full_clean()


def test_section_ii_requires_expected_adoption_date_when_no_or_other():
    instance = _make_instance()
    status = SectionIINBSAPStatus(
        reporting_instance=instance,
        nbsap_updated_status=NbsapStatus.YES,
        stakeholders_involved=StakeholderInvolvement.NO,
        nbsap_adopted_status=NbsapStatus.NO,
        nbsap_adopted_other_text="Not adopted",
        nbsap_expected_adoption_date=None,
        monitoring_system_description="Monitoring system.",
    )
    with pytest.raises(ValidationError):
        status.full_clean()


def test_section_ii_valid_minimum_passes():
    instance = _make_instance()
    status = SectionIINBSAPStatus(
        reporting_instance=instance,
        nbsap_updated_status=NbsapStatus.YES,
        stakeholders_involved=StakeholderInvolvement.NO,
        nbsap_adopted_status=NbsapStatus.NO,
        nbsap_adopted_other_text="Not adopted",
        nbsap_expected_adoption_date="2026-12-31",
        nbsap_expected_completion_date="2026-12-31",
        monitoring_system_description="Monitoring system.",
    )
    status.full_clean()


def test_binary_indicator_seed_is_idempotent():
    call_command("seed_binary_indicator_questions")
    counts_1 = {
        "groups": BinaryIndicatorGroup.objects.count(),
        "questions": BinaryIndicatorQuestion.objects.count(),
        "grouped_questions": BinaryIndicatorQuestion.objects.exclude(group__isnull=True).count(),
    }

    call_command("seed_binary_indicator_questions")
    counts_2 = {
        "groups": BinaryIndicatorGroup.objects.count(),
        "questions": BinaryIndicatorQuestion.objects.count(),
        "grouped_questions": BinaryIndicatorQuestion.objects.exclude(group__isnull=True).count(),
    }

    assert counts_1 == counts_2
    assert counts_1["groups"] > 0
    assert counts_1["grouped_questions"] > 0


def test_binary_indicator_response_supports_shapes():
    call_command("seed_binary_indicator_questions")
    question = BinaryIndicatorQuestion.objects.first()
    instance = _make_instance()

    response_single = BinaryIndicatorResponse.objects.create(
        reporting_instance=instance,
        question=question,
        response=["no"],
    )
    assert response_single.response == ["no"]

    response_multi = BinaryIndicatorResponse.objects.create(
        reporting_instance=instance,
        question=BinaryIndicatorQuestion.objects.exclude(id=question.id).first(),
        response=["a", "b"],
    )
    assert response_multi.response == ["a", "b"]

    response_text = BinaryIndicatorResponse.objects.create(
        reporting_instance=instance,
        question=BinaryIndicatorQuestion.objects.exclude(id__in=[question.id, response_multi.question_id]).first(),
        response="free text",
    )
    assert response_text.response == "free text"


def test_binary_group_response_unique_per_instance_group():
    call_command("seed_binary_indicator_questions")
    instance = _make_instance()
    group = BinaryIndicatorGroup.objects.first()
    BinaryIndicatorGroupResponse.objects.create(reporting_instance=instance, group=group)
    with pytest.raises(IntegrityError):
        BinaryIndicatorGroupResponse.objects.create(reporting_instance=instance, group=group)
