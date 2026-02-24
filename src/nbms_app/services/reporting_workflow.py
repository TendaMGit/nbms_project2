from __future__ import annotations

import hashlib
import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from nbms_app.models import (
    ReportExportArtifact,
    ReportSignoffRecord,
    ReportTemplatePack,
    ReportTemplatePackResponse,
    ReportWorkflowAction,
    ReportWorkflowActionType,
    ReportWorkflowDefinition,
    ReportWorkflowInstance,
    ReportWorkflowSectionApproval,
    ReportWorkflowStatus,
    ReportingSnapshot,
    ReportingStatus,
    SectionIIINationalTargetProgress,
)
from nbms_app.services.audit import record_audit_event
from nbms_app.services.authorization import (
    ROLE_ADMIN,
    ROLE_DATA_STEWARD,
    ROLE_PUBLISHING_AUTHORITY,
    ROLE_SECRETARIAT,
    ROLE_SECTION_LEAD,
    ROLE_TECHNICAL_COMMITTEE,
    is_system_admin,
    user_has_role,
)
from nbms_app.services.reporting_collab import payload_hash
from nbms_app.services.reporting_exports import (
    build_cbd_report_payload,
    render_cbd_docx_bytes,
    render_cbd_pdf_bytes,
    store_report_export_artifact,
)
from nbms_app.services.template_packs import build_default_response_payload, build_pack_validation


CBD_PACK_CODES = ("cbd_national_report_v1", "cbd_ort_nr7_v2")
REPORT_WORKFLOW_NAME = "cbd_national_report_signoff_v2"

DEFAULT_SIGNOFF_STEPS = [
    {"code": "draft", "title": "Draft", "role": "Author"},
    {"code": "in_progress", "title": "In Progress", "role": "Author"},
    {"code": "internal_review", "title": "Internal Review", "role": "SectionLead"},
    {"code": "technical_committee_review", "title": "Technical Committee Review", "role": "TechnicalCommittee"},
    {"code": "technical_committee_approved", "title": "Technical Committee Approved", "role": "TechnicalCommittee"},
    {"code": "dffe_clearance", "title": "DFFE Clearance", "role": "Secretariat"},
    {"code": "final_signed_off", "title": "Final Signed-off", "role": "PublishingAuthority"},
    {"code": "frozen", "title": "Frozen", "role": "PublishingAuthority"},
    {"code": "submitted", "title": "Submitted", "role": "System"},
    {"code": "public_released", "title": "Public Released", "role": "System"},
]


