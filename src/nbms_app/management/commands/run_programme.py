from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from nbms_app.models import MonitoringProgramme, ProgrammeRunType, User
from nbms_app.services.programme_ops import queue_programme_run


class Command(BaseCommand):
    help = "Queue or execute a monitoring programme run by programme code."

    def add_arguments(self, parser):
        parser.add_argument("--programme-code", required=True, help="MonitoringProgramme.programme_code")
        parser.add_argument("--run-type", default=ProgrammeRunType.FULL, choices=ProgrammeRunType.values)
        parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode.")
        parser.add_argument("--queue-only", action="store_true", help="Queue run without immediate execution.")
        parser.add_argument("--actor", default="", help="Optional actor username for audit attribution.")

    def handle(self, *args, **options):
        code = (options.get("programme_code") or "").strip()
        programme = MonitoringProgramme.objects.filter(programme_code=code, is_active=True).first()
        if not programme:
            raise CommandError(f"Active programme not found: {code}")

        actor = None
        actor_name = (options.get("actor") or "").strip()
        if actor_name:
            actor = User.objects.filter(username=actor_name).first()
            if not actor:
                self.stdout.write(self.style.WARNING(f"Actor '{actor_name}' not found; run attributed to system."))

        run = queue_programme_run(
            programme=programme,
            requested_by=actor,
            run_type=(options.get("run_type") or ProgrammeRunType.FULL),
            dry_run=bool(options.get("dry_run")),
            execute_now=not bool(options.get("queue_only")),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"programme={programme.programme_code} run_uuid={run.uuid} status={run.status} dry_run={run.dry_run}"
            )
        )
