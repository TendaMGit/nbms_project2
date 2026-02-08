import pytest

from nbms_app.models import MonitoringProgramme, ProgrammeRunStatus
from nbms_app.services.programme_ops import queue_programme_run


pytestmark = pytest.mark.django_db


def test_spatial_baselines_programme_records_qa_and_artefacts(monkeypatch):
    programme = MonitoringProgramme.objects.create(
        programme_code="NBMS-SPATIAL-BASELINES",
        title="Spatial Baselines Programme",
        scheduler_enabled=False,
        pipeline_definition_json={"steps": [{"key": "ingest_sources", "type": "ingest"}]},
        data_quality_rules_json={"minimum_dataset_links": 0, "minimum_indicator_links": 0},
    )

    monkeypatch.setattr(
        "nbms_app.services.programme_ops.sync_spatial_sources",
        lambda **kwargs: {
            "status_counts": {"ready": 1, "skipped": 0, "blocked": 0, "failed": 0},
            "results": [
                {
                    "source_code": "NE_ADMIN1_ZA",
                    "layer_code": "ZA_PROVINCES_NE",
                    "status": "ready",
                    "detail": "Ingestion succeeded.",
                    "rows_ingested": 9,
                    "checksum": "abc123",
                    "storage_path": "spatial/sources/ne_admin1_za/abc123-file.zip",
                    "run_id": "spatial-run-1",
                }
            ],
        },
    )

    run = queue_programme_run(programme=programme, run_type="full", dry_run=False, execute_now=True)
    run.refresh_from_db()

    assert run.status == ProgrammeRunStatus.SUCCEEDED
    assert run.artefacts.count() >= 1
    assert run.qa_results.count() >= 1
    assert run.artefacts.filter(label="run-report-json").exists()
    assert run.qa_results.first().status == "pass"
