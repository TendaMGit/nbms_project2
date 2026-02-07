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
        "title": "Ramsar COP14 National Report",
        "mea_code": "RAMSAR",
        "version": "v1",
        "description": "Ramsar reporting pack aligned to COP14 national report structure.",
        "export_handler": "ramsar_v1",
        "sections": [
            (
                "section_1_institutional",
                "Section 1 - Institutional Information",
                {
                    "fields": [
                        {
                            "key": "reporting_party",
                            "label": "Reporting Contracting Party",
                            "type": "text",
                            "required": True,
                        },
                        {
                            "key": "administrative_authority",
                            "label": "Administrative authority",
                            "type": "text",
                            "required": True,
                        },
                        {
                            "key": "national_focal_point_name",
                            "label": "National focal point name",
                            "type": "text",
                            "required": True,
                        },
                        {
                            "key": "national_focal_point_email",
                            "label": "National focal point email",
                            "type": "text",
                            "required": True,
                        },
                        {
                            "key": "reporting_period_start",
                            "label": "Reporting period start",
                            "type": "date",
                            "required": False,
                        },
                        {
                            "key": "reporting_period_end",
                            "label": "Reporting period end",
                            "type": "date",
                            "required": False,
                        },
                    ]
                },
            ),
            (
                "section_2_narrative",
                "Section 2 - National Wetland Context and Trends",
                {
                    "fields": [
                        {
                            "key": "wetland_inventory_status",
                            "label": "National wetland inventory and assessment status",
                            "type": "textarea",
                            "required": True,
                        },
                        {
                            "key": "key_policy_changes",
                            "label": "Key policy or governance changes since last report",
                            "type": "textarea",
                            "required": False,
                        },
                        {
                            "key": "priority_pressures",
                            "label": "Priority pressures affecting wetlands",
                            "type": "textarea",
                            "required": True,
                        },
                    ]
                },
            ),
            (
                "section_3_implementation_indicators",
                "Section 3 - Implementation Indicator Questions",
                {
                    "fields": [
                        {
                            "key": "implementation_questions",
                            "label": "Implementation indicator questions",
                            "type": "questionnaire",
                            "required": True,
                            "question_catalog": [
                                {
                                    "code": "R1.1",
                                    "title": "National wetland inventory coverage has improved.",
                                },
                                {
                                    "code": "R1.2",
                                    "title": "Wetland ecological character change monitoring is operational.",
                                },
                                {
                                    "code": "R2.1",
                                    "title": "Site management planning is implemented at Ramsar sites.",
                                },
                                {
                                    "code": "R2.2",
                                    "title": "Wise-use integration in national planning frameworks is in place.",
                                },
                                {
                                    "code": "R3.1",
                                    "title": "Wetland restoration implementation has progressed.",
                                },
                                {
                                    "code": "R3.2",
                                    "title": "Waterbird population monitoring informs management responses.",
                                },
                                {
                                    "code": "R4.1",
                                    "title": "Stakeholder and IPLC participation in wetland governance is effective.",
                                },
                                {
                                    "code": "R4.2",
                                    "title": "Ramsar CEPA implementation has improved awareness and action.",
                                },
                            ],
                            "allowed_values": ["yes", "partial", "no", "not_applicable"],
                        }
                    ]
                },
            ),
            (
                "section_4_annex_targets",
                "Section 4 - Optional National Targets Annex",
                {
                    "fields": [
                        {
                            "key": "annex_summary",
                            "label": "Annex summary",
                            "type": "textarea",
                            "required": False,
                        },
                        {
                            "key": "linked_indicator_codes",
                            "label": "Linked indicator codes",
                            "type": "multivalue",
                            "required": False,
                        },
                        {
                            "key": "linked_programme_codes",
                            "label": "Linked monitoring programme codes",
                            "type": "multivalue",
                            "required": False,
                        },
                    ]
                },
            ),
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
            for idx, section_def in enumerate(definition["sections"], start=1):
                if len(section_def) == 2:
                    code, title = section_def
                    schema_json = {
                        "fields": [
                            {"key": "summary", "label": "Summary", "type": "text", "required": True},
                            {"key": "details", "label": "Details", "type": "textarea", "required": False},
                        ]
                    }
                else:
                    code, title, schema_json = section_def
                _section, section_created = ReportTemplatePackSection.objects.update_or_create(
                    pack=pack,
                    code=code,
                    defaults={
                        "title": title,
                        "ordering": idx,
                        "schema_json": schema_json,
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
