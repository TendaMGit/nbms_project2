import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.db import connections, transaction
from django.db.models import Prefetch, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from urllib.parse import urlencode

from nbms_app.forms import (
    DataAgreementForm,
    DatasetCatalogForm,
    EvidenceForm,
    ExportPackageForm,
    IndicatorAlignmentForm,
    IndicatorForm,
    IndicatorMethodologyVersionForm,
    MethodologyForm,
    MethodologyVersionForm,
    MonitoringProgrammeForm,
    NationalTargetAlignmentForm,
    NationalTargetForm,
    OrganisationForm,
    ReportSectionResponseForm,
    SectionIReportContextForm,
    SectionIINBSAPStatusForm,
    SectionIIINationalTargetProgressForm,
    SectionIVFrameworkGoalProgressForm,
    SectionIVFrameworkTargetProgressForm,
    SectionVConclusionsForm,
    SensitivityClassForm,
    ReportingCycleForm,
    ReportingInstanceForm,
    UserCreateForm,
    UserUpdateForm,
)
from nbms_app.forms_catalog import (
    FrameworkCatalogForm,
    FrameworkGoalCatalogForm,
    FrameworkIndicatorCatalogForm,
    FrameworkTargetCatalogForm,
    build_readonly_panel,
    get_catalog_readonly_fields,
)
from nbms_app.models import (
    BinaryIndicatorGroup,
    BinaryIndicatorGroupResponse,
    BinaryIndicatorQuestion,
    BinaryIndicatorResponse,
    DataAgreement,
    Dataset,
    DatasetCatalog,
    DatasetCatalogIndicatorLink,
    DatasetRelease,
    Evidence,
    ExportPackage,
    ExportStatus,
    Framework,
    FrameworkGoal,
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    IndicatorFrameworkIndicatorLink,
    IndicatorMethodologyVersionLink,
    LifecycleStatus,
    Methodology,
    MethodologyDatasetLink,
    MethodologyVersion,
    MonitoringProgramme,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    ProgrammeDatasetLink,
    ReportSectionResponse,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    ReportingSnapshot,
    ReviewDecisionStatus,
    SectionIReportContext,
    SectionIINBSAPStatus,
    SectionIIINationalTargetProgress,
    SectionIVFrameworkGoalProgress,
    SectionIVFrameworkTargetProgress,
    SectionVConclusions,
    SensitivityClass,
    User,
    Notification,
    InstanceExportApproval,
    ApprovalDecision,
    ConsentStatus,
    SensitivityLevel,
)
from nbms_app.exports.ort_nr7_narrative import _required_templates, build_ort_nr7_narrative_payload
from nbms_app.exports.ort_nr7_v2 import build_ort_nr7_v2_payload
from nbms_app.services.authorization import (
    ROLE_ADMIN,
    ROLE_CONTRIBUTOR,
    ROLE_COMMUNITY_REPRESENTATIVE,
    ROLE_DATA_STEWARD,
    ROLE_INDICATOR_LEAD,
    ROLE_SECRETARIAT,
    can_edit_object,
    filter_queryset_for_user,
    is_system_admin,
    user_has_role,
)
from nbms_app.services.catalog_access import (
    can_edit_data_agreement,
    can_edit_dataset_catalog,
    can_edit_methodology,
    can_edit_monitoring_programme,
    can_edit_sensitivity_class,
    filter_data_agreements_for_user,
    filter_dataset_catalog_for_user,
    filter_methodologies_for_user,
    filter_monitoring_programmes_for_user,
    filter_organisations_for_user,
    filter_sensitivity_classes_for_user,
)
from nbms_app.services.audit import (
    audit_queryset_access,
    audit_sensitive_access,
    record_audit_event,
    suppress_audit_events,
)
from nbms_app.services.consent import (
    consent_is_granted,
    consent_status_for_instance,
    requires_consent,
    set_consent_status,
)
from nbms_app.services.indicator_data import binary_indicator_questions_for_user
from nbms_app.services.exports import approve_export, reject_export, release_export, submit_export_for_review
from nbms_app.services.instance_approvals import (
    approve_for_instance,
    can_approve_instance,
    bulk_approve_for_instance,
    bulk_revoke_for_instance,
    revoke_for_instance,
)
from nbms_app.services.lifecycle_service import archive_object, reactivate_object
from nbms_app.services.readiness import (
    get_evidence_readiness,
    get_export_package_readiness,
    get_indicator_readiness,
    get_instance_readiness,
    get_target_readiness,
)
from nbms_app.services.notifications import create_notification
from nbms_app.services.alignment_coverage import compute_alignment_coverage
from nbms_app.services.review import build_instance_review_summary, build_review_pack_context
from nbms_app.services.review_decisions import (
    create_review_decision,
    get_current_review_decision,
    review_decisions_for_user,
)
from nbms_app.services.section_progress import scoped_framework_targets, scoped_national_targets
from nbms_app.services.snapshots import (
    create_reporting_snapshot,
    diff_snapshot_readiness,
    diff_snapshots,
)
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
    datasets_qs = filter_dataset_catalog_for_user(
        DatasetCatalog.objects.select_related("custodian_org", "producer_org"),
        request.user,
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
                export_qs.filter(created_by=request.user, status=ExportStatus.DRAFT),
                "Export Package",
                "nbms_app:export_package_detail",
                url_param="package_uuid",
            )
        )
        my_drafts.sort(key=lambda item: item["updated_at"], reverse=True)

    pending_review = []
    if is_system_admin(request.user) or user_has_role(request.user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN):
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
            datasets_qs.filter(is_active=True),
            "Catalog Dataset",
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


def staff_or_system_admin_required(view_func):
    def _test(user):
        return bool(user and user.is_authenticated and (user.is_staff or is_system_admin(user)))

    return user_passes_test(_test)(view_func)

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
    if is_system_admin(user):
        return True
    return user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_INDICATOR_LEAD, ROLE_CONTRIBUTOR)


def _is_admin_user(user):
    return bool(user and (is_system_admin(user) or user_has_role(user, ROLE_ADMIN)))


def _is_catalog_manager(user):
    return bool(user and (is_system_admin(user) or user_has_role(user, ROLE_ADMIN)))


def _require_catalog_manager(user):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    if _is_catalog_manager(user):
        return
    raise PermissionDenied("Not allowed to manage catalog registries.")


def _is_alignment_manager(user):
    return bool(
        user
        and (
            is_system_admin(user)
            or user_has_role(
                user,
                ROLE_ADMIN,
                ROLE_SECRETARIAT,
                ROLE_DATA_STEWARD,
                ROLE_INDICATOR_LEAD,
            )
        )
    )


def _require_alignment_manager(user):
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    if _is_alignment_manager(user):
        return
    raise PermissionDenied("Not allowed to manage alignments.")


def _require_section_progress_access(instance, user):
    if is_system_admin(user) or user_has_role(user, ROLE_ADMIN):
        return
    approvals_exist = InstanceExportApproval.objects.filter(
        reporting_instance=instance,
        approval_scope="export",
    ).exists()
    if not approvals_exist:
        return
    if scoped_national_targets(instance, user).exists():
        return
    raise PermissionDenied("Not allowed to access section progress for this reporting instance.")


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
    if is_system_admin(user):
        return
    if user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD):
        return
    raise PermissionDenied("Not allowed to manage exports.")


def _can_create_export(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if is_system_admin(user):
        return True
    return user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD)


def _export_queryset_for_user(user):
    packages = ExportPackage.objects.select_related("organisation", "created_by").order_by("-created_at")
    if is_system_admin(user):
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


@staff_or_system_admin_required
def manage_organisation_list(request):
    organisations = Organisation.objects.order_by("name")
    return render(
        request,
        "nbms_app/manage/organisations_list.html",
        {"organisations": organisations},
    )


@staff_or_system_admin_required
def manage_organisation_create(request):
    form = OrganisationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        organisation = form.save()
        messages.success(request, f"Organisation '{organisation.name}' created.")
        return redirect("nbms_app:manage_organisation_list")
    return render(request, "nbms_app/manage/organisation_form.html", {"form": form, "mode": "create"})


@staff_or_system_admin_required
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


@staff_or_system_admin_required
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


@staff_or_system_admin_required
def manage_user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"User '{user.username}' created.")
        return redirect("nbms_app:manage_user_list")
    return render(request, "nbms_app/manage/user_form.html", {"form": form, "mode": "create"})


@staff_or_system_admin_required
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


@staff_or_system_admin_required
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
        NationalTarget.objects.select_related("organisation", "created_by")
        .exclude(status=LifecycleStatus.ARCHIVED)
        .order_by("code"),
        request.user,
        perm="nbms_app.view_nationaltarget",
    )
    targets = audit_queryset_access(request, targets, action="list")
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
    audit_sensitive_access(request, target)
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
    form = NationalTargetForm(request.POST or None, user=request.user)
    if not is_system_admin(request.user):
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
    form = NationalTargetForm(request.POST or None, instance=target, user=request.user)
    if not is_system_admin(request.user):
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
        Indicator.objects.select_related("national_target", "organisation", "created_by")
        .exclude(status=LifecycleStatus.ARCHIVED)
        .order_by("code"),
        request.user,
        perm="nbms_app.view_indicator",
    )
    target_uuid = request.GET.get("target")
    if target_uuid:
        indicators = indicators.filter(national_target__uuid=target_uuid)
    indicators = audit_queryset_access(request, indicators, action="list")
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
    audit_sensitive_access(request, indicator)
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
def national_target_alignments(request, target_uuid):
    targets = filter_queryset_for_user(
        NationalTarget.objects.select_related("organisation", "created_by"),
        request.user,
        perm="nbms_app.view_nationaltarget",
    )
    target = get_object_or_404(targets, uuid=target_uuid)
    audit_sensitive_access(request, target)
    frameworks = filter_queryset_for_user(
        Framework.objects.exclude(status=LifecycleStatus.ARCHIVED),
        request.user,
        perm="nbms_app.view_framework",
    ).order_by("code")
    selected_framework_uuid = request.GET.get("framework") or ""
    selected_framework = None
    if selected_framework_uuid:
        selected_framework = frameworks.filter(uuid=selected_framework_uuid).first()
    form = NationalTargetAlignmentForm(
        request.POST or None,
        user=request.user,
        framework_id=selected_framework.id if selected_framework else None,
    )
    if request.method == "POST":
        _require_alignment_manager(request.user)
        if form.is_valid():
            framework_target = form.cleaned_data["framework_target"]
            link = NationalTargetFrameworkTargetLink.objects.filter(
                national_target=target,
                framework_target=framework_target,
            ).first()
            if link:
                was_active = link.is_active
                link.relation_type = form.cleaned_data["relation_type"]
                link.confidence = form.cleaned_data["confidence"]
                link.notes = form.cleaned_data["notes"]
                link.source = form.cleaned_data["source"]
                link.save()
                if not was_active:
                    reactivate_object(request.user, link, request=request)
            else:
                link = form.save(commit=False)
                link.national_target = target
                link.save()
            messages.success(request, "Alignment saved.")
            return redirect("nbms_app:national_target_alignments", target_uuid=target.uuid)
    links = (
        NationalTargetFrameworkTargetLink.objects.filter(national_target=target, is_active=True)
        .select_related("framework_target", "framework_target__framework")
        .order_by("framework_target__framework__code", "framework_target__code")
    )
    if selected_framework:
        links = links.filter(framework_target__framework=selected_framework)
    return render(
        request,
        "nbms_app/alignments/national_target_alignments.html",
        {
            "target": target,
            "links": links,
            "form": form,
            "frameworks": frameworks,
            "selected_framework": selected_framework,
            "can_manage": _is_alignment_manager(request.user),
        },
    )


