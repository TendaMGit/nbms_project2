from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UsernameField
from django.core.exceptions import ValidationError
from django.db import models

from nbms_app.models import (
    BinaryIndicatorGroup,
    BinaryIndicatorResponse,
    BinaryIndicatorQuestion,
    Dataset,
    DatasetCatalog,
    DatasetRelease,
    DataAgreement,
    Evidence,
    ExportPackage,
    FrameworkIndicator,
    FrameworkGoal,
    FrameworkTarget,
    Indicator,
    IndicatorDataSeries,
    IndicatorFrameworkIndicatorLink,
    IndicatorMethodologyVersionLink,
    License,
    Methodology,
    MethodologyVersion,
    MonitoringProgramme,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    LifecycleStatus,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    SectionIReportContext,
    SectionIINBSAPStatus,
    SectionIIINationalTargetProgress,
    SectionIVFrameworkGoalProgress,
    SectionIVFrameworkTargetProgress,
    SectionVConclusions,
    SensitivityClass,
    SourceDocument,
    User,
)
from nbms_app.roles import get_canonical_groups_queryset
from nbms_app.section_help import apply_section_help
from nbms_app.services.authorization import filter_queryset_for_user
from nbms_app.services.catalog_access import (
    filter_data_agreements_for_user,
    filter_methodologies_for_user,
    filter_monitoring_programmes_for_user,
    filter_organisations_for_user,
    filter_sensitivity_classes_for_user,
)
from nbms_app.services.instance_approvals import approved_queryset
from nbms_app.services.indicator_data import (
    binary_indicator_responses_for_user,
    indicator_data_series_for_user,
)
from nbms_app.services.consent import consent_is_granted, requires_consent


