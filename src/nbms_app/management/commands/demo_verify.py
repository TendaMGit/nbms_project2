import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from django.core.management import BaseCommand, CommandError

from nbms_app.demo_constants import (
    DEMO_ADMIN_USERNAME,
    DEMO_EXPORT_TIME,
    DEMO_INDICATORS,
    DEMO_INSTANCE_UUID,
    DEMO_NATIONAL_TARGETS,
    DEMO_DATASET_UUID,
    DEMO_EVIDENCE_IPLC_UUID,
    DEMO_EVIDENCE_PUBLIC_UUID,
)
from nbms_app.exports.ort_nr7_v2 import build_ort_nr7_v2_payload
from nbms_app.models import ReportingInstance, User
from nbms_app.services.consent import requires_consent, set_consent_status
from nbms_app.services.instance_approvals import approve_for_instance
from nbms_app.services.readiness import get_instance_readiness
from nbms_app.services.review import build_review_pack_context


class Command(BaseCommand):
    help = "Verify deterministic demo seed outputs."

    def add_arguments(self, parser):
        parser.add_argument("--instance", help="ReportingInstance UUID (defaults to demo instance).")
        parser.add_argument(
            "--output-dir",
            default="docs/demo/golden",
            help="Directory to write demo export outputs.",
        )
        parser.add_argument("--approve-all", action="store_true", help="Approve all demo objects.")
        parser.add_argument("--grant-consent", action="store_true", help="Grant consent for IPLC demo objects.")
        parser.add_argument(
            "--resolve-blockers",
            action="store_true",
            help="Shortcut: approve all demo objects and grant consent.",
        )
        parser.add_argument("--strict", action="store_true", help="Exit non-zero if export is blocked.")

    def handle(self, *args, **options):
        instance_uuid = options.get("instance") or str(DEMO_INSTANCE_UUID)
        output_dir = Path(options.get("output_dir") or "docs/demo/golden")
        approve_all = options.get("approve_all")
        grant_consent = options.get("grant_consent")
        strict = options.get("strict")
        if options.get("resolve_blockers"):
            approve_all = True
            grant_consent = True

        instance = ReportingInstance.objects.select_related("cycle").filter(uuid=instance_uuid).first()
        if not instance:
            raise CommandError(f"ReportingInstance not found: {instance_uuid}")

        user = User.objects.filter(username=DEMO_ADMIN_USERNAME).first()
        if not user:
            raise CommandError(f"Demo admin user not found: {DEMO_ADMIN_USERNAME}")

        if approve_all:
            self._approve_all(instance, user)
        if grant_consent:
            self._grant_all_consent(instance, user)

        readiness = get_instance_readiness(instance, user)
        approvals = readiness["details"]["approvals"]
        consent = readiness["details"]["consent"]
        missing_consents = readiness["counts"]["missing_consents"]
        self.stdout.write(
            "Readiness summary: "
            f"targets approved {approvals['targets']['approved']}/{approvals['targets']['total']}, "
            f"indicators approved {approvals['indicators']['approved']}/{approvals['indicators']['total']}, "
            f"missing consents {missing_consents}"
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        export_path = output_dir / "demo_ort_nr7_v2.json"
        order_path = output_dir / "review_pack_order.json"

        payload = None
        try:
            with patch("nbms_app.exports.ort_nr7_v2.timezone.now", return_value=DEMO_EXPORT_TIME):
                payload = build_ort_nr7_v2_payload(instance=instance, user=user)
        except Exception as exc:  # noqa: BLE001
            if strict:
                raise CommandError(f"Export blocked: {exc}")
            self.stdout.write(self.style.WARNING(f"Export blocked: {exc}"))
        if payload:
            export_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            payload_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
            ).hexdigest()
            self.stdout.write(self.style.SUCCESS(f"Export written: {export_path}"))
            self.stdout.write(self.style.SUCCESS(f"Export sha256: {payload_hash}"))

        pack_context = build_review_pack_context(instance, user)
        section_iii_codes = [item["entry"].national_target.code for item in pack_context["section_iii_items"]]
        section_iv_codes = [item["entry"].framework_target.code for item in pack_context["section_iv_items"]]
        indicator_codes = []
        if pack_context["section_iii_items"]:
            indicator_codes = [
                item["series"].indicator.code
                for item in pack_context["section_iii_items"][0]["series_items"]
                if item["series"].indicator_id
            ]
        order_payload = {
            "section_iii_targets": section_iii_codes,
            "section_iv_framework_targets": section_iv_codes,
            "indicator_codes": indicator_codes,
        }
        order_path.write_text(
            json.dumps(order_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self.stdout.write(self.style.SUCCESS(f"Review pack order written: {order_path}"))

    def _approve_all(self, instance, user):
        from nbms_app.models import Dataset, Evidence, Indicator, NationalTarget
        from nbms_app.models import LifecycleStatus

        demo_targets = NationalTarget.objects.filter(
            status=LifecycleStatus.PUBLISHED,
            uuid__in=DEMO_NATIONAL_TARGETS.values(),
        )
        demo_indicators = Indicator.objects.filter(
            status=LifecycleStatus.PUBLISHED,
            uuid__in=DEMO_INDICATORS.values(),
        )
        demo_evidence = Evidence.objects.filter(
            status=LifecycleStatus.PUBLISHED,
            uuid__in=[DEMO_EVIDENCE_PUBLIC_UUID, DEMO_EVIDENCE_IPLC_UUID],
        )
        demo_datasets = Dataset.objects.filter(status=LifecycleStatus.PUBLISHED, uuid=DEMO_DATASET_UUID)

        for obj in [*demo_targets, *demo_indicators, *demo_evidence, *demo_datasets]:
            approve_for_instance(instance, obj, user)

    def _grant_all_consent(self, instance, user):
        from nbms_app.models import ConsentStatus, Dataset, Evidence, Indicator, NationalTarget
        from nbms_app.models import LifecycleStatus

        demo_targets = NationalTarget.objects.filter(
            status=LifecycleStatus.PUBLISHED,
            uuid__in=DEMO_NATIONAL_TARGETS.values(),
        )
        demo_indicators = Indicator.objects.filter(
            status=LifecycleStatus.PUBLISHED,
            uuid__in=DEMO_INDICATORS.values(),
        )
        demo_evidence = Evidence.objects.filter(
            status=LifecycleStatus.PUBLISHED,
            uuid__in=[DEMO_EVIDENCE_PUBLIC_UUID, DEMO_EVIDENCE_IPLC_UUID],
        )
        demo_datasets = Dataset.objects.filter(status=LifecycleStatus.PUBLISHED, uuid=DEMO_DATASET_UUID)

        for obj in [*demo_targets, *demo_indicators, *demo_evidence, *demo_datasets]:
            if requires_consent(obj):
                set_consent_status(instance, obj, user, ConsentStatus.GRANTED, note="demo verify")