@login_required
@require_POST
def national_target_alignment_archive(request, link_id):
    _require_alignment_manager(request.user)
    links = NationalTargetFrameworkTargetLink.objects.select_related(
        "national_target",
        "framework_target",
    ).filter(is_active=True)
    link = get_object_or_404(links, id=link_id)
    archive_object(request.user, link, request=request)
    messages.success(request, "Alignment archived.")
    return redirect("nbms_app:national_target_alignments", target_uuid=link.national_target.uuid)


@login_required
def indicator_alignments(request, indicator_uuid):
    indicators = filter_queryset_for_user(
        Indicator.objects.select_related("national_target", "organisation", "created_by"),
        request.user,
        perm="nbms_app.view_indicator",
    )
    indicator = get_object_or_404(indicators, uuid=indicator_uuid)
    audit_sensitive_access(request, indicator)
    frameworks = filter_queryset_for_user(
        Framework.objects.exclude(status=LifecycleStatus.ARCHIVED),
        request.user,
        perm="nbms_app.view_framework",
    ).order_by("code")
    selected_framework_uuid = request.GET.get("framework") or ""
    selected_framework = None
    if selected_framework_uuid:
        selected_framework = frameworks.filter(uuid=selected_framework_uuid).first()
    form = IndicatorAlignmentForm(
        request.POST or None,
        user=request.user,
        framework_id=selected_framework.id if selected_framework else None,
    )
    if request.method == "POST":
        _require_alignment_manager(request.user)
        if form.is_valid():
            framework_indicator = form.cleaned_data["framework_indicator"]
            link = IndicatorFrameworkIndicatorLink.objects.filter(
                indicator=indicator,
                framework_indicator=framework_indicator,
            ).first()
            if link:
                was_active = link.is_active
                link.relation_type = form.cleaned_data["relation_type"]
                link.confidence = form.cleaned_data["confidence"]
                link.notes = form.cleaned_data["notes"]
                link.source = form.cleaned_data["source"]
                link.save()
                if not was_active:
                    reactivate_object(request.user, link, request=request)
            else:
                link = form.save(commit=False)
                link.indicator = indicator
                link.save()
            messages.success(request, "Alignment saved.")
            return redirect("nbms_app:indicator_alignments", indicator_uuid=indicator.uuid)
    links = (
        IndicatorFrameworkIndicatorLink.objects.filter(indicator=indicator, is_active=True)
        .select_related("framework_indicator", "framework_indicator__framework")
        .order_by("framework_indicator__framework__code", "framework_indicator__code")
    )
    if selected_framework:
        links = links.filter(framework_indicator__framework=selected_framework)
    return render(
        request,
        "nbms_app/alignments/indicator_alignments.html",
        {
            "indicator": indicator,
            "links": links,
            "form": form,
            "frameworks": frameworks,
            "selected_framework": selected_framework,
            "can_manage": _is_alignment_manager(request.user),
        },
    )


@login_required
@require_POST
def indicator_alignment_archive(request, link_id):
    _require_alignment_manager(request.user)
    links = IndicatorFrameworkIndicatorLink.objects.select_related(
        "indicator",
        "framework_indicator",
    ).filter(is_active=True)
    link = get_object_or_404(links, id=link_id)
    archive_object(request.user, link, request=request)
    messages.success(request, "Alignment archived.")
    return redirect("nbms_app:indicator_alignments", indicator_uuid=link.indicator.uuid)


@login_required
def indicator_methodology_versions(request, indicator_uuid):
    indicators = filter_queryset_for_user(
        Indicator.objects.select_related("national_target", "organisation", "created_by"),
        request.user,
        perm="nbms_app.view_indicator",
    )
    indicator = get_object_or_404(indicators, uuid=indicator_uuid)
    audit_sensitive_access(request, indicator)
    form = IndicatorMethodologyVersionForm(request.POST or None, user=request.user)
    if request.method == "POST":
        _require_alignment_manager(request.user)
        if form.is_valid():
            version = form.cleaned_data["methodology_version"]
            link = IndicatorMethodologyVersionLink.objects.filter(
                indicator=indicator,
                methodology_version=version,
            ).first()
            if link:
                was_active = link.is_active
                link.is_primary = form.cleaned_data["is_primary"]
                link.notes = form.cleaned_data["notes"]
                link.source = form.cleaned_data["source"]
                link.save()
                if not was_active:
                    reactivate_object(request.user, link, request=request)
            else:
                link = form.save(commit=False)
                link.indicator = indicator
                link.save()
            messages.success(request, "Methodology version linked.")
            return redirect("nbms_app:indicator_methodologies", indicator_uuid=indicator.uuid)
    links = (
        IndicatorMethodologyVersionLink.objects.filter(indicator=indicator, is_active=True)
        .select_related("methodology_version", "methodology_version__methodology")
        .order_by("-is_primary", "methodology_version__methodology__methodology_code", "methodology_version__version")
    )
    return render(
        request,
        "nbms_app/alignments/indicator_methodologies.html",
        {
            "indicator": indicator,
            "links": links,
            "form": form,
            "can_manage": _is_alignment_manager(request.user),
        },
    )


@login_required
@require_POST
def indicator_methodology_archive(request, link_id):
    _require_alignment_manager(request.user)
    links = IndicatorMethodologyVersionLink.objects.select_related("indicator").filter(is_active=True)
    link = get_object_or_404(links, id=link_id)
    archive_object(request.user, link, request=request)
    messages.success(request, "Methodology link archived.")
    return redirect("nbms_app:indicator_methodologies", indicator_uuid=link.indicator.uuid)


@login_required
def indicator_create(request):
    _require_contributor(request.user)
    form = IndicatorForm(request.POST or None, user=request.user)
    form.fields["national_target"].queryset = filter_queryset_for_user(
        NationalTarget.objects.order_by("code"),
        request.user,
        perm="nbms_app.view_nationaltarget",
    )
    if not is_system_admin(request.user):
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
    form = IndicatorForm(request.POST or None, instance=indicator, user=request.user)
    form.fields["national_target"].queryset = filter_queryset_for_user(
        NationalTarget.objects.order_by("code"),
        request.user,
        perm="nbms_app.view_nationaltarget",
    )
    if not is_system_admin(request.user):
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
    evidence_items = audit_queryset_access(request, evidence_items, action="list")
    return render(request, "nbms_app/evidence/evidence_list.html", {"evidence_items": evidence_items})


def evidence_detail(request, evidence_uuid):
    evidence_qs = filter_queryset_for_user(
        Evidence.objects.select_related("organisation", "created_by"),
        request.user,
        perm="nbms_app.view_evidence",
    )
    evidence = get_object_or_404(evidence_qs, uuid=evidence_uuid)
    audit_sensitive_access(request, evidence)
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
    if not is_system_admin(request.user):
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
    if not is_system_admin(request.user):
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


def _sync_dataset_catalog_links(dataset, programmes, indicators, methodologies):
    ProgrammeDatasetLink.objects.filter(dataset=dataset).exclude(programme__in=programmes).delete()
    MethodologyDatasetLink.objects.filter(dataset=dataset).exclude(methodology__in=methodologies).delete()
    DatasetCatalogIndicatorLink.objects.filter(dataset=dataset).exclude(indicator__in=indicators).delete()

    existing_programmes = set(
        ProgrammeDatasetLink.objects.filter(dataset=dataset, programme__in=programmes).values_list(
            "programme_id", flat=True
        )
    )
    for programme in programmes:
        if programme.id not in existing_programmes:
            ProgrammeDatasetLink.objects.create(dataset=dataset, programme=programme)

    existing_methodologies = set(
        MethodologyDatasetLink.objects.filter(dataset=dataset, methodology__in=methodologies).values_list(
            "methodology_id", flat=True
        )
    )
    for methodology in methodologies:
        if methodology.id not in existing_methodologies:
            MethodologyDatasetLink.objects.create(dataset=dataset, methodology=methodology)

    existing_indicators = set(
        DatasetCatalogIndicatorLink.objects.filter(dataset=dataset, indicator__in=indicators).values_list(
            "indicator_id", flat=True
        )
    )
    for indicator in indicators:
        if indicator.id not in existing_indicators:
            DatasetCatalogIndicatorLink.objects.create(dataset=dataset, indicator=indicator)


def dataset_list(request):
    datasets = filter_dataset_catalog_for_user(
        DatasetCatalog.objects.select_related(
            "custodian_org",
            "producer_org",
            "agreement",
            "sensitivity_class",
        ).order_by("dataset_code"),
        request.user,
    )
    datasets = audit_queryset_access(request, datasets, action="list")
    return render(
        request,
        "nbms_app/datasets/dataset_list.html",
        {"datasets": datasets, "can_create_dataset": _can_create_data(request.user)},
    )


