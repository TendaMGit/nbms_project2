from django.urls import path

from nbms_app import api_spa


urlpatterns = [
    path("auth/me", api_spa.api_auth_me, name="api_auth_me"),
    path("auth/csrf", api_spa.api_auth_csrf, name="api_auth_csrf"),
    path("help/sections", api_spa.api_help_sections, name="api_help_sections"),
    path("system/health", api_spa.api_system_health, name="api_system_health"),
    path("dashboard/summary", api_spa.api_dashboard_summary, name="api_dashboard_summary"),
    path("indicators", api_spa.api_indicator_list, name="api_indicator_list"),
    path("indicators/<uuid:indicator_uuid>", api_spa.api_indicator_detail, name="api_indicator_detail"),
    path(
        "indicators/<uuid:indicator_uuid>/datasets",
        api_spa.api_indicator_datasets,
        name="api_indicator_datasets",
    ),
    path(
        "indicators/<uuid:indicator_uuid>/series",
        api_spa.api_indicator_series_summary,
        name="api_indicator_series_summary",
    ),
    path(
        "indicators/<uuid:indicator_uuid>/validation",
        api_spa.api_indicator_validation,
        name="api_indicator_validation",
    ),
    path(
        "indicators/<uuid:indicator_uuid>/transition",
        api_spa.api_indicator_transition,
        name="api_indicator_transition",
    ),
    path("spatial/layers", api_spa.api_spatial_layers, name="api_spatial_layers"),
    path(
        "spatial/layers/<slug:slug>/features",
        api_spa.api_spatial_layer_features,
        name="api_spatial_layer_features",
    ),
    path("template-packs", api_spa.api_template_pack_list, name="api_template_pack_list"),
    path(
        "template-packs/<str:pack_code>/sections",
        api_spa.api_template_pack_sections,
        name="api_template_pack_sections",
    ),
    path(
        "template-packs/<str:pack_code>/instances/<uuid:instance_uuid>/responses",
        api_spa.api_template_pack_instance_responses,
        name="api_template_pack_instance_responses",
    ),
    path(
        "template-packs/<str:pack_code>/instances/<uuid:instance_uuid>/export",
        api_spa.api_template_pack_export,
        name="api_template_pack_export",
    ),
]
