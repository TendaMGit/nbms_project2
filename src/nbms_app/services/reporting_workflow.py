from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from nbms_app.models import (
    ReportTemplatePack,
    ReportTemplatePackResponse,
    ReportWorkflowAction,
    ReportWorkflowActionType,
    ReportWorkflowDefinition,
    ReportWorkflowInstance,
    ReportWorkflowSectionApproval,
    ReportWorkflowStatus,
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
from nbms_app.services.template_packs import build_default_response_payload


CBD_PACK_CODES = ("cbd_national_report_v1", "cbd_ort_nr7_v2")
REPORT_WORKFLOW_NAME = "cbd_national_report_signoff_v1"

DEFAULT_SIGNOFF_STEPS = [
    {"code": "draft", "title": "Draft", "role": "Author"},
    {"code": "section_review", "title": "Section Review", "role": "SectionLead"},
    {"code": "technical_review", "title": "Technical Review", "role": "TechnicalCommittee"},
    {"code": "secretariat_consolidation", "title": "Secretariat Consolidation", "role": "Secretariat"},
    {"code": "publishing_authority_review", "title": "Publishing Authority Approval", "role": "PublishingAuthority"},
    {"code": "submitted", "title": "Submitted/Final", "role": "System"},
]


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
        "version_label": instance.version_label,
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
        current_step="draft",
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
    # Keep the gate strict but practical: any populated target progress evidence or dataset release is acceptable.
    section_iii = SectionIIINationalTargetProgress.objects.filter(reporting_instance=instance).prefetch_related(
        "evidence_items",
        "dataset_releases",
    )
    for row in section_iii:
        if row.evidence_items.exists() or row.dataset_releases.exists():
            return True
    return False


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


@transaction.atomic
def transition_report_workflow(*, instance, user, action, comment="", section_code=""):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    workflow = ensure_workflow_instance(instance)
    _ensure_section_approval_rows(workflow)
    snapshot, digest, pack = report_content_snapshot(instance)

    action = (action or "").strip().lower()
    if action == "submit":
        _require_role(user, ROLE_SECTION_LEAD, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN)
        workflow.current_step = "section_review"
        instance.status = ReportingStatus.SECTION_REVIEW
        action_type = ReportWorkflowActionType.SUBMIT
    elif action == "section_approve":
        _require_role(user, ROLE_SECTION_LEAD, ROLE_SECRETARIAT, ROLE_ADMIN)
        if not section_code:
            raise ValidationError("section_code is required for section_approve.")
        section = pack.sections.filter(code=section_code, is_active=True).first()
        if not section:
            raise ValidationError("Section not found for this pack.")
        approval = ReportWorkflowSectionApproval.objects.get(workflow_instance=workflow, section=section)
        approval.approved = True
        approval.approved_by = user
        approval.approved_at = timezone.now()
        approval.note = comment or approval.note
        approval.save(update_fields=["approved", "approved_by", "approved_at", "note", "updated_at"])
        if _all_sections_approved(workflow):
            workflow.current_step = "technical_review"
            instance.status = ReportingStatus.TECHNICAL_REVIEW
        action_type = ReportWorkflowActionType.APPROVE
    elif action == "technical_approve":
        _require_role(user, ROLE_TECHNICAL_COMMITTEE, ROLE_ADMIN)
        if not _all_sections_approved(workflow):
            raise ValidationError("All sections must be approved before technical approval.")
        if not _has_minimum_evidence(instance):
            raise ValidationError("Evidence gate not satisfied for technical approval.")
        workflow.current_step = "secretariat_consolidation"
        instance.status = ReportingStatus.SECRETARIAT_CONSOLIDATION
        action_type = ReportWorkflowActionType.TECHNICAL_APPROVE
    elif action == "consolidate":
        _require_role(user, ROLE_SECRETARIAT, ROLE_ADMIN)
        workflow.current_step = "publishing_authority_review"
        instance.status = ReportingStatus.PUBLISHING_AUTHORITY_REVIEW
        action_type = ReportWorkflowActionType.CONSOLIDATE
    elif action == "publishing_approve":
        _require_role(user, ROLE_PUBLISHING_AUTHORITY, ROLE_SECRETARIAT, ROLE_ADMIN)
        workflow.current_step = "submitted"
        workflow.status = ReportWorkflowStatus.COMPLETED
        workflow.completed_at = timezone.now()
        workflow.locked = True
        workflow.latest_content_hash = digest
        instance.status = ReportingStatus.SUBMITTED
        instance.final_content_hash = digest
        instance.finalized_at = timezone.now()
        _lock_sections(instance, user)
        action_type = ReportWorkflowActionType.PUBLISHING_APPROVE
    elif action == "reject":
        _require_role(user, ROLE_SECTION_LEAD, ROLE_TECHNICAL_COMMITTEE, ROLE_SECRETARIAT, ROLE_ADMIN)
        workflow.current_step = "draft"
        instance.status = ReportingStatus.DRAFT
        _unlock_sections(instance)
        action_type = ReportWorkflowActionType.REJECT
    elif action == "unlock":
        if not is_system_admin(user):
            raise PermissionDenied("Only SystemAdmin can unlock finalized reports.")
        workflow.status = ReportWorkflowStatus.CANCELLED
        workflow.completed_at = timezone.now()
        workflow.locked = False
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
        },
    )
    return workflow, workflow_action
