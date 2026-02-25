from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from nbms_app.forms_catalog import (
    FRAMEWORK_GOAL_READONLY_FIELDS,
    FRAMEWORK_INDICATOR_READONLY_FIELDS,
    FRAMEWORK_READONLY_FIELDS,
    FRAMEWORK_TARGET_READONLY_FIELDS,
    FrameworkCatalogForm,
    FrameworkGoalCatalogForm,
    FrameworkIndicatorCatalogForm,
    FrameworkTargetCatalogForm,
)
from nbms_app.models import (
    AuditEvent,
    BinaryIndicatorQuestion,
    BinaryIndicatorResponse,
    Dataset,
    DatasetRelease,
    DatasetCatalog,
    DatasetCatalogIndicatorLink,
    Evidence,
    ExportPackage,
    License,
    Framework,
    FrameworkIndicator,
    FrameworkGoal,
    FrameworkTarget,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorFrameworkIndicatorLink,
    IndicatorMethodologyVersionLink,
    Indicator,
    IndicatorDatasetLink,
    IndicatorEvidenceLink,
    IndicatorMethodProfile,
    IndicatorMethodRun,
    Methodology,
    MethodologyDatasetLink,
    MethodologyIndicatorLink,
    MethodologyVersion,
    MonitoringProgrammeAlert,
    MonitoringProgramme,
    MonitoringProgrammeRun,
    MonitoringProgrammeRunStep,
    MonitoringProgrammeSteward,
    BirdieModelOutput,
    BirdieSite,
    BirdieSpecies,
    IntegrationDataAsset,
    ReportProductRun,
    ReportProductTemplate,
    ReportTemplatePack,
    ReportTemplatePackResponse,
    ReportTemplatePackSection,
    ReportCommentThread,
    ReportSuggestedChange,
    ReportContext,
    ReportNarrativeBlock,
    ReportNarrativeBlockVersion,
    ReportSignoffRecord,
    ReportWorkflowInstance,
    ReportWorkflowAction,
    ReportWorkflowSectionApproval,
    ReportingSnapshot,
    ProgrammeDatasetLink,
    ProgrammeIndicatorLink,
    DataAgreement,
    SensitivityClass,
    LifecycleStatus,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    ReportSectionResponse,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    SourceDocument,
    User,
    UserPreference,
    ValidationRuleSet,
)
from nbms_app.services.authorization import ROLE_ADMIN, is_system_admin, user_has_role
from nbms_app.services.lifecycle_service import archive_object
from nbms_app.services.readiness import compute_reporting_readiness


ADMIN_DOMAIN_PREFIX = {
    # Reporting
    "ReportingCycle": "Reporting",
    "ReportingInstance": "Reporting",
    "ReportingSnapshot": "Reporting",
    "ReportTemplatePack": "Reporting",
    "ReportTemplatePackSection": "Reporting",
    "ReportTemplatePackResponse": "Reporting",
    "ReportSectionTemplate": "Reporting",
    "ReportSectionResponse": "Reporting",
    "ReportCommentThread": "Reporting",
    "ReportSuggestedChange": "Reporting",
    "ReportContext": "Reporting",
    "ReportNarrativeBlock": "Reporting",
    "ReportNarrativeBlockVersion": "Reporting",
    "ReportSignoffRecord": "Reporting",
    "ReportWorkflowInstance": "Reporting",
    "ReportWorkflowAction": "Reporting",
    "ReportWorkflowSectionApproval": "Reporting",
    "ReportProductTemplate": "Reporting",
    "ReportProductRun": "Reporting",
    # Indicators
    "Indicator": "Indicators",
    "IndicatorMethodProfile": "Indicators",
    "IndicatorMethodRun": "Indicators",
    "IndicatorDataSeries": "Indicators",
    "IndicatorDataPoint": "Indicators",
    "IndicatorDatasetLink": "Indicators",
    "IndicatorEvidenceLink": "Indicators",
    "IndicatorFrameworkIndicatorLink": "Indicators",
    # Registries
    "NationalTarget": "Registries",
    "NationalTargetFrameworkTargetLink": "Registries",
    "Framework": "Registries",
    "FrameworkGoal": "Registries",
    "FrameworkTarget": "Registries",
    "FrameworkIndicator": "Registries",
    "BinaryIndicatorQuestion": "Registries",
    "BinaryIndicatorResponse": "Registries",
    # Programmes
    "MonitoringProgramme": "Programmes",
    "MonitoringProgrammeRun": "Programmes",
    "MonitoringProgrammeRunStep": "Programmes",
    "MonitoringProgrammeAlert": "Programmes",
    # Data
    "Evidence": "Data",
    "Dataset": "Data",
    "DatasetRelease": "Data",
    "DatasetCatalog": "Data",
    "DatasetCatalogIndicatorLink": "Data",
    "SourceDocument": "Data",
    "License": "Data",
    # Security and system
    "Organisation": "Security",
    "User": "Security",
    "UserPreference": "Security",
    "DataAgreement": "Security",
    "SensitivityClass": "Security",
    "AuditEvent": "System",
    "ValidationRuleSet": "System",
    "ExportPackage": "System",
}

