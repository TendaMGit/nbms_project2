from django import forms
from django.contrib.auth.forms import UsernameField
from django.core.exceptions import ValidationError

from nbms_app.models import Organisation, User
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
