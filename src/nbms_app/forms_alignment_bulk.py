from django import forms

from nbms_app.models import (
    AlignmentRelationType,
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    IndicatorFrameworkIndicatorLink,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
)


class BulkTargetAlignmentForm(forms.Form):
    national_targets = forms.ModelMultipleChoiceField(queryset=NationalTarget.objects.none())
    framework_targets = forms.ModelMultipleChoiceField(queryset=FrameworkTarget.objects.none())
    relation_type = forms.ChoiceField(choices=AlignmentRelationType.choices)
    confidence = forms.IntegerField(required=False, min_value=0, max_value=100)
    notes = forms.CharField(required=False, widget=forms.Textarea)
    source = forms.URLField(required=False, label="Source citation", assume_scheme="https")

    def __init__(self, *args, targets_queryset=None, framework_targets_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        targets_queryset = targets_queryset if targets_queryset is not None else NationalTarget.objects.none()
        framework_targets_queryset = (
            framework_targets_queryset if framework_targets_queryset is not None else FrameworkTarget.objects.none()
        )
        self.fields["national_targets"].queryset = targets_queryset
        self.fields["framework_targets"].queryset = framework_targets_queryset
        self.fields["national_targets"].label_from_instance = lambda obj: f"{obj.code} - {obj.title}"
        self.fields["framework_targets"].label_from_instance = lambda obj: f"{obj.framework.code} {obj.code} - {obj.title}"


class BulkIndicatorAlignmentForm(forms.Form):
    indicators = forms.ModelMultipleChoiceField(queryset=Indicator.objects.none())
    framework_indicators = forms.ModelMultipleChoiceField(queryset=FrameworkIndicator.objects.none())
    relation_type = forms.ChoiceField(choices=AlignmentRelationType.choices)
    confidence = forms.IntegerField(required=False, min_value=0, max_value=100)
    notes = forms.CharField(required=False, widget=forms.Textarea)
    source = forms.URLField(required=False, label="Source citation", assume_scheme="https")

    def __init__(self, *args, indicators_queryset=None, framework_indicators_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        indicators_queryset = indicators_queryset if indicators_queryset is not None else Indicator.objects.none()
        framework_indicators_queryset = (
            framework_indicators_queryset if framework_indicators_queryset is not None else FrameworkIndicator.objects.none()
        )
        self.fields["indicators"].queryset = indicators_queryset
        self.fields["framework_indicators"].queryset = framework_indicators_queryset
        self.fields["indicators"].label_from_instance = lambda obj: f"{obj.code} - {obj.title}"
        self.fields["framework_indicators"].label_from_instance = lambda obj: f"{obj.framework.code} {obj.code} - {obj.title}"


class BulkTargetLinkRemoveForm(forms.Form):
    links = forms.ModelMultipleChoiceField(queryset=NationalTargetFrameworkTargetLink.objects.none())

    def __init__(self, *args, links_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["links"].queryset = links_queryset if links_queryset is not None else NationalTargetFrameworkTargetLink.objects.none()
        self.fields["links"].label_from_instance = (
            lambda obj: f"{obj.national_target.code} -> {obj.framework_target.framework.code} {obj.framework_target.code}"
        )


class BulkIndicatorLinkRemoveForm(forms.Form):
    links = forms.ModelMultipleChoiceField(queryset=IndicatorFrameworkIndicatorLink.objects.none())

    def __init__(self, *args, links_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["links"].queryset = links_queryset if links_queryset is not None else IndicatorFrameworkIndicatorLink.objects.none()
        self.fields["links"].label_from_instance = (
            lambda obj: f"{obj.indicator.code} -> {obj.framework_indicator.framework.code} {obj.framework_indicator.code}"
        )
