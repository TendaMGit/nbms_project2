import os

from django.core.management.base import BaseCommand, CommandError

from nbms_app.services.analytics_schema import ANALYTICS_SCHEMA, grant_superset_read_only


class Command(BaseCommand):
    help = "Ensure the read-only Superset role can only query the analytics schema."

    def add_arguments(self, parser):
        parser.add_argument("--role-name", default="superset_ro")
        parser.add_argument("--password-env", default="SUPERSET_NBMS_RO_PASSWORD")

    def handle(self, *args, **options):
        password_env = options["password_env"]
        password = os.getenv(password_env, "").strip()
        if not password:
            raise CommandError(f"Environment variable '{password_env}' must be set before creating the Superset read-only role.")

        grant_superset_read_only(role_name=options["role_name"], password=password)
        self.stdout.write(
            self.style.SUCCESS(
                f"Ensured role '{options['role_name']}' has CONNECT plus SELECT on schema '{ANALYTICS_SCHEMA}' only."
            )
        )
