from __future__ import annotations

from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from nbms_app.models import (
    EICATAssessment,
    EcosystemRiskAssessment,
    EcosystemTypologyCrosswalk,
    Evidence,
    LifecycleStatus,
    RegistryEvidenceLink,
    RegistryReviewStatus,
    SEICATAssessment,
    ValidationRuleSet,
)
from nbms_app.services.audit import record_audit_event, suppress_audit_events
from nbms_app.services.authorization import (
    ROLE_ADMIN,
    ROLE_DATA_STEWARD,
    ROLE_INDICATOR_LEAD,
    ROLE_SECRETARIAT,
    filter_queryset_for_user,
    is_system_admin,
    user_has_role,
)


@dataclass(frozen=True)
class RegistryWorkflowTarget:
    object_type: str
    model: type


WORKFLOW_TARGETS = {
    "ecosystem_crosswalk": RegistryWorkflowTarget(
        object_type="ecosystem_crosswalk",
        model=EcosystemTypologyCrosswalk,
    ),
    "ecosystem_risk_assessment": RegistryWorkflowTarget(
        object_type="ecosystem_risk_assessment",
        model=EcosystemRiskAssessment,
    ),
    "eicat_assessment": RegistryWorkflowTarget(
        object_type="eicat_assessment",
        model=EICATAssessment,
    ),
    "seicat_assessment": RegistryWorkflowTarget(
        object_type="seicat_assessment",
        model=SEICATAssessment,
    ),
}


def _default_workflow_rules():
    return {
        "evidence_required_for_actions": {
            "ecosystem_crosswalk": ["approve", "publish"],
            "ecosystem_risk_assessment": ["approve", "publish"],
            "eicat_assessment": ["approve", "publish"],
            "seicat_assessment": ["approve", "publish"],
        }
    }


def _load_workflow_rules():
    rules = _default_workflow_rules()
    override = (
        ValidationRuleSet.objects.filter(code="REGISTRY_WORKFLOW_DEFAULT", is_active=True)
        .order_by("-updated_at", "-id")
        .first()
    )
    if not override:
        return rules
    payload = override.rules_json or {}
    if not isinstance(payload, dict):
        return rules
    merged = dict(rules)
    merged.update(payload)
    return merged


def resolve_registry_target(object_type: str) -> RegistryWorkflowTarget:
    key = (object_type or "").strip().lower()
    target = WORKFLOW_TARGETS.get(key)
    if not target:
        raise ValidationError("Unsupported registry object type.")
    return target


def get_registry_object(*, object_type: str, object_uuid, user):
    target = resolve_registry_target(object_type)
    queryset = filter_queryset_for_user(target.model.objects.all(), user)
    obj = queryset.filter(uuid=object_uuid).first()
    if not obj:
        raise target.model.DoesNotExist()
    return target, obj


def _can_submit(user, obj):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if is_system_admin(user):
        return True
    if user_has_role(user, ROLE_ADMIN, ROLE_DATA_STEWARD, ROLE_INDICATOR_LEAD):
        return True
    return getattr(obj, "created_by_id", None) == user.id


