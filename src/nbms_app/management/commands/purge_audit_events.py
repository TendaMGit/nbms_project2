import re
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from nbms_app.models import AuditEvent


_AGE_RE = re.compile(r"^(?P<value>\d+)(?P<unit>[mhdwy])$")
_UNIT_MAP = {
    "m": "minutes",
    "h": "hours",
    "d": "days",
    "w": "weeks",
    "y": "days",
}


def _parse_age(value):
    match = _AGE_RE.match(value or "")
    if not match:
        raise CommandError("Invalid --older-than value. Use formats like 24m, 12h, 365d, 4w, 2y.")
    number = int(match.group("value"))
    unit = match.group("unit")
    if unit == "y":
        return timedelta(days=number * 365)
    return timedelta(**{_UNIT_MAP[unit]: number})


class Command(BaseCommand):
    help = "Purge AuditEvent rows older than a given age. Default is dry-run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--older-than",
            required=True,
            help="Age threshold (e.g., 24m, 12h, 365d, 4w, 2y).",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually delete rows. Without this flag, the command is dry-run.",
        )

    def handle(self, *args, **options):
        delta = _parse_age(options["older_than"])
        cutoff = timezone.now() - delta

        queryset = AuditEvent.objects.filter(created_at__lt=cutoff)
        summary = (
            queryset.values("event_type")
            .order_by("event_type")
            .annotate(count=Count("id"))
        )

        total = queryset.count()
        if total == 0:
            self.stdout.write("No audit events match the purge criteria.")
            return

        self.stdout.write(f"Audit events older than {options['older_than']} ({cutoff.isoformat()}):")
        for row in summary:
            label = row["event_type"] or "<blank>"
            self.stdout.write(f"- {label}: {row['count']}")
        self.stdout.write(f"Total: {total}")

        if not options["confirm"]:
            self.stdout.write("Dry-run mode: no rows deleted. Use --confirm to delete.")
            return

        with transaction.atomic():
            deleted, _ = queryset.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} audit events."))
