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
]