def _can_review(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return bool(is_system_admin(user) or user_has_role(user, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_DATA_STEWARD))


def list_registry_evidence_links(*, obj, user):
    content_type = ContentType.objects.get_for_model(obj.__class__)
    links = RegistryEvidenceLink.objects.filter(
        content_type=content_type,
        object_uuid=obj.uuid,
    ).select_related("evidence")
    visible_evidence = filter_queryset_for_user(
        Evidence.objects.filter(id__in=links.values_list("evidence_id", flat=True)),
        user,
    )
    visible_ids = set(visible_evidence.values_list("id", flat=True))
    rows = []
    for link in links.order_by("evidence__title", "id"):
        if link.evidence_id not in visible_ids:
            continue
        rows.append(
            {
                "uuid": str(link.uuid),
                "evidence_uuid": str(link.evidence.uuid),
                "title": link.evidence.title,
                "evidence_type": link.evidence.evidence_type,
                "source_url": link.evidence.source_url,
                "sensitivity": link.evidence.sensitivity,
                "notes": link.notes,
            }
        )
    return rows


def link_registry_evidence(*, obj, evidence_uuid, user, note: str = ""):
    if not _can_review(user):
        raise PermissionDenied("Not allowed to link registry evidence.")
    evidence = filter_queryset_for_user(Evidence.objects.all(), user).filter(uuid=evidence_uuid).first()
    if not evidence:
        raise ValidationError("Evidence not found or inaccessible.")
    content_type = ContentType.objects.get_for_model(obj.__class__)
    link, _ = RegistryEvidenceLink.objects.update_or_create(
        content_type=content_type,
        object_uuid=obj.uuid,
        evidence=evidence,
        defaults={
            "notes": note or "",
            "created_by": user if getattr(user, "is_authenticated", False) else None,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": evidence.sensitivity,
        },
    )
    record_audit_event(
        user,
        "registry_link_evidence",
        obj,
        metadata={"evidence_uuid": str(evidence.uuid), "link_uuid": str(link.uuid)},
    )
    return link


def _evidence_required_for_action(*, target: RegistryWorkflowTarget, action: str):
    rules = _load_workflow_rules()
    per_object = (rules.get("evidence_required_for_actions") or {}).get(target.object_type, [])
    return action in {str(item).strip().lower() for item in per_object if item}


def _assert_evidence_if_required(*, target: RegistryWorkflowTarget, obj, action: str):
    if not _evidence_required_for_action(target=target, action=action):
        return
    content_type = ContentType.objects.get_for_model(obj.__class__)
    has_linked = RegistryEvidenceLink.objects.filter(
        content_type=content_type,
        object_uuid=obj.uuid,
    ).exists()
    if not has_linked:
        raise ValidationError("Evidence links are required before this transition.")


def _set_review_markers(obj, *, status=None, reviewer=None):
    update_fields = []
    if status is not None and hasattr(obj, "review_status"):
        obj.review_status = status
        update_fields.append("review_status")
    if hasattr(obj, "reviewed_by_id"):
        obj.reviewed_by = reviewer
        update_fields.append("reviewed_by")
    if hasattr(obj, "reviewed_at"):
        obj.reviewed_at = timezone.now()
        update_fields.append("reviewed_at")
    return update_fields


def transition_registry_object(
    *,
    object_type: str,
    object_uuid,
    action: str,
    user,
    note: str = "",
    evidence_uuids=None,
):
    evidence_uuids = evidence_uuids or []
    target, obj = get_registry_object(object_type=object_type, object_uuid=object_uuid, user=user)
    action_key = (action or "").strip().lower()

    if action_key not in {"submit", "approve", "publish", "reject"}:
        raise ValidationError("Unsupported transition action.")

    if action_key == "submit":
        if not _can_submit(user, obj):
            raise PermissionDenied("Not allowed to submit this registry record.")
        if obj.status != LifecycleStatus.DRAFT:
            raise ValidationError("Only draft records can be submitted for review.")
        obj.status = LifecycleStatus.PENDING_REVIEW
        update_fields = ["status"]
        update_fields.extend(_set_review_markers(obj, status=RegistryReviewStatus.IN_REVIEW))
        with suppress_audit_events():
            obj.save(update_fields=list(dict.fromkeys(update_fields)))
    elif action_key == "approve":
        if not _can_review(user):
            raise PermissionDenied("Not allowed to approve this registry record.")
        if obj.status != LifecycleStatus.PENDING_REVIEW:
            raise ValidationError("Only records in review can be approved.")
        for evidence_uuid in evidence_uuids:
            link_registry_evidence(obj=obj, evidence_uuid=evidence_uuid, user=user, note=note)
        _assert_evidence_if_required(target=target, obj=obj, action=action_key)
        obj.status = LifecycleStatus.APPROVED
        update_fields = ["status"]
        update_fields.extend(_set_review_markers(obj, status=RegistryReviewStatus.APPROVED, reviewer=user))
        with suppress_audit_events():
            obj.save(update_fields=list(dict.fromkeys(update_fields)))
    elif action_key == "publish":
        if not _can_review(user):
            raise PermissionDenied("Not allowed to publish this registry record.")
        if obj.status != LifecycleStatus.APPROVED:
            raise ValidationError("Only approved records can be published.")
        for evidence_uuid in evidence_uuids:
            link_registry_evidence(obj=obj, evidence_uuid=evidence_uuid, user=user, note=note)
        _assert_evidence_if_required(target=target, obj=obj, action=action_key)
        obj.status = LifecycleStatus.PUBLISHED
        update_fields = ["status"]
        if hasattr(obj, "review_status") and obj.review_status != RegistryReviewStatus.APPROVED:
            obj.review_status = RegistryReviewStatus.APPROVED
            update_fields.append("review_status")
        with suppress_audit_events():
            obj.save(update_fields=list(dict.fromkeys(update_fields)))
    else:
        if not _can_review(user):
            raise PermissionDenied("Not allowed to reject this registry record.")
        if obj.status not in {LifecycleStatus.PENDING_REVIEW, LifecycleStatus.APPROVED}:
            raise ValidationError("Only records in review/approved state can be rejected.")
        if not (note or "").strip():
            raise ValidationError("Rejection note is required.")
        obj.status = LifecycleStatus.DRAFT
        if hasattr(obj, "evidence"):
            obj.evidence = ((obj.evidence or "").strip() + f"\nRejection note: {note.strip()}").strip()
            update_fields = ["status", "evidence"]
        else:
            update_fields = ["status"]
        update_fields.extend(_set_review_markers(obj, status=RegistryReviewStatus.REJECTED, reviewer=user))
        with suppress_audit_events():
            obj.save(update_fields=list(dict.fromkeys(update_fields)))

    record_audit_event(
        user,
        f"registry_{action_key}",
        obj,
        metadata={
            "object_type": target.object_type,
            "status": obj.status,
            "review_status": getattr(obj, "review_status", ""),
            "evidence_links": len(list_registry_evidence_links(obj=obj, user=user)),
        },
    )
    return obj