ADMIN_MODEL_ORDER = {name: idx for idx, name in enumerate(ADMIN_DOMAIN_PREFIX.keys())}


_ORIGINAL_GET_APP_LIST = admin.AdminSite.get_app_list


def _nbms_grouped_app_list(self, request, app_label=None):
    app_list = _ORIGINAL_GET_APP_LIST(self, request, app_label=app_label)
    for app in app_list:
        if app.get("app_label") != "nbms_app":
            continue
        for model in app.get("models", []):
            object_name = model.get("object_name", "")
            domain = ADMIN_DOMAIN_PREFIX.get(object_name)
            if domain and not str(model.get("name", "")).startswith(f"{domain} | "):
                model["name"] = f"{domain} | {model['name']}"
        app["models"].sort(key=lambda row: ADMIN_MODEL_ORDER.get(row.get("object_name", ""), 9999))
    return app_list


admin.AdminSite.get_app_list = _nbms_grouped_app_list


class CatalogArchiveAdminMixin(admin.ModelAdmin):
    archive_field = "status"

    def _is_catalog_manager(self, user):
        return bool(user and (is_system_admin(user) or user_has_role(user, ROLE_ADMIN)))

    def has_view_permission(self, request, obj=None):
        return self._is_catalog_manager(request.user)

    def has_add_permission(self, request):
        return self._is_catalog_manager(request.user)

    def has_change_permission(self, request, obj=None):
        return self._is_catalog_manager(request.user)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)

        class FormWithUser(form_class):
            def __init__(self, *args, **form_kwargs):
                form_kwargs["user"] = request.user
                super().__init__(*args, **form_kwargs)

        return FormWithUser

    def archive_selected(self, request, queryset):
        if not self._is_catalog_manager(request.user):
            return
        for obj in queryset:
            archive_object(request.user, obj, request=request)

    archive_selected.short_description = "Archive selected"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self.archive_field == "is_active":
            if "is_active__exact" in request.GET:
                return qs
            return qs.filter(is_active=True)
        if "status__exact" in request.GET:
            return qs
        return qs.exclude(status=LifecycleStatus.ARCHIVED)


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_code", "org_type", "contact_email", "is_active", "created_at")
    search_fields = ("name", "org_code", "contact_email")


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Organisation", {"fields": ("organisation",)}),
    )
    list_display = UserAdmin.list_display + ("organisation",)


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "theme_id", "theme_mode", "density", "default_geography", "updated_at")
    search_fields = ("user__username", "user__email")
    list_filter = ("theme_id", "theme_mode", "density", "default_geography")


