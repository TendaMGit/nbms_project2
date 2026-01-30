import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from nbms_app.models import ReportingInstance, User
from nbms_app.services.alignment_coverage import compute_alignment_coverage


def _expand_framework_codes(values):
    if not values:
        return []
    codes = []
    for entry in values:
        if not entry:
            continue
        for part in str(entry).split(","):
            part = part.strip()
            if part:
                codes.append(part)
    return codes


class Command(BaseCommand):
    help = "Compute alignment coverage for a reporting instance."

    def add_arguments(self, parser):
        parser.add_argument("--instance", required=True, help="Reporting instance UUID.")
        parser.add_argument("--scope", choices=["selected", "all"], default="selected")
        parser.add_argument("--format", choices=["json", "csv"], default="json")
        parser.add_argument("--framework", action="append", help="Limit to framework code(s).")
        parser.add_argument("--no-details", action="store_true", help="Skip coverage details.")
        parser.add_argument("--output-dir", help="Write CSV files to this directory.")
        parser.add_argument("--user", help="Username to run coverage as (ABAC).")

    def handle(self, *args, **options):
        instance_uuid = options["instance"]
        scope = options["scope"]
        output_format = options["format"]
        framework_codes = _expand_framework_codes(options.get("framework"))
        include_details = not options.get("no_details")
        output_dir = options.get("output_dir")

        instance = ReportingInstance.objects.filter(uuid=instance_uuid).first()
        if not instance:
            raise CommandError("Reporting instance not found.")

        user = None
        username = options.get("user")
        if username:
            user = User.objects.filter(username=username).first()
            if not user:
                raise CommandError("User not found.")

        coverage = compute_alignment_coverage(
            user=user,
            instance=instance,
            scope=scope,
            framework_codes=framework_codes,
            include_details=include_details,
        )

        if output_format == "json":
            payload = json.dumps(coverage, indent=2, sort_keys=True)
            self.stdout.write(payload)
            return

        self._write_csv(coverage, output_dir, include_details)

    def _write_csv(self, coverage, output_dir, include_details):
        if output_dir:
            base = Path(output_dir)
            base.mkdir(parents=True, exist_ok=True)
            self._write_summary_csv(base / "summary.csv", coverage)
            self._write_orphans_csv(
                base / "orphans_national_targets.csv",
                coverage["orphans"]["national_targets_unmapped"],
            )
            self._write_orphans_csv(
                base / "orphans_indicators.csv",
                coverage["orphans"]["indicators_unmapped"],
            )
            if include_details:
                self._write_details_csv(
                    base / "details_national_targets.csv",
                    coverage["coverage_details"]["national_targets"],
                    link_key="linked_framework_targets",
                )
                self._write_details_csv(
                    base / "details_indicators.csv",
                    coverage["coverage_details"]["indicators"],
                    link_key="linked_framework_indicators",
                )
            self.stdout.write(self.style.SUCCESS(f"CSV files written to {base}"))
            return

        writer = csv.writer(self.stdout)
        writer.writerow(["# summary"])
        self._write_summary_csv(writer, coverage)
        writer.writerow([])
        writer.writerow(["# orphans_national_targets"])
        self._write_orphans_csv(writer, coverage["orphans"]["national_targets_unmapped"])
        writer.writerow([])
        writer.writerow(["# orphans_indicators"])
        self._write_orphans_csv(writer, coverage["orphans"]["indicators_unmapped"])
        if include_details:
            writer.writerow([])
            writer.writerow(["# details_national_targets"])
            self._write_details_csv(writer, coverage["coverage_details"]["national_targets"], "linked_framework_targets")
            writer.writerow([])
            writer.writerow(["# details_indicators"])
            self._write_details_csv(writer, coverage["coverage_details"]["indicators"], "linked_framework_indicators")

    def _write_summary_csv(self, target, coverage):
        headers = [
            "instance_uuid",
            "scope",
            "targets_total",
            "targets_mapped",
            "targets_unmapped",
            "targets_pct_mapped",
            "indicators_total",
            "indicators_mapped",
            "indicators_unmapped",
            "indicators_pct_mapped",
        ]
        row = [
            coverage["instance_uuid"],
            coverage["scope"],
            coverage["summary"]["national_targets"]["total"],
            coverage["summary"]["national_targets"]["mapped"],
            coverage["summary"]["national_targets"]["unmapped"],
            coverage["summary"]["national_targets"]["pct_mapped"],
            coverage["summary"]["indicators"]["total"],
            coverage["summary"]["indicators"]["mapped"],
            coverage["summary"]["indicators"]["unmapped"],
            coverage["summary"]["indicators"]["pct_mapped"],
        ]

        if hasattr(target, "write"):
            writer = csv.writer(target)
            writer.writerow(headers)
            writer.writerow(row)
        else:
            with Path(target).open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                writer.writerow(row)

    def _write_orphans_csv(self, target, rows):
        headers = ["uuid", "code", "title"]
        if hasattr(target, "write"):
            writer = csv.writer(target)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([row.get("uuid"), row.get("code"), row.get("title")])
        else:
            with Path(target).open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                for row in rows:
                    writer.writerow([row.get("uuid"), row.get("code"), row.get("title")])

    def _write_details_csv(self, target, rows, link_key):
        headers = ["uuid", "code", "title", "mapped", "linked_codes"]
        if hasattr(target, "write"):
            writer = csv.writer(target)
            writer.writerow(headers)
            for row in rows:
                linked = row.get(link_key) or []
                linked_codes = ";".join(
                    f"{item.get('framework_code')}:{item.get('code')}" for item in linked
                )
                writer.writerow([row.get("uuid"), row.get("code"), row.get("title"), row.get("mapped"), linked_codes])
        else:
            with Path(target).open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                for row in rows:
                    linked = row.get(link_key) or []
                    linked_codes = ";".join(
                        f"{item.get('framework_code')}:{item.get('code')}" for item in linked
                    )
                    writer.writerow(
                        [row.get("uuid"), row.get("code"), row.get("title"), row.get("mapped"), linked_codes]
                    )
