from nbms_app.models import Notification
from nbms_app.services.metrics import inc_counter


def create_notification(recipient, message, url=""):
    if not recipient:
        return None
    notification = Notification.objects.create(recipient=recipient, message=message, url=url)
    inc_counter("notifications_created_total")
    return notification
