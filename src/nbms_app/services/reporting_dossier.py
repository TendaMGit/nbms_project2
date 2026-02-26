from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import django
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from nbms_app.models import (
    AuditEvent,
    DatasetRelease,
    Evidence,
    IndicatorEvidenceLink,
    ReportDossierArtifact,
    ReportSectionRevision,
    ReportTemplatePackResponse,
    ReportWorkflowAction,
    SectionIIINationalTargetProgress,
)
from nbms_app.services.audit import record_audit_event
from nbms_app.services.reporting_exports import (
    build_cbd_report_payload,
    render_cbd_docx_bytes,
    render_cbd_pdf_bytes,
    store_report_export_artifact,
)
from nbms_app.services.reporting_workflow import report_content_snapshot
from nbms_app.services.reporting_narratives import normalize_context_filters, render_section_narrative


def _canonical_json(value):
    return json.dumps(value or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _git_commit():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except Exception:  # noqa: BLE001
        return ""
    return (result.stdout or "").strip()


def _zip_write(zf, filename, payload):
    info = ZipInfo(filename=filename, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    zf.writestr(info, payload)


def _gather_evidence_manifest(instance):
    section_rows = SectionIIINationalTargetProgress.objects.filter(reporting_instance=instance).prefetch_related(
        "evidence_items",
        "indicator_data_series__indicator",
        "dataset_releases",
    )
    indicator_ids = set()
    linked_evidence_ids = set()
    for row in section_rows:
        linked_evidence_ids.update(row.evidence_items.values_list("id", flat=True))
        indicator_ids.update(
            row.indicator_data_series.exclude(indicator__isnull=True).values_list("indicator_id", flat=True)
        )
    if indicator_ids:
        linked_evidence_ids.update(
            IndicatorEvidenceLink.objects.filter(indicator_id__in=indicator_ids).values_list("evidence_id", flat=True)
        )

    evidence_rows = Evidence.objects.filter(id__in=linked_evidence_ids).order_by("title", "uuid")
    manifest = []
    for row in evidence_rows:
        manifest.append(
            {
                "uuid": str(row.uuid),
                "title": row.title,
                "type": row.evidence_type,
                "storage_ref": row.file.name if row.file else row.source_url,
                "checksum": "",
                "access_level": row.sensitivity,
            }
        )

    release_ids = set()
    for row in section_rows:
        release_ids.update(row.dataset_releases.values_list("id", flat=True))
    release_rows = DatasetRelease.objects.filter(id__in=release_ids).select_related("dataset").order_by(
        "dataset__title",
        "version",
        "uuid",
    )
    for row in release_rows:
        manifest.append(
            {
                "uuid": str(row.uuid),
                "title": f"{row.dataset.title} {row.version}" if row.dataset_id else row.version,
                "type": "dataset_release",
                "storage_ref": row.source_url or "",
                "checksum": "",
                "access_level": row.sensitivity,
            }
        )
    return manifest


def _revision_hash_chain(instance):
    rows = (
        ReportSectionRevision.objects.filter(section_response__reporting_instance=instance)
        .select_related("section_response__section", "author")
        .order_by("section_response__section__ordering", "section_response__section__code", "version", "id")
    )
    chain = []
    for row in rows:
        chain.append(
            {
                "section_code": row.section_response.section.code,
                "version": row.version,
                "hash": row.content_hash,
                "parent_hash": row.parent_hash,
                "author": row.author.username if row.author_id else None,
                "timestamp": row.created_at.isoformat(),
            }
        )
    return chain


def _workflow_audit_payload(instance):
    workflow_actions = ReportWorkflowAction.objects.filter(
        workflow_instance__reporting_instance=instance
    ).select_related("actor", "workflow_instance")
    comments_and_suggestions = AuditEvent.objects.filter(
        Q(action__startswith="report_"),
        object_uuid=instance.uuid,
    ).order_by("created_at", "id")
    return {
        "workflow_actions": [
            {
                "uuid": str(row.uuid),
                "workflow_instance_uuid": str(row.workflow_instance.uuid),
                "actor": row.actor.username if row.actor_id else None,
                "action_type": row.action_type,
                "comment": row.comment,
                "payload_hash": row.payload_hash,
                "created_at": row.created_at.isoformat(),
            }
            for row in workflow_actions.order_by("created_at", "id")
        ],
        "audit_events": [
            {
                "id": row.id,
                "action": row.action,
                "event_type": row.event_type,
                "object_type": row.object_type,
                "object_uuid": str(row.object_uuid) if row.object_uuid else None,
                "metadata": row.metadata,
                "created_at": row.created_at.isoformat(),
            }
            for row in comments_and_suggestions
        ],
    }


def generate_reporting_dossier(*, instance, user, linked_action=None, context_filters=None):
    payload = build_cbd_report_payload(instance=instance)
    context_filters = normalize_context_filters(context_filters)
    resolved_manifest = []
    for section in payload.get("sections", []):
        section_code = section.get("code")
        if not section_code:
            continue
        rendered = render_section_narrative(
            instance=instance,
            section_code=section_code,
            context_filters=context_filters,
        )
        section["rendered_narrative_html"] = rendered.get("rendered_html", "")
        section["resolved_values_manifest"] = rendered.get("resolved_values_manifest", [])
        resolved_manifest.extend(rendered.get("resolved_values_manifest", []))
    payload["context_filters"] = context_filters
    payload["resolved_values_manifest"] = resolved_manifest
    pdf_bytes = render_cbd_pdf_bytes(payload=payload)
    docx_bytes = render_cbd_docx_bytes(payload=payload)
    json_bytes = _canonical_json(payload).encode("utf-8")
    evidence_manifest = _gather_evidence_manifest(instance)
    audit_payload = _workflow_audit_payload(instance)
    revision_chain = _revision_hash_chain(instance)
    _snapshot_payload, report_hash, _pack = report_content_snapshot(instance)

    integrity = {
        "report_content_hash": report_hash,
        "revision_hash_chain": revision_chain,
        "export_hashes": {
            "pdf_hash": _hash_bytes(pdf_bytes),
            "docx_hash": _hash_bytes(docx_bytes),
            "json_hash": _hash_bytes(json_bytes),
        },
        "environment": {
            "git_commit": _git_commit(),
            "docker_image_tags": {
                "backend": "local",
                "frontend": "local",
            },
            "django_version": django.get_version(),
            "python_version": sys.version.split()[0],
        },
        "data_lineage": {
            "dataset_release_uuids": sorted(
                {
                    str(row.uuid)
                    for row in DatasetRelease.objects.filter(
                        section_iii_progress_entries__reporting_instance=instance
                    )
                }
            ),
            "registry_mart_refresh_timestamps": {},
        },
        "context": {
            "filters": context_filters,
            "resolved_values_count": len(resolved_manifest),
            "resolved_values_hash": _hash_bytes(_canonical_json(resolved_manifest).encode("utf-8")),
        },
    }

    visibility = {
        "is_public": bool(instance.is_public),
        "redaction_policy_summary": (
            "Public dossier" if instance.is_public else "Internal dossier restricted to authorized users."
        ),
    }

    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, mode="w", compression=ZIP_DEFLATED) as zf:
        _zip_write(zf, "submission.json", json_bytes)
        _zip_write(zf, "report.pdf", pdf_bytes)
        _zip_write(zf, "report.docx", docx_bytes)
        _zip_write(zf, "evidence_manifest.json", _canonical_json(evidence_manifest).encode("utf-8"))
        _zip_write(zf, "audit_log.json", _canonical_json(audit_payload).encode("utf-8"))
        _zip_write(zf, "integrity.json", _canonical_json(integrity).encode("utf-8"))
        _zip_write(zf, "visibility.json", _canonical_json(visibility).encode("utf-8"))
        if resolved_manifest:
            _zip_write(zf, "resolved_values_manifest.json", _canonical_json(resolved_manifest).encode("utf-8"))
    zip_bytes = zip_buffer.getvalue()

    pdf_artifact = store_report_export_artifact(
        instance=instance,
        generated_by=user,
        format_name="pdf",
        content_bytes=pdf_bytes,
        linked_action=linked_action,
        metadata={"source": "dossier"},
    )
    docx_artifact = store_report_export_artifact(
        instance=instance,
        generated_by=user,
        format_name="docx",
        content_bytes=docx_bytes,
        linked_action=linked_action,
        metadata={"source": "dossier"},
    )
    json_artifact = store_report_export_artifact(
        instance=instance,
        generated_by=user,
        format_name="json",
        content_bytes=json_bytes,
        linked_action=linked_action,
        metadata={"source": "dossier"},
    )
    dossier_export_artifact = store_report_export_artifact(
        instance=instance,
        generated_by=user,
        format_name="dossier",
        content_bytes=zip_bytes,
        linked_action=linked_action,
        metadata={"source": "dossier"},
    )

    dossier = ReportDossierArtifact.objects.create(
        reporting_instance=instance,
        storage_path=dossier_export_artifact.storage_path,
        content_hash=dossier_export_artifact.content_hash,
        manifest_json={
            "pdf_hash": pdf_artifact.content_hash,
            "docx_hash": docx_artifact.content_hash,
            "json_hash": json_artifact.content_hash,
            "dossier_hash": dossier_export_artifact.content_hash,
            "resolved_values_count": len(resolved_manifest),
        },
        generated_by=user if getattr(user, "is_authenticated", False) else None,
        linked_action=linked_action,
    )
    record_audit_event(
        user,
        "report_dossier_generated",
        instance,
        metadata={
            "dossier_uuid": str(dossier.uuid),
            "storage_path": dossier.storage_path,
            "content_hash": dossier.content_hash,
            "pdf_hash": pdf_artifact.content_hash,
            "docx_hash": docx_artifact.content_hash,
            "json_hash": json_artifact.content_hash,
            "context_filters": context_filters,
            "resolved_values_count": len(resolved_manifest),
        },
    )
    return dossier


def read_dossier_manifest(dossier):
    if not dossier:
        raise ValidationError("No dossier available.")
    return {
        "uuid": str(dossier.uuid),
        "storage_path": dossier.storage_path,
        "content_hash": dossier.content_hash,
        "manifest_json": dossier.manifest_json,
        "created_at": dossier.created_at.isoformat(),
    }
