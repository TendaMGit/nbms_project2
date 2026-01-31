import hashlib
import json
from pathlib import Path

import pytest
from django.core.management import call_command

from nbms_app.demo_constants import (
    DEMO_DATA_SERIES,
    DEMO_FRAMEWORK_TARGETS,
    DEMO_INDICATORS,
    DEMO_INSTANCE_UUID,
    DEMO_NATIONAL_TARGETS,
)
from nbms_app.models import (
    FrameworkTarget,
    Indicator,
    IndicatorDataSeries,
    NationalTarget,
    ReportingInstance,
    SectionIIINationalTargetProgress,
)


pytestmark = pytest.mark.django_db


def _hash_file(path):
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()


def test_demo_seed_idempotent():
    call_command("demo_seed", "--reset", "--confirm-reset")
    call_command("demo_seed")

    counts_1 = {
        "targets": NationalTarget.objects.filter(uuid__in=DEMO_NATIONAL_TARGETS.values()).count(),
        "indicators": Indicator.objects.filter(uuid__in=DEMO_INDICATORS.values()).count(),
        "framework_targets": FrameworkTarget.objects.filter(code__in=DEMO_FRAMEWORK_TARGETS.keys()).count(),
        "series": IndicatorDataSeries.objects.filter(uuid__in=DEMO_DATA_SERIES.values()).count(),
        "section_iii": SectionIIINationalTargetProgress.objects.filter(
            reporting_instance__uuid=DEMO_INSTANCE_UUID
        ).count(),
    }

    call_command("demo_seed")

    counts_2 = {
        "targets": NationalTarget.objects.filter(uuid__in=DEMO_NATIONAL_TARGETS.values()).count(),
        "indicators": Indicator.objects.filter(uuid__in=DEMO_INDICATORS.values()).count(),
        "framework_targets": FrameworkTarget.objects.filter(code__in=DEMO_FRAMEWORK_TARGETS.keys()).count(),
        "series": IndicatorDataSeries.objects.filter(uuid__in=DEMO_DATA_SERIES.values()).count(),
        "section_iii": SectionIIINationalTargetProgress.objects.filter(
            reporting_instance__uuid=DEMO_INSTANCE_UUID
        ).count(),
    }

    assert counts_1 == counts_2


def test_demo_verify_hash_deterministic(tmp_path):
    call_command("demo_seed", "--reset", "--confirm-reset", "--ready")
    call_command("demo_verify", "--resolve-blockers", f"--output-dir={tmp_path}")
    export_path = tmp_path / "demo_ort_nr7_v2.json"
    hash_1 = _hash_file(export_path)

    call_command("demo_verify", "--resolve-blockers", f"--output-dir={tmp_path}")
    hash_2 = _hash_file(export_path)

    assert hash_1 == hash_2