def dataset_detail(request, dataset_uuid):
    datasets = filter_dataset_catalog_for_user(
        DatasetCatalog.objects.select_related(
            "custodian_org",
            "producer_org",
            "agreement",
            "sensitivity_class",
        ),
        request.user,
    )
    dataset = get_object_or_404(datasets, uuid=dataset_uuid)
    audit_sensitive_access(request, dataset)
    can_edit = can_edit_dataset_catalog(request.user, dataset) if request.user.is_authenticated else False
    allowed_programmes = filter_monitoring_programmes_for_user(MonitoringProgramme.objects.all(), request.user)
    allowed_methodologies = filter_methodologies_for_user(Methodology.objects.all(), request.user)
    allowed_indicators = filter_queryset_for_user(
        Indicator.objects.all(), request.user, perm="nbms_app.view_indicator"
    )
    programme_links = (
        dataset.programme_links.filter(programme__in=allowed_programmes)
        .select_related("programme")
        .order_by("programme__programme_code")
    )
    methodology_links = (
        dataset.methodology_links.filter(methodology__in=allowed_methodologies)
        .select_related("methodology")
        .order_by("methodology__methodology_code")
    )
    indicator_links = (
        dataset.indicator_links.filter(indicator__in=allowed_indicators)
        .select_related("indicator")
        .order_by("indicator__code")
    )
    return render(
        request,
        "nbms_app/datasets/dataset_detail.html",
        {
            "dataset": dataset,
            "can_edit": can_edit,
            "programme_links": programme_links,
            "methodology_links": methodology_links,
            "indicator_links": indicator_links,
        },
    )


@login_required
def dataset_create(request):
    _require_contributor(request.user)
    form = DatasetCatalogForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        dataset = form.save(commit=False)
        if not dataset.custodian_org and getattr(request.user, "organisation", None):
            dataset.custodian_org = request.user.organisation
        dataset.save()
        _sync_dataset_catalog_links(
            dataset,
            form.cleaned_data.get("programmes", []),
            form.cleaned_data.get("indicators", []),
            form.cleaned_data.get("methodologies", []),
        )
        messages.success(request, "Dataset catalog entry created.")
        return redirect("nbms_app:dataset_detail", dataset_uuid=dataset.uuid)
    return render(request, "nbms_app/datasets/dataset_form.html", {"form": form, "mode": "create"})


@login_required
def dataset_edit(request, dataset_uuid):
    datasets = filter_dataset_catalog_for_user(
        DatasetCatalog.objects.select_related(
            "custodian_org",
            "producer_org",
            "agreement",
            "sensitivity_class",
        ),
        request.user,
    )
    dataset = get_object_or_404(datasets, uuid=dataset_uuid)
    if not can_edit_dataset_catalog(request.user, dataset):
        raise PermissionDenied("Not allowed to edit this dataset.")
    form = DatasetCatalogForm(request.POST or None, instance=dataset, user=request.user)
    if request.method == "POST" and form.is_valid():
        dataset = form.save()
        _sync_dataset_catalog_links(
            dataset,
            form.cleaned_data.get("programmes", []),
            form.cleaned_data.get("indicators", []),
            form.cleaned_data.get("methodologies", []),
        )
        messages.success(request, "Dataset catalog entry updated.")
        return redirect("nbms_app:dataset_detail", dataset_uuid=dataset.uuid)
    return render(
        request,
        "nbms_app/datasets/dataset_form.html",
        {"form": form, "mode": "edit", "dataset": dataset},
    )


def monitoring_programme_list(request):
    programmes = filter_monitoring_programmes_for_user(
        MonitoringProgramme.objects.select_related("lead_org", "sensitivity_class").order_by("programme_code"),
        request.user,
    )
    programmes = audit_queryset_access(request, programmes, action="list")
    return render(
        request,
        "nbms_app/catalog/monitoring_programme_list.html",
        {"programmes": programmes, "can_create_programme": _can_create_data(request.user)},
    )


def monitoring_programme_detail(request, programme_uuid):
    programmes = filter_monitoring_programmes_for_user(
        MonitoringProgramme.objects.select_related("lead_org", "sensitivity_class"),
        request.user,
    )
    programme = get_object_or_404(programmes, uuid=programme_uuid)
    audit_sensitive_access(request, programme)
    can_edit = can_edit_monitoring_programme(request.user, programme) if request.user.is_authenticated else False
    allowed_datasets = filter_dataset_catalog_for_user(DatasetCatalog.objects.all(), request.user)
    allowed_indicators = filter_queryset_for_user(
        Indicator.objects.all(), request.user, perm="nbms_app.view_indicator"
    )
    dataset_links = (
        programme.dataset_links.filter(dataset__in=allowed_datasets)
        .select_related("dataset")
        .order_by("dataset__dataset_code")
    )
    indicator_links = (
        programme.indicator_links.filter(indicator__in=allowed_indicators)
        .select_related("indicator")
        .order_by("indicator__code")
    )
    return render(
        request,
        "nbms_app/catalog/monitoring_programme_detail.html",
        {
            "programme": programme,
            "can_edit": can_edit,
            "dataset_links": dataset_links,
            "indicator_links": indicator_links,
        },
    )


@login_required
def monitoring_programme_create(request):
    _require_contributor(request.user)
    form = MonitoringProgrammeForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        programme = form.save(commit=False)
        if not programme.lead_org and getattr(request.user, "organisation", None):
            programme.lead_org = request.user.organisation
        programme.save()
        form.save_m2m()
        messages.success(request, "Monitoring programme created.")
        return redirect("nbms_app:monitoring_programme_detail", programme_uuid=programme.uuid)
    return render(request, "nbms_app/catalog/monitoring_programme_form.html", {"form": form, "mode": "create"})