class OrganisationForm(forms.ModelForm):
    class Meta:
        model = Organisation
        fields = ["name", "org_type", "contact_email", "is_active"]


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "organisation",
            "groups",
            "is_active",
        ]
        field_classes = {"username": UsernameField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["groups"].queryset = get_canonical_groups_queryset()

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 or password2:
            if password1 != password2:
                raise ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "organisation",
            "groups",
            "is_active",
        ]
        field_classes = {"username": UsernameField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["groups"].queryset = get_canonical_groups_queryset()


class EvidenceForm(forms.ModelForm):
    class Meta:
        model = Evidence
        fields = [
            "title",
            "description",
            "evidence_type",
            "source_url",
            "file",
            "organisation",
            "sensitivity",
        ]

    def clean_file(self):
        uploaded = self.cleaned_data.get("file")
        if not uploaded:
            return uploaded
        max_size = getattr(settings, "EVIDENCE_MAX_FILE_SIZE", 25 * 1024 * 1024)
        if uploaded.size > max_size:
            raise ValidationError("File exceeds the maximum allowed size.")
        allowed_exts = getattr(settings, "EVIDENCE_ALLOWED_EXTENSIONS", [])
        ext = Path(uploaded.name).suffix.lower()
        if allowed_exts and ext not in allowed_exts:
            raise ValidationError("File type is not allowed.")
        return uploaded


class DatasetForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = [
            "title",
            "description",
            "methodology",
            "source_url",
            "organisation",
            "sensitivity",
        ]


class DatasetCatalogForm(forms.ModelForm):
    programmes = forms.ModelMultipleChoiceField(queryset=MonitoringProgramme.objects.none(), required=False)
    indicators = forms.ModelMultipleChoiceField(queryset=Indicator.objects.none(), required=False)
    methodologies = forms.ModelMultipleChoiceField(queryset=Methodology.objects.none(), required=False)

    class Meta:
        model = DatasetCatalog
        fields = [
            "dataset_code",
            "title",
            "description",
            "dataset_type",
            "custodian_org",
            "producer_org",
            "licence",
            "access_level",
            "sensitivity_class",
            "consent_required",
            "agreement",
            "temporal_start",
            "temporal_end",
            "update_frequency",
            "spatial_coverage_description",
            "spatial_resolution",
            "taxonomy_standard",
            "ecosystem_classification",
            "doi_or_identifier",
            "landing_page_url",
            "api_endpoint_url",
            "file_formats",
            "qa_status",
            "citation",
            "keywords",
            "last_updated_date",
            "is_active",
            "source_system",
            "source_ref",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["custodian_org"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )
        self.fields["producer_org"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )
        self.fields["agreement"].queryset = filter_data_agreements_for_user(
            DataAgreement.objects.order_by("agreement_code"), user
        )
        self.fields["sensitivity_class"].queryset = filter_sensitivity_classes_for_user(
            SensitivityClass.objects.order_by("sensitivity_code"), user
        )
        self.fields["programmes"].queryset = filter_monitoring_programmes_for_user(
            MonitoringProgramme.objects.order_by("programme_code"), user
        )
        self.fields["methodologies"].queryset = filter_methodologies_for_user(
            Methodology.objects.order_by("methodology_code"), user
        )
        self.fields["indicators"].queryset = filter_queryset_for_user(
            Indicator.objects.all().order_by("code"),
            user,
            perm="nbms_app.view_indicator",
        )
        if self.instance and getattr(self.instance, "pk", None):
            self.fields["programmes"].initial = self.instance.programme_links.values_list("programme_id", flat=True)
            self.fields["methodologies"].initial = self.instance.methodology_links.values_list("methodology_id", flat=True)
            self.fields["indicators"].initial = self.instance.indicator_links.values_list("indicator_id", flat=True)


class MonitoringProgrammeForm(forms.ModelForm):
    partners = forms.ModelMultipleChoiceField(queryset=Organisation.objects.none(), required=False)

    class Meta:
        model = MonitoringProgramme
        fields = [
            "programme_code",
            "title",
            "description",
            "programme_type",
            "lead_org",
            "partners",
            "start_year",
            "end_year",
            "geographic_scope",
            "spatial_coverage_description",
            "taxonomic_scope",
            "ecosystem_scope",
            "objectives",
            "sampling_design_summary",
            "update_frequency",
            "qa_process_summary",
            "sensitivity_class",
            "consent_required",
            "agreement",
            "website_url",
            "primary_contact_name",
            "primary_contact_email",
            "alternative_contact_name",
            "alternative_contact_email",
            "notes",
            "is_active",
            "source_system",
            "source_ref",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lead_org"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )
        self.fields["partners"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )
        self.fields["sensitivity_class"].queryset = filter_sensitivity_classes_for_user(
            SensitivityClass.objects.order_by("sensitivity_code"), user
        )
        self.fields["agreement"].queryset = filter_data_agreements_for_user(
            DataAgreement.objects.order_by("agreement_code"), user
        )
        if self.instance and getattr(self.instance, "pk", None):
            self.fields["partners"].initial = self.instance.partners.values_list("id", flat=True)


class MethodologyForm(forms.ModelForm):
    class Meta:
        model = Methodology
        fields = [
            "methodology_code",
            "title",
            "description",
            "owner_org",
            "scope",
            "references_url",
            "is_active",
            "source_system",
            "source_ref",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner_org"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )


class MethodologyVersionForm(forms.ModelForm):
    class Meta:
        model = MethodologyVersion
        fields = [
            "methodology",
            "version",
            "status",
            "effective_date",
            "deprecated_date",
            "change_log",
            "protocol_url",
            "computational_script_url",
            "parameters_json",
            "qa_steps_summary",
            "peer_reviewed",
            "approval_body",
            "approval_reference",
            "is_active",
            "source_system",
            "source_ref",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["methodology"].queryset = filter_methodologies_for_user(
            Methodology.objects.order_by("methodology_code"), user
        )


class DataAgreementForm(forms.ModelForm):
    parties = forms.ModelMultipleChoiceField(queryset=Organisation.objects.none(), required=False)

    class Meta:
        model = DataAgreement
        fields = [
            "agreement_code",
            "title",
            "agreement_type",
            "status",
            "parties",
            "start_date",
            "end_date",
            "licence",
            "restrictions_summary",
            "benefit_sharing_terms",
            "citation_requirement",
            "document_url",
            "primary_contact_name",
            "primary_contact_email",
            "is_active",
            "source_system",
            "source_ref",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parties"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )
        if self.instance and getattr(self.instance, "pk", None):
            self.fields["parties"].initial = self.instance.parties.values_list("id", flat=True)


class SensitivityClassForm(forms.ModelForm):
    class Meta:
        model = SensitivityClass
        fields = [
            "sensitivity_code",
            "sensitivity_name",
            "description",
            "access_level_default",
            "consent_required_default",
            "redaction_policy",
            "legal_basis",
            "notes",
            "is_active",
            "source_system",
            "source_ref",
        ]


class IndicatorForm(forms.ModelForm):
    class Meta:
        model = Indicator
        fields = [
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
            "reporting_capability",
            "reporting_no_reason_codes",
            "reporting_no_reason_notes",
            "owner_organisation",
            "update_frequency",
            "last_updated_on",
            "coverage_geography",
            "coverage_time_start_year",
            "coverage_time_end_year",
            "data_quality_note",
            "organisation",
            "sensitivity",
            "source_system",
            "source_ref",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organisation"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )
        self.fields["responsible_org"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )
        self.fields["owner_organisation"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )
        user_qs = User.objects.order_by("username")
        if user and getattr(user, "organisation_id", None):
            user_qs = user_qs.filter(organisation_id=user.organisation_id)
        self.fields["data_steward"].queryset = user_qs
        self.fields["indicator_lead"].queryset = user_qs


class NationalTargetAlignmentForm(forms.ModelForm):
    class Meta:
        model = NationalTargetFrameworkTargetLink
        fields = ["framework_target", "relation_type", "confidence", "notes", "source"]

    def __init__(self, *args, user=None, framework_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        targets = filter_queryset_for_user(
            FrameworkTarget.objects.exclude(status=LifecycleStatus.ARCHIVED).select_related("framework"),
            user,
            perm="nbms_app.view_frameworktarget",
        )
        if framework_id:
            targets = targets.filter(framework_id=framework_id)
        self.fields["framework_target"].queryset = targets.order_by("framework__code", "code")


class IndicatorAlignmentForm(forms.ModelForm):
    class Meta:
        model = IndicatorFrameworkIndicatorLink
        fields = ["framework_indicator", "relation_type", "confidence", "notes", "source"]

    def __init__(self, *args, user=None, framework_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        indicators = filter_queryset_for_user(
            FrameworkIndicator.objects.exclude(status=LifecycleStatus.ARCHIVED).select_related("framework"),
            user,
            perm="nbms_app.view_frameworkindicator",
        )
        if framework_id:
            indicators = indicators.filter(framework_id=framework_id)
        self.fields["framework_indicator"].queryset = indicators.order_by("framework__code", "code")


class IndicatorMethodologyVersionForm(forms.ModelForm):
    class Meta:
        model = IndicatorMethodologyVersionLink
        fields = ["methodology_version", "is_primary", "notes", "source"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        methodologies = filter_methodologies_for_user(Methodology.objects.all(), user)
        versions = MethodologyVersion.objects.filter(methodology__in=methodologies, is_active=True)
        self.fields["methodology_version"].queryset = versions.select_related("methodology").order_by(
            "methodology__methodology_code",
            "version",
        )


class NationalTargetForm(forms.ModelForm):
    class Meta:
        model = NationalTarget
        fields = [
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
            "source_system",
            "source_ref",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organisation"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )
        self.fields["responsible_org"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )


class ExportPackageForm(forms.ModelForm):
    class Meta:
        model = ExportPackage
        fields = [
            "title",
            "description",
            "reporting_instance",
            "organisation",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reporting_instance"].queryset = ReportingInstance.objects.select_related("cycle").order_by("-created_at")
        self.fields["reporting_instance"].required = True


class ReportingCycleForm(forms.ModelForm):
    class Meta:
        model = ReportingCycle
        fields = [
            "code",
            "title",
            "start_date",
            "end_date",
            "due_date",
            "is_active",
        ]


class ReportingInstanceForm(forms.ModelForm):
    class Meta:
        model = ReportingInstance
        fields = [
            "cycle",
            "version_label",
            "status",
            "notes",
        ]


class ReportSectionResponseForm(forms.Form):
    def __init__(self, *args, template: ReportSectionTemplate, initial_data=None, **kwargs):
        if template is None:
            raise ValueError("template is required")
        self.template = template
        self.initial_data = initial_data or {}
        super().__init__(*args, **kwargs)

        schema = template.schema_json or {}
        fields = schema.get("fields", [])
        if not fields:
            self.fields["response_json"] = forms.JSONField(
                required=False,
                widget=forms.Textarea(attrs={"rows": 10}),
                help_text="Provide a JSON object for this section.",
            )
            if self.initial_data:
                self.fields["response_json"].initial = self.initial_data
            return

        for field in fields:
            key = field.get("key")
            if not key:
                continue
            label = field.get("label") or key.replace("_", " ").title()
            required = bool(field.get("required", False))
            help_text = field.get("help", "")
            self.fields[key] = forms.CharField(
                label=label,
                required=required,
                help_text=help_text,
                widget=forms.Textarea(attrs={"rows": 5}),
            )
            if key in self.initial_data:
                self.fields[key].initial = self.initial_data[key]

    def to_response_json(self):
        if "response_json" in self.fields:
            return self.cleaned_data.get("response_json") or {}
        data = {}
        for key in self.fields:
            data[key] = self.cleaned_data.get(key, "")
        return data


def _filter_evidence_queryset(user, instance):
    evidence_qs = Evidence.objects.all()
    if instance:
        evidence_qs = approved_queryset(instance, Evidence)
    evidence_qs = filter_queryset_for_user(evidence_qs, user)
    if not instance:
        return evidence_qs
    allowed_ids = [
        item.id
        for item in evidence_qs
        if not requires_consent(item) or consent_is_granted(instance, item)
    ]
    return Evidence.objects.filter(id__in=allowed_ids)


def _filter_dataset_releases_queryset(user, instance):
    dataset_qs = Dataset.objects.all()
    if instance:
        dataset_qs = approved_queryset(instance, Dataset)
    dataset_qs = filter_queryset_for_user(dataset_qs, user)
    releases = DatasetRelease.objects.filter(dataset__in=dataset_qs)
    if not instance:
        return releases
    allowed_ids = [
        item.id
        for item in releases
        if not requires_consent(item) or consent_is_granted(instance, item)
    ]
    return DatasetRelease.objects.filter(id__in=allowed_ids)


class SectionIIINationalTargetProgressForm(forms.ModelForm):
    indicator_data_series = forms.ModelMultipleChoiceField(
        queryset=IndicatorDataSeries.objects.none(),
        required=False,
    )
    binary_indicator_responses = forms.ModelMultipleChoiceField(
        queryset=BinaryIndicatorResponse.objects.none(),
        required=False,
    )
    evidence_items = forms.ModelMultipleChoiceField(
        queryset=Evidence.objects.none(),
        required=False,
    )
    dataset_releases = forms.ModelMultipleChoiceField(
        queryset=DatasetRelease.objects.none(),
        required=False,
    )

    class Meta:
        model = SectionIIINationalTargetProgress
        fields = [
            "progress_status",
            "progress_level",
            "summary",
            "actions_taken",
            "outcomes",
            "challenges_and_approaches",
            "effectiveness_examples",
            "sdg_and_other_agreements",
            "support_needed",
            "period_start",
            "period_end",
            "indicator_data_series",
            "binary_indicator_responses",
            "evidence_items",
            "dataset_releases",
        ]

    def __init__(self, *args, user=None, reporting_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        apply_section_help(self, "section_iii")
        if user is None:
            return
        instance = reporting_instance
        self.fields["summary"].label = "Progress summary"
        self.fields["challenges_and_approaches"].label = "Challenges and approaches"
        self.fields["sdg_and_other_agreements"].label = "SDG and other agreements"
        series_qs = indicator_data_series_for_user(user, instance)
        if instance:
            approved_indicators = approved_queryset(instance, Indicator).values_list("id", flat=True)
            series_qs = series_qs.filter(models.Q(indicator_id__in=approved_indicators) | models.Q(indicator__isnull=True))
        self.fields["indicator_data_series"].queryset = series_qs
        self.fields["binary_indicator_responses"].queryset = binary_indicator_responses_for_user(user, instance)
        self.fields["evidence_items"].queryset = _filter_evidence_queryset(user, instance)
        self.fields["dataset_releases"].queryset = _filter_dataset_releases_queryset(user, instance)

    def clean(self):
        cleaned = super().clean()
        if not (cleaned.get("summary") or "").strip():
            self.add_error("summary", "Progress summary is required for Section III.")
        return cleaned


class SectionIVFrameworkTargetProgressForm(forms.ModelForm):
    indicator_data_series = forms.ModelMultipleChoiceField(
        queryset=IndicatorDataSeries.objects.none(),
        required=False,
    )
    binary_indicator_responses = forms.ModelMultipleChoiceField(
        queryset=BinaryIndicatorResponse.objects.none(),
        required=False,
    )
    evidence_items = forms.ModelMultipleChoiceField(
        queryset=Evidence.objects.none(),
        required=False,
    )
    dataset_releases = forms.ModelMultipleChoiceField(
        queryset=DatasetRelease.objects.none(),
        required=False,
    )

    class Meta:
        model = SectionIVFrameworkTargetProgress
        fields = [
            "progress_status",
            "progress_level",
            "summary",
            "actions_taken",
            "outcomes",
            "challenges_and_approaches",
            "effectiveness_examples",
            "sdg_and_other_agreements",
            "support_needed",
            "period_start",
            "period_end",
            "indicator_data_series",
            "binary_indicator_responses",
            "evidence_items",
            "dataset_releases",
        ]

    def __init__(self, *args, user=None, reporting_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        apply_section_help(self, "section_iv_target")
        if user is None:
            return
        instance = reporting_instance
        self.fields["summary"].label = "Progress summary"
        self.fields["challenges_and_approaches"].label = "Challenges and approaches"
        self.fields["sdg_and_other_agreements"].label = "SDG and other agreements"
        series_qs = indicator_data_series_for_user(user, instance)
        if instance:
            approved_indicators = approved_queryset(instance, Indicator).values_list("id", flat=True)
            series_qs = series_qs.filter(models.Q(indicator_id__in=approved_indicators) | models.Q(indicator__isnull=True))
        self.fields["indicator_data_series"].queryset = series_qs
        self.fields["binary_indicator_responses"].queryset = binary_indicator_responses_for_user(user, instance)
        self.fields["evidence_items"].queryset = _filter_evidence_queryset(user, instance)
        self.fields["dataset_releases"].queryset = _filter_dataset_releases_queryset(user, instance)

    def clean(self):
        cleaned = super().clean()
        if not (cleaned.get("summary") or "").strip():
            self.add_error("summary", "Progress summary is required for Section IV targets.")
        return cleaned


STAKEHOLDER_GROUP_CHOICES = [
    ("women", "Women"),
    ("youth", "Youth"),
    ("indigenous_and_local_communities", "Indigenous peoples and local communities"),
    ("private_sector", "Private sector"),
    ("scientific_community", "Scientific community"),
    ("civil_society_organizations", "Civil society organizations"),
    ("local_and_subnational_government", "Local and subnational government"),
    ("other_stakeholders", "Other stakeholders"),
    ("other", "Other"),
]


class SectionIReportContextForm(forms.ModelForm):
    class Meta:
        model = SectionIReportContext
        fields = [
            "reporting_party_name",
            "submission_language",
            "additional_languages",
            "responsible_authorities",
            "contact_name",
            "contact_email",
            "preparation_process",
            "preparation_challenges",
            "acknowledgements",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_section_help(self, "section_i")


class SectionIINBSAPStatusForm(forms.ModelForm):
    stakeholder_groups = forms.MultipleChoiceField(
        choices=STAKEHOLDER_GROUP_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = SectionIINBSAPStatus
        fields = [
            "nbsap_updated_status",
            "nbsap_updated_other_text",
            "nbsap_expected_completion_date",
            "stakeholders_involved",
            "stakeholder_groups",
            "stakeholder_groups_other_text",
            "stakeholder_groups_notes",
            "nbsap_adopted_status",
            "nbsap_adopted_other_text",
            "nbsap_adoption_mechanism",
            "nbsap_expected_adoption_date",
            "monitoring_system_description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_section_help(self, "section_ii")
        self.fields["stakeholder_groups"].choices = STAKEHOLDER_GROUP_CHOICES

        if self.instance and getattr(self.instance, "stakeholder_groups", None):
            self.initial.setdefault("stakeholder_groups", self.instance.stakeholder_groups)


class SectionIVFrameworkGoalProgressForm(forms.ModelForm):
    evidence_items = forms.ModelMultipleChoiceField(
        queryset=Evidence.objects.none(),
        required=False,
    )

    class Meta:
        model = SectionIVFrameworkGoalProgress
        fields = [
            "progress_summary",
            "actions_taken",
            "outcomes",
            "challenges_and_approaches",
            "sdg_and_other_agreements",
            "evidence_items",
        ]

    def __init__(self, *args, user=None, reporting_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        apply_section_help(self, "section_iv_goal")
        if user is None:
            return
        instance = reporting_instance
        self.fields["evidence_items"].queryset = _filter_evidence_queryset(user, instance)


class SectionVConclusionsForm(forms.ModelForm):
    evidence_items = forms.ModelMultipleChoiceField(
        queryset=Evidence.objects.none(),
        required=False,
    )

    class Meta:
        model = SectionVConclusions
        fields = [
            "overall_assessment",
            "decision_15_8_information",
            "decision_15_7_information",
            "decision_15_11_information",
            "plant_conservation_information",
            "additional_notes",
            "evidence_items",
        ]

    def __init__(self, *args, user=None, reporting_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        apply_section_help(self, "section_v")
        if user is None:
            return
        instance = reporting_instance
        self.fields["evidence_items"].queryset = _filter_evidence_queryset(user, instance)
