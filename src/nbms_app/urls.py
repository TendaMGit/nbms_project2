from django.urls import path

from nbms_app import views
from nbms_app import views_audit
from nbms_app import views_metrics
from nbms_app import views_notifications

app_name = "nbms_app"

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health_db, name="health_db"),
    path("health/storage/", views.health_storage, name="health_storage"),
    path("manage/organisations/", views.manage_organisation_list, name="manage_organisation_list"),
    path("manage/organisations/new/", views.manage_organisation_create, name="manage_organisation_create"),
    path("manage/organisations/<int:org_id>/edit/", views.manage_organisation_edit, name="manage_organisation_edit"),
    path("manage/users/", views.manage_user_list, name="manage_user_list"),
    path("manage/users/new/", views.manage_user_create, name="manage_user_create"),
    path("manage/users/<int:user_id>/edit/", views.manage_user_edit, name="manage_user_edit"),
    path("manage/users/<int:user_id>/send-reset/", views.manage_user_send_reset, name="manage_user_send_reset"),
    path("national-targets/", views.national_target_list, name="national_target_list"),
    path("national-targets/new/", views.national_target_create, name="national_target_create"),
    path("national-targets/<uuid:target_uuid>/", views.national_target_detail, name="national_target_detail"),
    path("national-targets/<uuid:target_uuid>/edit/", views.national_target_edit, name="national_target_edit"),
    path("indicators/", views.indicator_list, name="indicator_list"),
    path("indicators/new/", views.indicator_create, name="indicator_create"),
    path("indicators/<uuid:indicator_uuid>/", views.indicator_detail, name="indicator_detail"),
    path("indicators/<uuid:indicator_uuid>/edit/", views.indicator_edit, name="indicator_edit"),
    path("evidence/", views.evidence_list, name="evidence_list"),
    path("evidence/new/", views.evidence_create, name="evidence_create"),
    path("evidence/<uuid:evidence_uuid>/", views.evidence_detail, name="evidence_detail"),
    path("evidence/<uuid:evidence_uuid>/edit/", views.evidence_edit, name="evidence_edit"),
    path("datasets/", views.dataset_list, name="dataset_list"),
    path("datasets/new/", views.dataset_create, name="dataset_create"),
    path("datasets/<uuid:dataset_uuid>/", views.dataset_detail, name="dataset_detail"),
    path("datasets/<uuid:dataset_uuid>/edit/", views.dataset_edit, name="dataset_edit"),
    path("exports/", views.export_package_list, name="export_package_list"),
    path("exports/new/", views.export_package_create, name="export_package_create"),
    path("exports/<uuid:package_uuid>/", views.export_package_detail, name="export_package_detail"),
    path(
        "exports/<uuid:package_uuid>/download/",
        views.export_package_download,
        name="export_package_download",
    ),
    path(
        "exports/instances/<uuid:instance_uuid>/ort-nr7-narrative.json",
        views.export_ort_nr7_narrative_instance,
        name="export_ort_nr7_narrative_instance",
    ),
    path(
        "exports/instances/<uuid:instance_uuid>/ort-nr7-v2.json",
        views.export_ort_nr7_v2_instance,
        name="export_ort_nr7_v2_instance",
    ),
    path(
        "exports/<uuid:package_uuid>/<str:action>/",
        views.export_package_action,
        name="export_package_action",
    ),
    path("reporting/cycles/", views.reporting_cycle_list, name="reporting_cycle_list"),
    path("reporting/cycles/new/", views.reporting_cycle_create, name="reporting_cycle_create"),
    path("reporting/cycles/<uuid:cycle_uuid>/", views.reporting_cycle_detail, name="reporting_cycle_detail"),
    path("reporting/instances/new/", views.reporting_instance_create, name="reporting_instance_create"),
    path(
        "reporting/instances/<uuid:instance_uuid>/",
        views.reporting_instance_detail,
        name="reporting_instance_detail",
    ),
    path(
        "reporting/set-current/<uuid:instance_uuid>/",
        views.reporting_set_current_instance,
        name="reporting_set_current_instance",
    ),
    path(
        "reporting/clear-current/",
        views.reporting_clear_current_instance,
        name="reporting_clear_current_instance",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/sections/",
        views.reporting_instance_sections,
        name="reporting_instance_sections",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/sections/<str:section_code>/edit/",
        views.reporting_instance_section_edit,
        name="reporting_instance_section_edit",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/sections/<str:section_code>/preview/",
        views.reporting_instance_section_preview,
        name="reporting_instance_section_preview",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/section-iii/",
        views.reporting_instance_section_iii,
        name="reporting_instance_section_iii",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/section-iii/<uuid:target_uuid>/",
        views.reporting_instance_section_iii_edit,
        name="reporting_instance_section_iii_edit",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/section-iv/",
        views.reporting_instance_section_iv,
        name="reporting_instance_section_iv",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/section-iv/<uuid:framework_target_uuid>/",
        views.reporting_instance_section_iv_edit,
        name="reporting_instance_section_iv_edit",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/approvals/",
        views.reporting_instance_approvals,
        name="reporting_instance_approvals",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/approvals/bulk/",
        views.reporting_instance_approval_bulk,
        name="reporting_instance_approval_bulk",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/approvals/<str:obj_type>/<uuid:obj_uuid>/<str:action>/",
        views.reporting_instance_approval_action,
        name="reporting_instance_approval_action",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/consent/",
        views.reporting_instance_consent,
        name="reporting_instance_consent",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/consent/<str:obj_type>/<uuid:obj_uuid>/<str:action>/",
        views.reporting_instance_consent_action,
        name="reporting_instance_consent_action",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/freeze/",
        views.reporting_instance_freeze,
        name="reporting_instance_freeze",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/report-pack/",
        views.reporting_instance_report_pack,
        name="reporting_instance_report_pack",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/review/",
        views.reporting_instance_review,
        name="reporting_instance_review",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/review-pack-v2/",
        views.reporting_instance_review_pack_v2,
        name="reporting_instance_review_pack_v2",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/review-decisions/",
        views.reporting_instance_review_decisions,
        name="reporting_instance_review_decisions",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/review-decisions/create/",
        views.reporting_instance_review_decision_create,
        name="reporting_instance_review_decision_create",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/snapshots/",
        views.reporting_instance_snapshots,
        name="reporting_instance_snapshots",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/snapshots/create/",
        views.reporting_instance_snapshot_create,
        name="reporting_instance_snapshot_create",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/snapshots/diff/",
        views.reporting_instance_snapshot_diff,
        name="reporting_instance_snapshot_diff",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/snapshots/<uuid:snapshot_uuid>/",
        views.reporting_instance_snapshot_detail,
        name="reporting_instance_snapshot_detail",
    ),
    path(
        "reporting/instances/<uuid:instance_uuid>/snapshots/<uuid:snapshot_uuid>/download.json",
        views.reporting_instance_snapshot_download,
        name="reporting_instance_snapshot_download",
    ),
    path("manage/review-queue/", views.review_queue, name="review_queue"),
    path("manage/review-queue/<str:obj_type>/<uuid:obj_uuid>/", views.review_detail, name="review_detail"),
    path(
        "manage/review-queue/<str:obj_type>/<uuid:obj_uuid>/<str:action>/",
        views.review_action,
        name="review_action",
    ),
    path("manage/audit-events/", views_audit.audit_event_list, name="audit_event_list"),
    path("notifications/", views_notifications.notification_list, name="notification_list"),
    path("metrics/", views_metrics.metrics, name="metrics"),
]
