from django.apps import AppConfig


class NbmsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nbms_app"

    def ready(self):
        import nbms_app.signals  # noqa: F401
        import nbms_app.signals_audit  # noqa: F401
