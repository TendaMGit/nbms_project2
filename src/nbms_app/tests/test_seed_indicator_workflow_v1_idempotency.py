import pytest
from django.core.management import call_command

from nbms_app.models import Dataset, Evidence, IndicatorDataSeries


pytestmark = pytest.mark.django_db


def test_seed_indicator_workflow_v1_is_idempotent_with_codes():
    call_command("seed_indicator_workflow_v1")
    call_command("seed_indicator_workflow_v1")

    assert Dataset.objects.filter(dataset_code__startswith="DS-NBMS-GBF-").count() == 4
    assert Evidence.objects.filter(evidence_code__startswith="EV-NBMS-GBF-").count() == 4
    assert IndicatorDataSeries.objects.filter(series_code__startswith="SER-NBMS-GBF-").count() == 4
