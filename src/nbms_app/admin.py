from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from nbms_app.models import (
    AuditEvent,
    Dataset,
    DatasetRelease,
    Evidence,
    ExportPackage,
    Framework,
    FrameworkIndicator,
    FrameworkTarget,
    IndicatorFrameworkIndicatorLink,
    Indicator,
    IndicatorDatasetLink,
    IndicatorEvidenceLink,
    LifecycleStatus,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    ReportSectionResponse,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    User,
    ValidationRuleSet,
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


@admin.register(Framework)
class FrameworkAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "status", "sensitivity", "organisation", "created_at")
    search_fields = ("code", "title")
    list_filter = ("status", "sensitivity", "organisation")


@admin.register(FrameworkTarget)
class FrameworkTargetAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "framework", "status", "sensitivity", "organisation", "created_at")
    search_fields = ("code", "title")
    list_filter = ("framework", "status", "sensitivity", "organisation")


@admin.register(FrameworkIndicator)
class FrameworkIndicatorAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "framework", "status", "sensitivity", "organisation", "created_at")
    search_fields = ("code", "title")
    list_filter = ("framework", "status", "sensitivity", "organisation")


@admin.register(NationalTargetFrameworkTargetLink)
class NationalTargetFrameworkTargetLinkAdmin(admin.ModelAdmin):
    list_display = ("national_target", "framework_target", "relation_type", "confidence", "created_at")
    search_fields = ("national_target__code", "framework_target__code")
    list_filter = ("relation_type", "framework_target__framework")


@admin.register(IndicatorFrameworkIndicatorLink)
class IndicatorFrameworkIndicatorLinkAdmin(admin.ModelAdmin):
    list_display = ("indicator", "framework_indicator", "relation_type", "confidence", "created_at")
    search_fields = ("indicator__code", "framework_indicator__code")
    list_filter = ("relation_type", "framework_indicator__framework")


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


@admin.register(ReportingCycle)
class ReportingCycleAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "start_date", "end_date", "due_date", "is_active")
    search_fields = ("code", "title")
    list_filter = ("is_active",)


@admin.register(ReportingInstance)
class ReportingInstanceAdmin(admin.ModelAdmin):
    list_display = ("cycle", "version_label", "status", "frozen_at", "frozen_by")
    search_fields = ("cycle__code", "version_label")
    list_filter = ("status",)


@admin.register(ReportSectionTemplate)
class ReportSectionTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "ordering", "is_active", "updated_at")
    search_fields = ("code", "title")
    list_filter = ("is_active",)
    ordering = ("ordering", "code")


@admin.register(ReportSectionResponse)
class ReportSectionResponseAdmin(admin.ModelAdmin):
    list_display = ("template", "reporting_instance", "updated_by", "updated_at")
    search_fields = ("template__code", "template__title", "reporting_instance__cycle__code")
    list_filter = ("template",)


@admin.register(ValidationRuleSet)
class ValidationRuleSetAdmin(admin.ModelAdmin):
    list_display = ("code", "applies_to", "is_active", "created_by", "updated_at")
    search_fields = ("code",)
    list_filter = ("applies_to", "is_active")


@admin.register(ExportPackage)
class ExportPackageAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "reporting_instance", "organisation", "created_by", "created_at")
    search_fields = ("title",)
    list_filter = ("status", "organisation")
    readonly_fields = ("payload", "generated_at", "released_at")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "object_type", "object_uuid", "actor", "created_at")
    list_filter = ("action", "object_type")
    search_fields = ("object_uuid", "action")
    readonly_fields = ("action", "object_type", "object_uuid", "actor", "metadata", "created_at", "updated_at")

