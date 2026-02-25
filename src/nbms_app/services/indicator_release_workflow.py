from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from nbms_app.models import (
    IndicatorDataSeries,
    IndicatorMethodologyVersionLink,
    LifecycleStatus,
    MethodologyStatus,
    SensitivityLevel,
)
from nbms_app.services.audit import record_audit_event, suppress_audit_events
from nbms_app.services.authorization import (
    ROLE_ADMIN,
    ROLE_DATA_STEWARD,
    ROLE_INDICATOR_LEAD,
    ROLE_SECRETARIAT,
    is_system_admin,
    user_has_role,
)
from nbms_app.services.metrics import inc_counter


_ITSC_APPROVAL_MARKERS = ("itsc", "technical committee")


def _same_org(user, obj):
    org_id = getattr(user, "organisation_id", None)
    obj_org_id = getattr(obj, "organisation_id", None)
    return bool(org_id and obj_org_id and org_id == obj_org_id)


def _can_submit_release(user, series: IndicatorDataSeries):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if is_system_admin(user):
        return True
    if getattr(series, "created_by_id", None) == user.id:
        return True
    if user_has_role(user, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_INDICATOR_LEAD, ROLE_DATA_STEWARD):
        return _same_org(user, series)
    return False


def _can_steward_review(user, series: IndicatorDataSeries):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if is_system_admin(user):
        return True
    if not user_has_role(user, ROLE_ADMIN, ROLE_DATA_STEWARD):
        return False
    return _same_org(user, series)


def release_requires_data_steward_review(series: IndicatorDataSeries):
    flags = {series.sensitivity}
    if series.indicator_id and series.indicator:
        flags.add(series.indicator.sensitivity)
    return bool(
        flags.intersection(
            {
                SensitivityLevel.RESTRICTED,
                SensitivityLevel.IPLC_SENSITIVE,
            }
        )
    )


def _is_itsc_approved_version(version):
    if version is None:
        return False
    if not version.is_active or version.status != MethodologyStatus.ACTIVE:
        return False
    approval_body = (version.approval_body or "").strip().lower()
    if not approval_body:
        return False
    return any(marker in approval_body for marker in _ITSC_APPROVAL_MARKERS)


def indicator_has_itsc_approved_method(series: IndicatorDataSeries):
    if not series.indicator_id:
        return False
    links = IndicatorMethodologyVersionLink.objects.filter(
        indicator=series.indicator,
        is_active=True,
        methodology_version__is_active=True,
    ).select_related("methodology_version")
    return any(_is_itsc_approved_version(link.methodology_version) for link in links)


def submit_indicator_release(series: IndicatorDataSeries, user, *, note="", sense_check_attested=False):
    if not _can_submit_release(user, series):
        raise PermissionDenied("Not allowed to submit indicator release.")
    if series.status != LifecycleStatus.DRAFT:
        raise ValidationError("Only draft indicator releases can be submitted.")
    if not series.data_points.exists():
        raise ValidationError("Indicator release must include at least one data point before submission.")
    if not sense_check_attested:
        raise ValidationError("Contributor sense-check attestation is required before submission.")
    if not indicator_has_itsc_approved_method(series):
        raise ValidationError("Indicator release requires an ITSC-approved method version before publication.")

    now = timezone.now()
    requires_steward = release_requires_data_steward_review(series)
    series.sense_check_attested = True
    series.sense_check_attested_by = user
    series.sense_check_attested_at = now
    series.review_note = note or ""
    series.status = LifecycleStatus.PENDING_REVIEW if requires_steward else LifecycleStatus.PUBLISHED

    update_fields = [
        "status",
        "review_note",
        "sense_check_attested",
        "sense_check_attested_by",
        "sense_check_attested_at",
        "updated_at",
    ]
    with suppress_audit_events():
        series.save(update_fields=update_fields)

    record_audit_event(
        user,
        "indicator_release_submit",
        series,
        metadata={
            "status": series.status,
            "requires_data_steward_review": requires_steward,
            "sense_check_attested": True,
        },
    )
    inc_counter(
        "workflow_transitions_total",
        labels={"action": "indicator_release_submit", "object_type": series.__class__.__name__},
    )

    if not requires_steward:
        record_audit_event(
            user,
            "indicator_release_publish_fast_path",
            series,
            metadata={"status": series.status},
        )
        inc_counter(
            "workflow_transitions_total",
            labels={"action": "indicator_release_publish_fast_path", "object_type": series.__class__.__name__},
        )
    return series


def approve_indicator_release(series: IndicatorDataSeries, user, *, note=""):
    if not _can_steward_review(user, series):
        raise PermissionDenied("Not allowed to approve sensitive indicator releases.")
    if series.status != LifecycleStatus.PENDING_REVIEW:
        raise ValidationError("Only pending indicator releases can be approved.")

    series.status = LifecycleStatus.PUBLISHED
    series.review_note = note or series.review_note or ""
    with suppress_audit_events():
        series.save(update_fields=["status", "review_note", "updated_at"])

    record_audit_event(
        user,
        "indicator_release_steward_approve",
        series,
        metadata={"status": series.status, "note": series.review_note},
    )
    inc_counter(
        "workflow_transitions_total",
        labels={"action": "indicator_release_steward_approve", "object_type": series.__class__.__name__},
    )
    return series


def get_release_workflow_state(series: IndicatorDataSeries):
    return {
        "status": series.status,
        "requires_data_steward_review": release_requires_data_steward_review(series),
        "itsc_method_approved": indicator_has_itsc_approved_method(series),
        "sense_check_attested": bool(series.sense_check_attested),
        "sense_check_attested_by": series.sense_check_attested_by.username if series.sense_check_attested_by_id else None,
        "sense_check_attested_at": series.sense_check_attested_at.isoformat() if series.sense_check_attested_at else None,
    }
