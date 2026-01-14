import logging

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import connections
from django.http import JsonResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def home(request):
    return render(request, "nbms_app/home.html")


def health_db(request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:  # noqa: BLE001
        logger.exception("Database health check failed.")
        return JsonResponse({"status": "error"}, status=503)


def health_storage(request):
    if not getattr(settings, "USE_S3", False):
        return JsonResponse({"status": "disabled", "detail": "USE_S3=0"})

    try:
        default_storage.listdir("")
        return JsonResponse({"status": "ok"})
    except Exception:  # noqa: BLE001
        logger.exception("Storage health check failed.")
        return JsonResponse({"status": "error"}, status=503)
