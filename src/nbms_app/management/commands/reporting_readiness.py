import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from nbms_app.models import Organisation, User
from nbms_app.services.readiness import compute_reporting_readiness


CSV_FIELDS = [
    "indicator_code",
    "indicator_title",
    "has_national_target",
    "has_framework_mapping",
    "has_programme",
    "has_dataset",
    "has_methodology_version",
    "consent_blocked",
    "sensitivity_blocked",
    "missing",
    "blockers",
]


class Command(BaseCommand):
    help = "Compute reporting readiness diagnostics for a reporting instance."

    def add_arguments(self, parser):
        parser.add_argument("--instance", required=True, help="Reporting instance UUID or ID.")
        parser.add_argument(
            "--format",
            choices=["json", "csv"],
            default="json",
            help="Output format (default: json).",
        )
        parser.add_argument("--output", help="Output path; stdout if omitted.")
        parser.add_argument("--scope", choices=["all", "selected"], default="all")
        parser.add_argument(
            "--mode",
            choices=["authoring", "release"],
            default="authoring",
            help="Readiness evaluation mode (default: authoring).",
        )
        parser.add_argument("--user", help="User id, email, or username for ABAC context.")
        parser.add_argument("--org", help="Organisation code for ABAC context (if no user provided).")
        parser.add_argument("--strict", action="store_true", help="Exit with non-zero status if not ready.")

    def handle(self, *args, **options):
        instance_ref = options["instance"]
        output_format = options["format"]
        output_path = options.get("output")
        scope = options["scope"]
        strict = options["strict"]
        mode = options["mode"]
        user = self._resolve_user(options.get("user"), options.get("org"))

        result = compute_reporting_readiness(instance_ref, scope=scope, user=user, mode=mode)

        if output_format == "json":
            payload = json.dumps(result, indent=2)
            if output_path:
                Path(output_path).write_text(payload, encoding="utf-8")
            else:
                self.stdout.write(payload)
        else:
            if output_path:
                handle = Path(output_path).open("w", newline="", encoding="utf-8")
                close_handle = True
            else:
                handle = self.stdout
                close_handle = False

            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
            writer.writeheader()
            for entry in result.get("per_indicator", []):
                flags = entry.get("flags", {})
                writer.writerow(
                    {
                        "indicator_code": entry.get("indicator_code", ""),
                        "indicator_title": entry.get("indicator_title", ""),
                        "has_national_target": str(flags.get("has_national_target", False)),
                        "has_framework_mapping": str(flags.get("has_framework_mapping", False)),
                        "has_programme": str(flags.get("has_monitoring_programme_link", False)),
                        "has_dataset": str(flags.get("has_dataset_catalog_link", False)),
                        "has_methodology_version": str(flags.get("has_methodology_version_link", False)),
                        "consent_blocked": str(flags.get("consent_blocked", False)),
                        "sensitivity_blocked": str(flags.get("sensitivity_blocked", False)),
                        "missing": ";".join(entry.get("missing", [])),
                        "blockers": ";".join(entry.get("blockers", [])),
                    }
                )
            if close_handle:
                handle.close()

        if strict and not result.get("summary", {}).get("overall_ready", False):
            raise CommandError("Reporting instance has blocking readiness gaps.")

    def _resolve_user(self, user_ref, org_code):
        if user_ref:
            user = self._lookup_user(user_ref)
            if not user:
                raise CommandError("User not found for provided --user.")
            return user
        if org_code:
            org = Organisation.objects.filter(org_code=org_code).first()
            if not org:
                raise CommandError("Organisation not found for provided --org.")

            class _OrgUserProxy:
                is_staff = False
                is_superuser = False
                is_authenticated = True

                def __init__(self, organisation_id):
                    self.organisation_id = organisation_id
                    self.id = None
                    self.groups = self._EmptyGroups()

                class _EmptyGroups:
                    def filter(self, **kwargs):
                        return self

                    def exists(self):
                        return False

            return _OrgUserProxy(org.id)
        return None

    def _lookup_user(self, user_ref):
        if user_ref.isdigit():
            return User.objects.filter(pk=int(user_ref)).first()
        return (
            User.objects.filter(email__iexact=user_ref).first()
            or User.objects.filter(username__iexact=user_ref).first()
        )
