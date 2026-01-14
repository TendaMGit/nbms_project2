from django import forms

from nbms_app.models import Organisation


class OrganisationForm(forms.ModelForm):
    class Meta:
        model = Organisation
        fields = ["name", "org_type", "contact_email", "is_active"]