@admin.register(NationalTarget)
class NationalTargetAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "status", "sensitivity", "export_approved", "organisation", "created_at")
    search_fields = ("code", "title")
    list_filter = ("status", "sensitivity", "organisation")

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.status in {LifecycleStatus.PENDING_REVIEW, LifecycleStatus.PUBLISHED}:
            if not (is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN)):
                readonly += [
                    "code",
                    "title",
                    "description",
                    "responsible_org",
                    "qa_status",
                    "reporting_cadence",
                    "source_document",
                    "license",
                    "provenance_notes",
                    "spatial_coverage",
                    "temporal_coverage",
                    "organisation",
                    "sensitivity",
                    "status",
                    "source_system",
                    "source_ref",
                ]
        readonly.append("export_approved")
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
            if not (is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN)):
                readonly += [
                    "code",
                    "title",
                    "national_target",
                    "indicator_type",
                    "reporting_cadence",
                    "qa_status",
                    "responsible_org",
                    "data_steward",
                    "indicator_lead",
                    "source_document",
                    "license",
                    "computation_notes",
                    "limitations",
                    "spatial_coverage",
                    "temporal_coverage",
                    "organisation",
                    "sensitivity",
                    "status",
                    "source_system",
                    "source_ref",
                ]
        readonly.append("export_approved")
        return readonly

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        if not obj.organisation and getattr(request.user, "organisation", None):
            obj.organisation = request.user.organisation
        super().save_model(request, obj, form, change)


@admin.register(Framework)
class FrameworkAdmin(CatalogArchiveAdminMixin):
    form = FrameworkCatalogForm
    readonly_fields = FRAMEWORK_READONLY_FIELDS
    actions = ("archive_selected",)
    list_display = ("code", "title", "status", "sensitivity", "organisation", "created_at")
    search_fields = ("code", "title")
    list_filter = ("status", "sensitivity", "organisation")


@admin.register(FrameworkGoal)
class FrameworkGoalAdmin(CatalogArchiveAdminMixin):
    form = FrameworkGoalCatalogForm
    readonly_fields = FRAMEWORK_GOAL_READONLY_FIELDS
    actions = ("archive_selected",)
    list_display = ("code", "title", "framework", "status", "sensitivity", "sort_order", "created_at")
    search_fields = ("code", "title", "framework__code")
    list_filter = ("framework", "status", "sensitivity")


@admin.register(FrameworkTarget)
class FrameworkTargetAdmin(CatalogArchiveAdminMixin):
    form = FrameworkTargetCatalogForm
    readonly_fields = FRAMEWORK_TARGET_READONLY_FIELDS
    actions = ("archive_selected",)
    list_display = ("code", "title", "framework", "goal", "status", "sensitivity", "organisation", "created_at")
    search_fields = ("code", "title")
    list_filter = ("framework", "goal", "status", "sensitivity", "organisation")


@admin.register(FrameworkIndicator)
class FrameworkIndicatorAdmin(CatalogArchiveAdminMixin):
    form = FrameworkIndicatorCatalogForm
    readonly_fields = FRAMEWORK_INDICATOR_READONLY_FIELDS
    actions = ("archive_selected",)
    list_display = (
        "code",
        "title",
        "framework",
        "framework_target",
        "indicator_type",
        "status",
        "sensitivity",
        "organisation",
        "created_at",
    )
    search_fields = ("code", "title")
    list_filter = ("framework", "framework_target", "indicator_type", "status", "sensitivity", "organisation")


@admin.register(NationalTargetFrameworkTargetLink)
class NationalTargetFrameworkTargetLinkAdmin(admin.ModelAdmin):
    list_display = ("national_target", "framework_target", "relation_type", "confidence", "is_active", "created_at")
    search_fields = ("national_target__code", "framework_target__code")
    list_filter = ("relation_type", "framework_target__framework", "is_active")


