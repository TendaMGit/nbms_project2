from nbms_app.models import ReportingInstance


def reporting_instance_context(request):
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_staff", False):
        return {}

    instances = ReportingInstance.objects.select_related("cycle").order_by("-created_at")[:20]
    current_uuid = request.session.get("current_reporting_instance_uuid")
    current_instance = None
    if current_uuid:
        current_instance = instances.filter(uuid=current_uuid).first()
        if not current_instance:
            current_instance = ReportingInstance.objects.select_related("cycle").filter(uuid=current_uuid).first()
    return {
        "current_reporting_instance": current_instance,
        "reporting_instances": instances,
        "current_reporting_instance_uuid": current_uuid,
    }
