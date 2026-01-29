import pytest
from django.core.exceptions import ValidationError

from nbms_app.models import Framework, FrameworkGoal, FrameworkIndicator, FrameworkTarget


@pytest.mark.django_db
def test_framework_target_cross_framework_clean_and_save():
    framework_a = Framework.objects.create(code="FW-A", title="Framework A")
    framework_b = Framework.objects.create(code="FW-B", title="Framework B")
    goal_a = FrameworkGoal.objects.create(framework=framework_a, code="A", title="Goal A")

    target = FrameworkTarget(framework=framework_b, goal=goal_a, code="T-1", title="Target")
    with pytest.raises(ValidationError):
        target.full_clean()

    with pytest.raises(ValidationError):
        target.save()


@pytest.mark.django_db
def test_framework_indicator_cross_framework_clean_and_save():
    framework_a = Framework.objects.create(code="FW-A", title="Framework A")
    framework_b = Framework.objects.create(code="FW-B", title="Framework B")
    target_a = FrameworkTarget.objects.create(framework=framework_a, code="T-A", title="Target A")

    indicator = FrameworkIndicator(
        framework=framework_b,
        framework_target=target_a,
        code="I-1",
        title="Indicator",
    )
    with pytest.raises(ValidationError):
        indicator.full_clean()

    with pytest.raises(ValidationError):
        indicator.save()
