from datetime import date

from django.core.management.base import BaseCommand

from nbms_app.models import Organisation, ReportTemplatePackResponse, ReportingCycle, ReportingInstance, User
from nbms_app.services.reporting_collab import append_revision, ensure_initial_revision
from nbms_app.services.reporting_workflow import resolve_cbd_pack
from nbms_app.services.template_packs import build_default_response_payload


DEMO_SECTION_CONTENT = {
    "section-i": {
        "country_name": "South Africa",
        "authorities": ["SANBI", "DFFE"],
        "contact_name": "NBMS Secretariat",
        "contact_title": "National Focal Point",
        "contact_email": "nbms@example.org",
        "contact_phone": "+27-12-000-0000",
        "contact_address": "Pretoria, South Africa",
        "preparation_process": "Whole-of-government authoring workflow.",
        "coordination_mechanisms": "Sectoral and subnational validation workshops.",
        "consultations": "IPLC, women, youth, private sector consultations included.",
        "challenges_encountered": "Dataset harmonization and reporting cadence alignment.",
    },
    "section-ii": {
        "nbsap_aligned_status": "in_progress",
        "nbsap_expected_completion_date": "2026-12-31",
        "stakeholders_engaged": "yes",
        "stakeholder_groups": ["indigenous_and_local_communities", "women", "youth", "private_sector"],
        "adopted_status": "in_progress",
        "adoption_expected_date": "2027-03-31",
        "adoption_specification": "Cabinet approval pathway is in progress.",
        "adoption_methods": ["council_of_ministers_president_pm", "environment_ministry_sector_ministry"],
        "monitoring_system_description": "NBMS programme-driven architecture with indicator and spatial pipelines.",
    },
    "section-iii": {
        "target_progress_rows": [
            {
                "national_target_code": "ZA-NT-01",
                "national_target_title": "Target 1",
                "actions_taken": "Ecosystem planning updated.",
                "progress_level": "on_track",
                "progress_summary_outcomes": "Spatial plans integrated.",
                "challenges_and_future_approaches": "Scale local implementation and improve finance flows.",
                "headline_indicator_data": [
                    {
                        "indicator_code": "NBMS-GBF-PA-COVERAGE",
                        "data_source_choice": "national_dataset",
                        "units": "percent",
                        "years": [2020, 2021, 2022],
                    }
                ],
                "binary_indicator_responses": [],
            },
            {
                "national_target_code": "ZA-NT-02",
                "national_target_title": "Target 6",
                "actions_taken": "IAS containment priorities implemented.",
                "progress_level": "insufficient_rate",
                "progress_summary_outcomes": "Pressure reduced in priority basins.",
                "challenges_and_future_approaches": "Increase local authority compliance and investment.",
                "headline_indicator_data": [],
                "binary_indicator_responses": [
                    {"question_code": "T6-B1", "response": "partial", "comment": "Institutional coverage expanded."}
                ],
            },
        ]
    },
    "section-iv": {
        "goal_progress_rows": [
            {
                "framework_goal_code": "A",
                "framework_goal_title": "Goal A",
                "summary_national_progress": "Progress is positive but uneven across provinces.",
                "selected_headline_binary_indicators": ["NBMS-GBF-PA-COVERAGE", "NBMS-GBF-IAS-PRESSURE"],
                "selected_component_indicators": [],
                "sources_of_data": ["Dataset release 2022"],
                "curated_override": "",
            }
        ]
    },
    "section-v": {
        "summary_assessment": "Implementation is progressing with measurable outcomes.",
        "achievements": "Protected area coverage increased and governance strengthened.",
        "challenges_and_gaps": "Financing and local capacity remain key barriers.",
        "support_provided": "Technical support and training delivered through SANBI/DFFE programmes.",
        "finance_table": [
            {"year": 2022, "source": "National budget", "amount_zar_millions": 125.0}
        ],
        "cross_references": ["section-iii", "section-iv"],
    },
    "annex": {
        "annex_items": [
            {
                "decision_topic_code": "COP16-31",
                "title": "Binary indicator updates",
                "summary": "All required binary indicators seeded and partially populated.",
            }
        ]
    },
}


class Command(BaseCommand):
    help = "Seed demo NR7/NR8 reporting instances with CBD national report workspace content."

    def handle(self, *args, **options):
        pack = resolve_cbd_pack()
        org, _ = Organisation.objects.get_or_create(
            org_code="SANBI",
            defaults={"name": "South African National Biodiversity Institute"},
        )
        publisher_org, _ = Organisation.objects.get_or_create(
            org_code="DFFE",
            defaults={"name": "Department of Forestry, Fisheries and the Environment"},
        )
        user = User.objects.filter(username="Tenda").first() or User.objects.filter(is_superuser=True).order_by("id").first()

        created_instances = []
        for cycle_code, title, start_year in (
            ("NR7", "Seventh National Report", 2024),
            ("NR8", "Eighth National Report", 2027),
        ):
            cycle, _ = ReportingCycle.objects.update_or_create(
                code=cycle_code,
                defaults={
                    "title": title,
                    "start_date": date(start_year, 1, 1),
                    "end_date": date(start_year + 2, 12, 31),
                    "due_date": date(start_year + 3, 3, 31),
                    "submission_window_start": date(start_year + 2, 10, 1),
                    "submission_window_end": date(start_year + 3, 3, 31),
                    "default_language": "English",
                    "allowed_languages": ["English"],
                    "is_active": cycle_code == "NR8",
                },
            )
            instance, _ = ReportingInstance.objects.update_or_create(
                cycle=cycle,
                version_label="v1",
                defaults={
                    "report_title": f"South Africa {cycle_code}",
                    "country_name": "South Africa",
                    "focal_point_org": org,
                    "publishing_authority_org": publisher_org,
                    "is_public": False,
                    "created_by": user,
                    "updated_by": user,
                },
            )
            created_instances.append(instance)

            for section in pack.sections.filter(is_active=True).order_by("ordering", "code"):
                response, _created = ReportTemplatePackResponse.objects.get_or_create(
                    reporting_instance=instance,
                    section=section,
                    defaults={"response_json": build_default_response_payload(section), "updated_by": user},
                )
                ensure_initial_revision(section_response=response, author=user)
                content = DEMO_SECTION_CONTENT.get(section.code)
                if content:
                    append_revision(
                        section_response=response,
                        content=content,
                        author=user,
                        note=f"seed_demo_reports:{cycle_code}",
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded demo report instances for NR7/NR8 ({len(created_instances)} instances)."
            )
        )
