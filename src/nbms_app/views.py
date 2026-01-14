import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.db import connections
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from nbms_app.forms import (
    DatasetForm,
    EvidenceForm,
    ExportPackageForm,
    OrganisationForm,
    UserCreateForm,
    UserUpdateForm,
)
from nbms_app.models import (
    Dataset,
    Evidence,
    ExportPackage,
    ExportStatus,
    Indicator,
    LifecycleStatus,
    NationalTarget,
    Organisation,
    User,
    Notification,
)
from nbms_app.services.authorization import (
    ROLE_CONTRIBUTOR,
    ROLE_DATA_STEWARD,
    ROLE_INDICATOR_LEAD,
    ROLE_SECRETARIAT,
    can_edit_object,
    filter_queryset_for_user,
    user_has_role,
)
from nbms_app.services.audit import record_audit_event
from nbms_app.services.exports import approve_export, reject_export, release_export, submit_export_for_review
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
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
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
    return render(request, "nbms_app/targets/nationaltarget_list.html", {"targets": targets})


def national_target_detail(request, target_uuid):
    targets = filter_queryset_for_user(
        NationalTarget.objects.select_related("organisation", "created_by"),
        request.user,
        perm="nbms_app.view_nationaltarget",
    )
    target = get_object_or_404(targets, uuid=target_uuid)
    return render(request, "nbms_app/targets/nationaltarget_detail.html", {"target": target})


def indicator_list(request):
    indicators = filter_queryset_for_user(
        Indicator.objects.select_related("national_target", "organisation", "created_by").order_by("code"),
        request.user,
        perm="nbms_app.view_indicator",
    )
    return render(request, "nbms_app/indicators/indicator_list.html", {"indicators": indicators})


def indicator_detail(request, indicator_uuid):
    indicators = filter_queryset_for_user(
        Indicator.objects.select_related("national_target", "organisation", "created_by"),
        request.user,
        perm="nbms_app.view_indicator",
    )
    indicator = get_object_or_404(indicators, uuid=indicator_uuid)
    return render(request, "nbms_app/indicators/indicator_detail.html", {"indicator": indicator})


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
    return render(
        request,
        "nbms_app/evidence/evidence_detail.html",
        {"evidence": evidence, "can_edit": can_edit},
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
    return render(
        request,
        "nbms_app/datasets/dataset_detail.html",
        {"dataset": dataset, "releases": releases, "can_edit": can_edit},
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
    return render(
        request,
        "nbms_app/exports/export_detail.html",
        {"package": package, "can_submit": can_submit, "can_review": can_review, "can_release": can_release},
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
