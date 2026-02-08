from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from nbms_app.models import (
    LifecycleStatus,
    MonitoringProgramme,
    Organisation,
    ProgrammeRefreshCadence,
    ProgrammeTemplate,
    ProgrammeType,
    QaStatus,
    SensitivityLevel,
    UpdateFrequency,
)
from nbms_app.services.registry_catalog import PROGRAMME_TEMPLATE_DEFINITIONS


class Command(BaseCommand):
    help = "Seed programme templates and optionally materialize active MonitoringProgramme records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--instantiate",
            action="store_true",
            help="Also create/update MonitoringProgramme rows from templates.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        instantiate = bool(options.get("instantiate"))
        sanbi, _ = Organisation.objects.get_or_create(
            org_code="SANBI",
            defaults={"name": "South African National Biodiversity Institute", "org_type": "Government"},
        )

        template_count = 0
        programme_count = 0
        for definition in PROGRAMME_TEMPLATE_DEFINITIONS:
            template, _ = ProgrammeTemplate.objects.update_or_create(
                template_code=definition.template_code,
                defaults={
                    "title": definition.title,
                    "description": definition.description,
                    "domain": definition.domain,
                    "pipeline_definition_json": definition.pipeline_definition_json,
                    "required_outputs_json": definition.required_outputs_json,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "qa_status": QaStatus.PUBLISHED,
                    "export_approved": True,
                    "is_active": True,
                    "organisation": sanbi,
                    "source_system": "programme_template_seed",
                    "source_ref": definition.template_code,
                },
            )
            template_count += 1

            if instantiate:
                MonitoringProgramme.objects.update_or_create(
                    programme_code=template.template_code,
                    defaults={
                        "title": template.title,
                        "description": template.description,
                        "programme_type": ProgrammeType.NATIONAL,
                        "lead_org": sanbi,
                        "refresh_cadence": ProgrammeRefreshCadence.MONTHLY,
                        "update_frequency": UpdateFrequency.MONTHLY,
                        "scheduler_enabled": True,
                        "geographic_scope": "South Africa",
                        "taxonomic_scope": template.domain.replace("_", " "),
                        "ecosystem_scope": "Cross-realm",
                        "objectives": f"Run {template.title} using reusable registry workflows.",
                        "sampling_design_summary": "Programme-template driven ingestion/validation/compute/publish sequence.",
                        "qa_process_summary": "QA per step with run-level provenance.",
                        "pipeline_definition_json": template.pipeline_definition_json,
                        "data_quality_rules_json": {"minimum_dataset_links": 0, "minimum_indicator_links": 0},
                        "lineage_notes": "Template-driven programme run lineage.",
                        "is_active": True,
                        "source_system": "programme_template_seed",
                        "source_ref": template.template_code,
                    },
                )
                programme_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded programme templates={template_count}."
                + (f" Instantiated programmes={programme_count}." if instantiate else "")
            )
        )