def _canonical_json(value):
    return json.dumps(value or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _hash_payload(value):
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def resolve_cbd_pack():
    for code in CBD_PACK_CODES:
        pack = ReportTemplatePack.objects.filter(code=code, is_active=True).first()
        if pack:
            return pack
    raise ValidationError("CBD National Report template pack is not seeded.")


def report_content_snapshot(instance):
    pack = resolve_cbd_pack()
    sections = list(pack.sections.filter(is_active=True).order_by("ordering", "code"))
    response_map = {
        row.section_id: row.response_json
        for row in ReportTemplatePackResponse.objects.filter(
            reporting_instance=instance,
            section__pack=pack,
        ).select_related("section")
    }
    payload_sections = []
    for section in sections:
        response_json = response_map.get(section.id)
        if response_json is None:
            response_json = build_default_response_payload(section)
        payload_sections.append(
            {
                "code": section.code,
                "title": section.title,
                "ordering": section.ordering,
                "response": response_json,
            }
        )
    payload = {
        "instance_uuid": str(instance.uuid),
        "cycle_code": instance.cycle.code if instance.cycle_id else "",
        "report_family": instance.report_family,
        "report_label": instance.report_label,
        "version_label": instance.version_label,
        "reporting_period_start": (
            instance.reporting_period_start.isoformat() if instance.reporting_period_start else None
        ),
        "reporting_period_end": (
            instance.reporting_period_end.isoformat() if instance.reporting_period_end else None
        ),
        "is_public": bool(instance.is_public),
        "sections": payload_sections,
    }
    return payload, payload_hash(payload), pack


def ensure_workflow_definition():
    definition, _ = ReportWorkflowDefinition.objects.update_or_create(
        object_type="reporting_instance",
        name=REPORT_WORKFLOW_NAME,
        defaults={
            "steps_json": DEFAULT_SIGNOFF_STEPS,
            "is_active": True,
        },
    )
    return definition


def ensure_workflow_instance(instance):
    definition = ensure_workflow_definition()
    workflow = (
        ReportWorkflowInstance.objects.filter(
            reporting_instance=instance,
            status=ReportWorkflowStatus.ACTIVE,
        )
        .select_related("definition")
        .order_by("-created_at", "-id")
        .first()
    )
    if workflow:
        return workflow
    workflow = ReportWorkflowInstance.objects.create(
        definition=definition,
        reporting_instance=instance,
        status=ReportWorkflowStatus.ACTIVE,
        current_step=ReportingStatus.DRAFT,
        started_at=timezone.now(),
    )
    _ensure_section_approval_rows(workflow)
    return workflow


def _ensure_section_approval_rows(workflow):
    pack = resolve_cbd_pack()
    for section in pack.sections.filter(is_active=True).order_by("ordering", "code"):
        ReportWorkflowSectionApproval.objects.get_or_create(
            workflow_instance=workflow,
            section=section,
        )


def _require_role(user, *roles):
    if is_system_admin(user):
        return
    if not user_has_role(user, *roles):
        raise PermissionDenied("Not allowed to perform this workflow action.")


def _all_sections_approved(workflow):
    approvals = workflow.section_approvals.select_related("section").all()
    if not approvals:
        return False
    return all(item.approved for item in approvals)


def _has_minimum_evidence(instance):
    # Structured Section III evidence gate.
    section_iii = SectionIIINationalTargetProgress.objects.filter(reporting_instance=instance).prefetch_related(
        "evidence_items",
        "dataset_releases",
    )
    for row in section_iii:
        if row.evidence_items.exists() or row.dataset_releases.exists():
            return True

    # Pack-level fallback gate for workspace JSON data.
    pack = resolve_cbd_pack()
    section_iii_pack = pack.sections.filter(code="section-iii", is_active=True).first()
    if not section_iii_pack:
        return False
    response = ReportTemplatePackResponse.objects.filter(
        reporting_instance=instance,
        section=section_iii_pack,
    ).first()
    rows = ((response.response_json or {}).get("target_progress_rows") or []) if response else []
    for row in rows:
        for key in ("evidence_links", "dataset_links", "indicator_links"):
            values = row.get(key) or []
            if isinstance(values, list) and values:
                return True
    return False


def _readiness_gate(instance, user, pack):
    report = build_pack_validation(pack=pack, instance=instance, user=user)
    blockers = [item for item in report.get("qa_items", []) if item.get("severity") == "BLOCKER"]
    return (not blockers), report, blockers


def _lock_sections(instance, user):
    ReportTemplatePackResponse.objects.filter(reporting_instance=instance).update(
        locked_for_editing=True,
        locked_at=timezone.now(),
        locked_by=user if getattr(user, "is_authenticated", False) else None,
    )


def _unlock_sections(instance):
    ReportTemplatePackResponse.objects.filter(reporting_instance=instance).update(
        locked_for_editing=False,
        locked_at=None,
        locked_by=None,
    )


def _record_action(*, workflow, user, action_type, comment, payload_digest, payload_json):
    return ReportWorkflowAction.objects.create(
        workflow_instance=workflow,
        actor=user if getattr(user, "is_authenticated", False) else None,
        action_type=action_type,
        comment=comment or "",
        payload_hash=payload_digest,
        payload_json=payload_json,
    )


def _infer_signer_role(user):
    if not user or not getattr(user, "is_authenticated", False):
        return ""
    if is_system_admin(user):
        return "SystemAdmin"
    for role in (
        ROLE_PUBLISHING_AUTHORITY,
        ROLE_TECHNICAL_COMMITTEE,
        ROLE_SECRETARIAT,
        ROLE_SECTION_LEAD,
        ROLE_DATA_STEWARD,
        ROLE_ADMIN,
    ):
        if user_has_role(user, role):
            return role
    return "User"


def _record_signoff(
    *,
    instance,
    snapshot,
    user,
    state_from,
    state_to,
    body,
    comment="",
    metadata=None,
):
    return ReportSignoffRecord.objects.create(
        reporting_instance=instance,
        snapshot=snapshot,
        signer=user if getattr(user, "is_authenticated", False) else None,
        signer_role=_infer_signer_role(user),
        body=body,
        state_from=state_from or "",
        state_to=state_to or "",
        signed_at=timezone.now(),
        comment=comment or "",
        snapshot_hash_pointer=(snapshot.payload_hash if snapshot else ""),
        metadata_json=metadata or {},
    )


def _create_immutable_snapshot_package(
    *,
    instance,
    user,
    linked_action,
    validation_report,
    context_filters=None,
    resolved_values_manifest=None,
):
    payload = build_cbd_report_payload(instance=instance)
    json_bytes = _canonical_json(payload).encode("utf-8")
    pdf_bytes = render_cbd_pdf_bytes(payload=payload)
    docx_bytes = render_cbd_docx_bytes(payload=payload)

    json_artifact = store_report_export_artifact(
        instance=instance,
        generated_by=user,
        format_name=ReportExportArtifact.FORMAT_JSON,
        content_bytes=json_bytes,
        linked_action=linked_action,
        metadata={"source": "workflow_snapshot"},
    )
    pdf_artifact = store_report_export_artifact(
        instance=instance,
        generated_by=user,
        format_name=ReportExportArtifact.FORMAT_PDF,
        content_bytes=pdf_bytes,
        linked_action=linked_action,
        metadata={"source": "workflow_snapshot"},
    )
    docx_artifact = store_report_export_artifact(
        instance=instance,
        generated_by=user,
        format_name=ReportExportArtifact.FORMAT_DOCX,
        content_bytes=docx_bytes,
        linked_action=linked_action,
        metadata={"source": "workflow_snapshot"},
    )

    payload_hash_value = _hash_payload(payload)
    blockers = [item for item in validation_report.get("qa_items", []) if item.get("severity") == "BLOCKER"]
    context_filters = context_filters or {}
    resolved_values_manifest = resolved_values_manifest or []

    snapshot, created = ReportingSnapshot.objects.get_or_create(
        reporting_instance=instance,
        payload_hash=payload_hash_value,
        defaults={
            "snapshot_type": "CBD_NR_SIGNOFF_PACKAGE_V1",
            "payload_json": payload,
            "exporter_schema": payload.get("schema", "nbms.cbd_national_report.v1"),
            "exporter_version": payload.get("exporter_version", "1.0.0"),
            "report_family": instance.report_family,
            "report_label": instance.report_label,
            "reporting_period_start": instance.reporting_period_start,
            "reporting_period_end": instance.reporting_period_end,
            "export_json_storage_path": json_artifact.storage_path,
            "export_json_hash": json_artifact.content_hash,
            "export_pdf_storage_path": pdf_artifact.storage_path,
            "export_pdf_hash": pdf_artifact.content_hash,
            "export_docx_storage_path": docx_artifact.storage_path,
            "export_docx_hash": docx_artifact.content_hash,
            "resolved_values_manifest_json": resolved_values_manifest,
            "context_filters_json": context_filters,
            "context_hash": _hash_payload(context_filters),
            "readiness_report_json": validation_report,
            "readiness_overall_ready": bool(validation_report.get("overall_ready")),
            "readiness_blocking_gap_count": len(blockers),
            "created_by": user if getattr(user, "is_authenticated", False) else None,
            "notes": "workflow_freeze_snapshot",
        },
    )
    if created:
        record_audit_event(
            user,
            "report_snapshot_created",
            instance,
            metadata={
                "snapshot_uuid": str(snapshot.uuid),
                "payload_hash": snapshot.payload_hash,
                "json_hash": json_artifact.content_hash,
                "pdf_hash": pdf_artifact.content_hash,
                "docx_hash": docx_artifact.content_hash,
                "context_hash": snapshot.context_hash,
            },
        )
    return snapshot


@transaction.atomic
def transition_report_workflow(
    *,
    instance,
    user,
    action,
    comment="",
    section_code="",
    context_filters=None,
    resolved_values_manifest=None,
):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    workflow = ensure_workflow_instance(instance)
    _ensure_section_approval_rows(workflow)
    snapshot, digest, pack = report_content_snapshot(instance)

    original_step = workflow.current_step
    action = (action or "").strip().lower()
    legacy_technical_approve = action == "technical_approve"
    signoff_body = ""
    signoff_metadata = {}
    validation_report = {}
    needs_snapshot = False

    # Backward-compatible aliases from earlier Phase 12 API contract.
    if action == "section_approve":
        action = "section_complete"
    elif action == "technical_approve":
        action = "technical_committee_approve"
    elif action == "consolidate":
        action = "dffe_clearance_approve"

    if action == "start_progress":
        _require_role(user, ROLE_SECTION_LEAD, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN)
        workflow.current_step = ReportingStatus.IN_PROGRESS
        instance.status = ReportingStatus.IN_PROGRESS
        action_type = ReportWorkflowActionType.START_PROGRESS

    elif action == "request_internal_review":
        _require_role(user, ROLE_SECTION_LEAD, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN)
        workflow.current_step = ReportingStatus.INTERNAL_REVIEW
        instance.status = ReportingStatus.INTERNAL_REVIEW
        action_type = ReportWorkflowActionType.REQUEST_INTERNAL_REVIEW

    elif action == "section_complete":
        _require_role(user, ROLE_SECTION_LEAD, ROLE_SECRETARIAT, ROLE_ADMIN)
        if not section_code:
            raise ValidationError("section_code is required for section_complete.")
        section = pack.sections.filter(code=section_code, is_active=True).first()
        if not section:
            raise ValidationError("Section not found for this pack.")
        approval = ReportWorkflowSectionApproval.objects.get(workflow_instance=workflow, section=section)
        approval.approved = True
        approval.approved_by = user
        approval.approved_at = timezone.now()
        approval.note = comment or approval.note
        approval.save(update_fields=["approved", "approved_by", "approved_at", "note", "updated_at"])
        if _all_sections_approved(workflow) and workflow.current_step in {ReportingStatus.DRAFT, ReportingStatus.IN_PROGRESS}:
            workflow.current_step = ReportingStatus.INTERNAL_REVIEW
            instance.status = ReportingStatus.INTERNAL_REVIEW
        action_type = ReportWorkflowActionType.SECTION_COMPLETE

    elif action == "request_technical_committee_review":
        _require_role(user, ROLE_SECTION_LEAD, ROLE_SECRETARIAT, ROLE_ADMIN)
        if not _all_sections_approved(workflow):
            raise ValidationError("All sections must be marked complete before Technical Committee review.")
        ready, validation_report, blockers = _readiness_gate(instance, user, pack)
        if not ready:
            raise ValidationError(
                "Readiness checks must pass before Technical Committee review: "
                + ", ".join(sorted({item.get("code", "unknown") for item in blockers}))
            )
        workflow.current_step = ReportingStatus.TECHNICAL_COMMITTEE_REVIEW
        instance.status = ReportingStatus.TECHNICAL_COMMITTEE_REVIEW
        action_type = ReportWorkflowActionType.REQUEST_TECHNICAL_COMMITTEE_REVIEW

    elif action == "technical_committee_approve":
        _require_role(user, ROLE_TECHNICAL_COMMITTEE, ROLE_ADMIN)
        if not _all_sections_approved(workflow):
            raise ValidationError("All sections must be complete before technical approval.")
        if not _has_minimum_evidence(instance):
            raise ValidationError("Mandatory evidence gate not satisfied for technical approval.")
        blockers = []
        if not legacy_technical_approve:
            ready, validation_report, blockers = _readiness_gate(instance, user, pack)
            if not ready:
                raise ValidationError(
                    "Readiness checks must pass before technical approval: "
                    + ", ".join(sorted({item.get("code", "unknown") for item in blockers}))
                )
        workflow.current_step = ReportingStatus.TECHNICAL_COMMITTEE_APPROVED
        instance.status = ReportingStatus.TECHNICAL_COMMITTEE_APPROVED
        signoff_body = "Technical Committee"
        signoff_metadata = {"blocking_gap_count": len(blockers)}
        action_type = ReportWorkflowActionType.TECHNICAL_COMMITTEE_APPROVE

    elif action == "dffe_clearance_approve":
        _require_role(user, ROLE_SECRETARIAT, ROLE_ADMIN)
        workflow.current_step = ReportingStatus.DFFE_CLEARANCE
        instance.status = ReportingStatus.DFFE_CLEARANCE
        signoff_body = "DFFE"
        action_type = ReportWorkflowActionType.DFFE_CLEARANCE_APPROVE

    elif action == "final_signoff":
        _require_role(user, ROLE_PUBLISHING_AUTHORITY, ROLE_SECRETARIAT, ROLE_ADMIN)
        workflow.current_step = ReportingStatus.FINAL_SIGNED_OFF
        instance.status = ReportingStatus.FINAL_SIGNED_OFF
        signoff_body = "Publishing Authority"
        action_type = ReportWorkflowActionType.FINAL_SIGNOFF

    elif action == "freeze":
        _require_role(user, ROLE_PUBLISHING_AUTHORITY, ROLE_SECRETARIAT, ROLE_ADMIN)
        if not _all_sections_approved(workflow):
            raise ValidationError("All sections must be complete before freezing.")
        if not _has_minimum_evidence(instance):
            raise ValidationError("Mandatory evidence gate not satisfied for freeze.")
        ready, validation_report, blockers = _readiness_gate(instance, user, pack)
        if not ready:
            raise ValidationError(
                "Readiness checks must pass before freeze: "
                + ", ".join(sorted({item.get("code", "unknown") for item in blockers}))
            )
        workflow.current_step = ReportingStatus.FROZEN
        workflow.locked = True
        instance.status = ReportingStatus.FROZEN
        instance.final_content_hash = digest
        instance.finalized_at = timezone.now()
        _lock_sections(instance, user)
        signoff_body = "Publishing Authority"
        signoff_metadata = {"blocking_gap_count": len(blockers)}
        needs_snapshot = True
        action_type = ReportWorkflowActionType.FREEZE

    elif action == "public_release":
        _require_role(user, ROLE_PUBLISHING_AUTHORITY, ROLE_SECRETARIAT, ROLE_ADMIN)
        if not instance.is_public:
            raise ValidationError("Public release requires is_public=true on the reporting instance.")
        if instance.status not in {ReportingStatus.SUBMITTED, ReportingStatus.RELEASED, ReportingStatus.PUBLIC_RELEASED}:
            raise ValidationError("Report must be submitted before public release.")
        workflow.current_step = ReportingStatus.PUBLIC_RELEASED
        workflow.status = ReportWorkflowStatus.COMPLETED
        workflow.completed_at = timezone.now()
        workflow.locked = True
        instance.status = ReportingStatus.PUBLIC_RELEASED
        action_type = ReportWorkflowActionType.PUBLIC_RELEASE

    elif action == "publishing_approve":
        # Legacy one-step compatibility: finalize, freeze, and submit.
        _require_role(user, ROLE_PUBLISHING_AUTHORITY, ROLE_SECRETARIAT, ROLE_ADMIN)
        if not _all_sections_approved(workflow):
            raise ValidationError("All sections must be complete before publishing approval.")
        if not _has_minimum_evidence(instance):
            raise ValidationError("Mandatory evidence gate not satisfied for publishing approval.")
        blockers = []
        validation_report = {
            "overall_ready": True,
            "qa_items": [],
            "legacy_action": True,
        }
        workflow.current_step = ReportingStatus.SUBMITTED
        workflow.status = ReportWorkflowStatus.COMPLETED
        workflow.completed_at = timezone.now()
        workflow.locked = True
        instance.status = ReportingStatus.SUBMITTED
        instance.final_content_hash = digest
        instance.finalized_at = timezone.now()
        _lock_sections(instance, user)
        signoff_body = "Publishing Authority"
        signoff_metadata = {"blocking_gap_count": len(blockers), "legacy_action": True}
        needs_snapshot = True
        action_type = ReportWorkflowActionType.PUBLISHING_APPROVE

    elif action == "submit":
        # Submit is dual-mode: draft submit requests internal review; frozen submit finalizes submission.
        if workflow.current_step in {ReportingStatus.FROZEN, ReportingStatus.FINAL_SIGNED_OFF} or instance.status in {
            ReportingStatus.FROZEN,
            ReportingStatus.FINAL_SIGNED_OFF,
        }:
            _require_role(user, ROLE_PUBLISHING_AUTHORITY, ROLE_SECRETARIAT, ROLE_ADMIN)
            if not instance.finalized_at:
                instance.finalized_at = timezone.now()
            if not instance.final_content_hash:
                instance.final_content_hash = digest
            workflow.current_step = ReportingStatus.SUBMITTED
            workflow.status = ReportWorkflowStatus.COMPLETED
            workflow.completed_at = timezone.now()
            workflow.locked = True
            instance.status = ReportingStatus.SUBMITTED
            _lock_sections(instance, user)
            needs_snapshot = True
            action_type = ReportWorkflowActionType.SUBMIT
        else:
            _require_role(user, ROLE_SECTION_LEAD, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN)
            workflow.current_step = ReportingStatus.INTERNAL_REVIEW
            instance.status = ReportingStatus.INTERNAL_REVIEW
            action_type = ReportWorkflowActionType.REQUEST_INTERNAL_REVIEW

    elif action == "reject":
        _require_role(user, ROLE_SECTION_LEAD, ROLE_TECHNICAL_COMMITTEE, ROLE_SECRETARIAT, ROLE_ADMIN)
        workflow.current_step = ReportingStatus.DRAFT
        workflow.status = ReportWorkflowStatus.ACTIVE
        workflow.completed_at = None
        workflow.locked = False
        instance.status = ReportingStatus.DRAFT
        _unlock_sections(instance)
        action_type = ReportWorkflowActionType.REJECT

    elif action == "unlock":
        if not is_system_admin(user):
            raise PermissionDenied("Only SystemAdmin can unlock finalized reports.")
        workflow.status = ReportWorkflowStatus.CANCELLED
        workflow.completed_at = timezone.now()
        workflow.locked = False
        workflow.current_step = ReportingStatus.DRAFT
        instance.status = ReportingStatus.DRAFT
        instance.finalized_at = None
        instance.final_content_hash = ""
        _unlock_sections(instance)
        action_type = ReportWorkflowActionType.UNLOCK

    else:
        raise ValidationError("Unsupported workflow action.")

    workflow.latest_content_hash = digest
    workflow.save(
        update_fields=[
            "current_step",
            "status",
            "completed_at",
            "locked",
            "latest_content_hash",
            "updated_at",
        ]
    )
    instance.updated_by = user
    instance.save(
        update_fields=[
            "status",
            "updated_by",
            "final_content_hash",
            "finalized_at",
            "updated_at",
        ]
    )
    workflow_action = _record_action(
        workflow=workflow,
        user=user,
        action_type=action_type,
        comment=comment,
        payload_digest=digest,
        payload_json=snapshot,
    )

    snapshot_record = None
    if needs_snapshot:
        if not validation_report:
            ready, validation_report, _blockers = _readiness_gate(instance, user, pack)
            if not ready:
                raise ValidationError("Readiness checks failed while creating immutable snapshot package.")
        snapshot_record = _create_immutable_snapshot_package(
            instance=instance,
            user=user,
            linked_action=workflow_action,
            validation_report=validation_report,
            context_filters=context_filters or {},
            resolved_values_manifest=resolved_values_manifest or [],
        )

    if signoff_body:
        _record_signoff(
            instance=instance,
            snapshot=snapshot_record,
            user=user,
            state_from=original_step,
            state_to=workflow.current_step,
            body=signoff_body,
            comment=comment,
            metadata=signoff_metadata,
        )

    record_audit_event(
        user,
        "report_workflow_action",
        instance,
        metadata={
            "workflow_instance_uuid": str(workflow.uuid),
            "workflow_action_uuid": str(workflow_action.uuid),
            "action": action,
            "status": instance.status,
            "current_step": workflow.current_step,
            "content_hash": digest,
            "section_code": section_code,
            "snapshot_uuid": str(snapshot_record.uuid) if snapshot_record else None,
            "signoff_body": signoff_body or "",
        },
    )
    return workflow, workflow_action
