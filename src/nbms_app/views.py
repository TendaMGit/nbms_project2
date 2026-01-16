import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.db import connections
from django.db.models import Prefetch
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urlencode

from nbms_app.forms import (
    DatasetForm,
    EvidenceForm,
    ExportPackageForm,
    IndicatorForm,
    NationalTargetForm,
    OrganisationForm,
    ReportSectionResponseForm,
    ReportingCycleForm,
    ReportingInstanceForm,
    UserCreateForm,
    UserUpdateForm,
)
from nbms_app.models import (
    Dataset,
    DatasetRelease,
    Evidence,
    ExportPackage,
    ExportStatus,
    Indicator,
    LifecycleStatus,
    NationalTarget,
    Organisation,
    ReportSectionResponse,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    User,
    Notification,
    InstanceExportApproval,
    ApprovalDecision,
    ConsentStatus,
    SensitivityLevel,
)
from nbms_app.services.authorization import (
    ROLE_ADMIN,
    ROLE_CONTRIBUTOR,
    ROLE_COMMUNITY_REPRESENTATIVE,
    ROLE_DATA_STEWARD,
    ROLE_INDICATOR_LEAD,
    ROLE_SECRETARIAT,
    can_edit_object,
    filter_queryset_for_user,
    user_has_role,
)
from nbms_app.services.audit import record_audit_event
from nbms_app.services.consent import (
    consent_is_granted,
    consent_status_for_instance,
    requires_consent,
    set_consent_status,
)
from nbms_app.services.exports import approve_export, reject_export, release_export, submit_export_for_review
from nbms_app.exports.ort7nr import build_ort7nr_package
from nbms_app.services.instance_approvals import (
    approve_for_instance,
    can_approve_instance,
    bulk_approve_for_instance,
    bulk_revoke_for_instance,
    revoke_for_instance,
)
from nbms_app.services.readiness import (
    get_dataset_readiness,
    get_evidence_readiness,
    get_export_package_readiness,
    get_indicator_readiness,
    get_instance_readiness,
    get_target_readiness,
)
from nbms_app.services.notifications import create_notification
from nbms_app.services.workflows import approve, reject

logger = logging.getLogger(__name__)


def home(request):
    indicators_qs = filter_queryset_for_user(
        Indicator.objects.select_related("organisation", "created_by", "national_target"),
        request.user,
        perm="nbms_app.view_indicator",
    )
    targets_qs = filter_queryset_for_user(
        NationalTarget.objects.select_related("organisation", "created_by"),
        request.user,
        perm="nbms_app.view_nationaltarget",
    )
    evidence_qs = filter_queryset_for_user(
        Evidence.objects.select_related("organisation", "created_by"),
        request.user,
        perm="nbms_app.view_evidence",
    )
    datasets_qs = filter_queryset_for_user(
        Dataset.objects.select_related("organisation", "created_by"),
        request.user,
        perm="nbms_app.view_dataset",
    )
    export_qs = _export_queryset_for_user(request.user)

    counts = {
        "indicators": indicators_qs.count(),
        "targets": targets_qs.count(),
        "evidence": evidence_qs.count(),
        "datasets": datasets_qs.count(),
        "exports": export_qs.count(),
    }

    my_drafts = []
    if request.user.is_authenticated:
        my_drafts.extend(
            _build_items(
                targets_qs.filter(created_by=request.user, status=LifecycleStatus.DRAFT),
                "National Target",
                "nbms_app:national_target_detail",
                url_param="target_uuid",
            )
        )
        my_drafts.extend(
            _build_items(
                indicators_qs.filter(created_by=request.user, status=LifecycleStatus.DRAFT),
                "Indicator",
                "nbms_app:indicator_detail",
                url_param="indicator_uuid",
            )
        )
        my_drafts.extend(
            _build_items(
                evidence_qs.filter(created_by=request.user, status=LifecycleStatus.DRAFT),
                "Evidence",
                "nbms_app:evidence_detail",
                url_param="evidence_uuid",
            )
        )
        my_drafts.extend(
            _build_items(
                datasets_qs.filter(created_by=request.user, status=LifecycleStatus.DRAFT),
                "Dataset",
                "nbms_app:dataset_detail",
                url_param="dataset_uuid",
            )
        )
        my_drafts.extend(
            _build_items(
                export_qs.filter(created_by=request.user, status=ExportStatus.DRAFT),
                "Export Package",
                "nbms_app:export_package_detail",
                url_param="package_uuid",
            )
        )
        my_drafts.sort(key=lambda item: item["updated_at"], reverse=True)

    pending_review = []
    if request.user.is_staff:
        pending_review.extend(
            _build_items(
                NationalTarget.objects.filter(status=LifecycleStatus.PENDING_REVIEW).select_related("created_by"),
                "National Target",
                "nbms_app:review_detail",
                url_kwargs={"obj_type": "target"},
            )
        )
        pending_review.extend(
            _build_items(
                Indicator.objects.filter(status=LifecycleStatus.PENDING_REVIEW).select_related("created_by"),
                "Indicator",
                "nbms_app:review_detail",
                url_kwargs={"obj_type": "indicator"},
            )
        )
        pending_review.extend(
            _build_items(
                Evidence.objects.filter(status=LifecycleStatus.PENDING_REVIEW).select_related("created_by"),
                "Evidence",
                "nbms_app:evidence_detail",
                url_param="evidence_uuid",
            )
        )
        pending_review.extend(
            _build_items(
                Dataset.objects.filter(status=LifecycleStatus.PENDING_REVIEW).select_related("created_by"),
                "Dataset",
                "nbms_app:dataset_detail",
                url_param="dataset_uuid",
            )
        )
        pending_review.extend(
            _build_items(
                ExportPackage.objects.filter(status=ExportStatus.PENDING_REVIEW).select_related("created_by"),
                "Export Package",
                "nbms_app:export_package_detail",
                url_param="package_uuid",
            )
        )
        pending_review.sort(key=lambda item: item["updated_at"], reverse=True)

    recently_published = []
    recently_published.extend(
        _build_items(
            targets_qs.filter(status=LifecycleStatus.PUBLISHED),
            "National Target",
            "nbms_app:national_target_detail",
            url_param="target_uuid",
        )
    )
    recently_published.extend(
        _build_items(
            indicators_qs.filter(status=LifecycleStatus.PUBLISHED),
            "Indicator",
            "nbms_app:indicator_detail",
            url_param="indicator_uuid",
        )
    )
    recently_published.extend(
        _build_items(
            evidence_qs.filter(status=LifecycleStatus.PUBLISHED),
            "Evidence",
            "nbms_app:evidence_detail",
            url_param="evidence_uuid",
        )
    )
    recently_published.extend(
        _build_items(
            datasets_qs.filter(status=LifecycleStatus.PUBLISHED),
            "Dataset",
            "nbms_app:dataset_detail",
            url_param="dataset_uuid",
        )
    )
    recently_published.sort(key=lambda item: item["updated_at"], reverse=True)

    unread_notifications = 0
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False).count()

    context = {
        "counts": counts,
        "my_drafts": my_drafts[:8],
        "pending_review": pending_review[:8],
        "recently_published": recently_published[:8],
        "can_create_evidence": _can_create_data(request.user),
        "can_create_dataset": _can_create_data(request.user),
        "can_create_export": _can_create_export(request.user),
        "unread_notifications": unread_notifications,
    }
    return render(request, "nbms_app/home.html", context)


def health_db(request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:  # noqa: BLE001
        logger.exception("Database health check failed.")
        return JsonResponse({"status": "error"}, status=503)


def health_storage(request):
    if not getattr(settings, "USE_S3", False):
        return JsonResponse({"status": "disabled", "detail": "USE_S3=0"})

    try:
        default_storage.listdir("")
        return JsonResponse({"status": "ok"})
    except Exception:  # noqa: BLE001
        logger.exception("Storage health check failed.")
        return JsonResponse({"status": "error"}, status=503)

def _require_contributor(user):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    if _is_admin_user(user):
        return
    if user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_INDICATOR_LEAD, ROLE_CONTRIBUTOR):
        return
    raise PermissionDenied("Not allowed to manage records.")


def _can_create_data(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    return user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_INDICATOR_LEAD, ROLE_CONTRIBUTOR)


def _is_admin_user(user):
    return bool(user and (getattr(user, "is_superuser", False) or getattr(user, "is_staff", False) or user_has_role(user, ROLE_ADMIN)))


def _band_for_checks(checks):
    for check in checks:
        if check.get("state") in {"blocked"}:
            return "red"
    for check in checks:
        if check.get("state") in {"missing", "incomplete", "warning", "draft"}:
            return "amber"
    return "green"


def _status_allows_edit(obj, user):
    if obj.status in {LifecycleStatus.PENDING_REVIEW, LifecycleStatus.PUBLISHED} and not _is_admin_user(user):
        return False
    return True


