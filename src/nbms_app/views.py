import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import PasswordResetForm
from django.core.files.storage import default_storage
from django.db import connections
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from nbms_app.forms import OrganisationForm, UserCreateForm, UserUpdateForm
from nbms_app.models import Organisation, User

logger = logging.getLogger(__name__)


def home(request):
    return render(request, "nbms_app/home.html")


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
