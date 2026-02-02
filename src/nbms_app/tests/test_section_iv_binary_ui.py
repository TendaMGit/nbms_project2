import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from nbms_app.models import (
    BinaryIndicatorGroup,
    BinaryIndicatorGroupResponse,
    BinaryIndicatorQuestion,
    BinaryIndicatorResponse,
    Framework,
    FrameworkIndicator,
    FrameworkIndicatorType,
    FrameworkTarget,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
    LifecycleStatus,
)
from nbms_app.services.authorization import ROLE_DATA_STEWARD


pytestmark = pytest.mark.django_db


def _create_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-BIN",
        title="Cycle BIN",
        start_date="2025-01-01",
        end_date="2025-12-31",
        due_date="2026-01-31",
        is_active=True,
    )
    return ReportingInstance.objects.create(cycle=cycle)


def _create_staff_user(org, username="staff-bin"):
    user = User.objects.create_user(
        username=username,
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=ROLE_DATA_STEWARD)
    user.groups.add(group)
    return user


def _create_indicator(org):
    framework = Framework.objects.create(code="GBF", title="GBF")
    target = FrameworkTarget.objects.create(
        framework=framework,
        code="T-1",
        title="Target 1",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    indicator = FrameworkIndicator.objects.create(
        framework=framework,
        framework_target=target,
        code="BIN-1",
        title="Binary 1",
        indicator_type=FrameworkIndicatorType.BINARY,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    return target, indicator


def test_binary_indicator_group_save_and_header_behavior(client):
    org = Organisation.objects.create(name="Org A")
    user = _create_staff_user(org)
    instance = _create_instance()

    BinaryIndicatorQuestion.objects.all().delete()
    BinaryIndicatorGroup.objects.all().delete()

    target, indicator = _create_indicator(org)
    group = BinaryIndicatorGroup.objects.create(
        key="group-test",
        framework_target=target,
        framework_indicator=indicator,
        target_code="GBF-TARGET-1",
    )
    header = BinaryIndicatorQuestion.objects.create(
        framework_indicator=indicator,
        group=group,
        group_key="group-test",
        question_key="header",
        question_type="text",
        question_text="Header",
        number="H1",
        sort_order=0,
    )
    q_single = BinaryIndicatorQuestion.objects.create(
        framework_indicator=indicator,
        group=group,
        group_key="group-test",
        question_key="q1",
        question_type="single",
        question_text="Question 1",
        number="1.1",
        sort_order=1,
        mandatory=True,
        options=[{"value": "yes", "label_key": "yes"}, {"value": "no", "label_key": "no"}],
        parent_question=header,
    )
    q_text = BinaryIndicatorQuestion.objects.create(
        framework_indicator=indicator,
        group=group,
        group_key="group-test",
        question_key="q2",
        question_type="text",
        question_text="Question 2",
        number="1.2",
        sort_order=2,
    )

    client.force_login(user)
    url = reverse("nbms_app:reporting_instance_section_iv_binary_indicators", args=[instance.uuid])
    resp = client.post(
        url,
        data={
            f"group_comment_{group.id}": "Comment",
            f"q_{header.id}": "Ignored",
            f"q_{q_single.id}": "yes",
            f"q_{q_text.id}": "Some text",
        },
    )
    assert resp.status_code == 302

    assert BinaryIndicatorGroupResponse.objects.filter(reporting_instance=instance, group=group).count() == 1
    assert BinaryIndicatorResponse.objects.filter(reporting_instance=instance, question=q_single).count() == 1
    assert BinaryIndicatorResponse.objects.filter(reporting_instance=instance, question=q_text).count() == 1
    assert BinaryIndicatorResponse.objects.filter(reporting_instance=instance, question=header).count() == 0


def test_binary_indicator_ordering(client):
    org = Organisation.objects.create(name="Org B")
    user = _create_staff_user(org, "staff-order")
    instance = _create_instance()

    BinaryIndicatorQuestion.objects.all().delete()
    BinaryIndicatorGroup.objects.all().delete()

    target, indicator = _create_indicator(org)
    group = BinaryIndicatorGroup.objects.create(
        key="group-order",
        framework_target=target,
        framework_indicator=indicator,
        target_code="GBF-TARGET-1",
        ordering=1,
    )
    q1 = BinaryIndicatorQuestion.objects.create(
        framework_indicator=indicator,
        group=group,
        group_key="group-order",
        question_key="q1",
        question_type="single",
        question_text="Question 1",
        number="B.1",
        sort_order=0,
        options=[{"value": "a", "label_key": "a"}],
    )
    q10 = BinaryIndicatorQuestion.objects.create(
        framework_indicator=indicator,
        group=group,
        group_key="group-order",
        question_key="q10",
        question_type="single",
        question_text="Question 10",
        number="B.10",
        sort_order=0,
        options=[{"value": "a", "label_key": "a"}],
    )
    q2 = BinaryIndicatorQuestion.objects.create(
        framework_indicator=indicator,
        group=group,
        group_key="group-order",
        question_key="q2",
        question_type="single",
        question_text="Question 2",
        number="B.2",
        sort_order=0,
        options=[{"value": "a", "label_key": "a"}],
    )

    client.force_login(user)
    url = reverse("nbms_app:reporting_instance_section_iv_binary_indicators", args=[instance.uuid])
    resp = client.get(url)
    assert resp.status_code == 200
    group_item = None
    for item in resp.context["groups"]:
        if item["group"].key == "group-order":
            group_item = item
            break
    assert group_item is not None
    numbers = [q["question"].number for q in group_item["questions"]]
    assert numbers == ["B.1", "B.10", "B.2"]
