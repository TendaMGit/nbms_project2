import pytest
from django.core.management import call_command

from nbms_app.management.commands.seed_end_to_end_demo import DEMO_CYCLE_CODE, DEMO_VERSION
from nbms_app.models import Indicator, Organisation, ReportingInstance
from nbms_app.services.readiness import compute_reporting_readiness


pytestmark = pytest.mark.django_db


def _get_demo_instance():
    return ReportingInstance.objects.get(cycle__code=DEMO_CYCLE_CODE, version_label=DEMO_VERSION)


def test_demo_seed_end_to_end_ready():
    call_command("seed_end_to_end_demo", apply=True, strict=True)

    instance = _get_demo_instance()
    readiness = compute_reporting_readiness(instance.uuid, scope="selected")
    summary = readiness["summary"]

    assert summary["overall_ready"] is True
    assert summary["blocking_gap_count"] == 0
    assert summary["total_indicators_in_scope"] >= 1


def test_demo_seed_idempotent():
    call_command("seed_end_to_end_demo", apply=True, strict=True)
    org_count = Organisation.objects.filter(org_code="DEMO-ORG").count()
    indicator_count = Indicator.objects.filter(code__startswith="DEMO-IND-").count()

    call_command("seed_end_to_end_demo", apply=True, strict=True)

    assert Organisation.objects.filter(org_code="DEMO-ORG").count() == org_count
    assert Indicator.objects.filter(code__startswith="DEMO-IND-").count() == indicator_count
