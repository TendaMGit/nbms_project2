import csv
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from nbms_app.services.hl21_1 import compute_hl21_1_gap_analysis


class Command(BaseCommand):
    help = "Compute interim HL21.1 gap analysis for GBF headline indicators."

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="User email or username to run as.")
        parser.add_argument("--instance", help="Reporting instance UUID (optional).")
        parser.add_argument(
            "--scope",
            choices=["selected", "all"],
            help="Scope: selected (instance-based) or all (registry).",
        )
        parser.add_argument(
            "--framework",
            default="GBF",
            help="Framework code to analyze (default: GBF).",
        )
        parser.add_argument(
            "--level",
            default="headline",
            help="Framework indicator level (default: headline).",
        )
        parser.add_argument(
            "--format",
            choices=["json", "csv"],
            default="json",
            help="Output format (default: json).",
        )
        parser.add_argument(
            "--out-dir",
            default="out/hl21_1",
            help="Output directory (default: out/hl21_1).",
        )
        parser.add_argument("--charts", action="store_true", help="Generate PNG charts (requires matplotlib).")
        parser.add_argument("--no-details", action="store_true", help="Suppress mapped indicator details.")

    def handle(self, *args, **options):
        user_value = options["user"]
        instance_uuid = options.get("instance")
        scope = options.get("scope")
        if not scope:
            scope = "selected" if instance_uuid else "all"

        User = get_user_model()
        user = User.objects.filter(email=user_value).first() or User.objects.filter(username=user_value).first()
        if not user:
            raise CommandError(f"User not found for '{user_value}'.")

        instance = None
        if instance_uuid:
            from nbms_app.models import ReportingInstance

            instance = ReportingInstance.objects.filter(uuid=instance_uuid).first()
            if not instance:
                raise CommandError(f"ReportingInstance not found for '{instance_uuid}'.")

        output = compute_hl21_1_gap_analysis(
            user=user,
            instance=instance,
            scope=scope,
            framework_code=options["framework"],
            indicator_level=options["level"],
            include_details=not options["no_details"],
            include_charts_data=options["charts"],
        )

        out_dir = Path(options["out_dir"]).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        if options["format"] == "json":
            summary_path = out_dir / "hl21_1_summary.json"
            with summary_path.open("w", encoding="utf-8") as handle:
                json.dump(output, handle, indent=2, sort_keys=True)
            self.stdout.write(self.style.SUCCESS(f"Wrote {summary_path}"))
        else:
            summary_path = out_dir / "hl21_1_summary.csv"
            summary_row = {
                "framework_code": output["framework_code"],
                "indicator_level": output["indicator_level"],
                "scope": output["scope"],
                "instance_uuid": output.get("instance_uuid") or "",
                "total_headline_indicators": output["summary"]["coverage_only"]["total_headline_indicators"],
                "addressed_count": output["summary"]["coverage_only"]["addressed_count"],
                "not_addressed_count": output["summary"]["coverage_only"]["not_addressed_count"],
                "addressed_pct": output["summary"]["coverage_only"]["addressed_pct"],
                "reportable_count": output["summary"]["coverage_reportability"]["reportable_count"],
                "not_reportable_count": output["summary"]["coverage_reportability"]["not_reportable_count"],
                "reportable_pct": output["summary"]["coverage_reportability"]["reportable_pct"],
            }
            with summary_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(summary_row.keys()))
                writer.writeheader()
                writer.writerow(summary_row)
            self.stdout.write(self.style.SUCCESS(f"Wrote {summary_path}"))

            indicators_path = out_dir / "hl21_1_headline_indicators.csv"
            indicator_fieldnames = [
                "framework_indicator_code",
                "framework_indicator_title",
                "gbf_target_code",
                "status",
                "mapped_national_indicators",
                "notes",
            ]
            with indicators_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=indicator_fieldnames)
                writer.writeheader()
                for item in output["headline_indicators"]:
                    mapped_codes = [entry["code"] for entry in item.get("mapped_national_indicators", [])]
                    notes = ""
                    if item.get("reportable"):
                        sources = ",".join(item.get("reportability_sources") or [])
                        notes = f"reportable:{sources}" if sources else "reportable"
                    writer.writerow(
                        {
                            "framework_indicator_code": item.get("framework_indicator_code") or "",
                            "framework_indicator_title": item.get("framework_indicator_title") or "",
                            "gbf_target_code": item.get("framework_target_code") or "",
                            "status": item.get("status") or "",
                            "mapped_national_indicators": ";".join(mapped_codes),
                            "notes": notes,
                        }
                    )
            self.stdout.write(self.style.SUCCESS(f"Wrote {indicators_path}"))

            by_target_path = out_dir / "hl21_1_by_target.csv"
            by_target_fieldnames = [
                "gbf_target_code",
                "total",
                "addressed",
                "not_addressed",
                "addressed_pct",
                "reportable",
                "not_reportable",
                "reportable_pct",
            ]
            with by_target_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=by_target_fieldnames)
                writer.writeheader()
                for item in output["by_target"]:
                    writer.writerow(
                        {
                            "gbf_target_code": item.get("framework_target_code") or "",
                            "total": item.get("total") or 0,
                            "addressed": item.get("addressed") or 0,
                            "not_addressed": item.get("not_addressed") or 0,
                            "addressed_pct": item.get("addressed_pct") or 0,
                            "reportable": item.get("reportable") or 0,
                            "not_reportable": item.get("not_reportable") or 0,
                            "reportable_pct": item.get("reportable_pct") or 0,
                        }
                    )
            self.stdout.write(self.style.SUCCESS(f"Wrote {by_target_path}"))

        if options["charts"]:
            try:
                import matplotlib.pyplot as plt
            except ImportError as exc:
                raise CommandError(
                    "matplotlib is required for --charts. Install it or rerun without --charts."
                ) from exc

            charts = output.get("charts") or {}
            addressed = charts.get("addressed_vs_not") or {}
            labels = ["addressed", "not_addressed"]
            sizes = [addressed.get("addressed", 0), addressed.get("not_addressed", 0)]
            fig, ax = plt.subplots()
            ax.pie(sizes, labels=labels, autopct="%1.1f%%")
            ax.set_title("HL21.1 addressed vs not addressed")
            pie_path = out_dir / "hl21_1_addressed_pie.png"
            fig.savefig(pie_path, bbox_inches="tight")
            plt.close(fig)
            self.stdout.write(self.style.SUCCESS(f"Wrote {pie_path}"))

            by_target = charts.get("by_target") or []
            if by_target:
                labels = [item.get("framework_target_code") or "" for item in by_target]
                values = [item.get("addressed_pct") or 0 for item in by_target]
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.bar(labels, values)
                ax.set_ylabel("Addressed (%)")
                ax.set_title("HL21.1 addressed % by GBF target")
                ax.set_ylim(0, 100)
                bar_path = out_dir / "hl21_1_by_target_bar.png"
                fig.savefig(bar_path, bbox_inches="tight")
                plt.close(fig)
                self.stdout.write(self.style.SUCCESS(f"Wrote {bar_path}"))