@admin.register(IndicatorFrameworkIndicatorLink)
class IndicatorFrameworkIndicatorLinkAdmin(admin.ModelAdmin):
    list_display = ("indicator", "framework_indicator", "relation_type", "confidence", "is_active", "created_at")
    search_fields = ("indicator__code", "framework_indicator__code")
    list_filter = ("relation_type", "framework_indicator__framework", "is_active")


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("title", "evidence_type", "status", "sensitivity", "export_approved", "organisation", "created_at")
    search_fields = ("title", "evidence_type")
    list_filter = ("status", "sensitivity", "organisation")

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.status in {LifecycleStatus.PENDING_REVIEW, LifecycleStatus.PUBLISHED}:
            if not (is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN)):
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
        readonly.append("export_approved")
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
            if not (is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN)):
                readonly += [
                    "title",
                    "description",
                    "methodology",
                    "source_url",
                    "organisation",
                    "sensitivity",
                    "status",
                ]
        readonly.append("export_approved")
        return readonly

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        if not obj.organisation and getattr(request.user, "organisation", None):
            obj.organisation = request.user.organisation
        super().save_model(request, obj, form, change)


class MethodologyVersionInline(admin.TabularInline):
    model = MethodologyVersion
    extra = 0


class ProgrammeDatasetLinkInline(admin.TabularInline):
    model = ProgrammeDatasetLink
    extra = 0


class ProgrammeIndicatorLinkInline(admin.TabularInline):
    model = ProgrammeIndicatorLink
    extra = 0


class MonitoringProgrammeStewardInline(admin.TabularInline):
    model = MonitoringProgrammeSteward
    extra = 0


class MethodologyDatasetLinkInline(admin.TabularInline):
    model = MethodologyDatasetLink
    extra = 0


class MethodologyIndicatorLinkInline(admin.TabularInline):
    model = MethodologyIndicatorLink
    extra = 0


class DatasetCatalogIndicatorLinkInline(admin.TabularInline):
    model = DatasetCatalogIndicatorLink
    extra = 0


@admin.register(SensitivityClass)
class SensitivityClassAdmin(admin.ModelAdmin):
    list_display = ("sensitivity_code", "sensitivity_name", "access_level_default", "consent_required_default", "is_active")
    search_fields = ("sensitivity_code", "sensitivity_name")
    list_filter = ("access_level_default", "consent_required_default", "is_active")


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "url", "is_active", "created_at")
    search_fields = ("code", "title")
    list_filter = ("is_active",)


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "source_url", "version_date", "created_by", "created_at")
    search_fields = ("title", "source_url", "citation")
    list_filter = ("version_date",)


@admin.register(DataAgreement)
class DataAgreementAdmin(admin.ModelAdmin):
    list_display = ("agreement_code", "title", "agreement_type", "status", "is_active", "created_at")
    search_fields = ("agreement_code", "title")
    list_filter = ("agreement_type", "status", "is_active")
    filter_horizontal = ("parties",)


@admin.register(DatasetCatalog)
class DatasetCatalogAdmin(admin.ModelAdmin):
    list_display = ("dataset_code", "title", "dataset_type", "access_level", "is_active", "last_updated_date")
    search_fields = ("dataset_code", "title")
    list_filter = ("access_level", "is_active", "qa_status")
    inlines = [
        ProgrammeDatasetLinkInline,
        MethodologyDatasetLinkInline,
        DatasetCatalogIndicatorLinkInline,
    ]


@admin.register(MonitoringProgramme)
class MonitoringProgrammeAdmin(admin.ModelAdmin):
    list_display = (
        "programme_code",
        "title",
        "programme_type",
        "lead_org",
        "refresh_cadence",
        "scheduler_enabled",
        "last_run_at",
        "is_active",
    )
    search_fields = ("programme_code", "title")
    list_filter = ("programme_type", "refresh_cadence", "scheduler_enabled", "is_active")
    inlines = [MonitoringProgrammeStewardInline, ProgrammeDatasetLinkInline, ProgrammeIndicatorLinkInline]
    filter_horizontal = ("partners", "operating_institutions")


