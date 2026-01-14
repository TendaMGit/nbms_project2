from django.urls import path

from nbms_app import views

app_name = "nbms_app"

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health_db, name="health_db"),
    path("health/storage/", views.health_storage, name="health_storage"),
]
