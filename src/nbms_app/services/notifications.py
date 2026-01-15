from nbms_app.models import Notification


def create_notification(recipient, message, url=""):
    if not recipient:
        return None
    return Notification.objects.create(recipient=recipient, message=message, url=url)