@admin.register(Methodology)
class MethodologyAdmin(admin.ModelAdmin):
    list_display = ("methodology_code", "title", "owner_org", "is_active")
    search_fields = ("methodology_code", "title")
    list_filter = ("is_active",)
    inlines = [MethodologyVersionInline, MethodologyDatasetLinkInline, MethodologyIndicatorLinkInline]


@admin.register(ProgrammeDatasetLink)
class ProgrammeDatasetLinkAdmin(admin.ModelAdmin):
    list_display = ("programme", "dataset", "relationship_type", "role", "is_active")
    search_fields = ("programme__programme_code", "dataset__dataset_code")
    list_filter = ("relationship_type", "is_active")


@admin.register(ProgrammeIndicatorLink)
class ProgrammeIndicatorLinkAdmin(admin.ModelAdmin):
    list_display = ("programme", "indicator", "relationship_type", "role", "is_active")
    search_fields = ("programme__programme_code", "indicator__code")
    list_filter = ("relationship_type", "is_active")


@admin.register(MonitoringProgrammeSteward)
class MonitoringProgrammeStewardAdmin(admin.ModelAdmin):
    list_display = ("programme", "user", "role", "is_primary", "is_active", "created_at")
    search_fields = ("programme__programme_code", "user__username", "user__email")
    list_filter = ("role", "is_primary", "is_active")


@admin.register(MonitoringProgrammeRun)
class MonitoringProgrammeRunAdmin(admin.ModelAdmin):
    list_display = (
        "programme",
        "run_type",
        "trigger",
        "status",
        "dry_run",
        "requested_by",
        "started_at",
        "finished_at",
        "created_at",
    )
    search_fields = ("programme__programme_code", "requested_by__username", "uuid")
    list_filter = ("run_type", "trigger", "status", "dry_run")


@admin.register(MonitoringProgrammeRunStep)
class MonitoringProgrammeRunStepAdmin(admin.ModelAdmin):
    list_display = ("run", "ordering", "step_key", "step_type", "status", "started_at", "finished_at")
    search_fields = ("run__programme__programme_code", "run__uuid", "step_key")
    list_filter = ("step_type", "status")


@admin.register(MonitoringProgrammeAlert)
class MonitoringProgrammeAlertAdmin(admin.ModelAdmin):
    list_display = ("programme", "severity", "state", "code", "created_at", "resolved_at")
    search_fields = ("programme__programme_code", "code", "message")
    list_filter = ("severity", "state")


@admin.register(MethodologyDatasetLink)
class MethodologyDatasetLinkAdmin(admin.ModelAdmin):
    list_display = ("methodology", "dataset", "relationship_type", "role", "is_active")
    search_fields = ("methodology__methodology_code", "dataset__dataset_code")
    list_filter = ("relationship_type", "is_active")


@admin.register(MethodologyIndicatorLink)
class MethodologyIndicatorLinkAdmin(admin.ModelAdmin):
    list_display = ("methodology", "indicator", "relationship_type", "role", "is_active")
    search_fields = ("methodology__methodology_code", "indicator__code")
    list_filter = ("relationship_type", "is_active")


@admin.register(IndicatorMethodologyVersionLink)
class IndicatorMethodologyVersionLinkAdmin(admin.ModelAdmin):
    list_display = ("indicator", "methodology_version", "is_primary", "is_active", "created_at")
    search_fields = ("indicator__code", "methodology_version__version", "methodology_version__methodology__methodology_code")
    list_filter = ("is_primary", "is_active")


@admin.register(DatasetCatalogIndicatorLink)
class DatasetCatalogIndicatorLinkAdmin(admin.ModelAdmin):
    list_display = ("dataset", "indicator", "relationship_type", "role", "is_active")
    search_fields = ("dataset__dataset_code", "indicator__code")
    list_filter = ("relationship_type", "is_active")