def _can_manage_consent(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if _is_admin_user(user):
        return True
    return user_has_role(user, ROLE_COMMUNITY_REPRESENTATIVE, ROLE_SECRETARIAT, ROLE_DATA_STEWARD)


def _require_export_creator(user):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return
    if user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD):
        return
    raise PermissionDenied("Not allowed to manage exports.")


def _can_create_export(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    return user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD)


def _export_queryset_for_user(user):
    packages = ExportPackage.objects.select_related("organisation", "created_by").order_by("-created_at")
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return packages
    if not user or not getattr(user, "is_authenticated", False):
        return packages.none()
    if user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD):
        org_id = getattr(user, "organisation_id", None)
        if org_id:
            return packages.filter(organisation_id=org_id)
    return packages.filter(created_by=user)


def _current_reporting_instance(request):
    instance_uuid = request.session.get("current_reporting_instance_uuid")
    if not instance_uuid:
        return None
    return ReportingInstance.objects.select_related("cycle").filter(uuid=instance_uuid).first()


def _build_items(queryset, label, url_name, url_param="obj_uuid", url_kwargs=None):
    items = []
    url_kwargs = url_kwargs or {}
    for obj in queryset.order_by("-updated_at")[:10]:
        kwargs = {url_param: obj.uuid}
        if "obj_type" in url_kwargs:
            kwargs = {"obj_type": url_kwargs["obj_type"], "obj_uuid": obj.uuid}
        items.append(
            {
                "label": label,
                "title": getattr(obj, "title", None) or getattr(obj, "code", None) or str(obj),
                "url": reverse(url_name, kwargs=kwargs),
                "updated_at": obj.updated_at,
                "status": getattr(obj, "status", ""),
            }
        )
    return items


def _build_approval_items(queryset, approvals):
    items = []
    for obj in queryset:
        approval = approvals.get(obj.uuid)
        items.append(
            {
                "obj": obj,
                "decision": approval.decision if approval else "",
                "approved": bool(approval and approval.decision == ApprovalDecision.APPROVED),
            }
        )
    return items


def _consent_items(queryset, instance):
    items = []
    for obj in queryset:
        status = consent_status_for_instance(instance, obj)
        items.append({"obj": obj, "status": status})
    return items


def _approval_state_for_instance(instance, user, obj_type=None, obj_uuid=None):
    models = {
        "indicators": Indicator,
        "targets": NationalTarget,
        "evidence": Evidence,
        "datasets": Dataset,
    }
    state = {}
    items = models.items()
    if obj_type and obj_type in models:
        items = [(obj_type, models[obj_type])]
    for key, model in items:
        queryset = filter_queryset_for_user(
            model.objects.select_related("organisation", "created_by").order_by("code" if key in {"indicators", "targets"} else "title"),
            user,
        )
        if obj_uuid:
            queryset = queryset.filter(uuid=obj_uuid)
        content_type = ContentType.objects.get_for_model(model)
        approvals = InstanceExportApproval.objects.filter(
            reporting_instance=instance,
            content_type=content_type,
            approval_scope="export",
        )
        approval_map = {approval.object_uuid: approval for approval in approvals}
        state[key] = _build_approval_items(queryset, approval_map)
    for key in models:
        state.setdefault(key, [])
    return state


@staff_member_required
def manage_organisation_list(request):
    organisations = Organisation.objects.order_by("name")
    return render(
        request,
        "nbms_app/manage/organisations_list.html",
        {"organisations": organisations},
    )


@staff_member_required
def manage_organisation_create(request):
    form = OrganisationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        organisation = form.save()
        messages.success(request, f"Organisation '{organisation.name}' created.")
        return redirect("nbms_app:manage_organisation_list")
    return render(request, "nbms_app/manage/organisation_form.html", {"form": form, "mode": "create"})


@staff_member_required
def manage_organisation_edit(request, org_id):
    organisation = get_object_or_404(Organisation, pk=org_id)
    form = OrganisationForm(request.POST or None, instance=organisation)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Organisation '{organisation.name}' updated.")
        return redirect("nbms_app:manage_organisation_list")
    return render(
        request,
        "nbms_app/manage/organisation_form.html",
        {"form": form, "mode": "edit", "organisation": organisation},
    )


@staff_member_required
def manage_user_list(request):
    org_filter = request.GET.get("org")
    users = User.objects.select_related("organisation").prefetch_related("groups").order_by("username")
    if org_filter:
        users = users.filter(organisation_id=org_filter)
    organisations = Organisation.objects.order_by("name")
    return render(
        request,
        "nbms_app/manage/users_list.html",
        {"users": users, "organisations": organisations, "org_filter": org_filter or ""},
    )


@staff_member_required
def manage_user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"User '{user.username}' created.")
        return redirect("nbms_app:manage_user_list")
    return render(request, "nbms_app/manage/user_form.html", {"form": form, "mode": "create"})


@staff_member_required
def manage_user_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    form = UserUpdateForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"User '{user.username}' updated.")
        return redirect("nbms_app:manage_user_list")
    return render(
        request,
        "nbms_app/manage/user_form.html",
        {"form": form, "mode": "edit", "managed_user": user},
    )


@staff_member_required
def manage_user_send_reset(request, user_id):
    if request.method != "POST":
        return redirect("nbms_app:manage_user_list")

    user = get_object_or_404(User, pk=user_id)
    if not user.email:
        messages.error(request, "User does not have an email address.")
        return redirect("nbms_app:manage_user_edit", user_id=user.id)

    form = PasswordResetForm({"email": user.email})
    if form.is_valid():
        form.save(
            request=request,
            use_https=request.is_secure(),
            subject_template_name="registration/password_reset_subject.txt",
            email_template_name="registration/password_reset_email.html",
        )
        messages.success(request, f"Password reset email sent to {user.email}.")
    else:
        messages.error(request, "Unable to send password reset email.")

    return redirect("nbms_app:manage_user_edit", user_id=user.id)


def national_target_list(request):
    targets = filter_queryset_for_user(
        NationalTarget.objects.select_related("organisation", "created_by").order_by("code"),
        request.user,
        perm="nbms_app.view_nationaltarget",
    )
    return render(
        request,
        "nbms_app/targets/nationaltarget_list.html",
        {"targets": targets, "can_create_target": _can_create_data(request.user)},
    )


def national_target_detail(request, target_uuid):
    targets = filter_queryset_for_user(
        NationalTarget.objects.select_related("organisation", "created_by"),
        request.user,
        perm="nbms_app.view_nationaltarget",
    )
    target = get_object_or_404(targets, uuid=target_uuid)
    can_edit = can_edit_object(request.user, target) and _status_allows_edit(target, request.user)
    current_instance = _current_reporting_instance(request)
    readiness = get_target_readiness(target, request.user, instance=current_instance)
    approvals_url = None
    consent_url = None
    indicators_url = None
    if current_instance:
        base_approvals = reverse(
            "nbms_app:reporting_instance_approvals",
            kwargs={"instance_uuid": current_instance.uuid},
        )
        approvals_url = f"{base_approvals}?{urlencode({'obj_type': 'targets', 'obj_uuid': target.uuid})}"
        consent_url = reverse("nbms_app:reporting_instance_consent", kwargs={"instance_uuid": current_instance.uuid})
    indicators_url = f"{reverse('nbms_app:indicator_list')}?target={target.uuid}"
    core_checks = [
        {"label": check["label"], "state": check["state"]}
        for check in readiness["checks"]
        if check["key"] not in {"approval", "consent"}
    ]
    core_checks.append(
        {
            "label": "Published indicators",
            "state": "ok" if readiness["details"]["published_indicator_count"] else "missing",
            "count": readiness["details"]["published_indicator_count"],
        }
    )
    core_card = {
        "title": "Core completeness",
        "icon": "sections",
        "band": _band_for_checks(core_checks),
        "band_label": _band_for_checks(core_checks),
        "checks": core_checks,
        "footer_actions": [{"label": "View indicators under this target", "url": indicators_url}],
    }
    if current_instance:
        instance_checks = [
            {
                "label": "Approval",
                "state": "ok" if readiness["details"]["approval_status"] == "approved" else "missing",
                "action_url": approvals_url,
            },
            {
                "label": "Consent",
                "state": "ok"
                if not readiness["details"]["consent_required"] or readiness["details"]["consent_status"] == "granted"
                else "missing",
                "action_url": consent_url,
            },
            {
                "label": "Approved indicators",
                "state": "ok" if readiness["details"]["approved_indicator_count"] else "missing",
                "count": readiness["details"]["approved_indicator_count"],
            },
            {
                "label": "Eligible for export",
                "state": "ok" if readiness["details"]["eligible_for_export"] else "missing",
            },
        ]
        instance_card = {
            "title": "Instance readiness",
            "icon": "export",
            "band": _band_for_checks(instance_checks),
            "band_label": _band_for_checks(instance_checks),
            "checks": instance_checks,
            "subtitle": f"Current instance: {current_instance}",
        }
    else:
        instance_card = {
            "title": "Instance readiness",
            "icon": "export",
            "band": "grey",
            "band_label": "Not set",
            "message": "Set a current reporting instance to see export readiness.",
        }
    return render(
        request,
        "nbms_app/targets/nationaltarget_detail.html",
        {
            "target": target,
            "can_edit": can_edit,
            "readiness": readiness,
            "current_instance": current_instance,
            "approvals_url": approvals_url,
            "consent_url": consent_url,
            "indicators_url": indicators_url,
            "readiness_cards": [core_card, instance_card],
        },
    )


