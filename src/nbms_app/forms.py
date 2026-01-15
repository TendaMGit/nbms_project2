from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UsernameField
from django.core.exceptions import ValidationError

from nbms_app.models import (
    Dataset,
    Evidence,
    ExportPackage,
    Indicator,
    NationalTarget,
    Organisation,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    User,
)
from nbms_app.roles import get_canonical_groups_queryset


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


class IndicatorForm(forms.ModelForm):
    class Meta:
        model = Indicator
        fields = [
            "code",
            "title",
            "national_target",
            "organisation",
            "sensitivity",
        ]


class NationalTargetForm(forms.ModelForm):
    class Meta:
        model = NationalTarget
        fields = [
            "code",
            "title",
            "description",
            "organisation",
            "sensitivity",
        ]


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