@admin.register(DatasetRelease)
class DatasetReleaseAdmin(admin.ModelAdmin):
    list_display = ("dataset", "version", "status", "sensitivity", "export_approved", "organisation", "created_at")
    search_fields = ("dataset__title", "version")
    list_filter = ("status", "sensitivity", "organisation")

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.status in {LifecycleStatus.PENDING_REVIEW, LifecycleStatus.PUBLISHED}:
            if not (is_system_admin(request.user) or user_has_role(request.user, ROLE_ADMIN)):
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
        readonly.append("export_approved")
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


@admin.register(IndicatorDataSeries)
class IndicatorDataSeriesAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "indicator",
        "framework_indicator",
        "value_type",
        "unit",
        "status",
        "sensitivity",
        "organisation",
        "created_at",
    )
    search_fields = ("title", "indicator__code", "framework_indicator__code")
    list_filter = ("value_type", "status", "sensitivity", "organisation")


@admin.register(IndicatorDataPoint)
class IndicatorDataPointAdmin(admin.ModelAdmin):
    list_display = ("series", "year", "value_numeric", "value_text", "dataset_release", "created_at")
    search_fields = ("series__indicator__code", "series__framework_indicator__code")
    list_filter = ("year", "dataset_release")


@admin.register(IndicatorMethodProfile)
class IndicatorMethodProfileAdmin(admin.ModelAdmin):
    list_display = (
        "indicator",
        "method_type",
        "implementation_key",
        "readiness_state",
        "last_success_at",
        "is_active",
    )
    search_fields = ("indicator__code", "implementation_key", "summary")
    list_filter = ("method_type", "readiness_state", "is_active")


@admin.register(IndicatorMethodRun)
class IndicatorMethodRunAdmin(admin.ModelAdmin):
    list_display = ("profile", "status", "requested_by", "started_at", "finished_at", "created_at")
    search_fields = ("profile__indicator__code", "profile__implementation_key", "uuid")
    list_filter = ("status",)


@admin.register(BirdieSpecies)
class BirdieSpeciesAdmin(admin.ModelAdmin):
    list_display = ("species_code", "common_name", "scientific_name", "guild", "is_restricted", "updated_at")
    search_fields = ("species_code", "common_name", "scientific_name", "guild")
    list_filter = ("guild", "is_restricted")


@admin.register(BirdieSite)
class BirdieSiteAdmin(admin.ModelAdmin):
    list_display = ("site_code", "site_name", "province_code", "convention_type", "is_restricted")
    search_fields = ("site_code", "site_name", "province_code", "convention_type")
    list_filter = ("province_code", "convention_type", "is_restricted")


@admin.register(BirdieModelOutput)
class BirdieModelOutputAdmin(admin.ModelAdmin):
    list_display = ("metric_code", "year", "site", "species", "indicator", "value_numeric", "is_restricted")
    search_fields = ("metric_code", "site__site_code", "species__species_code", "indicator__code")
    list_filter = ("metric_code", "year", "is_restricted")


@admin.register(IntegrationDataAsset)
class IntegrationDataAssetAdmin(admin.ModelAdmin):
    list_display = ("source_system", "layer", "dataset_key", "record_key", "is_restricted", "updated_at")
    search_fields = ("source_system", "dataset_key", "record_key", "source_endpoint")
    list_filter = ("source_system", "layer", "is_restricted")


@admin.register(ReportTemplatePack)
class ReportTemplatePackAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "mea_code", "version", "is_active", "updated_at")
    search_fields = ("code", "title", "mea_code")
    list_filter = ("mea_code", "is_active")


@admin.register(ReportTemplatePackSection)
class ReportTemplatePackSectionAdmin(admin.ModelAdmin):
    list_display = ("pack", "code", "title", "ordering", "is_active")
    search_fields = ("pack__code", "code", "title")
    list_filter = ("pack__mea_code", "is_active")


@admin.register(ReportTemplatePackResponse)
class ReportTemplatePackResponseAdmin(admin.ModelAdmin):
    list_display = (
        "section",
        "reporting_instance",
        "current_version",
        "locked_for_editing",
        "updated_by",
        "updated_at",
    )
    search_fields = (
        "section__pack__code",
        "section__code",
        "section__title",
        "reporting_instance__uuid",
        "reporting_instance__cycle__code",
    )
    list_filter = ("section__pack__mea_code", "section__code", "locked_for_editing")


