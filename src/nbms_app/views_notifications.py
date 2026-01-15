from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from nbms_app.models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by("-created_at")
    return render(request, "nbms_app/notifications.html", {"notifications": notifications})