@login_required
def national_target_create(request):
    _require_contributor(request.user)
    form = NationalTargetForm(request.POST or None)
    if not request.user.is_staff:
        form.fields["organisation"].disabled = True
    if request.method == "POST" and form.is_valid():
        target = form.save(commit=False)
        if not target.created_by:
            target.created_by = request.user
        if not target.organisation and getattr(request.user, "organisation", None):
            target.organisation = request.user.organisation
        target.save()
        messages.success(request, "National target created.")
        return redirect("nbms_app:national_target_detail", target_uuid=target.uuid)
    return render(request, "nbms_app/targets/nationaltarget_form.html", {"form": form, "mode": "create"})


@login_required
def national_target_edit(request, target_uuid):
    targets = filter_queryset_for_user(
        NationalTarget.objects.select_related("organisation", "created_by"),
        request.user,
        perm="nbms_app.view_nationaltarget",
    )
    target = get_object_or_404(targets, uuid=target_uuid)
    if not can_edit_object(request.user, target):
        raise PermissionDenied("Not allowed to edit this national target.")
    if not _status_allows_edit(target, request.user):
        raise PermissionDenied("National target cannot be edited at this status.")
    form = NationalTargetForm(request.POST or None, instance=target)
    if not request.user.is_staff:
        form.fields["organisation"].disabled = True
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "National target updated.")
        return redirect("nbms_app:national_target_detail", target_uuid=target.uuid)
    return render(
        request,
        "nbms_app/targets/nationaltarget_form.html",
        {"form": form, "mode": "edit", "target": target},
    )


def indicator_list(request):
    indicators = filter_queryset_for_user(
        Indicator.objects.select_related("national_target", "organisation", "created_by").order_by("code"),
        request.user,
        perm="nbms_app.view_indicator",
    )
    target_uuid = request.GET.get("target")
    if target_uuid:
        indicators = indicators.filter(national_target__uuid=target_uuid)
    return render(
        request,
        "nbms_app/indicators/indicator_list.html",
        {"indicators": indicators, "can_create_indicator": _can_create_data(request.user)},
    )


def indicator_detail(request, indicator_uuid):
    indicators = filter_queryset_for_user(
        Indicator.objects.select_related("national_target", "organisation", "created_by"),
        request.user,
        perm="nbms_app.view_indicator",
    )
    indicator = get_object_or_404(indicators, uuid=indicator_uuid)
    can_edit = can_edit_object(request.user, indicator) and _status_allows_edit(indicator, request.user)
    current_instance = _current_reporting_instance(request)
    readiness = get_indicator_readiness(indicator, request.user, instance=current_instance)
    approvals_url = None
    consent_url = None
    if current_instance:
        base_approvals = reverse(
            "nbms_app:reporting_instance_approvals",
            kwargs={"instance_uuid": current_instance.uuid},
        )
        approvals_url = f"{base_approvals}?{urlencode({'obj_type': 'indicators', 'obj_uuid': indicator.uuid})}"
        consent_url = reverse("nbms_app:reporting_instance_consent", kwargs={"instance_uuid": current_instance.uuid})
    core_checks = [
        {"label": check["label"], "state": check["state"]}
        for check in readiness["checks"]
        if check["key"] not in {"approval", "consent"}
    ]
    core_card = {
        "title": "Core completeness",
        "icon": "sections",
        "band": _band_for_checks(core_checks),
        "band_label": _band_for_checks(core_checks),
        "checks": core_checks,
    }
    if current_instance:
        instance_checks = [
            {
                "label": "Approval",
                "state": "ok" if readiness["details"]["approval_status"] == "approved" else "missing",
                "action_url": approvals_url,
            },
            {
                "label": "Consent",
                "state": "ok"
                if not readiness["details"]["consent_required"] or readiness["details"]["consent_status"] == "granted"
                else "missing",
                "action_url": consent_url,
            },
            {
                "label": "Eligible for export",
                "state": "ok" if readiness["details"]["eligible_for_export"] else "missing",
            },
        ]
        instance_card = {
            "title": "Instance readiness",
            "icon": "export",
            "band": _band_for_checks(instance_checks),
            "band_label": _band_for_checks(instance_checks),
            "checks": instance_checks,
            "subtitle": f"Current instance: {current_instance}",
        }
    else:
        instance_card = {
            "title": "Instance readiness",
            "icon": "export",
            "band": "grey",
            "band_label": "Not set",
            "message": "Set a current reporting instance to see export readiness.",
        }
    return render(
        request,
        "nbms_app/indicators/indicator_detail.html",
        {
            "indicator": indicator,
            "can_edit": can_edit,
            "readiness": readiness,
            "current_instance": current_instance,
            "approvals_url": approvals_url,
            "consent_url": consent_url,
            "readiness_cards": [core_card, instance_card],
        },
    )


@login_required
def indicator_create(request):
    _require_contributor(request.user)
    form = IndicatorForm(request.POST or None)
    form.fields["national_target"].queryset = filter_queryset_for_user(
        NationalTarget.objects.order_by("code"),
        request.user,
        perm="nbms_app.view_nationaltarget",
    )
    if not request.user.is_staff:
        form.fields["organisation"].disabled = True
    if request.method == "POST" and form.is_valid():
        indicator = form.save(commit=False)
        if not indicator.created_by:
            indicator.created_by = request.user
        if not indicator.organisation and getattr(request.user, "organisation", None):
            indicator.organisation = request.user.organisation
        indicator.save()
        messages.success(request, "Indicator created.")
        return redirect("nbms_app:indicator_detail", indicator_uuid=indicator.uuid)
    return render(request, "nbms_app/indicators/indicator_form.html", {"form": form, "mode": "create"})


@login_required
def indicator_edit(request, indicator_uuid):
    indicators = filter_queryset_for_user(
        Indicator.objects.select_related("national_target", "organisation", "created_by"),
        request.user,
        perm="nbms_app.view_indicator",
    )
    indicator = get_object_or_404(indicators, uuid=indicator_uuid)
    if not can_edit_object(request.user, indicator):
        raise PermissionDenied("Not allowed to edit this indicator.")
    if not _status_allows_edit(indicator, request.user):
        raise PermissionDenied("Indicator cannot be edited at this status.")
    form = IndicatorForm(request.POST or None, instance=indicator)
    form.fields["national_target"].queryset = filter_queryset_for_user(
        NationalTarget.objects.order_by("code"),
        request.user,
        perm="nbms_app.view_nationaltarget",
    )
    if not request.user.is_staff:
        form.fields["organisation"].disabled = True
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Indicator updated.")
        return redirect("nbms_app:indicator_detail", indicator_uuid=indicator.uuid)
    return render(
        request,
        "nbms_app/indicators/indicator_form.html",
        {"form": form, "mode": "edit", "indicator": indicator},
    )


def evidence_list(request):
    evidence_items = filter_queryset_for_user(
        Evidence.objects.select_related("organisation", "created_by").order_by("title"),
        request.user,
        perm="nbms_app.view_evidence",
    )
    return render(request, "nbms_app/evidence/evidence_list.html", {"evidence_items": evidence_items})


