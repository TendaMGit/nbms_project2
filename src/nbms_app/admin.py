from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from nbms_app.models import Indicator, LifecycleStatus, NationalTarget, Organisation, User
from nbms_app.services.authorization import ROLE_ADMIN, user_has_role


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_type", "contact_email", "is_active", "created_at")
    search_fields = ("name", "contact_email")


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Organisation", {"fields": ("organisation",)}),
    )
    list_display = UserAdmin.list_display + ("organisation",)


@admin.register(NationalTarget)
class NationalTargetAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "status", "sensitivity", "organisation", "created_at")
    search_fields = ("code", "title")
    list_filter = ("status", "sensitivity", "organisation")

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.status in {LifecycleStatus.PENDING_REVIEW, LifecycleStatus.PUBLISHED}:
            if not (request.user.is_superuser or user_has_role(request.user, ROLE_ADMIN)):
                readonly += [
                    "code",
                    "title",
                    "description",
                    "organisation",
                    "sensitivity",
                    "status",
                ]
        return readonly

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        if not obj.organisation and getattr(request.user, "organisation", None):
            obj.organisation = request.user.organisation
        super().save_model(request, obj, form, change)


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "national_target", "status", "sensitivity", "organisation", "created_at")
    search_fields = ("code", "title")
    list_filter = ("national_target", "status", "sensitivity", "organisation")

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.status in {LifecycleStatus.PENDING_REVIEW, LifecycleStatus.PUBLISHED}:
            if not (request.user.is_superuser or user_has_role(request.user, ROLE_ADMIN)):
                readonly += [
                    "code",
                    "title",
                    "national_target",
                    "organisation",
                    "sensitivity",
                    "status",
                ]
        return readonly

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        if not obj.organisation and getattr(request.user, "organisation", None):
            obj.organisation = request.user.organisation
        super().save_model(request, obj, form, change)

