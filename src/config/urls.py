from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from two_factor.urls import urlpatterns as tf_urls

from nbms_app.api import api_router

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include((tf_urls[0], tf_urls[1]), namespace=tf_urls[1])),
    path("", include("nbms_app.urls")),
    path("api/", include("nbms_app.api_urls")),
    path("api/v1/", include(api_router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
