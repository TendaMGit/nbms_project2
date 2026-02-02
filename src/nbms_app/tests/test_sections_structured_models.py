import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

from nbms_app.models import (
    BinaryIndicatorGroup,
    BinaryIndicatorQuestion,
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


def test_section_ii_valid_minimum_passes():
    instance = _make_instance()
    status = SectionIINBSAPStatus(
        reporting_instance=instance,
        nbsap_updated_status=NbsapStatus.YES,
        stakeholders_involved=StakeholderInvolvement.NO,
        nbsap_adopted_status=NbsapStatus.NO,
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