@admin.register(ReportProductTemplate)
class ReportProductTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "version", "is_active", "updated_at")
    search_fields = ("code", "title")
    list_filter = ("is_active",)


@admin.register(ReportProductRun)
class ReportProductRunAdmin(admin.ModelAdmin):
    list_display = ("template", "status", "reporting_instance", "generated_by", "generated_at", "created_at")
    search_fields = ("template__code", "uuid", "reporting_instance__uuid")
    list_filter = ("status",)


@admin.register(BinaryIndicatorQuestion)
class BinaryIndicatorQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "framework_indicator",
        "group_key",
        "question_key",
        "section",
        "number",
        "question_type",
        "multiple",
        "mandatory",
        "sort_order",
    )
    search_fields = ("framework_indicator__code", "group_key", "question_key", "question_text")
    list_filter = ("framework_indicator", "question_type", "multiple", "mandatory")


@admin.register(BinaryIndicatorResponse)
class BinaryIndicatorResponseAdmin(admin.ModelAdmin):
    list_display = ("reporting_instance", "question", "created_at")
    search_fields = ("reporting_instance__uuid", "question__framework_indicator__code", "question__question_key")
    list_filter = ("reporting_instance",)


@admin.register(ReportingCycle)
class ReportingCycleAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "start_date", "end_date", "due_date", "is_active")
    search_fields = ("code", "title")
    list_filter = ("is_active",)


@admin.register(ReportingInstance)
class ReportingInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "report_family",
        "report_label",
        "cycle",
        "version_label",
        "reporting_period_start",
        "reporting_period_end",
        "is_public",
        "status",
        "frozen_at",
        "frozen_by",
        "readiness_percent",
        "blocking_gap_count",
    )
    search_fields = ("cycle__code", "version_label", "country_name", "report_title", "report_label")
    list_filter = ("report_family", "report_label", "status", "is_public")
    actions = ["generate_readiness_report"]

    @admin.display(description="Readiness %")
    def readiness_percent(self, obj):
        result = compute_reporting_readiness(obj.uuid, scope="selected")
        return result["summary"].get("ready_percent")

    @admin.display(description="Blocking gaps")
    def blocking_gap_count(self, obj):
        result = compute_reporting_readiness(obj.uuid, scope="selected")
        return result["summary"].get("blocking_gap_count")

    @admin.action(description="Generate readiness report")
    def generate_readiness_report(self, request, queryset):
        for instance in queryset:
            result = compute_reporting_readiness(instance.uuid, scope="selected", user=request.user)
            summary = result["summary"]
            message = (
                f"{instance}: ready {summary.get('ready_percent', 0)}% "
                f"({summary.get('blocking_gap_count', 0)} blocking indicators)."
            )
            self.message_user(request, message)


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


@admin.register(ReportCommentThread)
class ReportCommentThreadAdmin(admin.ModelAdmin):
    list_display = (
        "section_response",
        "json_path",
        "field_name",
        "status",
        "created_by",
        "created_at",
        "resolved_by",
        "resolved_at",
    )
    search_fields = (
        "json_path",
        "field_name",
        "section_response__section__code",
        "section_response__reporting_instance__uuid",
        "created_by__username",
    )
    list_filter = ("status", "field_name", "created_at")


@admin.register(ReportSuggestedChange)
class ReportSuggestedChangeAdmin(admin.ModelAdmin):
    list_display = (
        "section_response",
        "field_name",
        "base_version",
        "status",
        "created_by",
        "created_at",
        "decided_by",
        "decided_at",
    )
    search_fields = (
        "field_name",
        "section_response__section__code",
        "section_response__reporting_instance__uuid",
        "created_by__username",
        "decided_by__username",
    )
    list_filter = ("status", "field_name", "created_at", "decided_at")


