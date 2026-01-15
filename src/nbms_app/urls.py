from django.urls import path

from nbms_app import views

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
]
