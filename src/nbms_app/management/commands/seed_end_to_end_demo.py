from pathlib import Path

from django.core.management import BaseCommand, CommandError, call_command

from nbms_app.models import (
    ConsentRecord,
    ConsentStatus,
    DatasetCatalog,
    Framework,
    FrameworkGoal,
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorFrameworkIndicatorLink,
    LifecycleStatus,
    Methodology,
    MethodologyVersion,
    MonitoringProgramme,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    ReportingStatus,
    SectionIIINationalTargetProgress,
    SensitivityLevel,
    User,
)
from nbms_app.services.consent import set_consent_status
from nbms_app.services.readiness import compute_reporting_readiness


DEMO_SOURCE = "demo_seed"
DEMO_REF = "demo_v1"
DEMO_PREFIX = "DEMO-"
DEMO_FRAMEWORK_CODE = "DEMO-GBF"
DEMO_CYCLE_CODE = "DEMO-CYCLE-7NR"
DEMO_VERSION = "demo"


class Command(BaseCommand):
    help = "Seed an end-to-end demo dataset for reference catalog and reporting readiness."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run).")
        parser.add_argument("--reset", action="store_true", help="Remove demo-tagged records before seeding.")
        parser.add_argument("--strict", action="store_true", help="Exit non-zero if readiness is not ready.")

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        reset = options["reset"]
        strict = options["strict"]

        if reset:
            self._reset_demo()

        if not apply_changes:
            self.stdout.write(self.style.WARNING("Dry-run: no changes applied. Use --apply to seed demo data."))
            return

        fixtures_dir = Path(__file__).resolve().parents[4] / "docs" / "reference_catalog" / "demo_fixtures"
        if not fixtures_dir.exists():
            raise CommandError(f"Demo fixtures not found at {fixtures_dir}")

        demo_user, demo_org = self._ensure_demo_user()
        framework, _ = Framework.objects.update_or_create(
            code=DEMO_FRAMEWORK_CODE,
            defaults={"title": "Demo GBF Framework"},
        )

        import_order = [
            ("organisation", "organisation_demo.csv"),
            ("sensitivity_class", "sensitivity_class_demo.csv"),
            ("data_agreement", "data_agreement_demo.csv"),
            ("monitoring_programme", "monitoring_programme_demo.csv"),
            ("dataset_catalog", "dataset_catalog_demo.csv"),
            ("methodology", "methodology_demo.csv"),
            ("methodology_version", "methodology_version_demo.csv"),
            ("programme_dataset_link", "programme_dataset_link_demo.csv"),
            ("methodology_dataset_link", "methodology_dataset_link_demo.csv"),
        ]

        for entity, filename in import_order:
            path = fixtures_dir / filename
            if path.exists():
                call_command(
                    "reference_catalog_import",
                    entity=entity,
                    file=str(path),
                    mode="upsert",
                    strict=True,
                )

        gbf_files = [
            ("gbf_goals", "gbf_goals_demo.csv"),
            ("gbf_targets", "gbf_targets_demo.csv"),
            ("gbf_indicators", "gbf_indicators_demo.csv"),
        ]
        for entity, filename in gbf_files:
            path = fixtures_dir / filename
            if path.exists():
                call_command(
                    "reference_catalog_import",
                    entity=entity,
                    file=str(path),
                    mode="upsert",
                    strict=True,
                )

        instance = self._ensure_reporting_instance()
        target = self._ensure_national_target(demo_org, demo_user)
        indicators = self._ensure_indicators(target, demo_org, demo_user)
        self._ensure_framework_mapping(indicators, framework)

        call_command(
            "reference_catalog_import",
            entity="programme_indicator_link",
            file=str(fixtures_dir / "programme_indicator_link_demo.csv"),
            mode="upsert",
            strict=True,
        )
        call_command(
            "reference_catalog_import",
            entity="methodology_indicator_link",
            file=str(fixtures_dir / "methodology_indicator_link_demo.csv"),
            mode="upsert",
            strict=True,
        )

        series_list = self._seed_indicator_data(indicators, demo_org, demo_user)
        progress, _ = SectionIIINationalTargetProgress.objects.get_or_create(
            reporting_instance=instance,
            national_target=target,
        )
        progress.indicator_data_series.set(series_list)

        self._seed_consent(instance, demo_user)

        readiness = compute_reporting_readiness(instance.uuid, scope="selected", user=demo_user)
        summary = readiness["summary"]
        self.stdout.write(
            self.style.SUCCESS(
                "Readiness summary: "
                f"{summary.get('total_indicators_in_scope')} indicators, "
                f"blocking gaps {summary.get('blocking_gap_count')}, "
                f"overall_ready={summary.get('overall_ready')}"
            )
        )
        if strict and not summary.get("overall_ready"):
            top_blockers = readiness.get("diagnostics", {}).get("top_blockers", [])
            blocker_text = ", ".join([f"{item['code']}={item['count']}" for item in top_blockers]) or "none"
            raise CommandError(f"Readiness not met. Top blockers: {blocker_text}")

    def _ensure_demo_user(self):
        org, _ = Organisation.objects.get_or_create(
            org_code="DEMO-ORG",
            defaults={"name": "Demo Biodiversity Org"},
        )
        user, _ = User.objects.get_or_create(
            username="demo_admin",
            defaults={"is_staff": True, "organisation": org},
        )
        if user.organisation_id != org.id:
            user.organisation = org
            user.save(update_fields=["organisation"])
        return user, org

    def _ensure_reporting_instance(self):
        cycle, _ = ReportingCycle.objects.get_or_create(
            code=DEMO_CYCLE_CODE,
            defaults={
                "title": "Demo 7NR Cycle",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "due_date": "2026-02-28",
                "is_active": True,
            },
        )
        instance, _ = ReportingInstance.objects.get_or_create(
            cycle=cycle,
            version_label=DEMO_VERSION,
            defaults={"status": ReportingStatus.DRAFT},
        )
        return instance

    def _ensure_national_target(self, org, user):
        target, _ = NationalTarget.objects.update_or_create(
            code="DEMO-NT1",
            defaults={
                "title": "Demo National Target",
                "description": "Demo national target for readiness.",
                "organisation": org,
                "created_by": user,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
            },
        )
        return target

    def _ensure_indicators(self, target, org, user):
        indicators = []
        for code, title in [("DEMO-IND-1", "Demo Indicator 1"), ("DEMO-IND-2", "Demo Indicator 2")]:
            indicator, _ = Indicator.objects.update_or_create(
                code=code,
                defaults={
                    "title": title,
                    "national_target": target,
                    "organisation": org,
                    "created_by": user,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                },
            )
            indicators.append(indicator)
        return indicators

    def _ensure_framework_mapping(self, indicators, framework):
        target = FrameworkTarget.objects.filter(framework=framework, code="DEMO-T1").first()
        if not target:
            target = FrameworkTarget.objects.create(
                framework=framework,
                code="DEMO-T1",
                title="Demo Framework Target",
                status=LifecycleStatus.PUBLISHED,
                sensitivity=SensitivityLevel.PUBLIC,
                source_system=DEMO_SOURCE,
                source_ref=DEMO_REF,
            )

        national_target = indicators[0].national_target if indicators else None
        if national_target:
            NationalTargetFrameworkTargetLink.objects.update_or_create(
                national_target=national_target,
                framework_target=target,
                defaults={},
            )

        mapping = {
            "DEMO-IND-1": "DEMO-FW-IND-1",
            "DEMO-IND-2": "DEMO-FW-IND-2",
        }
        for indicator in indicators:
            fw_code = mapping.get(indicator.code, f"DEMO-FW-{indicator.code}")
            fw_indicator = FrameworkIndicator.objects.filter(framework=framework, code=fw_code).first()
            if not fw_indicator:
                fw_indicator = FrameworkIndicator.objects.create(
                    framework=framework,
                    framework_target=target,
                    code=fw_code,
                    title=f"Demo Framework Indicator {indicator.code}",
                    status=LifecycleStatus.PUBLISHED,
                    sensitivity=SensitivityLevel.PUBLIC,
                    source_system=DEMO_SOURCE,
                    source_ref=DEMO_REF,
                )
            IndicatorFrameworkIndicatorLink.objects.update_or_create(
                indicator=indicator,
                framework_indicator=fw_indicator,
                defaults={},
            )

    def _seed_indicator_data(self, indicators, org, user):
        series_list = []
        for idx, indicator in enumerate(indicators, start=1):
            series, _ = IndicatorDataSeries.objects.get_or_create(
                indicator=indicator,
                defaults={
                    "title": f"Demo series {indicator.code}",
                    "unit": "count",
                    "organisation": org,
                    "created_by": user,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                },
            )
            IndicatorDataPoint.objects.update_or_create(
                series=series,
                year=2020,
                disaggregation={},
                dataset_release=None,
                defaults={"value_numeric": 10 + idx, "value_text": ""},
            )
            IndicatorDataPoint.objects.update_or_create(
                series=series,
                year=2021,
                disaggregation={},
                dataset_release=None,
                defaults={"value_numeric": 12 + idx, "value_text": ""},
            )
            series_list.append(series)
        return series_list

    def _seed_consent(self, instance, user):
        programme = MonitoringProgramme.objects.filter(source_system=DEMO_SOURCE).first()
        dataset = DatasetCatalog.objects.filter(source_system=DEMO_SOURCE).first()

        for obj in [programme, dataset]:
            if not obj:
                continue
            if getattr(obj, "consent_required", False):
                set_consent_status(
                    instance,
                    obj,
                    user,
                    ConsentStatus.GRANTED,
                    note="demo seed",
                )

    def _reset_demo(self):
        demo_instances = ReportingInstance.objects.filter(
            cycle__code=DEMO_CYCLE_CODE,
            version_label=DEMO_VERSION,
        )
        ConsentRecord.objects.filter(reporting_instance__in=demo_instances).delete()
        SectionIIINationalTargetProgress.objects.filter(reporting_instance__in=demo_instances).delete()

        demo_indicators = Indicator.objects.filter(code__startswith=DEMO_PREFIX)
        series = IndicatorDataSeries.objects.filter(indicator__in=demo_indicators)
        IndicatorDataPoint.objects.filter(series__in=series).delete()
        series.delete()
        IndicatorFrameworkIndicatorLink.objects.filter(indicator__in=demo_indicators).delete()

        MethodologyVersion.objects.filter(source_system=DEMO_SOURCE).delete()
        Methodology.objects.filter(source_system=DEMO_SOURCE).delete()
        MonitoringProgramme.objects.filter(source_system=DEMO_SOURCE).delete()
        DatasetCatalog.objects.filter(source_system=DEMO_SOURCE).delete()

        demo_instances.delete()
        ReportingCycle.objects.filter(code=DEMO_CYCLE_CODE).delete()

        demo_indicators.delete()
        NationalTarget.objects.filter(code__startswith=DEMO_PREFIX).delete()

        FrameworkIndicator.objects.filter(source_system=DEMO_SOURCE).delete()
        FrameworkTarget.objects.filter(source_system=DEMO_SOURCE).delete()
        FrameworkGoal.objects.filter(source_system=DEMO_SOURCE).delete()
        Framework.objects.filter(code=DEMO_FRAMEWORK_CODE).delete()

        Organisation.objects.filter(org_code__startswith=DEMO_PREFIX).delete()
        User.objects.filter(username="demo_admin").delete()
