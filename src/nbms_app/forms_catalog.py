from django import forms

from nbms_app.models import (
    Framework,
    FrameworkGoal,
    FrameworkIndicator,
    FrameworkTarget,
    LifecycleStatus,
    Organisation,
)
from nbms_app.services.authorization import filter_queryset_for_user
from nbms_app.services.catalog_access import filter_organisations_for_user


FRAMEWORK_READONLY_FIELDS = ("uuid", "created_by", "created_at", "updated_at")
FRAMEWORK_GOAL_READONLY_FIELDS = ("uuid", "created_by", "created_at", "updated_at")
FRAMEWORK_TARGET_READONLY_FIELDS = ("uuid", "created_by", "created_at", "updated_at")
FRAMEWORK_INDICATOR_READONLY_FIELDS = ("uuid", "created_by", "created_at", "updated_at")

CATALOG_READONLY_FIELDS = {
    Framework: FRAMEWORK_READONLY_FIELDS,
    FrameworkGoal: FRAMEWORK_GOAL_READONLY_FIELDS,
    FrameworkTarget: FRAMEWORK_TARGET_READONLY_FIELDS,
    FrameworkIndicator: FRAMEWORK_INDICATOR_READONLY_FIELDS,
}


def get_catalog_readonly_fields(model):
    return CATALOG_READONLY_FIELDS.get(model, ())


def build_readonly_panel(instance, field_names):
    readonly = []
    if not instance:
        return readonly
    for name in field_names:
        label = name.replace("_", " ").title()
        try:
            label = instance._meta.get_field(name).verbose_name
        except Exception:  # noqa: BLE001
            pass
        value = getattr(instance, name, None)
        readonly.append(
            {
                "name": name,
                "label": label,
                "value": value if value not in (None, "") else "-",
            }
        )
    return readonly


class FrameworkCatalogForm(forms.ModelForm):
    class Meta:
        model = Framework
        fields = [
            "code",
            "title",
            "description",
            "organisation",
            "status",
            "sensitivity",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organisation"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )


class FrameworkGoalCatalogForm(forms.ModelForm):
    class Meta:
        model = FrameworkGoal
        fields = [
            "framework",
            "code",
            "title",
            "official_text",
            "description",
            "sort_order",
            "organisation",
            "status",
            "sensitivity",
            "review_note",
            "source_system",
            "source_ref",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["framework"].queryset = filter_queryset_for_user(
            Framework.objects.order_by("code"),
            user,
            perm="nbms_app.view_framework",
        )
        self.fields["organisation"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )


class FrameworkTargetCatalogForm(forms.ModelForm):
    class Meta:
        model = FrameworkTarget
        fields = [
            "framework",
            "goal",
            "code",
            "title",
            "official_text",
            "description",
            "organisation",
            "status",
            "sensitivity",
            "source_system",
            "source_ref",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        frameworks = filter_queryset_for_user(
            Framework.objects.order_by("code"),
            user,
            perm="nbms_app.view_framework",
        )
        framework_ids = list(frameworks.values_list("id", flat=True))
        self.fields["framework"].queryset = frameworks
        self.fields["organisation"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )
        goal_qs = FrameworkGoal.objects.filter(framework_id__in=framework_ids).exclude(
            status=LifecycleStatus.ARCHIVED
        )
        framework_id = self.data.get("framework") or getattr(self.instance, "framework_id", None)
        if framework_id:
            goal_qs = goal_qs.filter(framework_id=framework_id)
        self.fields["goal"].queryset = goal_qs.order_by("framework__code", "sort_order", "code")


class FrameworkIndicatorCatalogForm(forms.ModelForm):
    class Meta:
        model = FrameworkIndicator
        fields = [
            "framework",
            "framework_target",
            "code",
            "title",
            "description",
            "indicator_type",
            "organisation",
            "status",
            "sensitivity",
            "source_system",
            "source_ref",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        frameworks = filter_queryset_for_user(
            Framework.objects.order_by("code"),
            user,
            perm="nbms_app.view_framework",
        )
        framework_ids = list(frameworks.values_list("id", flat=True))
        self.fields["framework"].queryset = frameworks
        self.fields["organisation"].queryset = filter_organisations_for_user(
            Organisation.objects.order_by("name"), user
        )
        target_qs = filter_queryset_for_user(
            FrameworkTarget.objects.select_related("framework").order_by("framework__code", "code"),
            user,
            perm="nbms_app.view_frameworktarget",
        )
        if framework_ids:
            target_qs = target_qs.filter(framework_id__in=framework_ids)
        framework_id = self.data.get("framework") or getattr(self.instance, "framework_id", None)
        if framework_id:
            target_qs = target_qs.filter(framework_id=framework_id)
        self.fields["framework_target"].queryset = target_qs
