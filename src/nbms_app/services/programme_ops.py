from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from nbms_app.models import (
    IndicatorMethodProfile,
    MonitoringProgramme,
    MonitoringProgrammeAlert,
    MonitoringProgrammeArtefactRef,
    MonitoringProgrammeQAResult,
    MonitoringProgrammeRun,
    MonitoringProgrammeRunStep,
    ProgrammeAlertSeverity,
    ProgrammeQaStatus,
    ProgrammeRefreshCadence,
    ProgrammeRunStatus,
    ProgrammeRunTrigger,
    ProgrammeRunType,
    ProgrammeStepType,
)
from nbms_app.services.indicator_method_sdk import run_method_profile
from nbms_app.services.audit import record_audit_event
from nbms_app.services.authorization import is_system_admin
from nbms_app.services.catalog_access import can_edit_monitoring_programme
from nbms_app.services.spatial_sources import sync_spatial_sources


CADENCE_DELTA_MAP = {
    ProgrammeRefreshCadence.DAILY: timedelta(days=1),
    ProgrammeRefreshCadence.WEEKLY: timedelta(days=7),
    ProgrammeRefreshCadence.MONTHLY: timedelta(days=30),
    ProgrammeRefreshCadence.QUARTERLY: timedelta(days=91),
    ProgrammeRefreshCadence.ANNUAL: timedelta(days=365),
}


DEFAULT_PIPELINE_STEPS = [
    {"key": "ingest", "type": ProgrammeStepType.INGEST},
    {"key": "validate", "type": ProgrammeStepType.VALIDATE},
    {"key": "compute", "type": ProgrammeStepType.COMPUTE},
    {"key": "publish", "type": ProgrammeStepType.PUBLISH},
]


def user_can_manage_programme(user, programme):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if is_system_admin(user):
        return True
    if can_edit_monitoring_programme(user, programme):
        return True
    return programme.steward_assignments.filter(user=user, is_active=True).exists()


def resolve_next_run_at(cadence, from_time=None):
    if cadence in {ProgrammeRefreshCadence.MANUAL, ProgrammeRefreshCadence.AD_HOC, ""}:
        return None
    base_time = from_time or timezone.now()
    delta = CADENCE_DELTA_MAP.get(cadence)
    if not delta:
        return None
    return base_time + delta


def create_programme_alert(
    *,
    programme,
    code,
    message,
    severity=ProgrammeAlertSeverity.WARNING,
    run=None,
    created_by=None,
    details=None,
):
    return MonitoringProgrammeAlert.objects.create(
        programme=programme,
        run=run,
        severity=severity,
        code=code,
        message=message,
        details_json=details or {},
        created_by=created_by,
    )


def _pipeline_steps(programme, run_type):
    configured_steps = (programme.pipeline_definition_json or {}).get("steps") or []
    if configured_steps:
        steps = []
        for item in configured_steps:
            step_type = (item.get("type") or "").strip().lower()
            if step_type not in ProgrammeStepType.values:
                continue
            steps.append(
                {
                    "key": (item.get("key") or step_type).strip() or step_type,
                    "type": step_type,
                }
            )
        if steps:
            return steps
    if run_type and run_type != ProgrammeRunType.FULL:
        return [{"key": run_type, "type": run_type}]
    return DEFAULT_PIPELINE_STEPS


def _minimum_rule_int(rules, key, default_value):
    value = rules.get(key, default_value)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default_value


def queue_programme_run(
    *,
    programme,
    requested_by=None,
    run_type=ProgrammeRunType.FULL,
    trigger=ProgrammeRunTrigger.MANUAL,
    dry_run=False,
    execute_now=True,
    request_id="",
):
    dataset_link_count = programme.dataset_links.filter(is_active=True).count()
    indicator_link_count = programme.indicator_links.filter(is_active=True).count()
    run = MonitoringProgrammeRun.objects.create(
        programme=programme,
        run_type=run_type,
        trigger=trigger,
        dry_run=bool(dry_run),
        requested_by=requested_by if getattr(requested_by, "is_authenticated", False) else None,
        input_summary_json={
            "dataset_link_count": dataset_link_count,
            "indicator_link_count": indicator_link_count,
        },
        request_id=request_id or "",
    )
    record_audit_event(
        requested_by,
        "programme_run_queued",
        run,
        metadata={
            "programme_uuid": str(programme.uuid),
            "run_type": run_type,
            "trigger": trigger,
            "dry_run": bool(dry_run),
        },
    )
    if execute_now:
        execute_programme_run(run=run, actor=requested_by)
    return run


