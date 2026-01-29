from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = "Diagnose schema drift and provide recovery guidance."

    def handle(self, *args, **options):
        issues = []
        loader = MigrationLoader(connection)
        recorder = MigrationRecorder(connection)

        latest = loader.graph.leaf_nodes("nbms_app")
        applied = set(recorder.applied_migrations())
        for app_label, name in latest:
            if (app_label, name) not in applied:
                issues.append(f"Missing migration: {app_label}.{name}")

        drift_checks = [
            ("nbms_app_nationaltarget", "responsible_org_id"),
            ("nbms_app_auditevent", "event_type"),
        ]

        with connection.cursor() as cursor:
            for table, column in drift_checks:
                cursor.execute(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = %s AND column_name = %s
                    """,
                    [table, column],
                )
                if cursor.fetchone() is None:
                    issues.append(f"Missing column: {table}.{column}")

        if not issues:
            self.stdout.write(self.style.SUCCESS("No schema drift detected."))
            return

        self.stdout.write(self.style.WARNING("Schema drift detected:"))
        for issue in issues:
            self.stdout.write(f"- {issue}")

        self.stdout.write("")
        self.stdout.write("Safest recovery steps:")
        self.stdout.write("If you use Docker:")
        self.stdout.write("  scripts\\infra_down.ps1 -Volumes")
        self.stdout.write("  scripts\\infra_up.ps1")
        self.stdout.write("  python manage.py migrate")
        self.stdout.write("  python manage.py seed_reporting_defaults")
        self.stdout.write("")
        self.stdout.write("If you use a local DB:")
        self.stdout.write("  Install PostgreSQL client tools (psql) or use Docker.")
        self.stdout.write("  Then run: python manage.py migrate")
