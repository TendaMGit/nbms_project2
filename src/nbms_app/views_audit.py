from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from nbms_app.models import AuditEvent


@staff_member_required
def audit_event_list(request):
    events = AuditEvent.objects.select_related("actor").order_by("-created_at")[:200]
    return render(request, "nbms_app/manage/audit_events.html", {"events": events})