def evidence_detail(request, evidence_uuid):
    evidence_qs = filter_queryset_for_user(
        Evidence.objects.select_related("organisation", "created_by"),
        request.user,
        perm="nbms_app.view_evidence",
    )
    evidence = get_object_or_404(evidence_qs, uuid=evidence_uuid)
    can_edit = can_edit_object(request.user, evidence) if request.user.is_authenticated else False
    current_instance = _current_reporting_instance(request)
    readiness = get_evidence_readiness(evidence, request.user, instance=current_instance)
    approvals_url = None
    consent_url = None
    if current_instance:
        base_approvals = reverse(
            "nbms_app:reporting_instance_approvals",
            kwargs={"instance_uuid": current_instance.uuid},
        )
        approvals_url = f"{base_approvals}?{urlencode({'obj_type': 'evidence', 'obj_uuid': evidence.uuid})}"
        consent_url = reverse("nbms_app:reporting_instance_consent", kwargs={"instance_uuid": current_instance.uuid})
    core_checks = [
        {"label": check["label"], "state": check["state"]}
        for check in readiness["checks"]
        if check["key"] not in {"approval", "consent"}
    ]
    core_card = {
        "title": "Core completeness",
        "icon": "sections",
        "band": _band_for_checks(core_checks),
        "band_label": _band_for_checks(core_checks),
        "checks": core_checks,
    }
    if current_instance:
        instance_checks = [
            {
                "label": "Approval",
                "state": "ok" if readiness["details"]["approval_status"] == "approved" else "missing",
                "action_url": approvals_url,
            },
            {
                "label": "Consent",
                "state": "ok"
                if not readiness["details"]["consent_required"] or readiness["details"]["consent_status"] == "granted"
                else "missing",
                "action_url": consent_url,
            },
            {
                "label": "Eligible for export",
                "state": "ok" if readiness["details"]["eligible_for_export"] else "missing",
            },
        ]
        instance_card = {
            "title": "Instance readiness",
            "icon": "export",
            "band": _band_for_checks(instance_checks),
            "band_label": _band_for_checks(instance_checks),
            "checks": instance_checks,
            "subtitle": f"Current instance: {current_instance}",
        }
    else:
        instance_card = {
            "title": "Instance readiness",
            "icon": "export",
            "band": "grey",
            "band_label": "Not set",
            "message": "Set a current reporting instance to see export readiness.",
        }
    return render(
        request,
        "nbms_app/evidence/evidence_detail.html",
        {
            "evidence": evidence,
            "can_edit": can_edit,
            "readiness": readiness,
            "current_instance": current_instance,
            "approvals_url": approvals_url,
            "consent_url": consent_url,
            "readiness_cards": [core_card, instance_card],
        },
    )


@login_required
def evidence_create(request):
    _require_contributor(request.user)
    form = EvidenceForm(request.POST or None, request.FILES or None)
    if not request.user.is_staff:
        form.fields["organisation"].disabled = True
    if request.method == "POST" and form.is_valid():
        evidence = form.save(commit=False)
        if not evidence.created_by:
            evidence.created_by = request.user
        if not evidence.organisation and getattr(request.user, "organisation", None):
            evidence.organisation = request.user.organisation
        evidence.save()
        messages.success(request, "Evidence created.")
        return redirect("nbms_app:evidence_detail", evidence_uuid=evidence.uuid)
    return render(request, "nbms_app/evidence/evidence_form.html", {"form": form, "mode": "create"})


@login_required
def evidence_edit(request, evidence_uuid):
    evidence_qs = filter_queryset_for_user(
        Evidence.objects.select_related("organisation", "created_by"),
        request.user,
        perm="nbms_app.view_evidence",
    )
    evidence = get_object_or_404(evidence_qs, uuid=evidence_uuid)
    if not can_edit_object(request.user, evidence):
        raise PermissionDenied("Not allowed to edit this evidence.")
    form = EvidenceForm(request.POST or None, request.FILES or None, instance=evidence)
    if not request.user.is_staff:
        form.fields["organisation"].disabled = True
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Evidence updated.")
        return redirect("nbms_app:evidence_detail", evidence_uuid=evidence.uuid)
    return render(
        request,
        "nbms_app/evidence/evidence_form.html",
        {"form": form, "mode": "edit", "evidence": evidence},
    )


def dataset_list(request):
    datasets = filter_queryset_for_user(
        Dataset.objects.select_related("organisation", "created_by").order_by("title"),
        request.user,
        perm="nbms_app.view_dataset",
    )
    return render(request, "nbms_app/datasets/dataset_list.html", {"datasets": datasets})


def dataset_detail(request, dataset_uuid):
    datasets = filter_queryset_for_user(
        Dataset.objects.select_related("organisation", "created_by"),
        request.user,
        perm="nbms_app.view_dataset",
    )
    dataset = get_object_or_404(datasets, uuid=dataset_uuid)
    releases = dataset.releases.order_by("-created_at")
    can_edit = can_edit_object(request.user, dataset) if request.user.is_authenticated else False
    current_instance = _current_reporting_instance(request)
    readiness = get_dataset_readiness(dataset, request.user, instance=current_instance)
    approvals_url = None
    consent_url = None
    if current_instance:
        base_approvals = reverse(
            "nbms_app:reporting_instance_approvals",
            kwargs={"instance_uuid": current_instance.uuid},
        )
        approvals_url = f"{base_approvals}?{urlencode({'obj_type': 'datasets', 'obj_uuid': dataset.uuid})}"
        consent_url = reverse("nbms_app:reporting_instance_consent", kwargs={"instance_uuid": current_instance.uuid})
    core_checks = [
        {"label": check["label"], "state": check["state"]}
        for check in readiness["checks"]
        if check["key"] not in {"approval", "consent"}
    ]
    core_checks.append(
        {
            "label": "Used by indicators",
            "state": "ok" if readiness["details"]["linked_indicator_count"] else "missing",
            "count": readiness["details"]["linked_indicator_count"],
        }
    )
    core_card = {
        "title": "Core completeness",
        "icon": "sections",
        "band": _band_for_checks(core_checks),
        "band_label": _band_for_checks(core_checks),
        "checks": core_checks,
    }
    if current_instance:
        instance_checks = [
            {
                "label": "Approval",
                "state": "ok" if readiness["details"]["approval_status"] == "approved" else "missing",
                "action_url": approvals_url,
            },
            {
                "label": "Consent",
                "state": "ok"
                if not readiness["details"]["consent_required"] or readiness["details"]["consent_status"] == "granted"
                else "missing",
                "action_url": consent_url,
            },
            {
                "label": "Eligible for export",
                "state": "ok" if readiness["details"]["eligible_for_export"] else "missing",
            },
            {
                "label": "Approved indicators (current instance)",
                "state": "ok" if readiness["details"]["approved_linked_indicator_count"] else "missing",
                "count": readiness["details"]["approved_linked_indicator_count"],
            },
        ]
        instance_card = {
            "title": "Instance readiness",
            "icon": "export",
            "band": _band_for_checks(instance_checks),
            "band_label": _band_for_checks(instance_checks),
            "checks": instance_checks,
            "subtitle": f"Current instance: {current_instance}",
        }
    else:
        instance_card = {
            "title": "Instance readiness",
            "icon": "export",
            "band": "grey",
            "band_label": "Not set",
            "message": "Set a current reporting instance to see export readiness.",
        }
    return render(
        request,
        "nbms_app/datasets/dataset_detail.html",
        {
            "dataset": dataset,
            "releases": releases,
            "can_edit": can_edit,
            "readiness": readiness,
            "current_instance": current_instance,
            "approvals_url": approvals_url,
            "consent_url": consent_url,
            "readiness_cards": [core_card, instance_card],
        },
    )


@login_required
def dataset_create(request):
    _require_contributor(request.user)
    form = DatasetForm(request.POST or None)
    if not request.user.is_staff:
        form.fields["organisation"].disabled = True
    if request.method == "POST" and form.is_valid():
        dataset = form.save(commit=False)
        if not dataset.created_by:
            dataset.created_by = request.user
        if not dataset.organisation and getattr(request.user, "organisation", None):
            dataset.organisation = request.user.organisation
        dataset.save()
        messages.success(request, "Dataset created.")
        return redirect("nbms_app:dataset_detail", dataset_uuid=dataset.uuid)
    return render(request, "nbms_app/datasets/dataset_form.html", {"form": form, "mode": "create"})


@login_required
def dataset_edit(request, dataset_uuid):
    datasets = filter_queryset_for_user(
        Dataset.objects.select_related("organisation", "created_by"),
        request.user,
        perm="nbms_app.view_dataset",
    )
    dataset = get_object_or_404(datasets, uuid=dataset_uuid)
    if not can_edit_object(request.user, dataset):
        raise PermissionDenied("Not allowed to edit this dataset.")
    form = DatasetForm(request.POST or None, instance=dataset)
    if not request.user.is_staff:
        form.fields["organisation"].disabled = True
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Dataset updated.")
        return redirect("nbms_app:dataset_detail", dataset_uuid=dataset.uuid)
    return render(
        request,
        "nbms_app/datasets/dataset_form.html",
        {"form": form, "mode": "edit", "dataset": dataset},
    )


@login_required
def export_package_list(request):
    packages = _export_queryset_for_user(request.user)
    return render(request, "nbms_app/exports/export_list.html", {"packages": packages})


@login_required
def export_package_create(request):
    _require_export_creator(request.user)
    form = ExportPackageForm(request.POST or None)
    if not request.user.is_staff:
        form.fields["organisation"].disabled = True
    if request.method == "POST" and form.is_valid():
        package = form.save(commit=False)
        if not package.created_by:
            package.created_by = request.user
        if not package.organisation and getattr(request.user, "organisation", None):
            package.organisation = request.user.organisation
        package.save()
        messages.success(request, "Export package created.")
        return redirect("nbms_app:export_package_detail", package_uuid=package.uuid)
    return render(request, "nbms_app/exports/export_form.html", {"form": form, "mode": "create"})


