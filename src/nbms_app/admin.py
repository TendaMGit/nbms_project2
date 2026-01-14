from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from nbms_app.models import Indicator, NationalTarget, Organisation, User


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

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        if not obj.organisation and getattr(request.user, "organisation", None):
            obj.organisation = request.user.organisation
        super().save_model(request, obj, form, change)

