from __future__ import annotations

import hashlib
import json

from django.core.cache import cache
from django.db.models import Max
from django.utils import timezone

from nbms_app.indicator_methods.base import MethodContext
from nbms_app.indicator_methods.registry import get_method
from nbms_app.models import (
    BinaryIndicatorResponse,
    IndicatorDataPoint,
    IndicatorFrameworkIndicatorLink,
    IndicatorMethodReadiness,
    IndicatorMethodRun,
    IndicatorMethodRunStatus,
    IndicatorMethodType,
    SpatialFeature,
)
from nbms_app.services.audit import record_audit_event


def _latest_input_stamp(profile):
    indicator = profile.indicator
    if profile.method_type == IndicatorMethodType.CSV_IMPORT:
        return (
            IndicatorDataPoint.objects.filter(series__indicator=indicator).aggregate(value=Max("updated_at")).get("value")
        )
    if profile.method_type == IndicatorMethodType.BINARY_QUESTIONNAIRE:
        framework_indicator_ids = IndicatorFrameworkIndicatorLink.objects.filter(
            indicator=indicator,
            is_active=True,
        ).values_list("framework_indicator_id", flat=True)
        return (
            BinaryIndicatorResponse.objects.filter(question__framework_indicator_id__in=framework_indicator_ids).aggregate(
                value=Max("updated_at")
            ).get("value")
        )
    if profile.method_type == IndicatorMethodType.SPATIAL_OVERLAY:
        return SpatialFeature.objects.filter(indicator=indicator).aggregate(value=Max("updated_at")).get("value")
    return indicator.updated_at


def _build_input_hash(profile, params, input_stamp):
    blob = {
        "profile_uuid": str(profile.uuid),
        "indicator_uuid": str(profile.indicator.uuid),
        "method_type": profile.method_type,
        "implementation_key": profile.implementation_key,
        "params": params or {},
        "input_stamp": input_stamp.isoformat() if input_stamp else None,
    }
    payload = json.dumps(blob, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_method_profile(*, profile, user=None, params=None, use_cache=True):
    params = params or {}
    now = timezone.now()
    run = IndicatorMethodRun.objects.create(
        profile=profile,
        status=IndicatorMethodRunStatus.BLOCKED,
        started_at=now,
        requested_by=user if getattr(user, "is_authenticated", False) else None,
        parameters_json=params,
    )

    method = get_method(profile.implementation_key)
    if not method:
        run.status = IndicatorMethodRunStatus.FAILED
        run.error_message = f"No implementation registered for key '{profile.implementation_key}'."
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        profile.last_run_at = run.finished_at
        profile.readiness_state = IndicatorMethodReadiness.BLOCKED
        profile.readiness_notes = run.error_message
        profile.save(update_fields=["last_run_at", "readiness_state", "readiness_notes", "updated_at"])
        return run

    input_stamp = _latest_input_stamp(profile)
    input_hash = _build_input_hash(profile, params, input_stamp)
    run.input_hash = input_hash

    cache_key = f"indicator_method:{input_hash}"
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            run.status = IndicatorMethodRunStatus.SUCCEEDED
            run.output_json = {**cached, "cache_hit": True}
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "output_json", "finished_at", "input_hash", "updated_at"])
            profile.last_run_at = run.finished_at
            profile.last_success_at = run.finished_at
            profile.readiness_state = IndicatorMethodReadiness.READY
            profile.readiness_notes = "Method execution succeeded (cache hit)."
            profile.save(
                update_fields=[
                    "last_run_at",
                    "last_success_at",
                    "readiness_state",
                    "readiness_notes",
                    "updated_at",
                ]
            )
            record_audit_event(
                user,
                "indicator_method_run",
                run,
                metadata={
                    "profile_uuid": str(profile.uuid),
                    "status": run.status,
                    "cache_hit": True,
                },
            )
            return run

    result = method.run(MethodContext(indicator=profile.indicator, profile=profile, user=user, params=params))
    finished = timezone.now()
    mapped_status = {
        "succeeded": IndicatorMethodRunStatus.SUCCEEDED,
        "blocked": IndicatorMethodRunStatus.BLOCKED,
        "failed": IndicatorMethodRunStatus.FAILED,
    }.get(result.status, IndicatorMethodRunStatus.FAILED)

    run.status = mapped_status
    run.output_json = result.output
    run.error_message = result.error_message
    run.finished_at = finished
    run.save(
        update_fields=["status", "output_json", "error_message", "finished_at", "input_hash", "updated_at"]
    )

    profile.last_run_at = finished
    if mapped_status == IndicatorMethodRunStatus.SUCCEEDED:
        profile.last_success_at = finished
        profile.readiness_state = IndicatorMethodReadiness.READY
        profile.readiness_notes = "Method execution succeeded."
        if use_cache:
            cache.set(cache_key, result.output, timeout=3600)
    elif mapped_status == IndicatorMethodRunStatus.BLOCKED:
        profile.readiness_state = IndicatorMethodReadiness.PARTIAL
        profile.readiness_notes = result.error_message or "Method blocked due to missing inputs."
    else:
        profile.readiness_state = IndicatorMethodReadiness.BLOCKED
        profile.readiness_notes = result.error_message or "Method execution failed."

    profile.save(
        update_fields=[
            "last_run_at",
            "last_success_at",
            "readiness_state",
            "readiness_notes",
            "updated_at",
        ]
    )
    record_audit_event(
        user,
        "indicator_method_run",
        run,
        metadata={
            "profile_uuid": str(profile.uuid),
            "status": run.status,
            "cache_hit": False,
        },
    )
    return run