@login_required
def export_package_detail(request, package_uuid):
    package = get_object_or_404(_export_queryset_for_user(request.user), uuid=package_uuid)
    can_submit = package.created_by_id == request.user.id or user_has_role(request.user, ROLE_SECRETARIAT)
    can_review = user_has_role(request.user, ROLE_DATA_STEWARD, ROLE_SECRETARIAT) or request.user.is_staff
    can_release = user_has_role(request.user, ROLE_SECRETARIAT) or request.user.is_staff
    readiness = get_export_package_readiness(package, request.user)
    eligibility_checks = [
        {
            "label": check["label"],
            "state": check["state"],
            "action_url": check.get("action_url"),
        }
        for check in readiness.get("checks", [])
    ]
    for item in readiness.get("blockers", []):
        eligibility_checks.append({"label": item["message"], "state": "blocked"})
    for item in readiness.get("warnings", []):
        eligibility_checks.append({"label": item["message"], "state": "warning"})
    included_checks = [
        {
            "label": "Indicators included",
            "state": "ok" if readiness["counts"]["approved_indicators"] else "missing",
            "count": readiness["counts"]["approved_indicators"],
        },
        {
            "label": "Targets included",
            "state": "ok" if readiness["counts"]["approved_targets"] else "missing",
            "count": readiness["counts"]["approved_targets"],
        },
        {
            "label": "Evidence included",
            "state": "ok" if readiness["counts"]["approved_evidence"] else "missing",
            "count": readiness["counts"]["approved_evidence"],
        },
        {
            "label": "Datasets included",
            "state": "ok" if readiness["counts"]["approved_datasets"] else "missing",
            "count": readiness["counts"]["approved_datasets"],
        },
    ]
    readiness_cards = [
        {
            "title": "Package Eligibility",
            "icon": "export",
            "band": readiness["status"],
            "band_label": readiness["status"],
            "checks": eligibility_checks,
            "message": "No export blockers detected." if readiness["status"] == "green" else "",
        },
        {
            "title": "Included counts",
            "icon": "approvals",
            "band": _band_for_checks(included_checks),
            "band_label": _band_for_checks(included_checks),
            "checks": included_checks,
        },
    ]
    return render(
        request,
        "nbms_app/exports/export_detail.html",
        {
            "package": package,
            "can_submit": can_submit,
            "can_review": can_review,
            "can_release": can_release,
            "readiness": readiness,
            "readiness_cards": readiness_cards,
        },
    )


@login_required
def export_package_action(request, package_uuid, action):
    if request.method != "POST":
        return redirect("nbms_app:export_package_list")
    package = get_object_or_404(_export_queryset_for_user(request.user), uuid=package_uuid)
    note = request.POST.get("note", "").strip()
    try:
        if action == "submit":
            submit_export_for_review(package, request.user)
            messages.success(request, "Export submitted for review.")
        elif action == "approve":
            approve_export(package, request.user, note=note)
            messages.success(request, "Export approved.")
        elif action == "reject":
            reject_export(package, request.user, note=note)
            messages.success(request, "Export rejected.")
        elif action == "release":
            release_export(package, request.user)
            messages.success(request, "Export released.")
        else:
            raise Http404()
    except Exception as exc:  # noqa: BLE001
        messages.error(request, str(exc))
    return redirect("nbms_app:export_package_detail", package_uuid=package.uuid)


