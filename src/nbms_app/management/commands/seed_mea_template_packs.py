from django.core.management.base import BaseCommand

from nbms_app.models import (
    Framework,
    FrameworkGoal,
    FrameworkTarget,
    LifecycleStatus,
    ReportTemplatePack,
    ReportTemplatePackSection,
)


PACK_DEFINITIONS = [
    {
        "code": "cbd_ort_nr7_v2",
        "title": "CBD ORT NR7 v2",
        "mea_code": "CBD",
        "version": "v2",
        "description": "CBD online reporting tool pack for 7th national report.",
        "export_handler": "cbd_ort_nr7_v2",
        "sections": [
            ("section-i", "Report Context"),
            ("section-ii", "NBSAP Status"),
            ("section-iii", "Progress in National Targets"),
            ("section-iv", "Progress in GBF Goals and Targets"),
            ("section-v", "Conclusions"),
        ],
    },
    {
        "code": "ramsar_v1",
        "title": "Ramsar National Report Scaffold",
        "mea_code": "RAMSAR",
        "version": "v1",
        "description": "Scaffold for wetlands reporting pack.",
        "export_handler": "ramsar_v1",
        "sections": [
            ("wetland_extent", "Wetland extent and condition"),
            ("management_effectiveness", "Management effectiveness"),
            ("restoration_actions", "Restoration actions and financing"),
        ],
    },
    {
        "code": "cites_v1",
        "title": "CITES Reporting Scaffold",
        "mea_code": "CITES",
        "version": "v1",
        "description": "Scaffold for trade pressure and enforcement reporting.",
        "export_handler": "cites_v1",
        "sections": [
            ("trade_pressure", "Trade pressure summary"),
            ("permits_compliance", "Permits and compliance"),
            ("enforcement_outcomes", "Enforcement outcomes"),
        ],
    },
    {
        "code": "cms_v1",
        "title": "CMS Reporting Scaffold",
        "mea_code": "CMS",
        "version": "v1",
        "description": "Scaffold for migratory species reporting.",
        "export_handler": "cms_v1",
        "sections": [
            ("species_status", "Migratory species status"),
            ("threats_pressures", "Threats and pressures"),
            ("conservation_actions", "Conservation actions"),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed runtime template packs for CBD and scaffold MEAs."

    def handle(self, *args, **options):
        framework, _ = Framework.objects.get_or_create(
            code="GBF",
            defaults={
                "title": "Kunming-Montreal Global Biodiversity Framework",
                "description": "Global Biodiversity Framework",
                "status": LifecycleStatus.PUBLISHED,
            },
        )
        FrameworkGoal.objects.get_or_create(
            framework=framework,
            code="A",
            defaults={
                "title": "Goal A",
                "status": LifecycleStatus.PUBLISHED,
                "description": "Ecosystem integrity and species persistence.",
            },
        )
        FrameworkTarget.objects.get_or_create(
            framework=framework,
            code="1",
            defaults={
                "title": "Target 1",
                "status": LifecycleStatus.PUBLISHED,
                "description": "Spatial planning and biodiversity value retention.",
            },
        )

        packs_created = 0
        sections_created = 0
        for definition in PACK_DEFINITIONS:
            pack, created = ReportTemplatePack.objects.update_or_create(
                code=definition["code"],
                defaults={
                    "title": definition["title"],
                    "mea_code": definition["mea_code"],
                    "version": definition["version"],
                    "description": definition["description"],
                    "framework": framework if definition["mea_code"] == "CBD" else None,
                    "export_handler": definition["export_handler"],
                    "is_active": True,
                },
            )
            if created:
                packs_created += 1
            for idx, (code, title) in enumerate(definition["sections"], start=1):
                _section, section_created = ReportTemplatePackSection.objects.update_or_create(
                    pack=pack,
                    code=code,
                    defaults={
                        "title": title,
                        "ordering": idx,
                        "schema_json": {
                            "fields": [
                                {"key": "summary", "label": "Summary", "type": "text", "required": True},
                                {"key": "details", "label": "Details", "type": "textarea", "required": False},
                            ]
                        },
                        "is_active": True,
                    },
                )
                if section_created:
                    sections_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded template packs: {len(PACK_DEFINITIONS)} total, "
                f"{packs_created} created, {sections_created} sections created."
            )
        )
