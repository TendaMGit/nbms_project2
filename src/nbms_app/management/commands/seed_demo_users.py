from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from nbms_app.demo_users import markdown_table, seed_demo_user_pack, write_demo_users_markdown


def _truthy(value: str):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Command(BaseCommand):
    help = "Seed local demo users for major roles (strictly gated to dev/test)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=str(Path("docs") / "ops" / "DEMO_USERS.md"),
            help="Output markdown path for generated demo user table.",
        )

    def handle(self, *args, **options):
        env_name = str(getattr(settings, "ENVIRONMENT", "")).lower()
        dev_runtime = bool(getattr(settings, "DEBUG", False)) or env_name in {"dev", "test"}
        if not dev_runtime:
            raise CommandError("seed_demo_users is disabled outside DEBUG/dev/test runtime.")

        if not _truthy(os.environ.get("SEED_DEMO_USERS", "0")):
            raise CommandError("seed_demo_users requires SEED_DEMO_USERS=1.")
        if not _truthy(os.environ.get("ALLOW_INSECURE_DEMO_PASSWORDS", "0")):
            raise CommandError("seed_demo_users requires ALLOW_INSECURE_DEMO_PASSWORDS=1.")

        rows = seed_demo_user_pack(allow_insecure_passwords=True)
        output_path = Path(options["output"])
        if not output_path.is_absolute():
            output_path = Path(settings.BASE_DIR) / output_path
        write_demo_users_markdown(output_path, rows)

        self.stdout.write(self.style.SUCCESS(f"Seeded demo users ({len(rows)} rows)."))
        self.stdout.write(markdown_table(rows))
        self.stdout.write(f"Wrote {output_path}")