@login_required
def export_package_download(request, package_uuid):
    package = get_object_or_404(_export_queryset_for_user(request.user), uuid=package_uuid)
    if package.status != ExportStatus.RELEASED:
        raise PermissionDenied("Export not released.")
    record_audit_event(request.user, "export_download", package, metadata={"status": package.status})
    response = JsonResponse(package.payload, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = f'attachment; filename="export-{package.uuid}.json"'
    return response


@staff_member_required
def export_ort7nr_instance(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    try:
        package = build_ort7nr_package(instance=instance, user=request.user)
    except PermissionDenied as exc:
        return JsonResponse({"error": str(exc)}, status=403)
    except ValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(package, json_dumps_params={"indent": 2})


@staff_member_required
def reporting_cycle_list(request):
    cycles = ReportingCycle.objects.order_by("-start_date", "code")
    return render(request, "nbms_app/reporting/cycle_list.html", {"cycles": cycles})


@staff_member_required
def reporting_cycle_create(request):
    form = ReportingCycleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cycle = form.save()
        messages.success(request, f"Reporting cycle '{cycle.code}' created.")
        return redirect("nbms_app:reporting_cycle_detail", cycle_uuid=cycle.uuid)
    return render(request, "nbms_app/reporting/cycle_form.html", {"form": form, "mode": "create"})


@staff_member_required
def reporting_cycle_detail(request, cycle_uuid):
    cycle = get_object_or_404(ReportingCycle, uuid=cycle_uuid)
    instances = cycle.instances.order_by("-created_at")
    return render(
        request,
        "nbms_app/reporting/cycle_detail.html",
        {"cycle": cycle, "instances": instances},
    )


@staff_member_required
def reporting_instance_create(request):
    cycle_uuid = request.GET.get("cycle")
    initial = {}
    if cycle_uuid:
        cycle = get_object_or_404(ReportingCycle, uuid=cycle_uuid)
        initial["cycle"] = cycle
    form = ReportingInstanceForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        instance = form.save()
        messages.success(request, "Reporting instance created.")
        return redirect("nbms_app:reporting_instance_detail", instance_uuid=instance.uuid)
    return render(request, "nbms_app/reporting/instance_form.html", {"form": form, "mode": "create"})


@staff_member_required
def reporting_instance_detail(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle", "frozen_by"), uuid=instance_uuid)
    readiness = get_instance_readiness(instance, request.user)
    section_items = readiness["details"]["sections"]["sections"]
    for item in section_items:
        item["edit_url"] = reverse(
            "nbms_app:reporting_instance_section_edit",
            kwargs={"instance_uuid": instance.uuid, "section_code": item["code"]},
        )
        item["preview_url"] = reverse(
            "nbms_app:reporting_instance_section_preview",
            kwargs={"instance_uuid": instance.uuid, "section_code": item["code"]},
        )
    approvals_base = reverse("nbms_app:reporting_instance_approvals", kwargs={"instance_uuid": instance.uuid})
    approvals_links = {
        "indicators": f"{approvals_base}?{urlencode({'obj_type': 'indicators'})}",
        "targets": f"{approvals_base}?{urlencode({'obj_type': 'targets'})}",
        "evidence": f"{approvals_base}?{urlencode({'obj_type': 'evidence'})}",
        "datasets": f"{approvals_base}?{urlencode({'obj_type': 'datasets'})}",
    }
    missing_required = readiness["details"]["sections"]["missing_required_sections"]
    incomplete_required = readiness["details"]["sections"]["incomplete_required_sections"]
    sections_band = "green"
    if missing_required:
        sections_band = "red" if settings.EXPORT_REQUIRE_SECTIONS else "amber"
    elif incomplete_required:
        sections_band = "amber"

    approvals = readiness["details"]["approvals"]
    approvals_pending = any(item["pending"] for item in approvals.values())
    approvals_band = "amber" if approvals_pending else "green"

    consent_missing = readiness["counts"]["missing_consents"]
    consent_band = "red" if consent_missing else "green"

    export_band = readiness["status"]
    export_checks = []
    for item in readiness["blockers"]:
        export_checks.append({"label": item["message"], "state": "blocked"})
    for item in readiness["warnings"]:
        export_checks.append({"label": item["message"], "state": "warning"})

    sections_checks = []
    for section in section_items:
        sections_checks.append(
            {
                "label": f"{section['code']} — {section['title']}",
                "state": section["state"],
                "actions": [
                    {"label": "Edit", "url": section["edit_url"]},
                    {"label": "Preview", "url": section["preview_url"]},
                ],
            }
        )

    approvals_checks = [
        {
            "label": "Indicators approved",
            "state": "ok" if approvals["indicators"]["pending"] == 0 else "incomplete",
            "count": f"{approvals['indicators']['approved']}/{approvals['indicators']['total']}",
            "action_url": approvals_links["indicators"],
        },
        {
            "label": "Targets approved",
            "state": "ok" if approvals["targets"]["pending"] == 0 else "incomplete",
            "count": f"{approvals['targets']['approved']}/{approvals['targets']['total']}",
            "action_url": approvals_links["targets"],
        },
        {
            "label": "Evidence approved",
            "state": "ok" if approvals["evidence"]["pending"] == 0 else "incomplete",
            "count": f"{approvals['evidence']['approved']}/{approvals['evidence']['total']}",
            "action_url": approvals_links["evidence"],
        },
        {
            "label": "Datasets approved",
            "state": "ok" if approvals["datasets"]["pending"] == 0 else "incomplete",
            "count": f"{approvals['datasets']['approved']}/{approvals['datasets']['total']}",
            "action_url": approvals_links["datasets"],
        },
    ]

    readiness_cards = [
        {
            "title": "Readiness Score",
            "icon": "instance",
            "band": readiness["readiness_band"],
            "band_label": readiness["readiness_band"],
            "score": readiness["readiness_score"],
            "score_breakdown": readiness["score_breakdown"],
        },
        {
            "title": "Sections completeness",
            "icon": "sections",
            "band": sections_band,
            "band_label": sections_band,
            "checks": sections_checks,
            "message": (
                "Missing required sections: "
                + ", ".join(missing_required)
                if missing_required
                else "Incomplete required sections: " + ", ".join(incomplete_required)
                if incomplete_required
                else ""
            ),
            "footer_actions": [
                {"label": "Open sections list", "url": reverse("nbms_app:reporting_instance_sections", kwargs={"instance_uuid": instance.uuid})}
            ],
        },
        {
            "title": "Approvals",
            "icon": "approvals",
            "band": approvals_band,
            "band_label": approvals_band,
            "checks": approvals_checks,
            "footer_actions": [{"label": "Open approval workspace", "url": approvals_base}],
        },
        {
            "title": "Consent",
            "icon": "consent",
            "band": consent_band,
            "band_label": consent_band,
            "checks": [
                {
                    "label": "Missing consent for approved IPLC records",
                    "state": "blocked" if consent_missing else "ok",
                    "count": consent_missing,
                    "action_url": reverse("nbms_app:reporting_instance_consent", kwargs={"instance_uuid": instance.uuid}),
                }
            ],
        },
        {
            "title": "Export readiness",
            "icon": "export",
            "band": export_band,
            "band_label": export_band,
            "checks": export_checks or [{"label": "No export blockers detected.", "state": "ok"}],
        },
        {
            "title": "Action queue",
            "icon": "warning",
            "band": readiness["status"],
            "band_label": readiness["status"],
            "queue": readiness.get("top_10_actions", []),
            "message": "No blockers detected." if not readiness.get("top_10_actions") else "",
        },
    ]
    return render(
        request,
        "nbms_app/reporting/instance_detail.html",
        {
            "instance": instance,
            "is_admin": _is_admin_user(request.user),
            "readiness": readiness,
            "approvals_url": approvals_base,
            "approvals_links": approvals_links,
            "consent_url": reverse("nbms_app:reporting_instance_consent", kwargs={"instance_uuid": instance.uuid}),
            "readiness_cards": readiness_cards,
        },
    )


def build_report_pack_context(instance, user):
    readiness = get_instance_readiness(instance, user)
    section_state = readiness["details"]["sections"]
    required_codes = set(section_state["required_section_codes"])
    sections = []
    for section in section_state["sections"]:
        if section["code"] not in required_codes:
            continue
        template = section["template"]
        response = section["response"]
        response_json = response.response_json if response else {}
        fields = []
        for field in (template.schema_json or {}).get("fields", []):
            key = field.get("key")
            if not key:
                continue
            label = field.get("label") or key.replace("_", " ").title()
            fields.append({"key": key, "label": label, "value": response_json.get(key, "")})
        sections.append(
            {
                "template": template,
                "code": section["code"],
                "title": template.title,
                "state": section["state"],
                "response": response,
                "fields": fields,
                "edit_url": reverse(
                    "nbms_app:reporting_instance_section_edit",
                    kwargs={"instance_uuid": instance.uuid, "section_code": template.code},
                ),
                "preview_url": reverse(
                    "nbms_app:reporting_instance_section_preview",
                    kwargs={"instance_uuid": instance.uuid, "section_code": template.code},
                ),
            }
        )

    def approved_queryset(model, extra_select=None, extra_prefetch=None):
        content_type = ContentType.objects.get_for_model(model)
        approved_ids = InstanceExportApproval.objects.filter(
            reporting_instance=instance,
            content_type=content_type,
            approval_scope="export",
            decision=ApprovalDecision.APPROVED,
        ).values_list("object_uuid", flat=True)
        queryset = filter_queryset_for_user(model.objects.filter(uuid__in=approved_ids), user)
        if extra_select:
            queryset = queryset.select_related(*extra_select)
        if extra_prefetch:
            queryset = queryset.prefetch_related(*extra_prefetch)
        return queryset

    approved_indicators = approved_queryset(
        Indicator,
        extra_select=["national_target", "organisation", "created_by"],
    ).filter(status=LifecycleStatus.PUBLISHED)
    approved_targets = approved_queryset(
        NationalTarget,
        extra_select=["organisation", "created_by"],
    ).filter(status=LifecycleStatus.PUBLISHED)
    approved_evidence = approved_queryset(
        Evidence,
        extra_select=["organisation", "created_by"],
    ).filter(status=LifecycleStatus.PUBLISHED)
    approved_datasets = approved_queryset(
        Dataset,
        extra_select=["organisation", "created_by"],
        extra_prefetch=[
            Prefetch(
                "releases",
                queryset=DatasetRelease.objects.filter(status=LifecycleStatus.PUBLISHED).order_by("-release_date"),
            )
        ],
    ).filter(status=LifecycleStatus.PUBLISHED)

    missing_required = section_state["missing_required_sections"]
    missing_consents = readiness["counts"]["missing_consents"]
    export_blockers = []
    if settings.EXPORT_REQUIRE_SECTIONS and missing_required:
        export_blockers.append(f"Missing required sections: {', '.join(missing_required)}")
    if missing_consents:
        export_blockers.append("Missing consent for approved IPLC-sensitive items.")
    section_state = "ok"
    if missing_required:
        section_state = "blocked" if settings.EXPORT_REQUIRE_SECTIONS else "missing"

    approvals = readiness["details"]["approvals"]
    approvals_card = {
        "title": "Approvals coverage",
        "icon": "approvals",
        "band": "amber" if any(item["pending"] for item in approvals.values()) else "green",
        "checks": [
            {
                "label": f"Indicators approved {approvals['indicators']['approved']} / {approvals['indicators']['total']}",
                "state": "ok" if approvals["indicators"]["approved"] else "missing",
            },
            {
                "label": f"Targets approved {approvals['targets']['approved']} / {approvals['targets']['total']}",
                "state": "ok" if approvals["targets"]["approved"] else "missing",
            },
            {
                "label": f"Evidence approved {approvals['evidence']['approved']} / {approvals['evidence']['total']}",
                "state": "ok" if approvals["evidence"]["approved"] else "missing",
            },
            {
                "label": f"Datasets approved {approvals['datasets']['approved']} / {approvals['datasets']['total']}",
                "state": "ok" if approvals["datasets"]["approved"] else "missing",
            },
        ],
        "footer_actions": [
            {
                "label": "Open approvals workspace",
                "url": reverse("nbms_app:reporting_instance_approvals", kwargs={"instance_uuid": instance.uuid}),
            }
        ],
    }
    consent_card = {
        "title": "Consent readiness",
        "icon": "consent",
        "band": "red" if missing_consents else "green",
        "checks": [
            {
                "label": "Missing IPLC consents",
                "state": "blocked" if missing_consents else "ok",
                "count": missing_consents,
            }
        ],
        "footer_actions": [
            {
                "label": "Open consent workspace",
                "url": reverse("nbms_app:reporting_instance_consent", kwargs={"instance_uuid": instance.uuid}),
            }
        ],
    }
    export_card = {
        "title": "Export readiness",
        "icon": "export",
        "band": "red" if export_blockers else "green",
        "checks": [
            {
                "label": "Required sections complete" if settings.EXPORT_REQUIRE_SECTIONS else "Sections present",
                "state": section_state,
            },
            {
                "label": "Consent cleared",
                "state": "blocked" if missing_consents else "ok",
            },
        ],
        "message": "Export blocked: " + " ".join(export_blockers) if export_blockers else "",
    }
    score_card = {
        "title": "Readiness score",
        "icon": "instance",
        "band": readiness["readiness_band"],
        "score": readiness["readiness_score"],
        "score_breakdown": readiness["score_breakdown"],
    }

    return {
        "instance": instance,
        "readiness": readiness,
        "sections": sections,
        "approved_indicators": approved_indicators,
        "approved_targets": approved_targets,
        "approved_evidence": approved_evidence,
        "approved_datasets": approved_datasets,
        "approved_counts": {
            "indicators": approved_indicators.count(),
            "targets": approved_targets.count(),
            "evidence": approved_evidence.count(),
            "datasets": approved_datasets.count(),
            "dataset_releases": DatasetRelease.objects.filter(
                dataset__in=approved_datasets,
                status=LifecycleStatus.PUBLISHED,
            ).count(),
        },
        "export_blockers": export_blockers,
        "score_card": score_card,
        "approvals_card": approvals_card,
        "consent_card": consent_card,
        "export_card": export_card,
    }


def reporting_instance_report_pack(request, instance_uuid):
    if not request.user.is_staff:
        raise PermissionDenied("Staff-only action.")

    instance = get_object_or_404(
        ReportingInstance.objects.select_related("cycle", "frozen_by"),
        uuid=instance_uuid,
    )
    context = build_report_pack_context(instance, request.user)
    return render(request, "nbms_app/reporting/report_pack.html", context)


@staff_member_required
def reporting_set_current_instance(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    request.session["current_reporting_instance_uuid"] = str(instance.uuid)
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    return redirect("nbms_app:reporting_instance_detail", instance_uuid=instance.uuid)


@staff_member_required
def reporting_clear_current_instance(request):
    request.session.pop("current_reporting_instance_uuid", None)
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    return redirect("nbms_app:home")


@staff_member_required
def reporting_instance_sections(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    readiness = get_instance_readiness(instance, request.user)
    items = [
        {
            "template": section["template"],
            "response": section["response"],
            "is_required": section["required"],
        }
        for section in readiness["details"]["sections"]["sections"]
    ]
    return render(
        request,
        "nbms_app/reporting/instance_sections.html",
        {"instance": instance, "items": items, "is_admin": _is_admin_user(request.user)},
    )


@staff_member_required
def reporting_instance_section_edit(request, instance_uuid, section_code):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    template = get_object_or_404(ReportSectionTemplate, code=section_code, is_active=True)
    response = ReportSectionResponse.objects.filter(reporting_instance=instance, template=template).first()
    initial_data = response.response_json if response else {}
    form = ReportSectionResponseForm(request.POST or None, template=template, initial_data=initial_data)

    admin_override = bool(getattr(request.user, "is_superuser", False) or user_has_role(request.user, ROLE_ADMIN))
    read_only = bool(instance.frozen_at and not admin_override)
    if read_only:
        for field in form.fields.values():
            field.disabled = True

    if request.method == "POST":
        if read_only:
            raise PermissionDenied("Reporting instance is frozen.")
        if form.is_valid():
            data = form.to_response_json()
            if response:
                response.response_json = data
                response.updated_by = request.user
                response.save(update_fields=["response_json", "updated_by", "updated_at"])
            else:
                ReportSectionResponse.objects.create(
                    reporting_instance=instance,
                    template=template,
                    response_json=data,
                    updated_by=request.user,
                )
            messages.success(request, f"Updated {template.title}.")
            return redirect("nbms_app:reporting_instance_sections", instance_uuid=instance.uuid)

    return render(
        request,
        "nbms_app/reporting/section_edit.html",
        {"instance": instance, "template": template, "form": form, "read_only": read_only},
    )


@staff_member_required
def reporting_instance_section_preview(request, instance_uuid, section_code):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    template = get_object_or_404(ReportSectionTemplate, code=section_code, is_active=True)
    response = ReportSectionResponse.objects.filter(reporting_instance=instance, template=template).first()
    response_json = response.response_json if response else {}
    fields = []
    for field in (template.schema_json or {}).get("fields", []):
        key = field.get("key")
        if not key:
            continue
        label = field.get("label") or key.replace("_", " ").title()
        fields.append({"key": key, "label": label, "value": response_json.get(key, "")})
    return render(
        request,
        "nbms_app/reporting/section_preview.html",
        {
            "instance": instance,
            "template": template,
            "response": response,
            "fields": fields,
            "response_json": response_json,
        },
    )


@login_required
def reporting_instance_approvals(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    if not can_approve_instance(request.user):
        raise PermissionDenied("Not allowed to access approvals.")

    obj_type = request.GET.get("obj_type")
    obj_uuid = request.GET.get("obj_uuid")
    approval_state = _approval_state_for_instance(instance, request.user, obj_type=obj_type, obj_uuid=obj_uuid)
    context = {
        "instance": instance,
        "indicator_items": approval_state["indicators"],
        "target_items": approval_state["targets"],
        "evidence_items": approval_state["evidence"],
        "dataset_items": approval_state["datasets"],
        "is_admin": _is_admin_user(request.user),
    }
    return render(request, "nbms_app/reporting/instance_approvals.html", context)


@login_required
def reporting_instance_approval_action(request, instance_uuid, obj_type, obj_uuid, action):
    if request.method != "POST":
        return redirect("nbms_app:reporting_instance_approvals", instance_uuid=instance_uuid)

    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    if not can_approve_instance(request.user):
        raise PermissionDenied("Not allowed to approve.")

    model_map = {
        "indicator": Indicator,
        "target": NationalTarget,
        "evidence": Evidence,
        "dataset": Dataset,
    }
    model = model_map.get(obj_type)
    if not model:
        raise Http404()

    queryset = filter_queryset_for_user(
        model.objects.select_related("organisation", "created_by"),
        request.user,
    )
    obj = get_object_or_404(queryset, uuid=obj_uuid)
    note = request.POST.get("note", "").strip()
    admin_override = request.POST.get("admin_override") in {"1", "true", "yes"}

    if action == "approve":
        approve_for_instance(instance, obj, request.user, note=note, admin_override=admin_override)
        record_audit_event(
            request.user,
            "instance_export_approve",
            obj,
            metadata={"instance_uuid": str(instance.uuid), "decision": ApprovalDecision.APPROVED},
        )
        if instance.frozen_at and admin_override and _is_admin_user(request.user):
            record_audit_event(
                request.user,
                "instance_export_override",
                obj,
                metadata={"instance_uuid": str(instance.uuid), "decision": ApprovalDecision.APPROVED},
            )
        create_notification(
            getattr(obj, "created_by", None),
            f"Export approved for {obj.__class__.__name__}: {getattr(obj, 'code', None) or getattr(obj, 'title', '')}",
            url=reverse("nbms_app:reporting_instance_approvals", kwargs={"instance_uuid": instance.uuid}),
        )
        messages.success(request, "Approval recorded.")
    elif action == "revoke":
        revoke_for_instance(instance, obj, request.user, note=note, admin_override=admin_override)
        record_audit_event(
            request.user,
            "instance_export_revoke",
            obj,
            metadata={"instance_uuid": str(instance.uuid), "decision": ApprovalDecision.REVOKED},
        )
        if instance.frozen_at and admin_override and _is_admin_user(request.user):
            record_audit_event(
                request.user,
                "instance_export_override",
                obj,
                metadata={"instance_uuid": str(instance.uuid), "decision": ApprovalDecision.REVOKED},
            )
        create_notification(
            getattr(obj, "created_by", None),
            f"Export approval revoked for {obj.__class__.__name__}: {getattr(obj, 'code', None) or getattr(obj, 'title', '')}",
            url=reverse("nbms_app:reporting_instance_approvals", kwargs={"instance_uuid": instance.uuid}),
        )
        messages.success(request, "Approval revoked.")
    else:
        raise Http404()

    return redirect("nbms_app:reporting_instance_approvals", instance_uuid=instance.uuid)


@login_required
def reporting_instance_approval_bulk(request, instance_uuid):
    if request.method != "POST":
        return redirect("nbms_app:reporting_instance_approvals", instance_uuid=instance_uuid)

    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    approvals_base = reverse("nbms_app:reporting_instance_approvals", kwargs={"instance_uuid": instance.uuid})
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("Staff-only action.")
    if not can_approve_instance(request.user):
        raise PermissionDenied("Not allowed to approve.")

    obj_type = request.POST.get("obj_type", "").strip().lower()
    action = request.POST.get("action", "").strip().lower()
    mode = request.POST.get("mode", "selected").strip().lower()
    admin_override = request.POST.get("admin_override") in {"1", "true", "yes"}
    note = request.POST.get("note", "").strip()
    rule_type = request.POST.get("rule_type", "").strip().lower()

    if instance.frozen_at and not (admin_override and _is_admin_user(request.user)):
        raise PermissionDenied("Reporting instance is frozen.")

    model_map = {
        "indicators": Indicator,
        "indicator": Indicator,
        "targets": NationalTarget,
        "target": NationalTarget,
        "evidence": Evidence,
        "datasets": Dataset,
        "dataset": Dataset,
    }
    model = model_map.get(obj_type)
    if not model:
        raise Http404()

    queryset = filter_queryset_for_user(
        model.objects.select_related("organisation", "created_by"),
        request.user,
    )
    if action == "approve":
        queryset = queryset.filter(status=LifecycleStatus.PUBLISHED)

    if mode == "selected":
        selected = request.POST.getlist("selected")
        queryset = queryset.filter(uuid__in=selected)
    elif mode == "rule" and rule_type == "indicator_by_target" and model is Indicator:
        target_uuid = request.POST.get("target_uuid")
        if not target_uuid:
            messages.error(request, "Target is required for this rule.")
            return redirect("nbms_app:reporting_instance_approvals", instance_uuid=instance.uuid)
        target_qs = filter_queryset_for_user(
            NationalTarget.objects.select_related("organisation", "created_by"),
            request.user,
        )
        target = get_object_or_404(target_qs, uuid=target_uuid)
        queryset = queryset.filter(national_target=target)

    total_count = queryset.count()
    sample = list(queryset[:10])
    missing_consent_count = 0
    for obj in queryset:
        if requires_consent(obj) and not consent_is_granted(instance, obj):
            missing_consent_count += 1
    if request.POST.get("confirm") != "1":
        return render(
            request,
            "nbms_app/reporting/instance_bulk_confirm.html",
            {
                "instance": instance,
                "obj_type": obj_type,
                "action": action,
                "mode": mode,
                "rule_type": rule_type,
                "total_count": total_count,
                "sample": sample,
                "selected_ids": request.POST.getlist("selected"),
                "target_uuid": request.POST.get("target_uuid", ""),
                "admin_override": admin_override,
                "note": note,
                "missing_consent_count": missing_consent_count,
            },
        )

    if action == "approve":
        result = bulk_approve_for_instance(
            instance,
            queryset,
            request.user,
            note=note,
            admin_override=admin_override,
            skip_missing_consent=True,
        )
        approved = result["approved"]
        skipped = result["skipped"]
        for obj, _approval in approved:
            record_audit_event(
                request.user,
                "instance_export_approve",
                obj,
                metadata={"instance_uuid": str(instance.uuid), "bulk": True, "decision": ApprovalDecision.APPROVED},
            )
            create_notification(
                getattr(obj, "created_by", None),
                f"Export approved for {obj.__class__.__name__}: {getattr(obj, 'code', None) or getattr(obj, 'title', '')}",
                url=approvals_base,
            )
        record_audit_event(
            request.user,
            "instance_export_bulk",
            instance,
            metadata={
                "instance_uuid": str(instance.uuid),
                "action": "approve",
                "obj_type": obj_type,
                "count": len(approved),
                "skipped": len(skipped),
            },
        )
        if skipped:
            messages.warning(request, f"Skipped {len(skipped)} IPLC-sensitive items without consent.")
        messages.success(request, f"Approved {len(approved)} items.")
    elif action == "revoke":
        revoked = bulk_revoke_for_instance(
            instance,
            queryset,
            request.user,
            note=note,
            admin_override=admin_override,
        )
        for obj, _approval in revoked:
            record_audit_event(
                request.user,
                "instance_export_revoke",
                obj,
                metadata={"instance_uuid": str(instance.uuid), "bulk": True, "decision": ApprovalDecision.REVOKED},
            )
            create_notification(
                getattr(obj, "created_by", None),
                f"Export approval revoked for {obj.__class__.__name__}: {getattr(obj, 'code', None) or getattr(obj, 'title', '')}",
                url=approvals_base,
            )
        record_audit_event(
            request.user,
            "instance_export_bulk",
            instance,
            metadata={
                "instance_uuid": str(instance.uuid),
                "action": "revoke",
                "obj_type": obj_type,
                "count": len(revoked),
            },
        )
        messages.success(request, f"Revoked {len(revoked)} items.")
    else:
        raise Http404()

    return redirect("nbms_app:reporting_instance_approvals", instance_uuid=instance.uuid)


@login_required
def reporting_instance_consent(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    if not _can_manage_consent(request.user):
        raise PermissionDenied("Not allowed to access consent workspace.")

    def _consent_queryset(model):
        queryset = filter_queryset_for_user(
            model.objects.select_related("organisation", "created_by"),
            request.user,
        )
        return queryset.filter(sensitivity=SensitivityLevel.IPLC_SENSITIVE)

    context = {
        "instance": instance,
        "indicator_items": _consent_items(_consent_queryset(Indicator), instance),
        "target_items": _consent_items(_consent_queryset(NationalTarget), instance),
        "evidence_items": _consent_items(_consent_queryset(Evidence), instance),
        "dataset_items": _consent_items(_consent_queryset(Dataset), instance),
    }
    return render(request, "nbms_app/reporting/instance_consent.html", context)


@login_required
def reporting_instance_consent_action(request, instance_uuid, obj_type, obj_uuid, action):
    if request.method != "POST":
        return redirect("nbms_app:reporting_instance_consent", instance_uuid=instance_uuid)

    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    if not _can_manage_consent(request.user):
        raise PermissionDenied("Not allowed to manage consent.")

    model_map = {
        "indicator": Indicator,
        "target": NationalTarget,
        "evidence": Evidence,
        "dataset": Dataset,
    }
    model = model_map.get(obj_type)
    if not model:
        raise Http404()

    queryset = filter_queryset_for_user(
        model.objects.select_related("organisation", "created_by"),
        request.user,
    ).filter(sensitivity=SensitivityLevel.IPLC_SENSITIVE)
    obj = get_object_or_404(queryset, uuid=obj_uuid)
    note = request.POST.get("note", "").strip()
    document = request.FILES.get("consent_document")

    if action == "grant":
        set_consent_status(instance, obj, request.user, ConsentStatus.GRANTED, note=note, document=document)
        messages.success(request, "Consent granted.")
    elif action == "revoke":
        set_consent_status(instance, obj, request.user, ConsentStatus.REVOKED, note=note, document=document)
        messages.success(request, "Consent revoked.")
    elif action == "deny":
        set_consent_status(instance, obj, request.user, ConsentStatus.DENIED, note=note, document=document)
        messages.success(request, "Consent denied.")
    else:
        raise Http404()

    return redirect("nbms_app:reporting_instance_consent", instance_uuid=instance.uuid)


@staff_member_required
def reporting_instance_freeze(request, instance_uuid):
    if request.method != "POST":
        return redirect("nbms_app:reporting_instance_detail", instance_uuid=instance_uuid)

    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    action = request.POST.get("action", "freeze")

    if action == "unfreeze":
        if not _is_admin_user(request.user):
            raise PermissionDenied("Only admins can unfreeze reporting instances.")
        instance.frozen_at = None
        instance.frozen_by = None
        instance.save(update_fields=["frozen_at", "frozen_by"])
        record_audit_event(
            request.user,
            "instance_unfreeze",
            instance,
            metadata={"instance_uuid": str(instance.uuid)},
        )
        create_notification(
            request.user,
            f"Reporting instance unfrozen: {instance}",
            url=reverse("nbms_app:reporting_instance_detail", kwargs={"instance_uuid": instance.uuid}),
        )
        messages.success(request, "Reporting instance unfrozen.")
        return redirect("nbms_app:reporting_instance_detail", instance_uuid=instance.uuid)

    if instance.frozen_at:
        messages.info(request, "Reporting instance is already frozen.")
        return redirect("nbms_app:reporting_instance_detail", instance_uuid=instance.uuid)

    instance.frozen_at = timezone.now()
    instance.frozen_by = request.user
    instance.save(update_fields=["frozen_at", "frozen_by"])
    record_audit_event(
        request.user,
        "instance_freeze",
        instance,
        metadata={"instance_uuid": str(instance.uuid)},
    )
    create_notification(
        request.user,
        f"Reporting instance frozen: {instance}",
        url=reverse("nbms_app:reporting_instance_detail", kwargs={"instance_uuid": instance.uuid}),
    )
    messages.success(request, "Reporting instance frozen.")
    return redirect("nbms_app:reporting_instance_detail", instance_uuid=instance.uuid)


@staff_member_required
def review_queue(request):
    targets = NationalTarget.objects.filter(status=LifecycleStatus.PENDING_REVIEW).order_by("code")
    indicators = Indicator.objects.filter(status=LifecycleStatus.PENDING_REVIEW).order_by("code")
    return render(
        request,
        "nbms_app/manage/review_queue.html",
        {"targets": targets, "indicators": indicators},
    )


@staff_member_required
def review_detail(request, obj_type, obj_uuid):
    if obj_type == "target":
        obj = get_object_or_404(NationalTarget, uuid=obj_uuid)
        perm_code = "nbms_app.view_nationaltarget"
    elif obj_type == "indicator":
        obj = get_object_or_404(Indicator, uuid=obj_uuid)
        perm_code = "nbms_app.view_indicator"
    else:
        raise Http404()

    if not request.user.has_perm(perm_code, obj) and not request.user.is_superuser:
        raise Http404()

    return render(request, "nbms_app/manage/review_detail.html", {"obj": obj, "obj_type": obj_type})


@staff_member_required
def review_action(request, obj_type, obj_uuid, action):
    if request.method != "POST":
        return redirect("nbms_app:review_queue")

    note = request.POST.get("note", "").strip()

    if obj_type == "target":
        obj = get_object_or_404(NationalTarget, uuid=obj_uuid)
    elif obj_type == "indicator":
        obj = get_object_or_404(Indicator, uuid=obj_uuid)
    else:
        raise Http404()

    try:
        if action == "approve":
            approve(obj, request.user, note=note)
            messages.success(request, "Item approved.")
        elif action == "reject":
            reject(obj, request.user, note=note)
            messages.success(request, "Item rejected.")
        else:
            raise Http404()
    except Exception as exc:  # noqa: BLE001
        messages.error(request, str(exc))

    return redirect("nbms_app:review_detail", obj_type=obj_type, obj_uuid=obj.uuid)
