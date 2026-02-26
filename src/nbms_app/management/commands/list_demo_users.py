from __future__ import annotations

from django.core.management.base import BaseCommand

from nbms_app.demo_users import list_demo_user_rows, markdown_table


class Command(BaseCommand):
    help = "List currently seeded demo users in markdown table format."

    def handle(self, *args, **options):
        rows = list_demo_user_rows()
        if not rows:
            self.stdout.write("No demo users are present. Run `python manage.py seed_demo_users` first.")
            return
        self.stdout.write(markdown_table(rows))
