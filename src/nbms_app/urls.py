from django.urls import path

from nbms_app import views

app_name = "nbms_app"

urlpatterns = [
    path("", views.home, name="home"),
]