def execute_programme_run(*, run, actor=None):
    if run.status == ProgrammeRunStatus.RUNNING:
        return run

    actor = actor if getattr(actor, "is_authenticated", False) else run.requested_by
    programme = run.programme
    now = timezone.now()
    run.status = ProgrammeRunStatus.RUNNING
    run.started_at = now
    run.error_message = ""
    run.save(update_fields=["status", "started_at", "error_message", "updated_at"])
    record_audit_event(
        actor,
        "programme_run_started",
        run,
        metadata={"programme_uuid": str(programme.uuid), "run_type": run.run_type},
    )

    rules = programme.data_quality_rules_json or {}
    min_datasets = _minimum_rule_int(rules, "minimum_dataset_links", 1)
    min_indicators = _minimum_rule_int(rules, "minimum_indicator_links", 1)
    dataset_link_count = programme.dataset_links.filter(is_active=True).count()
    indicator_link_count = programme.indicator_links.filter(is_active=True).count()

    final_status = ProgrammeRunStatus.SUCCEEDED
    run_errors = []
    step_summaries = []
    steps = _pipeline_steps(programme, run.run_type)

    for index, step in enumerate(steps, start=1):
        step_obj = MonitoringProgrammeRunStep.objects.create(
            run=run,
            ordering=index,
            step_key=step["key"],
            step_type=step["type"],
            status=ProgrammeRunStatus.RUNNING,
            started_at=timezone.now(),
        )
        step_state = ProgrammeRunStatus.SUCCEEDED
        step_details = {
            "dry_run": run.dry_run,
            "dataset_link_count": dataset_link_count,
            "indicator_link_count": indicator_link_count,
        }

        if step["type"] == ProgrammeStepType.INGEST and programme.programme_code == "NBMS-BIRDIE-INTEGRATION":
            if run.dry_run:
                step_details["integration"] = {"source": "BIRDIE", "dry_run": True}
            else:
                from nbms_app.integrations.birdie.service import ingest_birdie_snapshot

                ingest_summary = ingest_birdie_snapshot(actor=actor)
                step_details["integration"] = {"source": "BIRDIE", "summary": ingest_summary}

        if step["type"] == ProgrammeStepType.INGEST and programme.programme_code == "NBMS-SPATIAL-BASELINES":
            if run.dry_run:
                step_details["integration"] = {"source": "spatial_sources", "dry_run": True}
            else:
                spatial_summary = sync_spatial_sources(
                    actor=actor,
                    include_optional=False,
                    force=False,
                    dry_run=False,
                    seed_defaults=True,
                )
                step_details["integration"] = {"source": "spatial_sources", "summary": spatial_summary}
                for row in spatial_summary.get("results", []):
                    storage_path = row.get("storage_path") or ""
                    if storage_path:
                        MonitoringProgrammeArtefactRef.objects.create(
                            run=run,
                            step=step_obj,
                            label=f"{row.get('source_code', 'source')}-raw",
                            storage_path=storage_path,
                            media_type="application/zip",
                            checksum_sha256=row.get("checksum", ""),
                            metadata_json={
                                "source_code": row.get("source_code"),
                                "layer_code": row.get("layer_code"),
                                "run_id": row.get("run_id"),
                            },
                        )
                    qa_status = {
                        "ready": ProgrammeQaStatus.PASS,
                        "skipped": ProgrammeQaStatus.WARN,
                        "blocked": ProgrammeQaStatus.FAIL,
                        "failed": ProgrammeQaStatus.FAIL,
                    }.get(row.get("status"), ProgrammeQaStatus.WARN)
                    MonitoringProgrammeQAResult.objects.create(
                        run=run,
                        step=step_obj,
                        code=f"SPATIAL_SOURCE_{row.get('source_code', 'unknown')}",
                        status=qa_status,
                        message=row.get("detail") or row.get("status") or "No detail provided.",
                        details_json=row,
                    )
                failed_count = int(spatial_summary.get("status_counts", {}).get("failed", 0))
                blocked_count = int(spatial_summary.get("status_counts", {}).get("blocked", 0))
                if failed_count:
                    step_state = ProgrammeRunStatus.FAILED
                    final_status = ProgrammeRunStatus.FAILED
                    run_errors.append(f"Spatial source sync failed for {failed_count} source(s).")
                elif blocked_count:
                    step_state = ProgrammeRunStatus.BLOCKED
                    final_status = ProgrammeRunStatus.BLOCKED
                    run_errors.append(f"Spatial source sync blocked for {blocked_count} source(s).")

        if step["type"] == ProgrammeStepType.COMPUTE and programme.programme_code == "NBMS-BIRDIE-INTEGRATION":
            profiles = IndicatorMethodProfile.objects.filter(
                indicator__code__startswith="BIRDIE-",
                is_active=True,
            ).order_by("indicator__code", "method_type", "id")[:20]
            method_runs = []
            for profile in profiles:
                method_run = run_method_profile(profile=profile, user=actor, params={"programme_run": str(run.uuid)})
                method_runs.append(
                    {
                        "profile_uuid": str(profile.uuid),
                        "indicator_code": profile.indicator.code,
                        "status": method_run.status,
                    }
                )
            step_details["method_runs"] = method_runs

        if step["type"] == ProgrammeStepType.VALIDATE:
            problems = []
            if dataset_link_count < min_datasets:
                problems.append(f"Requires at least {min_datasets} active dataset links.")
            if indicator_link_count < min_indicators:
                problems.append(f"Requires at least {min_indicators} active indicator links.")
            if problems:
                step_state = ProgrammeRunStatus.BLOCKED
                final_status = ProgrammeRunStatus.BLOCKED
                problem_text = " ".join(problems)
                run_errors.append(problem_text)
                create_programme_alert(
                    programme=programme,
                    run=run,
                    code="PROGRAMME_QA_THRESHOLD",
                    severity=ProgrammeAlertSeverity.WARNING,
                    message=problem_text,
                    created_by=actor,
                    details={
                        "minimum_dataset_links": min_datasets,
                        "minimum_indicator_links": min_indicators,
                        "dataset_link_count": dataset_link_count,
                        "indicator_link_count": indicator_link_count,
                    },
                )
            step_details["checks"] = {
                "minimum_dataset_links": min_datasets,
                "minimum_indicator_links": min_indicators,
            }

        if step["type"] == ProgrammeStepType.PUBLISH and run.dry_run:
            step_details["note"] = "Dry-run mode skipped publication side effects."

        step_obj.status = step_state
        step_obj.finished_at = timezone.now()
        step_obj.details_json = step_details
        if run_errors:
            step_obj.log_excerpt = run_errors[-1]
        step_obj.save(update_fields=["status", "finished_at", "details_json", "log_excerpt", "updated_at"])

        step_summaries.append(
            {
                "ordering": index,
                "step_key": step_obj.step_key,
                "step_type": step_obj.step_type,
                "status": step_obj.status,
            }
        )
        if step_state in {ProgrammeRunStatus.BLOCKED, ProgrammeRunStatus.FAILED}:
            break

    if final_status == ProgrammeRunStatus.SUCCEEDED and run_errors:
        final_status = ProgrammeRunStatus.FAILED

    finished = timezone.now()
    run.status = final_status
    run.finished_at = finished
    run.log_excerpt = "\n".join(run_errors[:10]) if run_errors else "Programme run completed."
    run.error_message = "\n".join(run_errors) if run_errors else ""
    run.output_summary_json = {
        "step_count": len(step_summaries),
        "status_counts": {
            "succeeded": len([item for item in step_summaries if item["status"] == ProgrammeRunStatus.SUCCEEDED]),
            "blocked": len([item for item in step_summaries if item["status"] == ProgrammeRunStatus.BLOCKED]),
            "failed": len([item for item in step_summaries if item["status"] == ProgrammeRunStatus.FAILED]),
        },
        "qa_counts": {
            "pass": run.qa_results.filter(status=ProgrammeQaStatus.PASS).count(),
            "warn": run.qa_results.filter(status=ProgrammeQaStatus.WARN).count(),
            "fail": run.qa_results.filter(status=ProgrammeQaStatus.FAIL).count(),
        },
        "artefact_count": run.artefacts.count(),
        "open_alerts": programme.alerts.filter(state="open").count(),
    }
    run.lineage_json = {
        "programme_uuid": str(programme.uuid),
        "run_uuid": str(run.uuid),
        "steps": step_summaries,
    }
    run.save(
        update_fields=[
            "status",
            "finished_at",
            "log_excerpt",
            "error_message",
            "output_summary_json",
            "lineage_json",
            "updated_at",
        ]
    )

    programme.last_run_at = finished
    programme.next_run_at = resolve_next_run_at(programme.refresh_cadence, from_time=finished)
    programme.save(update_fields=["last_run_at", "next_run_at", "updated_at"])

    event_action = {
        ProgrammeRunStatus.SUCCEEDED: "programme_run_succeeded",
        ProgrammeRunStatus.BLOCKED: "programme_run_blocked",
        ProgrammeRunStatus.FAILED: "programme_run_failed",
    }.get(final_status, "programme_run_updated")
    record_audit_event(
        actor,
        event_action,
        run,
        metadata={
            "programme_uuid": str(programme.uuid),
            "status": final_status,
            "run_type": run.run_type,
            "dry_run": run.dry_run,
        },
    )
    return run


@transaction.atomic
def process_due_programmes(*, actor=None, limit=20):
    now = timezone.now()
    queued_runs = []
    programmes = (
        MonitoringProgramme.objects.filter(is_active=True, scheduler_enabled=True)
        .filter(Q(next_run_at__isnull=True) | Q(next_run_at__lte=now))
        .order_by("next_run_at", "programme_code", "uuid")[: max(1, int(limit))]
    )
    for programme in programmes:
        run = queue_programme_run(
            programme=programme,
            requested_by=actor,
            run_type=ProgrammeRunType.FULL,
            trigger=ProgrammeRunTrigger.SCHEDULED,
            dry_run=False,
            execute_now=True,
        )
        queued_runs.append(run)
    return queued_runs
