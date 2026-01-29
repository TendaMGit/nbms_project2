import os
import subprocess

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


def _column_exists(cursor, table, column):
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        [table, column],
    )
    return cursor.fetchone() is not None


def _detect_docker():
    use_docker = os.environ.get("USE_DOCKER", "").lower() in {"1", "true", "yes"}
    if use_docker:
        return True
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return "nbms_postgis" in (result.stdout or "")
    except Exception:
        return False


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
                if not _column_exists(cursor, table, column):
                    issues.append(f"Missing column: {table}.{column}")

        if not issues:
            self.stdout.write(self.style.SUCCESS("No schema drift detected."))
            return

        docker_detected = _detect_docker()
        self.stdout.write(self.style.WARNING("Schema drift detected:"))
        for issue in issues:
            self.stdout.write(f"- {issue}")

        self.stdout.write("")
        self.stdout.write("Safest recovery steps:")
        if docker_detected:
            self.stdout.write("Docker detected:")
            self.stdout.write("  scripts\\infra_down.ps1 -ResetVolumes")
            self.stdout.write("  scripts\\infra_up.ps1")
            self.stdout.write("  python manage.py migrate")
            self.stdout.write("  python manage.py seed_reporting_defaults")
        else:
            self.stdout.write("If you use Docker:")
            self.stdout.write("  scripts\\infra_down.ps1 -ResetVolumes")
            self.stdout.write("  scripts\\infra_up.ps1")
            self.stdout.write("  python manage.py migrate")
            self.stdout.write("  python manage.py seed_reporting_defaults")
            self.stdout.write("")
            self.stdout.write("If you use a local DB:")
            self.stdout.write("  Install PostgreSQL client tools (psql) or use Docker.")
            self.stdout.write("  Then run: python manage.py migrate")
