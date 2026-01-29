from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from nbms_app.models import (
    InstanceExportApproval,
    ReviewDecision,
    ReviewDecisionStatus,
    ReportingSnapshot,
)
from nbms_app.services.authorization import is_system_admin
from nbms_app.services.section_progress import scoped_national_targets


ALLOWED_EXPORT_SCHEMAS = {"nbms.ort.nr7.v2"}


class _StrictUserProxy:
    def __init__(self, user):
        self._user = user

    def __getattr__(self, name):
        if name in {"is_staff", "is_superuser"}:
            return False
        return getattr(self._user, name)


def _strict_user(user):
    if not user:
        return user
    if is_system_admin(user):
        return user
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return _StrictUserProxy(user)
    return user


def _require_instance_access(instance, user):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")

    strict_user = _strict_user(user)
    approvals_exist = InstanceExportApproval.objects.filter(
        reporting_instance=instance,
        approval_scope="export",
    ).exists()
    if not approvals_exist:
        return

    if scoped_national_targets(instance, strict_user).exists():
        return

    raise PermissionDenied("Not allowed to access review decisions for this reporting instance.")


def _latest_snapshot(instance):
    return (
        ReportingSnapshot.objects.filter(reporting_instance=instance)
        .order_by("-created_at")
        .first()
    )


def review_decisions_for_user(instance, user):
    _require_instance_access(instance, user)
    return (
        ReviewDecision.objects.filter(reporting_instance=instance)
        .select_related("snapshot", "created_by", "supersedes")
        .order_by("-created_at")
    )


@transaction.atomic
def create_review_decision(*, instance, snapshot, user, decision, notes="", supersedes=None):
    _require_instance_access(instance, user)
    if not snapshot:
        raise ValidationError("A snapshot is required to create a review decision.")
    if snapshot.reporting_instance_id != instance.id:
        raise ValidationError("Snapshot does not belong to this reporting instance.")
    if snapshot.exporter_schema not in ALLOWED_EXPORT_SCHEMAS:
        raise ValidationError("Snapshot schema is not eligible for review approval.")

    decision = str(decision or "").strip()
    if decision not in ReviewDecisionStatus.values:
        raise ValidationError("Invalid review decision.")

    if decision == ReviewDecisionStatus.APPROVED:
        if not instance.frozen_at:
            raise ValidationError("Instance must be frozen before approval.")
        latest = _latest_snapshot(instance)
        if not latest or latest.id != snapshot.id:
            raise ValidationError("Approval requires the latest snapshot for this instance.")

    if supersedes and supersedes.reporting_instance_id != instance.id:
        raise ValidationError("Superseded decision does not belong to this reporting instance.")

    if not supersedes:
        supersedes = (
            ReviewDecision.objects.filter(reporting_instance=instance)
            .order_by("-created_at")
            .first()
        )

    return ReviewDecision.objects.create(
        reporting_instance=instance,
        snapshot=snapshot,
        decision=decision,
        notes=notes or "",
        created_by=user if getattr(user, "is_authenticated", False) else None,
        supersedes=supersedes,
    )


def get_current_review_decision(instance, user):
    _require_instance_access(instance, user)
    return (
        ReviewDecision.objects.filter(reporting_instance=instance)
        .order_by("-created_at")
        .first()
    )
