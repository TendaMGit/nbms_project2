import pytest
from django.core.management import call_command

from nbms_app.models import (
    Framework,
    Indicator,
    MonitoringProgramme,
    ProgrammeIndicatorLink,
)


pytestmark = pytest.mark.django_db


def test_seed_indicator_workflow_v1_is_idempotent():
    call_command("seed_indicator_workflow_v1")
    call_command("seed_indicator_workflow_v1")

    expected = {
        "NBMS-GBF-ECOSYSTEM-EXTENT",
        "NBMS-GBF-ECOSYSTEM-THREAT",
        "NBMS-GBF-ECOSYSTEM-PROTECTION",
        "NBMS-GBF-SPECIES-THREAT",
        "NBMS-GBF-SPECIES-PROTECTION",
        "NBMS-GBF-PA-COVERAGE",
        "NBMS-GBF-IAS-PRESSURE",
        "NBMS-GBF-RESTORATION-PROGRESS",
        "NBMS-GBF-SPECIES-HABITAT-INDEX",
        "NBMS-GBF-GENETIC-DIVERSITY",
    }
    codes = set(Indicator.objects.values_list("code", flat=True))
    assert expected.issubset(codes)

    programme = MonitoringProgramme.objects.get(programme_code="NBMS-MONITORING-CORE")
    assert ProgrammeIndicatorLink.objects.filter(programme=programme).count() >= 10
    assert Framework.objects.filter(code="GBF").exists()