@login_required
def monitoring_programme_edit(request, programme_uuid):
    programmes = filter_monitoring_programmes_for_user(
        MonitoringProgramme.objects.select_related("lead_org", "sensitivity_class"),
        request.user,
    )
    programme = get_object_or_404(programmes, uuid=programme_uuid)
    if not can_edit_monitoring_programme(request.user, programme):
        raise PermissionDenied("Not allowed to edit this monitoring programme.")
    form = MonitoringProgrammeForm(request.POST or None, instance=programme, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Monitoring programme updated.")
        return redirect("nbms_app:monitoring_programme_detail", programme_uuid=programme.uuid)
    return render(
        request,
        "nbms_app/catalog/monitoring_programme_form.html",
        {"form": form, "mode": "edit", "programme": programme},
    )


def methodology_list(request):
    methodologies = filter_methodologies_for_user(
        Methodology.objects.select_related("owner_org").order_by("methodology_code"),
        request.user,
    )
    methodologies = audit_queryset_access(request, methodologies, action="list")
    return render(
        request,
        "nbms_app/catalog/methodology_list.html",
        {"methodologies": methodologies, "can_create_methodology": _can_create_data(request.user)},
    )


def methodology_detail(request, methodology_uuid):
    methodologies = filter_methodologies_for_user(
        Methodology.objects.select_related("owner_org"),
        request.user,
    )
    methodology = get_object_or_404(methodologies, uuid=methodology_uuid)
    audit_sensitive_access(request, methodology)
    can_edit = can_edit_methodology(request.user, methodology) if request.user.is_authenticated else False
    versions = methodology.versions.order_by("-effective_date", "-created_at")
    allowed_datasets = filter_dataset_catalog_for_user(DatasetCatalog.objects.all(), request.user)
    allowed_indicators = filter_queryset_for_user(
        Indicator.objects.all(), request.user, perm="nbms_app.view_indicator"
    )
    dataset_links = (
        methodology.dataset_links.filter(dataset__in=allowed_datasets)
        .select_related("dataset")
        .order_by("dataset__dataset_code")
    )
    indicator_links = (
        methodology.indicator_links.filter(indicator__in=allowed_indicators)
        .select_related("indicator")
        .order_by("indicator__code")
    )
    return render(
        request,
        "nbms_app/catalog/methodology_detail.html",
        {
            "methodology": methodology,
            "can_edit": can_edit,
            "versions": versions,
            "dataset_links": dataset_links,
            "indicator_links": indicator_links,
        },
    )


@login_required
def methodology_create(request):
    _require_contributor(request.user)
    form = MethodologyForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        methodology = form.save(commit=False)
        if not methodology.owner_org and getattr(request.user, "organisation", None):
            methodology.owner_org = request.user.organisation
        methodology.save()
        messages.success(request, "Methodology created.")
        return redirect("nbms_app:methodology_detail", methodology_uuid=methodology.uuid)
    return render(request, "nbms_app/catalog/methodology_form.html", {"form": form, "mode": "create"})


@login_required
def methodology_edit(request, methodology_uuid):
    methodologies = filter_methodologies_for_user(
        Methodology.objects.select_related("owner_org"),
        request.user,
    )
    methodology = get_object_or_404(methodologies, uuid=methodology_uuid)
    if not can_edit_methodology(request.user, methodology):
        raise PermissionDenied("Not allowed to edit this methodology.")
    form = MethodologyForm(request.POST or None, instance=methodology, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Methodology updated.")
        return redirect("nbms_app:methodology_detail", methodology_uuid=methodology.uuid)
    return render(
        request,
        "nbms_app/catalog/methodology_form.html",
        {"form": form, "mode": "edit", "methodology": methodology},
    )


def methodology_version_list(request):
    methodologies = filter_methodologies_for_user(Methodology.objects.all(), request.user)
    methodology_ids = list(methodologies.values_list("id", flat=True))
    versions = MethodologyVersion.objects.select_related("methodology").filter(
        methodology_id__in=methodology_ids
    ).order_by("methodology__methodology_code", "-effective_date", "-created_at")
    versions = audit_queryset_access(request, versions, action="list")
    return render(
        request,
        "nbms_app/catalog/methodology_version_list.html",
        {"versions": versions, "can_create_version": _can_create_data(request.user)},
    )


def methodology_version_detail(request, version_uuid):
    methodologies = filter_methodologies_for_user(Methodology.objects.all(), request.user)
    methodology_ids = list(methodologies.values_list("id", flat=True))
    versions = MethodologyVersion.objects.select_related("methodology").filter(methodology_id__in=methodology_ids)
    version = get_object_or_404(versions, uuid=version_uuid)
    audit_sensitive_access(request, version)
    can_edit = can_edit_methodology(request.user, version.methodology) if request.user.is_authenticated else False
    return render(
        request,
        "nbms_app/catalog/methodology_version_detail.html",
        {"version": version, "can_edit": can_edit},
    )


@login_required
def methodology_version_create(request):
    _require_contributor(request.user)
    form = MethodologyVersionForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        version = form.save()
        messages.success(request, "Methodology version created.")
        return redirect("nbms_app:methodology_detail", methodology_uuid=version.methodology.uuid)
    return render(
        request,
        "nbms_app/catalog/methodology_version_form.html",
        {"form": form, "mode": "create"},
    )


@login_required
def methodology_version_edit(request, version_uuid):
    methodologies = filter_methodologies_for_user(Methodology.objects.all(), request.user)
    methodology_ids = list(methodologies.values_list("id", flat=True))
    versions = MethodologyVersion.objects.select_related("methodology").filter(methodology_id__in=methodology_ids)
    version = get_object_or_404(versions, uuid=version_uuid)
    audit_sensitive_access(request, version, action="edit")
    if not can_edit_methodology(request.user, version.methodology):
        raise PermissionDenied("Not allowed to edit this methodology version.")
    form = MethodologyVersionForm(request.POST or None, instance=version, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Methodology version updated.")
        return redirect("nbms_app:methodology_detail", methodology_uuid=version.methodology.uuid)
    return render(
        request,
        "nbms_app/catalog/methodology_version_form.html",
        {"form": form, "mode": "edit", "version": version},
    )


def data_agreement_list(request):
    agreements = filter_data_agreements_for_user(
        DataAgreement.objects.prefetch_related("parties").order_by("agreement_code"),
        request.user,
    )
    agreements = audit_queryset_access(request, agreements, action="list")
    return render(
        request,
        "nbms_app/catalog/data_agreement_list.html",
        {"agreements": agreements, "can_create_agreement": _can_create_data(request.user)},
    )


def data_agreement_detail(request, agreement_uuid):
    agreements = filter_data_agreements_for_user(
        DataAgreement.objects.prefetch_related("parties"),
        request.user,
    )
    agreement = get_object_or_404(agreements, uuid=agreement_uuid)
    audit_sensitive_access(request, agreement)
    can_edit = can_edit_data_agreement(request.user, agreement) if request.user.is_authenticated else False
    return render(
        request,
        "nbms_app/catalog/data_agreement_detail.html",
        {"agreement": agreement, "can_edit": can_edit},
    )


@login_required
def data_agreement_create(request):
    _require_contributor(request.user)
    form = DataAgreementForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        agreement = form.save()
        messages.success(request, "Data agreement created.")
        return redirect("nbms_app:data_agreement_detail", agreement_uuid=agreement.uuid)
    return render(request, "nbms_app/catalog/data_agreement_form.html", {"form": form, "mode": "create"})


@login_required
def data_agreement_edit(request, agreement_uuid):
    agreements = filter_data_agreements_for_user(
        DataAgreement.objects.prefetch_related("parties"),
        request.user,
    )
    agreement = get_object_or_404(agreements, uuid=agreement_uuid)
    if not can_edit_data_agreement(request.user, agreement):
        raise PermissionDenied("Not allowed to edit this data agreement.")
    form = DataAgreementForm(request.POST or None, instance=agreement, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Data agreement updated.")
        return redirect("nbms_app:data_agreement_detail", agreement_uuid=agreement.uuid)
    return render(
        request,
        "nbms_app/catalog/data_agreement_form.html",
        {"form": form, "mode": "edit", "agreement": agreement},
    )


def sensitivity_class_list(request):
    classes = filter_sensitivity_classes_for_user(
        SensitivityClass.objects.order_by("sensitivity_code"),
        request.user,
    )
    return render(
        request,
        "nbms_app/catalog/sensitivity_class_list.html",
        {"classes": classes, "can_create_class": _can_create_data(request.user)},
    )


def sensitivity_class_detail(request, class_uuid):
    classes = filter_sensitivity_classes_for_user(
        SensitivityClass.objects.order_by("sensitivity_code"),
        request.user,
    )
    sensitivity_class = get_object_or_404(classes, uuid=class_uuid)
    audit_sensitive_access(request, sensitivity_class)
    can_edit = can_edit_sensitivity_class(request.user, sensitivity_class) if request.user.is_authenticated else False
    return render(
        request,
        "nbms_app/catalog/sensitivity_class_detail.html",
        {"sensitivity_class": sensitivity_class, "can_edit": can_edit},
    )


@login_required
def sensitivity_class_create(request):
    _require_contributor(request.user)
    if not can_edit_sensitivity_class(request.user, None):
        raise PermissionDenied("Not allowed to manage sensitivity classes.")
    form = SensitivityClassForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        sensitivity_class = form.save()
        messages.success(request, "Sensitivity class created.")
        return redirect("nbms_app:sensitivity_class_detail", class_uuid=sensitivity_class.uuid)
    return render(request, "nbms_app/catalog/sensitivity_class_form.html", {"form": form, "mode": "create"})


@login_required
def sensitivity_class_edit(request, class_uuid):
    classes = filter_sensitivity_classes_for_user(
        SensitivityClass.objects.order_by("sensitivity_code"),
        request.user,
    )
    sensitivity_class = get_object_or_404(classes, uuid=class_uuid)
    if not can_edit_sensitivity_class(request.user, sensitivity_class):
        raise PermissionDenied("Not allowed to edit this sensitivity class.")
    form = SensitivityClassForm(request.POST or None, instance=sensitivity_class)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Sensitivity class updated.")
        return redirect("nbms_app:sensitivity_class_detail", class_uuid=sensitivity_class.uuid)
    return render(
        request,
        "nbms_app/catalog/sensitivity_class_form.html",
        {"form": form, "mode": "edit", "sensitivity_class": sensitivity_class},
    )


def framework_list(request):
    frameworks = filter_queryset_for_user(
        Framework.objects.exclude(status=LifecycleStatus.ARCHIVED).order_by("code"),
        request.user,
        perm="nbms_app.view_framework",
    )
    query = request.GET.get("q")
    if query:
        frameworks = frameworks.filter(Q(code__icontains=query) | Q(title__icontains=query))
    return render(
        request,
        "nbms_app/frameworks/framework_list.html",
        {"frameworks": frameworks, "query": query, "can_manage_catalog": _is_catalog_manager(request.user)},
    )


def framework_detail(request, framework_uuid):
    frameworks = filter_queryset_for_user(
        Framework.objects.order_by("code"),
        request.user,
        perm="nbms_app.view_framework",
    )
    framework = get_object_or_404(frameworks, uuid=framework_uuid)
    goals = filter_queryset_for_user(
        FrameworkGoal.objects.filter(framework=framework)
        .exclude(status=LifecycleStatus.ARCHIVED)
        .order_by("sort_order", "code"),
        request.user,
    )
    targets = filter_queryset_for_user(
        FrameworkTarget.objects.filter(framework=framework)
        .exclude(status=LifecycleStatus.ARCHIVED)
        .order_by("code"),
        request.user,
        perm="nbms_app.view_frameworktarget",
    )
    indicators = filter_queryset_for_user(
        FrameworkIndicator.objects.filter(framework=framework)
        .exclude(status=LifecycleStatus.ARCHIVED)
        .order_by("code"),
        request.user,
        perm="nbms_app.view_frameworkindicator",
    )
    return render(
        request,
        "nbms_app/frameworks/framework_detail.html",
        {
            "framework": framework,
            "goals": goals,
            "targets": targets,
            "indicators": indicators,
            "can_manage_catalog": _is_catalog_manager(request.user),
        },
    )


def framework_goal_list(request):
    framework_ids = list(
        filter_queryset_for_user(
            Framework.objects.exclude(status=LifecycleStatus.ARCHIVED),
            request.user,
            perm="nbms_app.view_framework",
        ).values_list(
            "id", flat=True
        )
    )
    goals = filter_queryset_for_user(
        FrameworkGoal.objects.filter(framework_id__in=framework_ids)
        .exclude(status=LifecycleStatus.ARCHIVED)
        .order_by("framework__code", "sort_order"),
        request.user,
    )
    query = request.GET.get("q")
    if query:
        goals = goals.filter(Q(code__icontains=query) | Q(title__icontains=query))
    return render(
        request,
        "nbms_app/frameworks/framework_goal_list.html",
        {"goals": goals, "query": query, "can_manage_catalog": _is_catalog_manager(request.user)},
    )


def framework_goal_detail(request, goal_uuid):
    framework_ids = list(
        filter_queryset_for_user(
            Framework.objects.exclude(status=LifecycleStatus.ARCHIVED),
            request.user,
            perm="nbms_app.view_framework",
        ).values_list(
            "id", flat=True
        )
    )
    goals = filter_queryset_for_user(
        FrameworkGoal.objects.filter(framework_id__in=framework_ids).exclude(status=LifecycleStatus.ARCHIVED),
        request.user,
    )
    goal = get_object_or_404(goals, uuid=goal_uuid)
    targets = filter_queryset_for_user(
        FrameworkTarget.objects.filter(goal=goal).exclude(status=LifecycleStatus.ARCHIVED).order_by("code"),
        request.user,
        perm="nbms_app.view_frameworktarget",
    )
    return render(
        request,
        "nbms_app/frameworks/framework_goal_detail.html",
        {"goal": goal, "targets": targets, "can_manage_catalog": _is_catalog_manager(request.user)},
    )


def framework_target_list(request):
    targets = filter_queryset_for_user(
        FrameworkTarget.objects.select_related("framework", "goal")
        .exclude(status=LifecycleStatus.ARCHIVED)
        .order_by("framework__code", "code"),
        request.user,
        perm="nbms_app.view_frameworktarget",
    )
    query = request.GET.get("q")
    if query:
        targets = targets.filter(Q(code__icontains=query) | Q(title__icontains=query))
    return render(
        request,
        "nbms_app/frameworks/framework_target_list.html",
        {"targets": targets, "query": query, "can_manage_catalog": _is_catalog_manager(request.user)},
    )


def framework_target_detail(request, target_uuid):
    targets = filter_queryset_for_user(
        FrameworkTarget.objects.select_related("framework", "goal").exclude(status=LifecycleStatus.ARCHIVED),
        request.user,
        perm="nbms_app.view_frameworktarget",
    )
    target = get_object_or_404(targets, uuid=target_uuid)
    indicators = filter_queryset_for_user(
        FrameworkIndicator.objects.filter(framework_target=target)
        .exclude(status=LifecycleStatus.ARCHIVED)
        .order_by("code"),
        request.user,
        perm="nbms_app.view_frameworkindicator",
    )
    return render(
        request,
        "nbms_app/frameworks/framework_target_detail.html",
        {"target": target, "indicators": indicators, "can_manage_catalog": _is_catalog_manager(request.user)},
    )


def framework_indicator_list(request):
    indicators = filter_queryset_for_user(
        FrameworkIndicator.objects.select_related("framework", "framework_target")
        .exclude(status=LifecycleStatus.ARCHIVED)
        .order_by("framework__code", "code"),
        request.user,
        perm="nbms_app.view_frameworkindicator",
    )
    query = request.GET.get("q")
    if query:
        indicators = indicators.filter(Q(code__icontains=query) | Q(title__icontains=query))
    return render(
        request,
        "nbms_app/frameworks/framework_indicator_list.html",
        {"indicators": indicators, "query": query, "can_manage_catalog": _is_catalog_manager(request.user)},
    )


def framework_indicator_detail(request, indicator_uuid):
    indicators = filter_queryset_for_user(
        FrameworkIndicator.objects.select_related("framework", "framework_target").exclude(status=LifecycleStatus.ARCHIVED),
        request.user,
        perm="nbms_app.view_frameworkindicator",
    )
    indicator = get_object_or_404(indicators, uuid=indicator_uuid)
    return render(
        request,
        "nbms_app/frameworks/framework_indicator_detail.html",
        {"indicator": indicator, "can_manage_catalog": _is_catalog_manager(request.user)},
    )


@login_required
def framework_create(request):
    _require_catalog_manager(request.user)
    form = FrameworkCatalogForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        framework = form.save(commit=False)
        if not framework.created_by:
            framework.created_by = request.user
        if not framework.organisation and getattr(request.user, "organisation", None):
            framework.organisation = request.user.organisation
        framework.save()
        messages.success(request, "Framework created.")
        return redirect("nbms_app:framework_detail", framework_uuid=framework.uuid)
    return render(request, "nbms_app/frameworks/framework_form.html", {"form": form, "mode": "create"})


@login_required
def framework_edit(request, framework_uuid):
    _require_catalog_manager(request.user)
    frameworks = filter_queryset_for_user(
        Framework.objects.order_by("code"),
        request.user,
        perm="nbms_app.view_framework",
    )
    framework = get_object_or_404(frameworks, uuid=framework_uuid)
    form = FrameworkCatalogForm(request.POST or None, instance=framework, user=request.user)
    readonly_fields = build_readonly_panel(framework, get_catalog_readonly_fields(Framework))
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Framework updated.")
        return redirect("nbms_app:framework_detail", framework_uuid=framework.uuid)
    return render(
        request,
        "nbms_app/frameworks/framework_form.html",
        {
            "form": form,
            "mode": "edit",
            "framework": framework,
            "readonly_fields": readonly_fields,
        },
    )


@login_required
@require_POST
def framework_archive(request, framework_uuid):
    _require_catalog_manager(request.user)
    frameworks = filter_queryset_for_user(
        Framework.objects.order_by("code"),
        request.user,
        perm="nbms_app.view_framework",
    )
    framework = get_object_or_404(frameworks, uuid=framework_uuid)
    archive_object(request.user, framework, request=request)
    messages.success(request, "Framework archived.")
    return redirect("nbms_app:framework_list")


@login_required
def framework_goal_create(request):
    _require_catalog_manager(request.user)
    form = FrameworkGoalCatalogForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        goal = form.save(commit=False)
        if not goal.created_by:
            goal.created_by = request.user
        if not goal.organisation and getattr(request.user, "organisation", None):
            goal.organisation = request.user.organisation
        goal.save()
        messages.success(request, "Framework goal created.")
        return redirect("nbms_app:framework_goal_detail", goal_uuid=goal.uuid)
    return render(request, "nbms_app/frameworks/framework_goal_form.html", {"form": form, "mode": "create"})


@login_required
def framework_goal_edit(request, goal_uuid):
    _require_catalog_manager(request.user)
    framework_ids = list(
        filter_queryset_for_user(
            Framework.objects.exclude(status=LifecycleStatus.ARCHIVED),
            request.user,
            perm="nbms_app.view_framework",
        ).values_list("id", flat=True)
    )
    goals = FrameworkGoal.objects.filter(framework_id__in=framework_ids)
    goal = get_object_or_404(goals, uuid=goal_uuid)
    form = FrameworkGoalCatalogForm(request.POST or None, instance=goal, user=request.user)
    readonly_fields = build_readonly_panel(goal, get_catalog_readonly_fields(FrameworkGoal))
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Framework goal updated.")
        return redirect("nbms_app:framework_goal_detail", goal_uuid=goal.uuid)
    return render(
        request,
        "nbms_app/frameworks/framework_goal_form.html",
        {
            "form": form,
            "mode": "edit",
            "goal": goal,
            "readonly_fields": readonly_fields,
        },
    )


@login_required
@require_POST
def framework_goal_archive(request, goal_uuid):
    _require_catalog_manager(request.user)
    framework_ids = list(
        filter_queryset_for_user(
            Framework.objects.exclude(status=LifecycleStatus.ARCHIVED),
            request.user,
            perm="nbms_app.view_framework",
        ).values_list("id", flat=True)
    )
    goals = FrameworkGoal.objects.filter(framework_id__in=framework_ids)
    goal = get_object_or_404(goals, uuid=goal_uuid)
    archive_object(request.user, goal, request=request)
    messages.success(request, "Framework goal archived.")
    return redirect("nbms_app:framework_goal_list")


@login_required
def framework_target_create(request):
    _require_catalog_manager(request.user)
    form = FrameworkTargetCatalogForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        target = form.save(commit=False)
        if not target.created_by:
            target.created_by = request.user
        if not target.organisation and getattr(request.user, "organisation", None):
            target.organisation = request.user.organisation
        target.save()
        messages.success(request, "Framework target created.")
        return redirect("nbms_app:framework_target_detail", target_uuid=target.uuid)
    return render(request, "nbms_app/frameworks/framework_target_form.html", {"form": form, "mode": "create"})


@login_required
def framework_target_edit(request, target_uuid):
    _require_catalog_manager(request.user)
    targets = filter_queryset_for_user(
        FrameworkTarget.objects.select_related("framework", "goal"),
        request.user,
        perm="nbms_app.view_frameworktarget",
    )
    target = get_object_or_404(targets, uuid=target_uuid)
    form = FrameworkTargetCatalogForm(request.POST or None, instance=target, user=request.user)
    readonly_fields = build_readonly_panel(target, get_catalog_readonly_fields(FrameworkTarget))
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Framework target updated.")
        return redirect("nbms_app:framework_target_detail", target_uuid=target.uuid)
    return render(
        request,
        "nbms_app/frameworks/framework_target_form.html",
        {
            "form": form,
            "mode": "edit",
            "target": target,
            "readonly_fields": readonly_fields,
        },
    )


@login_required
@require_POST
def framework_target_archive(request, target_uuid):
    _require_catalog_manager(request.user)
    targets = filter_queryset_for_user(
        FrameworkTarget.objects.select_related("framework", "goal"),
        request.user,
        perm="nbms_app.view_frameworktarget",
    )
    target = get_object_or_404(targets, uuid=target_uuid)
    archive_object(request.user, target, request=request)
    messages.success(request, "Framework target archived.")
    return redirect("nbms_app:framework_target_list")


@login_required
def framework_indicator_create(request):
    _require_catalog_manager(request.user)
    form = FrameworkIndicatorCatalogForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        indicator = form.save(commit=False)
        if not indicator.created_by:
            indicator.created_by = request.user
        if not indicator.organisation and getattr(request.user, "organisation", None):
            indicator.organisation = request.user.organisation
        indicator.save()
        messages.success(request, "Framework indicator created.")
        return redirect("nbms_app:framework_indicator_detail", indicator_uuid=indicator.uuid)
    return render(
        request,
        "nbms_app/frameworks/framework_indicator_form.html",
        {"form": form, "mode": "create"},
    )


@login_required
def framework_indicator_edit(request, indicator_uuid):
    _require_catalog_manager(request.user)
    indicators = filter_queryset_for_user(
        FrameworkIndicator.objects.select_related("framework", "framework_target"),
        request.user,
        perm="nbms_app.view_frameworkindicator",
    )
    indicator = get_object_or_404(indicators, uuid=indicator_uuid)
    form = FrameworkIndicatorCatalogForm(request.POST or None, instance=indicator, user=request.user)
    readonly_fields = build_readonly_panel(indicator, get_catalog_readonly_fields(FrameworkIndicator))
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Framework indicator updated.")
        return redirect("nbms_app:framework_indicator_detail", indicator_uuid=indicator.uuid)
    return render(
        request,
        "nbms_app/frameworks/framework_indicator_form.html",
        {
            "form": form,
            "mode": "edit",
            "indicator": indicator,
            "readonly_fields": readonly_fields,
        },
    )


@login_required
@require_POST
def framework_indicator_archive(request, indicator_uuid):
    _require_catalog_manager(request.user)
    indicators = filter_queryset_for_user(
        FrameworkIndicator.objects.select_related("framework", "framework_target"),
        request.user,
        perm="nbms_app.view_frameworkindicator",
    )
    indicator = get_object_or_404(indicators, uuid=indicator_uuid)
    archive_object(request.user, indicator, request=request)
    messages.success(request, "Framework indicator archived.")
    return redirect("nbms_app:framework_indicator_list")


@login_required
def export_package_list(request):
    packages = _export_queryset_for_user(request.user)
    return render(request, "nbms_app/exports/export_list.html", {"packages": packages})


@login_required
def export_package_create(request):
    _require_export_creator(request.user)
    form = ExportPackageForm(request.POST or None)
    if not is_system_admin(request.user):
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
    can_submit = (
        package.created_by_id == request.user.id
        or user_has_role(request.user, ROLE_SECRETARIAT)
        or is_system_admin(request.user)
    )
    can_review = user_has_role(request.user, ROLE_DATA_STEWARD, ROLE_SECRETARIAT) or is_system_admin(request.user)
    can_release = user_has_role(request.user, ROLE_SECRETARIAT) or is_system_admin(request.user)
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


@staff_or_system_admin_required
def export_ort_nr7_narrative_instance(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    try:
        payload = build_ort_nr7_narrative_payload(instance=instance, user=request.user)
    except PermissionDenied as exc:
        return JsonResponse({"error": str(exc)}, status=403)
    except ValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    record_audit_event(
        request.user,
        "export_nr7_narrative",
        instance,
        metadata={"download": False},
        request=request,
    )
    return JsonResponse(payload, json_dumps_params={"indent": 2})


@staff_or_system_admin_required
def export_ort_nr7_v2_instance(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    try:
        payload = build_ort_nr7_v2_payload(instance=instance, user=request.user)
    except PermissionDenied as exc:
        return JsonResponse({"error": str(exc)}, status=403)
    except ValidationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    response = JsonResponse(payload, json_dumps_params={"indent": 2})
    download = str(request.GET.get("download", "")).lower() in {"1", "true", "yes"}
    record_audit_event(
        request.user,
        "export_nr7_v2",
        instance,
        metadata={"download": bool(download)},
        request=request,
    )
    if download:
        response["Content-Disposition"] = f'attachment; filename="ort-nr7-v2-{instance.uuid}.json"'
    return response


@staff_or_system_admin_required
def reporting_cycle_list(request):
    cycles = ReportingCycle.objects.order_by("-start_date", "code")
    return render(request, "nbms_app/reporting/cycle_list.html", {"cycles": cycles})


@staff_or_system_admin_required
def reporting_cycle_create(request):
    form = ReportingCycleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cycle = form.save()
        messages.success(request, f"Reporting cycle '{cycle.code}' created.")
        return redirect("nbms_app:reporting_cycle_detail", cycle_uuid=cycle.uuid)
    return render(request, "nbms_app/reporting/cycle_form.html", {"form": form, "mode": "create"})


@staff_or_system_admin_required
def reporting_cycle_detail(request, cycle_uuid):
    cycle = get_object_or_404(ReportingCycle, uuid=cycle_uuid)
    instances = cycle.instances.order_by("-created_at")
    return render(
        request,
        "nbms_app/reporting/cycle_detail.html",
        {"cycle": cycle, "instances": instances},
    )


@staff_or_system_admin_required
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


@staff_or_system_admin_required
def reporting_instance_detail(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle", "frozen_by"), uuid=instance_uuid)
    readiness = get_instance_readiness(instance, request.user)
    alignment_coverage = compute_alignment_coverage(
        user=request.user,
        instance=instance,
        scope="selected",
        include_details=False,
    )
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
            "alignment_coverage": alignment_coverage,
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


@staff_or_system_admin_required
def reporting_instance_report_pack(request, instance_uuid):
    instance = get_object_or_404(
        ReportingInstance.objects.select_related("cycle", "frozen_by"),
        uuid=instance_uuid,
    )
    context = build_report_pack_context(instance, request.user)
    return render(request, "nbms_app/reporting/report_pack.html", context)


@staff_or_system_admin_required
def reporting_instance_review(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    summary = build_instance_review_summary(instance, request.user)
    alignment_coverage = compute_alignment_coverage(
        user=request.user,
        instance=instance,
        scope="selected",
        include_details=False,
    )
    export_url = reverse("nbms_app:export_ort_nr7_v2_instance", kwargs={"instance_uuid": instance.uuid})
    export_download_url = f"{export_url}?download=1"
    snapshots_qs = ReportingSnapshot.objects.filter(reporting_instance=instance).order_by("-created_at")
    latest_snapshot = snapshots_qs.first()
    decisions = []
    current_decision = None
    can_manage_decisions = True
    try:
        decisions = review_decisions_for_user(instance, request.user)
        current_decision = decisions.first() if hasattr(decisions, "first") else None
    except PermissionDenied:
        can_manage_decisions = False
    context = {
        "instance": instance,
        "summary": summary,
        "alignment_coverage": alignment_coverage,
        "export_url": export_url,
        "export_download_url": export_download_url,
        "snapshots": snapshots_qs,
        "latest_snapshot": latest_snapshot,
        "decisions": decisions,
        "current_decision": current_decision,
        "decision_choices": ReviewDecisionStatus.choices,
        "can_manage_decisions": can_manage_decisions,
    }
    return render(request, "nbms_app/reporting/review_dashboard.html", context)


@staff_or_system_admin_required
def reporting_instance_alignment_coverage(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    coverage = compute_alignment_coverage(
        user=request.user,
        instance=instance,
        scope="selected",
        include_details=False,
    )
    return render(
        request,
        "nbms_app/alignment/coverage_detail.html",
        {"instance": instance, "coverage": coverage},
    )


@staff_or_system_admin_required
def reporting_instance_review_pack_v2(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle", "frozen_by"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    templates = _required_templates()
    responses = ReportSectionResponse.objects.filter(
        reporting_instance=instance,
        template__in=templates,
    ).select_related("template", "updated_by")
    response_map = {response.template_id: response for response in responses}
    sections = []
    for template in templates:
        response = response_map.get(template.id)
        sections.append(
            {
                "code": template.code,
                "title": template.title,
                "content": response.response_json if response else {},
            }
        )

    pack_context = build_review_pack_context(instance, request.user)
    export_url = reverse("nbms_app:export_ort_nr7_v2_instance", kwargs={"instance_uuid": instance.uuid})
    export_download_url = f"{export_url}?download=1"
    context = {
        "instance": instance,
        "sections": sections,
        "export_url": export_url,
        "export_download_url": export_download_url,
        **pack_context,
    }
    return render(request, "nbms_app/reporting/review_pack_v2.html", context)


def _snapshot_counts(payload):
    return {
        "sections": len(payload.get("sections") or []),
        "section_iii": len(payload.get("section_iii_progress") or []),
        "section_iv": len(payload.get("section_iv_progress") or []),
        "indicator_series": len(payload.get("indicator_data_series") or []),
        "binary_responses": len(payload.get("binary_indicator_data") or []),
    }


@staff_or_system_admin_required
def reporting_instance_snapshots(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    snapshots = (
        ReportingSnapshot.objects.filter(reporting_instance=instance)
        .select_related("created_by")
        .order_by("-created_at")
    )
    context = {
        "instance": instance,
        "snapshots": snapshots,
    }
    return render(request, "nbms_app/reporting/snapshots_list.html", context)


@staff_or_system_admin_required
def reporting_instance_snapshot_create(request, instance_uuid):
    if request.method != "POST":
        return redirect("nbms_app:reporting_instance_snapshots", instance_uuid=instance_uuid)

    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    note = request.POST.get("note", "").strip()
    try:
        snapshot = create_reporting_snapshot(instance=instance, user=request.user, note=note)
        messages.success(request, "Snapshot created.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect("nbms_app:reporting_instance_snapshots", instance_uuid=instance.uuid)


@staff_or_system_admin_required
def reporting_instance_snapshot_detail(request, instance_uuid, snapshot_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    snapshot = get_object_or_404(
        ReportingSnapshot.objects.select_related("created_by"),
        reporting_instance=instance,
        uuid=snapshot_uuid,
    )
    record_audit_event(
        request.user,
        "snapshot_view",
        snapshot,
        metadata={"instance_uuid": str(instance.uuid)},
    )
    context = {
        "instance": instance,
        "snapshot": snapshot,
        "counts": _snapshot_counts(snapshot.payload_json or {}),
    }
    return render(request, "nbms_app/reporting/snapshot_detail.html", context)


@staff_or_system_admin_required
def reporting_instance_snapshot_download(request, instance_uuid, snapshot_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    snapshot = get_object_or_404(
        ReportingSnapshot.objects.select_related("created_by"),
        reporting_instance=instance,
        uuid=snapshot_uuid,
    )
    record_audit_event(
        request.user,
        "snapshot_download",
        snapshot,
        metadata={"instance_uuid": str(instance.uuid)},
    )
    response = JsonResponse(snapshot.payload_json, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = f'attachment; filename="snapshot-{snapshot.uuid}.json"'
    return response


@staff_or_system_admin_required
def reporting_instance_snapshot_diff(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    snapshots_qs = ReportingSnapshot.objects.filter(reporting_instance=instance).order_by("-created_at")

    snapshot_a = None
    snapshot_b = None
    a_uuid = request.GET.get("a")
    b_uuid = request.GET.get("b")
    if a_uuid and b_uuid:
        snapshot_a = get_object_or_404(snapshots_qs, uuid=a_uuid)
        snapshot_b = get_object_or_404(snapshots_qs, uuid=b_uuid)
    else:
        snapshots = list(snapshots_qs[:2])
        if snapshots:
            snapshot_b = snapshots[0]
        if len(snapshots) > 1:
            snapshot_a = snapshots[1]

    diff = None
    readiness_diff = None
    if snapshot_a and snapshot_b:
        diff = diff_snapshots(snapshot_a.payload_json, snapshot_b.payload_json)
        readiness_diff = diff_snapshot_readiness(snapshot_a, snapshot_b)
        record_audit_event(
            request.user,
            "snapshot_diff",
            snapshot_b,
            metadata={
                "instance_uuid": str(instance.uuid),
                "snapshot_a": str(snapshot_a.uuid),
                "snapshot_b": str(snapshot_b.uuid),
            },
        )

    context = {
        "instance": instance,
        "snapshots": snapshots_qs,
        "snapshot_a": snapshot_a,
        "snapshot_b": snapshot_b,
        "diff": diff,
        "readiness_diff": readiness_diff,
    }
    return render(request, "nbms_app/reporting/snapshot_diff.html", context)


@staff_or_system_admin_required
def reporting_instance_review_decisions(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    decisions = review_decisions_for_user(instance, request.user)
    snapshots = ReportingSnapshot.objects.filter(reporting_instance=instance).order_by("-created_at")
    latest_snapshot = snapshots.first()
    context = {
        "instance": instance,
        "decisions": decisions,
        "snapshots": snapshots,
        "latest_snapshot": latest_snapshot,
        "decision_choices": ReviewDecisionStatus.choices,
    }
    return render(request, "nbms_app/reporting/review_decisions_list.html", context)


@staff_or_system_admin_required
def reporting_instance_review_decision_create(request, instance_uuid):
    if request.method != "POST":
        return redirect("nbms_app:reporting_instance_review_decisions", instance_uuid=instance_uuid)

    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    decision_value = request.POST.get("decision", "")
    notes = request.POST.get("notes", "").strip()
    snapshot_uuid = request.POST.get("snapshot_uuid")
    snapshots = ReportingSnapshot.objects.filter(reporting_instance=instance).order_by("-created_at")
    snapshot = None
    if snapshot_uuid:
        snapshot = snapshots.filter(uuid=snapshot_uuid).first()
    if not snapshot:
        snapshot = snapshots.first()

    try:
        decision = create_review_decision(
            instance=instance,
            snapshot=snapshot,
            user=request.user,
            decision=decision_value,
            notes=notes,
        )
        messages.success(request, "Review decision recorded.")
    except PermissionDenied:
        raise
    except ValidationError as exc:
        messages.error(request, str(exc))

    next_url = request.POST.get("next") or reverse(
        "nbms_app:reporting_instance_review_decisions",
        kwargs={"instance_uuid": instance.uuid},
    )
    return redirect(next_url)


@staff_or_system_admin_required
def reporting_set_current_instance(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    request.session["current_reporting_instance_uuid"] = str(instance.uuid)
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    return redirect("nbms_app:reporting_instance_detail", instance_uuid=instance.uuid)


@staff_or_system_admin_required
def reporting_clear_current_instance(request):
    request.session.pop("current_reporting_instance_uuid", None)
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    return redirect("nbms_app:home")


@staff_or_system_admin_required
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
    structured_links = [
        {
            "code": "section-i",
            "title": "Section I: Report context",
            "url": reverse("nbms_app:reporting_instance_section_i", kwargs={"instance_uuid": instance.uuid}),
        },
        {
            "code": "section-ii",
            "title": "Section II: NBSAP status",
            "url": reverse("nbms_app:reporting_instance_section_ii", kwargs={"instance_uuid": instance.uuid}),
        },
        {
            "code": "section-iii",
            "title": "Section III: National targets progress",
            "url": reverse("nbms_app:reporting_instance_section_iii", kwargs={"instance_uuid": instance.uuid}),
        },
        {
            "code": "section-iv-goals",
            "title": "Section IV: GBF goals",
            "url": reverse("nbms_app:reporting_instance_section_iv_goals", kwargs={"instance_uuid": instance.uuid}),
        },
        {
            "code": "section-iv-targets",
            "title": "Section IV: GBF targets",
            "url": reverse("nbms_app:reporting_instance_section_iv", kwargs={"instance_uuid": instance.uuid}),
        },
        {
            "code": "section-iv-binary",
            "title": "Section IV: Binary indicators",
            "url": reverse(
                "nbms_app:reporting_instance_section_iv_binary_indicators",
                kwargs={"instance_uuid": instance.uuid},
            ),
        },
        {
            "code": "section-v",
            "title": "Section V: Conclusions",
            "url": reverse("nbms_app:reporting_instance_section_v", kwargs={"instance_uuid": instance.uuid}),
        },
    ]
    return render(
        request,
        "nbms_app/reporting/instance_sections.html",
        {
            "instance": instance,
            "items": items,
            "structured_links": structured_links,
            "is_admin": _is_admin_user(request.user),
        },
    )


@staff_or_system_admin_required
def reporting_instance_section_edit(request, instance_uuid, section_code):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    template = get_object_or_404(ReportSectionTemplate, code=section_code, is_active=True)
    response = ReportSectionResponse.objects.filter(reporting_instance=instance, template=template).first()
    initial_data = response.response_json if response else {}
    form = ReportSectionResponseForm(request.POST or None, template=template, initial_data=initial_data)

    admin_override = bool(is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN))
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


@staff_or_system_admin_required
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


@staff_or_system_admin_required
def reporting_instance_section_i(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    context = SectionIReportContext.objects.filter(reporting_instance=instance).first()

    initial = {}
    if not context:
        initial = {
            "reporting_party_name": getattr(settings, "NBMS_REPORTING_PARTY_NAME", "South Africa"),
            "submission_language": getattr(settings, "NBMS_SUBMISSION_LANGUAGE", "English"),
        }
    form = SectionIReportContextForm(request.POST or None, instance=context, initial=initial)

    admin_override = bool(is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN))
    read_only = bool(instance.frozen_at and not admin_override)
    if read_only:
        for field in form.fields.values():
            field.disabled = True

    if request.method == "POST":
        if read_only:
            raise PermissionDenied("Reporting instance is frozen.")
        if form.is_valid():
            entry = form.save(commit=False)
            entry.reporting_instance = instance
            entry.updated_by = request.user
            entry.save()
            messages.success(request, "Updated Section I report context.")
            return redirect("nbms_app:reporting_instance_section_i", instance_uuid=instance.uuid)

    return render(
        request,
        "nbms_app/reporting/section_i_edit.html",
        {"instance": instance, "form": form, "read_only": read_only},
    )


@staff_or_system_admin_required
def reporting_instance_section_ii(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    status = SectionIINBSAPStatus.objects.filter(reporting_instance=instance).first()
    form = SectionIINBSAPStatusForm(request.POST or None, instance=status)

    admin_override = bool(is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN))
    read_only = bool(instance.frozen_at and not admin_override)
    if read_only:
        for field in form.fields.values():
            field.disabled = True

    if request.method == "POST":
        if read_only:
            raise PermissionDenied("Reporting instance is frozen.")
        if form.is_valid():
            entry = form.save(commit=False)
            entry.reporting_instance = instance
            entry.updated_by = request.user
            entry.save()
            messages.success(request, "Updated Section II NBSAP status.")
            return redirect("nbms_app:reporting_instance_section_ii", instance_uuid=instance.uuid)

    return render(
        request,
        "nbms_app/reporting/section_ii_edit.html",
        {"instance": instance, "form": form, "read_only": read_only},
    )


@staff_or_system_admin_required
def reporting_instance_section_v(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    conclusions = SectionVConclusions.objects.filter(reporting_instance=instance).first()
    form = SectionVConclusionsForm(
        request.POST or None,
        instance=conclusions,
        user=request.user,
        reporting_instance=instance,
    )

    admin_override = bool(is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN))
    read_only = bool(instance.frozen_at and not admin_override)
    if read_only:
        for field in form.fields.values():
            field.disabled = True

    if request.method == "POST":
        if read_only:
            raise PermissionDenied("Reporting instance is frozen.")
        if form.is_valid():
            entry = form.save(commit=False)
            entry.reporting_instance = instance
            entry.updated_by = request.user
            entry.save()
            form.save_m2m()
            messages.success(request, "Updated Section V conclusions.")
            return redirect("nbms_app:reporting_instance_section_v", instance_uuid=instance.uuid)

    return render(
        request,
        "nbms_app/reporting/section_v_edit.html",
        {"instance": instance, "form": form, "read_only": read_only},
    )


@staff_or_system_admin_required
def reporting_instance_section_iv_goals(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    goals_qs = filter_queryset_for_user(
        FrameworkGoal.objects.select_related("framework"),
        request.user,
    ).filter(status=LifecycleStatus.PUBLISHED)

    scoped_targets = scoped_framework_targets(instance, request.user)
    if scoped_targets.exists():
        goal_ids = scoped_targets.values_list("goal_id", flat=True)
        goals_qs = goals_qs.filter(id__in=goal_ids)
    else:
        goals_qs = goals_qs.filter(framework__code="GBF")

    goals_qs = goals_qs.order_by("framework__code", "sort_order", "code")
    entries = SectionIVFrameworkGoalProgress.objects.filter(
        reporting_instance=instance,
        framework_goal__in=goals_qs,
    )
    entry_map = {entry.framework_goal_id: entry for entry in entries}
    items = [{"goal": goal, "entry": entry_map.get(goal.id)} for goal in goals_qs]

    admin_override = bool(is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN))
    read_only = bool(instance.frozen_at and not admin_override)
    return render(
        request,
        "nbms_app/reporting/section_iv_goals_list.html",
        {"instance": instance, "items": items, "read_only": read_only},
    )


@staff_or_system_admin_required
def reporting_instance_section_iv_goal_edit(request, instance_uuid, goal_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    goal = get_object_or_404(
        filter_queryset_for_user(FrameworkGoal.objects.select_related("framework"), request.user),
        uuid=goal_uuid,
    )
    entry = SectionIVFrameworkGoalProgress.objects.filter(
        reporting_instance=instance, framework_goal=goal
    ).first()
    form = SectionIVFrameworkGoalProgressForm(
        request.POST or None,
        instance=entry,
        user=request.user,
        reporting_instance=instance,
    )

    admin_override = bool(is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN))
    read_only = bool(instance.frozen_at and not admin_override)
    if read_only:
        for field in form.fields.values():
            field.disabled = True

    if request.method == "POST":
        if read_only:
            raise PermissionDenied("Reporting instance is frozen.")
        if form.is_valid():
            progress = form.save(commit=False)
            progress.reporting_instance = instance
            progress.framework_goal = goal
            progress.updated_by = request.user
            progress.save()
            form.save_m2m()
            messages.success(request, f"Updated Section IV goal progress for {goal.code}.")
            return redirect("nbms_app:reporting_instance_section_iv_goals", instance_uuid=instance.uuid)

    return render(
        request,
        "nbms_app/reporting/section_iv_goal_edit.html",
        {"instance": instance, "goal": goal, "form": form, "read_only": read_only},
    )


def _binary_group_sort_key(group):
    target_code = ""
    if group.framework_target_id and group.framework_target:
        target_code = group.framework_target.code
    elif group.target_code:
        target_code = group.target_code
    return (target_code, group.ordering, group.key)


def _binary_question_sort_key(question):
    return (
        question.sort_order,
        question.section or "",
        question.number or "",
        question.question_key,
    )


@staff_or_system_admin_required
def reporting_instance_section_iv_binary_indicators(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)

    admin_override = bool(is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN))
    read_only = bool(instance.frozen_at and not admin_override)

    allowed_questions = (
        binary_indicator_questions_for_user(request.user, instance)
        .select_related("group", "framework_indicator", "parent_question")
        .prefetch_related("child_questions")
    )
    group_ids = allowed_questions.values_list("group_id", flat=True).distinct()
    groups_qs = (
        BinaryIndicatorGroup.objects.filter(id__in=group_ids, is_active=True)
        .select_related("framework_target", "framework_indicator")
    )
    groups = sorted(groups_qs, key=_binary_group_sort_key)

    responses = BinaryIndicatorResponse.objects.filter(
        reporting_instance=instance,
        question__in=allowed_questions,
    )
    response_map = {resp.question_id: resp for resp in responses}

    group_responses = BinaryIndicatorGroupResponse.objects.filter(
        reporting_instance=instance,
        group__in=groups,
    )
    group_response_map = {resp.group_id: resp for resp in group_responses}

    questions_by_group = {}
    for question in allowed_questions:
        questions_by_group.setdefault(question.group_id, []).append(question)

    def _normalize_question_type(question):
        raw_type = (question.question_type or "").lower()
        if raw_type in {"single", "option"}:
            return "single"
        if raw_type in {"multiple", "checkbox"}:
            return "multiple"
        if raw_type in {"text", "string", "header"}:
            return "text"
        return "single"

    def _ordered_questions(question_list):
        children_map = {}
        for item in question_list:
            if item.parent_question_id:
                children_map.setdefault(item.parent_question_id, []).append(item)
        root_items = [item for item in question_list if not item.parent_question_id]
        root_items = sorted(root_items, key=_binary_question_sort_key)
        ordered = []
        for root in root_items:
            ordered.append(root)
            if root.id in children_map:
                ordered.extend(sorted(children_map[root.id], key=_binary_question_sort_key))
        return ordered, children_map

    errors = {}
    if request.method == "POST":
        if read_only:
            raise PermissionDenied("Reporting instance is frozen.")
        cleaned = {}
        ordered_cache = {}
        header_ids = set()
        for group_id, question_items in questions_by_group.items():
            ordered, children_map = _ordered_questions(question_items)
            ordered_cache[group_id] = (ordered, children_map)
            header_ids.update(children_map.keys())

        for question in allowed_questions:
            if question.id in header_ids:
                continue
            field_name = f"q_{question.id}"
            q_type = _normalize_question_type(question)
            if q_type == "single":
                value = (request.POST.get(field_name) or "").strip()
            elif q_type == "multiple":
                value = request.POST.getlist(field_name)
            else:
                value = (request.POST.get(field_name) or "").strip()
            cleaned[question.id] = value

            if question.mandatory:
                empty = (value == "" or value == [] or value is None)
                if empty:
                    errors[question.id] = "This field is required."

        if not errors:
            with transaction.atomic():
                for group in groups:
                    comment_field = f"group_comment_{group.id}"
                    comment = (request.POST.get(comment_field) or "").strip()
                    if comment:
                        BinaryIndicatorGroupResponse.objects.update_or_create(
                            reporting_instance=instance,
                            group=group,
                            defaults={"comments": comment, "updated_by": request.user},
                        )
                    else:
                        existing = group_response_map.get(group.id)
                        if existing:
                            existing.delete()

                for question in allowed_questions:
                    if question.id in header_ids:
                        continue
                    value = cleaned.get(question.id)
                    existing = response_map.get(question.id)
                    empty = (value == "" or value == [] or value is None)
                    if empty:
                        if existing:
                            existing.delete()
                        continue
                    BinaryIndicatorResponse.objects.update_or_create(
                        reporting_instance=instance,
                        question=question,
                        defaults={"response": value},
                    )
            messages.success(request, "Updated binary indicator responses.")
            return redirect(
                "nbms_app:reporting_instance_section_iv_binary_indicators",
                instance_uuid=instance.uuid,
            )

    group_items = []
    for group in groups:
        group_questions = questions_by_group.get(group.id, [])
        ordered, children_map = _ordered_questions(group_questions)
        question_items = []
        for question in ordered:
            is_header = question.id in children_map
            response = response_map.get(question.id)
            value = response.response if response else None
            selected_values = value if isinstance(value, list) else [value] if value else []
            question_items.append(
                {
                    "question": question,
                    "is_header": is_header,
                    "value": value,
                    "selected_values": selected_values,
                    "error": errors.get(question.id),
                }
            )
        group_items.append(
            {
                "group": group,
                "comment": (group_response_map.get(group.id).comments if group_response_map.get(group.id) else ""),
                "questions": question_items,
            }
        )

    return render(
        request,
        "nbms_app/reporting/section_iv_binary_indicators.html",
        {
            "instance": instance,
            "groups": group_items,
            "read_only": read_only,
            "errors": errors,
        },
    )


@staff_or_system_admin_required
def reporting_instance_section_iii(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    targets = scoped_national_targets(instance, request.user)
    entries = (
        SectionIIINationalTargetProgress.objects.filter(
            reporting_instance=instance,
            national_target__in=targets,
        )
        .select_related("national_target")
        .order_by("national_target__code")
    )
    entry_map = {entry.national_target_id: entry for entry in entries}
    items = [{"target": target, "entry": entry_map.get(target.id)} for target in targets]

    admin_override = bool(is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN))
    read_only = bool(instance.frozen_at and not admin_override)
    return render(
        request,
        "nbms_app/reporting/section_iii_list.html",
        {"instance": instance, "items": items, "read_only": read_only},
    )


@staff_or_system_admin_required
def reporting_instance_section_iii_edit(request, instance_uuid, target_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    targets = scoped_national_targets(instance, request.user)
    target = get_object_or_404(targets, uuid=target_uuid)
    entry = SectionIIINationalTargetProgress.objects.filter(
        reporting_instance=instance, national_target=target
    ).first()
    form = SectionIIINationalTargetProgressForm(
        request.POST or None,
        instance=entry,
        user=request.user,
        reporting_instance=instance,
    )

    admin_override = bool(is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN))
    read_only = bool(instance.frozen_at and not admin_override)
    if read_only:
        for field in form.fields.values():
            field.disabled = True

    if request.method == "POST":
        if read_only:
            raise PermissionDenied("Reporting instance is frozen.")
        if form.is_valid():
            progress = form.save(commit=False)
            progress.reporting_instance = instance
            progress.national_target = target
            progress.save()
            form.save_m2m()
            messages.success(request, f"Updated Section III progress for {target.code}.")
            return redirect("nbms_app:reporting_instance_section_iii", instance_uuid=instance.uuid)

    return render(
        request,
        "nbms_app/reporting/section_iii_edit.html",
        {
            "instance": instance,
            "target": target,
            "form": form,
            "read_only": read_only,
        },
    )


@staff_or_system_admin_required
def reporting_instance_section_iv(request, instance_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    targets = scoped_framework_targets(instance, request.user)
    entries = (
        SectionIVFrameworkTargetProgress.objects.filter(
            reporting_instance=instance,
            framework_target__in=targets,
        )
        .select_related("framework_target", "framework_target__framework")
        .order_by("framework_target__framework__code", "framework_target__code")
    )
    entry_map = {entry.framework_target_id: entry for entry in entries}
    items = [{"target": target, "entry": entry_map.get(target.id)} for target in targets]

    admin_override = bool(is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN))
    read_only = bool(instance.frozen_at and not admin_override)
    return render(
        request,
        "nbms_app/reporting/section_iv_list.html",
        {"instance": instance, "items": items, "read_only": read_only},
    )


@staff_or_system_admin_required
def reporting_instance_section_iv_edit(request, instance_uuid, framework_target_uuid):
    instance = get_object_or_404(ReportingInstance.objects.select_related("cycle"), uuid=instance_uuid)
    _require_section_progress_access(instance, request.user)
    targets = scoped_framework_targets(instance, request.user)
    target = get_object_or_404(targets, uuid=framework_target_uuid)
    entry = SectionIVFrameworkTargetProgress.objects.filter(
        reporting_instance=instance, framework_target=target
    ).first()
    form = SectionIVFrameworkTargetProgressForm(
        request.POST or None,
        instance=entry,
        user=request.user,
        reporting_instance=instance,
    )

    admin_override = bool(is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN))
    read_only = bool(instance.frozen_at and not admin_override)
    if read_only:
        for field in form.fields.values():
            field.disabled = True

    if request.method == "POST":
        if read_only:
            raise PermissionDenied("Reporting instance is frozen.")
        if form.is_valid():
            progress = form.save(commit=False)
            progress.reporting_instance = instance
            progress.framework_target = target
            progress.save()
            form.save_m2m()
            messages.success(request, f"Updated Section IV progress for {target.code}.")
            return redirect("nbms_app:reporting_instance_section_iv", instance_uuid=instance.uuid)

    return render(
        request,
        "nbms_app/reporting/section_iv_edit.html",
        {
            "instance": instance,
            "target": target,
            "form": form,
            "read_only": read_only,
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


@staff_or_system_admin_required
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
        with suppress_audit_events():
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
    with suppress_audit_events():
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


@staff_or_system_admin_required
def review_queue(request):
    targets = NationalTarget.objects.filter(status=LifecycleStatus.PENDING_REVIEW).order_by("code")
    indicators = Indicator.objects.filter(status=LifecycleStatus.PENDING_REVIEW).order_by("code")
    return render(
        request,
        "nbms_app/manage/review_queue.html",
        {"targets": targets, "indicators": indicators},
    )


@staff_or_system_admin_required
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


@staff_or_system_admin_required
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