@admin.register(ReportContext)
class ReportContextAdmin(admin.ModelAdmin):
    list_display = (
        "reporting_instance",
        "user",
        "session_key",
        "context_hash",
        "is_active",
        "updated_at",
    )
    search_fields = ("reporting_instance__uuid", "user__username", "session_key", "context_hash")
    list_filter = ("is_active", "updated_at")


@admin.register(ReportNarrativeBlock)
class ReportNarrativeBlockAdmin(admin.ModelAdmin):
    list_display = (
        "reporting_instance",
        "section_code",
        "block_key",
        "title",
        "current_version",
        "updated_by",
        "updated_at",
    )
    search_fields = (
        "reporting_instance__uuid",
        "section_code",
        "block_key",
        "title",
        "onlyoffice_document_key",
    )
    list_filter = ("section_code", "updated_at")


@admin.register(ReportNarrativeBlockVersion)
class ReportNarrativeBlockVersionAdmin(admin.ModelAdmin):
    list_display = ("block", "version", "content_hash", "created_by", "created_at")
    search_fields = ("block__reporting_instance__uuid", "block__section_code", "block__block_key", "content_hash")
    list_filter = ("created_at",)


@admin.register(ReportingSnapshot)
class ReportingSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "reporting_instance",
        "snapshot_type",
        "report_label",
        "payload_hash",
        "readiness_overall_ready",
        "created_by",
        "created_at",
    )
    search_fields = ("reporting_instance__uuid", "snapshot_type", "payload_hash", "report_label")
    list_filter = ("snapshot_type", "report_label", "readiness_overall_ready", "created_at")
    readonly_fields = (
        "payload_json",
        "payload_hash",
        "context_filters_json",
        "resolved_values_manifest_json",
        "readiness_report_json",
    )


@admin.register(ReportSignoffRecord)
class ReportSignoffRecordAdmin(admin.ModelAdmin):
    list_display = (
        "reporting_instance",
        "signer",
        "signer_role",
        "body",
        "state_from",
        "state_to",
        "signed_at",
    )
    search_fields = (
        "reporting_instance__uuid",
        "signer__username",
        "signer_role",
        "body",
        "snapshot_hash_pointer",
    )
    list_filter = ("body", "state_to", "signed_at")


@admin.register(ReportWorkflowInstance)
class ReportWorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = ("reporting_instance", "status", "current_step", "locked", "started_at", "completed_at")
    search_fields = ("reporting_instance__uuid", "reporting_instance__cycle__code", "current_step")
    list_filter = ("status", "current_step", "locked")


@admin.register(ReportWorkflowAction)
class ReportWorkflowActionAdmin(admin.ModelAdmin):
    list_display = ("workflow_instance", "action_type", "actor", "created_at")
    search_fields = (
        "workflow_instance__reporting_instance__uuid",
        "workflow_instance__reporting_instance__cycle__code",
        "action_type",
        "actor__username",
        "payload_hash",
    )
    list_filter = ("action_type", "created_at")


@admin.register(ReportWorkflowSectionApproval)
class ReportWorkflowSectionApprovalAdmin(admin.ModelAdmin):
    list_display = ("workflow_instance", "section", "approved", "approved_by", "approved_at")
    search_fields = (
        "workflow_instance__reporting_instance__uuid",
        "section__code",
        "section__title",
        "approved_by__username",
    )
    list_filter = ("approved", "section__code", "approved_at")


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
    list_display = ("event_type", "object_type", "object_uuid", "actor", "created_at")
    list_filter = ("event_type", "object_type", "request_method")
    search_fields = ("object_uuid", "action", "event_type", "request_path", "request_id")
    readonly_fields = (
        "action",
        "event_type",
        "content_type",
        "object_type",
        "object_id",
        "object_uuid",
        "actor",
        "metadata",
        "request_path",
        "request_method",
        "ip_address",
        "user_agent",
        "session_key",
        "request_id",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

