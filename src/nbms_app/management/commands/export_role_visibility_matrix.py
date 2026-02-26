from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from nbms_app.demo_users import WARNING_BANNER
from nbms_app.models import User
from nbms_app.role_visibility import UI_SURFACES, demo_role_matrix


class Command(BaseCommand):
    help = "Export role visibility matrix (markdown + csv) for seeded demo users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--markdown",
            default=str(Path("docs") / "ops" / "ROLE_VISIBILITY_MATRIX.md"),
            help="Markdown output path.",
        )
        parser.add_argument(
            "--csv",
            default=str(Path("docs") / "ops" / "ROLE_VISIBILITY_MATRIX.csv"),
            help="CSV output path.",
        )

    def handle(self, *args, **options):
        users = {user.username: user for user in User.objects.all().select_related("organisation").prefetch_related("groups")}
        rows = demo_role_matrix(users)
        if not rows:
            self.stdout.write("No seeded demo users found; run `python manage.py seed_demo_users` first.")
            return

        md_path = Path(options["markdown"])
        if not md_path.is_absolute():
            md_path = Path(settings.BASE_DIR) / md_path
        csv_path = Path(options["csv"])
        if not csv_path.is_absolute():
            csv_path = Path(settings.BASE_DIR) / csv_path
        md_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        md_lines = [
            f"# ROLE VISIBILITY MATRIX ({WARNING_BANNER})",
            "",
            "Generated from code registries:",
            "- `src/nbms_app/demo_users.py`",
            "- `src/nbms_app/role_visibility.py`",
            "",
            "## Surfaces",
            "",
            "| label | route | capability | public |",
            "|---|---|---|---|",
        ]
        for surface in UI_SURFACES:
            md_lines.append(
                f"| {surface.label} | {surface.route} | {surface.capability or ''} | {'yes' if surface.public else 'no'} |"
            )

        md_lines.extend(
            [
                "",
                "## Role Matrix",
                "",
                "| username | org | groups | staff? | superuser? | visible_routes |",
                "|---|---|---|---|---|---|",
            ]
        )
        for row in rows:
            md_lines.append(
                f"| {row['username']} | {row['org_code']} | {row['groups']} | {row['is_staff']} | {row['is_superuser']} | {row['visible_routes']} |"
            )
        md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

        csv_lines = ["username,org_code,groups,is_staff,is_superuser,visible_routes"]
        for row in rows:
            csv_lines.append(
                ",".join(
                    [
                        row["username"],
                        row["org_code"],
                        row["groups"].replace(",", ";"),
                        row["is_staff"],
                        row["is_superuser"],
                        row["visible_routes"].replace(",", ";"),
                    ]
                )
            )
        csv_path.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Wrote {md_path} and {csv_path}"))
