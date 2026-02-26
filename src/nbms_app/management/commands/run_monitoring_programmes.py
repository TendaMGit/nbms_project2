from django.core.management.base import BaseCommand

from nbms_app.models import User
from nbms_app.services.programme_ops import process_due_programmes


class Command(BaseCommand):
    help = "Process due monitoring programme runs using the programme operations queue."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20, help="Maximum number of due programmes to process.")
        parser.add_argument(
            "--actor",
            type=str,
            default="",
            help="Optional username to attribute audit actions to.",
        )

    def handle(self, *args, **options):
        actor = None
        actor_username = (options.get("actor") or "").strip()
        if actor_username:
            actor = User.objects.filter(username=actor_username).first()
            if not actor:
                self.stdout.write(self.style.WARNING(f"Actor '{actor_username}' not found. Running without actor."))

        runs = process_due_programmes(actor=actor, limit=max(1, int(options["limit"])))
        self.stdout.write(self.style.SUCCESS(f"Processed {len(runs)} programme run(s)."))
        for run in runs:
            self.stdout.write(f"- {run.programme.programme_code} :: {run.uuid} :: {run.status}")
