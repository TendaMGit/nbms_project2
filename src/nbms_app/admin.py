from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from nbms_app.models import (
    AuditEvent,
    Dataset,
    DatasetRelease,
    Evidence,
    ExportPackage,
    Indicator,
    IndicatorDatasetLink,
    IndicatorEvidenceLink,
    LifecycleStatus,
    NationalTarget,
    Organisation,
    User,
)
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
    list_display = ("code", "title", "status", "sensitivity", "export_approved", "organisation", "created_at")
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
    list_display = (
        "code",
        "title",
        "national_target",
        "status",
        "sensitivity",
        "export_approved",
        "organisation",
        "created_at",
    )
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


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("title", "evidence_type", "status", "sensitivity", "export_approved", "organisation", "created_at")
    search_fields = ("title", "evidence_type")
    list_filter = ("status", "sensitivity", "organisation")

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.status in {LifecycleStatus.PENDING_REVIEW, LifecycleStatus.PUBLISHED}:
            if not (request.user.is_superuser or user_has_role(request.user, ROLE_ADMIN)):
                readonly += [
                    "title",
                    "evidence_type",
                    "description",
                    "source_url",
                    "file",
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


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "sensitivity", "export_approved", "organisation", "created_at")
    search_fields = ("title",)
    list_filter = ("status", "sensitivity", "organisation")

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.status in {LifecycleStatus.PENDING_REVIEW, LifecycleStatus.PUBLISHED}:
            if not (request.user.is_superuser or user_has_role(request.user, ROLE_ADMIN)):
                readonly += [
                    "title",
                    "description",
                    "methodology",
                    "source_url",
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


@admin.register(DatasetRelease)
class DatasetReleaseAdmin(admin.ModelAdmin):
    list_display = ("dataset", "version", "status", "sensitivity", "export_approved", "organisation", "created_at")
    search_fields = ("dataset__title", "version")
    list_filter = ("status", "sensitivity", "organisation")

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.status in {LifecycleStatus.PENDING_REVIEW, LifecycleStatus.PUBLISHED}:
            if not (request.user.is_superuser or user_has_role(request.user, ROLE_ADMIN)):
                readonly += [
                    "dataset",
                    "version",
                    "release_date",
                    "snapshot_title",
                    "snapshot_description",
                    "snapshot_methodology",
                    "organisation",
                    "sensitivity",
                    "status",
                ]
        return readonly

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        if not obj.organisation and getattr(obj, "dataset", None):
            obj.organisation = obj.dataset.organisation
        if not obj.organisation and getattr(request.user, "organisation", None):
            obj.organisation = request.user.organisation
        super().save_model(request, obj, form, change)


@admin.register(IndicatorEvidenceLink)
class IndicatorEvidenceLinkAdmin(admin.ModelAdmin):
    list_display = ("indicator", "evidence", "created_at")
    search_fields = ("indicator__code", "evidence__title")


@admin.register(IndicatorDatasetLink)
class IndicatorDatasetLinkAdmin(admin.ModelAdmin):
    list_display = ("indicator", "dataset", "created_at")
    search_fields = ("indicator__code", "dataset__title")


@admin.register(ExportPackage)
class ExportPackageAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "organisation", "created_by", "created_at")
    search_fields = ("title",)
    list_filter = ("status", "organisation")
    readonly_fields = ("payload", "generated_at", "released_at")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "object_type", "object_uuid", "actor", "created_at")
    list_filter = ("action", "object_type")
    search_fields = ("object_uuid", "action")
    readonly_fields = ("action", "object_type", "object_uuid", "actor", "metadata", "created_at", "updated_at")

