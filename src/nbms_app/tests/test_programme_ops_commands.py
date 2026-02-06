from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from nbms_app.models import MonitoringProgramme, MonitoringProgrammeRun, Organisation, ProgrammeRefreshCadence


pytestmark = pytest.mark.django_db


def test_seed_programme_ops_v1_command_is_idempotent():
    call_command("seed_programme_ops_v1")
    call_command("seed_programme_ops_v1")

    assert MonitoringProgramme.objects.filter(programme_code="NBMS-CORE-PROGRAMME").exists()
    assert MonitoringProgramme.objects.filter(programme_code="NBMS-BIRDIE-INTEGRATION").exists()
    core = MonitoringProgramme.objects.get(programme_code="NBMS-CORE-PROGRAMME")
    birdie = MonitoringProgramme.objects.get(programme_code="NBMS-BIRDIE-INTEGRATION")
    assert core.runs.exists()
    assert birdie.runs.exists()


def test_run_monitoring_programmes_processes_due_programmes():
    org = Organisation.objects.create(name="Scheduler Org", org_code="SCH-ORG")
    programme = MonitoringProgramme.objects.create(
        programme_code="PROG-SCHED-1",
        title="Scheduled Programme",
        lead_org=org,
        refresh_cadence=ProgrammeRefreshCadence.DAILY,
        scheduler_enabled=True,
        next_run_at=timezone.now() - timedelta(hours=2),
        pipeline_definition_json={"steps": [{"key": "validate", "type": "validate"}]},
        data_quality_rules_json={"minimum_dataset_links": 0, "minimum_indicator_links": 0},
    )

    call_command("run_monitoring_programmes", "--limit", "5")

    programme.refresh_from_db()
    assert programme.last_run_at is not None
    assert programme.next_run_at is not None
    runs = MonitoringProgrammeRun.objects.filter(programme=programme).order_by("-created_at")
    assert runs.exists()
    assert runs.first().status in {"succeeded", "blocked"}
