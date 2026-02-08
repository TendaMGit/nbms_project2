from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from nbms_app.models import (
    EcosystemRiskAssessment,
    EcosystemType,
    IucnRleCategory,
    LifecycleStatus,
    QaStatus,
    RegistryReviewStatus,
    SensitivityLevel,
)


class Command(BaseCommand):
    help = "Seed demo ecosystem/taxon/IAS registries with standards-aligned records."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_get_reference", verbosity=0)
        call_command("sync_taxon_backbone", "--seed-demo", "--skip-remote", verbosity=0)
        call_command("sync_specimen_vouchers", "--seed-demo", verbosity=0)
        call_command("sync_griis_za", "--seed-demo", verbosity=0)
        try:
            call_command("sync_vegmap_baseline", "--use-demo-layer", "--vegmap-version", "demo", verbosity=0)
        except Exception as exc:  # noqa: BLE001
            self.stdout.write(self.style.WARNING(f"VegMap demo extraction skipped: {exc}"))

        seeded = 0
        for ecosystem in EcosystemType.objects.order_by("ecosystem_code", "id")[:10]:
            EcosystemRiskAssessment.objects.update_or_create(
                ecosystem_type=ecosystem,
                assessment_year=2024,
                assessment_scope="national",
                defaults={
                    "category": IucnRleCategory.NT,
                    "criterion_a": "Baseline trend available; requires detailed decline analysis.",
                    "criterion_b": "Distribution decline requires validation.",
                    "criterion_c": "",
                    "criterion_d": "",
                    "criterion_e": "",
                    "evidence": "Demo seed for RLE-ready workflow.",
                    "review_status": RegistryReviewStatus.NEEDS_REVIEW,
                    "status": LifecycleStatus.DRAFT,
                    "sensitivity": SensitivityLevel.INTERNAL,
                    "qa_status": QaStatus.DRAFT,
                    "export_approved": False,
                    "source_system": "registry_demo_seed",
                    "source_ref": ecosystem.ecosystem_code,
                },
            )
            seeded += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Registry demo seeding complete. ecosystem_assessments_seeded={seeded}."
            )
        )
