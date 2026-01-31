from django.contrib.auth.models import Group
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction

from nbms_app.demo_constants import (
    DEMO_ADMIN_USERNAME,
    DEMO_CYCLE_CODE,
    DEMO_CYCLE_TITLE,
    DEMO_CYCLE_UUID,
    DEMO_DATASET_CATALOG_UUID,
    DEMO_DATASET_RELEASE_UUID,
    DEMO_DATASET_UUID,
    DEMO_DATA_SERIES,
    DEMO_DATA_POINTS,
    DEMO_DEFAULT_PASSWORD,
    DEMO_EVIDENCE_IPLC_UUID,
    DEMO_EVIDENCE_PUBLIC_UUID,
    DEMO_FRAMEWORK_CODE,
    DEMO_FRAMEWORK_GOAL_CODE,
    DEMO_FRAMEWORK_GOAL_TITLE,
    DEMO_FRAMEWORK_GOAL_UUID,
    DEMO_FRAMEWORK_INDICATORS,
    DEMO_FRAMEWORK_TARGETS,
    DEMO_FRAMEWORK_TITLE,
    DEMO_FRAMEWORK_UUID,
    DEMO_INDICATORS,
    DEMO_INSTANCE_UUID,
    DEMO_INSTANCE_VERSION,
    DEMO_MANAGER_USERNAME,
    DEMO_METHODOLOGY_UUID,
    DEMO_METHODOLOGY_VERSION_UUID,
    DEMO_MONITORING_PROGRAMME_UUID,
    DEMO_NATIONAL_TARGETS,
    DEMO_ORG_A_CODE,
    DEMO_ORG_A_NAME,
    DEMO_ORG_B_CODE,
    DEMO_ORG_B_NAME,
    DEMO_PARTNER_USERNAME,
    DEMO_PERIOD_END,
    DEMO_PERIOD_START,
    DEMO_RELEASE_DATE,
    DEMO_SECTION_III,
    DEMO_SECTION_IV,
    DEMO_SOURCE,
    DEMO_TAG,
)
from nbms_app.models import (
    ConsentRecord,
    ConsentStatus,
    Dataset,
    DatasetCatalog,
    DatasetRelease,
    Evidence,
    Framework,
    FrameworkGoal,
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorFrameworkIndicatorLink,
    InstanceExportApproval,
    LifecycleStatus,
    Methodology,
    MethodologyVersion,
    MonitoringProgramme,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    ProgressStatus,
    ReportingCycle,
    ReportingInstance,
    ReportingStatus,
    SectionIIINationalTargetProgress,
    SectionIVFrameworkTargetProgress,
    SensitivityLevel,
    User,
)
from nbms_app.services.authorization import (
    ROLE_ADMIN,
    ROLE_CONTRIBUTOR,
    ROLE_DATA_STEWARD,
    ROLE_SECRETARIAT,
)
from nbms_app.services.consent import consent_is_granted, requires_consent, set_consent_status
from nbms_app.services.instance_approvals import approve_for_instance


class Command(BaseCommand):
    help = "Seed deterministic demo data for end-to-end walkthroughs."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Remove demo-tagged data before seeding.")
        parser.add_argument(
            "--confirm-reset",
            action="store_true",
            help="Confirm reset (required with --reset).",
        )
        parser.add_argument("--approve-all", action="store_true", help="Approve all demo objects.")
        parser.add_argument("--grant-consent", action="store_true", help="Grant consent for IPLC demo objects.")
        parser.add_argument(
            "--ready",
            action="store_true",
            help="Shortcut: approve all demo objects and grant consent.",
        )

    def handle(self, *args, **options):
        reset = options["reset"]
        confirm_reset = options["confirm_reset"]
        approve_all = options["approve_all"]
        grant_consent = options["grant_consent"]
        if options["ready"]:
            approve_all = True
            grant_consent = True

        if reset:
            if not confirm_reset:
                raise CommandError("--reset requires --confirm-reset to proceed.")
            self._reset_demo()

        with transaction.atomic():
            demo_org_a, demo_org_b = self._ensure_orgs()
            demo_admin, demo_manager, demo_partner = self._ensure_users(demo_org_a, demo_org_b)

            self._seed_templates()

            cycle, instance = self._ensure_reporting_instance()
            framework = self._ensure_framework(demo_admin, demo_org_a)
            goal = self._ensure_framework_goal(framework, demo_admin, demo_org_a)
            framework_targets = self._ensure_framework_targets(framework, goal, demo_admin, demo_org_a)
            framework_indicators = self._ensure_framework_indicators(
                framework,
                framework_targets,
                demo_admin,
                demo_org_a,
            )

            targets = self._ensure_national_targets(demo_admin, demo_org_a)
            indicators = self._ensure_indicators(targets, demo_admin, demo_org_a)

            self._ensure_mappings(targets, indicators, framework_targets, framework_indicators)

            programme = self._ensure_monitoring_programme(demo_org_a)
            methodology, methodology_version = self._ensure_methodology(demo_org_a)
            dataset_catalog = self._ensure_dataset_catalog(demo_org_a, programme)

            dataset, release = self._ensure_dataset_and_release(demo_admin, demo_org_a)
            evidence_public, evidence_iplc = self._ensure_evidence(demo_admin, demo_org_a)

            series_list = self._ensure_indicator_series(indicators, demo_admin, demo_org_a)
            self._ensure_indicator_points(series_list, release)

            self._ensure_section_progress(
                instance,
                targets,
                framework_targets,
                series_list,
                evidence_public,
                evidence_iplc,
                release,
            )

            if grant_consent:
                self._ensure_consent(instance, demo_admin, [evidence_iplc])

            self._ensure_approvals(
                instance,
                demo_admin,
                targets,
                indicators,
                evidence_public,
                evidence_iplc,
                dataset,
                approve_all=approve_all,
            )

        self.stdout.write(self.style.SUCCESS(f"Demo seed complete for instance {instance.uuid}"))
        if not grant_consent:
            self.stdout.write(self.style.WARNING("Consent not granted for IPLC demo evidence (expected blocker)."))
        if not approve_all:
            self.stdout.write(self.style.WARNING("Some demo objects remain unapproved (expected blocker)."))

    def _seed_templates(self):
        from nbms_app.models import BinaryIndicatorQuestion, ReportSectionTemplate, ValidationRuleSet

        if not ReportSectionTemplate.objects.exists():
            call_command("seed_report_templates")
        if not ValidationRuleSet.objects.exists():
            call_command("seed_validation_rules")
        if not BinaryIndicatorQuestion.objects.exists():
            call_command("seed_binary_indicator_questions")

    def _ensure_orgs(self):
        org_a, _ = Organisation.objects.update_or_create(
            org_code=DEMO_ORG_A_CODE,
            defaults={
                "name": DEMO_ORG_A_NAME,
            },
        )
        org_b, _ = Organisation.objects.update_or_create(
            org_code=DEMO_ORG_B_CODE,
            defaults={
                "name": DEMO_ORG_B_NAME,
            },
        )
        return org_a, org_b

    def _ensure_group(self, name):
        return Group.objects.get_or_create(name=name)[0]

    def _ensure_users(self, org_a, org_b):
        admin = User.objects.get_or_create(
            username=DEMO_ADMIN_USERNAME,
            defaults={"is_staff": True, "organisation": org_a},
        )[0]
        admin.is_staff = True
        admin.organisation = org_a
        admin.set_password(DEMO_DEFAULT_PASSWORD)
        admin.save(update_fields=["is_staff", "organisation", "password"])
        admin.groups.add(self._ensure_group(ROLE_ADMIN))
        admin.groups.add(self._ensure_group(ROLE_SECRETARIAT))

        manager = User.objects.get_or_create(
            username=DEMO_MANAGER_USERNAME,
            defaults={"is_staff": True, "organisation": org_a},
        )[0]
        manager.is_staff = True
        manager.organisation = org_a
        manager.set_password(DEMO_DEFAULT_PASSWORD)
        manager.save(update_fields=["is_staff", "organisation", "password"])
        manager.groups.add(self._ensure_group(ROLE_SECRETARIAT))
        manager.groups.add(self._ensure_group(ROLE_DATA_STEWARD))

        partner = User.objects.get_or_create(
            username=DEMO_PARTNER_USERNAME,
            defaults={"is_staff": False, "organisation": org_b},
        )[0]
        partner.is_staff = False
        partner.organisation = org_b
        partner.set_password(DEMO_DEFAULT_PASSWORD)
        partner.save(update_fields=["is_staff", "organisation", "password"])
        partner.groups.add(self._ensure_group(ROLE_CONTRIBUTOR))

        return admin, manager, partner

    def _ensure_reporting_instance(self):
        cycle, _ = ReportingCycle.objects.update_or_create(
            uuid=DEMO_CYCLE_UUID,
            defaults={
                "code": DEMO_CYCLE_CODE,
                "title": DEMO_CYCLE_TITLE,
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "due_date": "2026-02-28",
                "is_active": True,
            },
        )
        instance, _ = ReportingInstance.objects.update_or_create(
            uuid=DEMO_INSTANCE_UUID,
            defaults={
                "cycle": cycle,
                "version_label": DEMO_INSTANCE_VERSION,
                "status": ReportingStatus.DRAFT,
            },
        )
        return cycle, instance

    def _ensure_framework(self, user, org):
        framework = Framework.objects.filter(code=DEMO_FRAMEWORK_CODE).first()
        if framework:
            return framework
        return Framework.objects.create(
            uuid=DEMO_FRAMEWORK_UUID,
            code=DEMO_FRAMEWORK_CODE,
            title=DEMO_FRAMEWORK_TITLE,
            organisation=org,
            created_by=user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )

    def _ensure_framework_goal(self, framework, user, org):
        goal, _ = FrameworkGoal.objects.update_or_create(
            uuid=DEMO_FRAMEWORK_GOAL_UUID,
            defaults={
                "framework": framework,
                "code": DEMO_FRAMEWORK_GOAL_CODE,
                "title": DEMO_FRAMEWORK_GOAL_TITLE,
                "organisation": org,
                "created_by": user,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
                "source_system": DEMO_SOURCE,
                "source_ref": DEMO_TAG,
            },
        )
        return goal

    def _ensure_framework_targets(self, framework, goal, user, org):
        targets = []
        for code, uid in DEMO_FRAMEWORK_TARGETS.items():
            target, _ = FrameworkTarget.objects.update_or_create(
                uuid=uid,
                defaults={
                    "framework": framework,
                    "goal": goal,
                    "code": code,
                    "title": f"Demo Framework Target {code}",
                    "organisation": org,
                    "created_by": user,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "source_system": DEMO_SOURCE,
                    "source_ref": DEMO_TAG,
                },
            )
            targets.append(target)
        return targets

    def _ensure_framework_indicators(self, framework, targets, user, org):
        indicators = []
        target_map = {target.code: target for target in targets}
        for code, uid in DEMO_FRAMEWORK_INDICATORS.items():
            target = target_map.get("DEMO-T1") if code == "DEMO-FI-1" else target_map.get("DEMO-T2")
            indicator, _ = FrameworkIndicator.objects.update_or_create(
                uuid=uid,
                defaults={
                    "framework": framework,
                    "framework_target": target,
                    "code": code,
                    "title": f"Demo Framework Indicator {code}",
                    "organisation": org,
                    "created_by": user,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "source_system": DEMO_SOURCE,
                    "source_ref": DEMO_TAG,
                },
            )
            indicators.append(indicator)
        return indicators

    def _ensure_national_targets(self, user, org):
        targets = []
        for code, uid in DEMO_NATIONAL_TARGETS.items():
            target, _ = NationalTarget.objects.update_or_create(
                uuid=uid,
                defaults={
                    "code": code,
                    "title": f"Demo National Target {code}",
                    "description": "Demo target for walkthrough.",
                    "organisation": org,
                    "created_by": user,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "source_system": DEMO_SOURCE,
                    "source_ref": DEMO_TAG,
                },
            )
            targets.append(target)
        return targets

    def _ensure_indicators(self, targets, user, org):
        target_map = {target.code: target for target in targets}
        indicators = []
        for code, uid in DEMO_INDICATORS.items():
            target = target_map.get("DEMO-NT-1") if code == "DEMO-IND-1" else target_map.get("DEMO-NT-2")
            indicator, _ = Indicator.objects.update_or_create(
                uuid=uid,
                defaults={
                    "code": code,
                    "title": f"Demo Indicator {code}",
                    "national_target": target,
                    "organisation": org,
                    "created_by": user,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "source_system": DEMO_SOURCE,
                    "source_ref": DEMO_TAG,
                },
            )
            indicators.append(indicator)
        return indicators

    def _ensure_mappings(self, targets, indicators, framework_targets, framework_indicators):
        target_map = {target.code: target for target in targets}
        framework_target_map = {target.code: target for target in framework_targets}
        indicator_map = {indicator.code: indicator for indicator in indicators}
        framework_indicator_map = {indicator.code: indicator for indicator in framework_indicators}

        NationalTargetFrameworkTargetLink.objects.update_or_create(
            national_target=target_map["DEMO-NT-1"],
            framework_target=framework_target_map["DEMO-T1"],
            defaults={"relation_type": "contributes_to"},
        )

        IndicatorFrameworkIndicatorLink.objects.update_or_create(
            indicator=indicator_map["DEMO-IND-1"],
            framework_indicator=framework_indicator_map["DEMO-FI-1"],
            defaults={"relation_type": "contributes_to"},
        )

    def _ensure_monitoring_programme(self, org):
        programme, _ = MonitoringProgramme.objects.update_or_create(
            uuid=DEMO_MONITORING_PROGRAMME_UUID,
            defaults={
                "programme_code": "DEMO-PROG-1",
                "title": "Demo Monitoring Programme",
                "description": "Demo monitoring programme for walkthrough.",
                "lead_org": org,
                "is_active": True,
                "source_system": DEMO_SOURCE,
                "source_ref": DEMO_TAG,
            },
        )
        return programme

    def _ensure_methodology(self, org):
        methodology, _ = Methodology.objects.update_or_create(
            uuid=DEMO_METHODOLOGY_UUID,
            defaults={
                "methodology_code": "DEMO-METH-1",
                "title": "Demo Methodology",
                "description": "Demo methodology for walkthrough.",
                "owner_org": org,
                "is_active": True,
                "source_system": DEMO_SOURCE,
                "source_ref": DEMO_TAG,
            },
        )
        version, _ = MethodologyVersion.objects.update_or_create(
            uuid=DEMO_METHODOLOGY_VERSION_UUID,
            defaults={
                "methodology": methodology,
                "version": "v1",
                "status": "draft",
                "change_log": "Initial demo version.",
                "is_active": True,
                "source_system": DEMO_SOURCE,
                "source_ref": DEMO_TAG,
            },
        )
        return methodology, version

    def _ensure_dataset_catalog(self, org, programme):
        dataset, _ = DatasetCatalog.objects.update_or_create(
            uuid=DEMO_DATASET_CATALOG_UUID,
            defaults={
                "dataset_code": "DEMO-DATASET-1",
                "title": "Demo Catalog Dataset",
                "description": "Demo dataset for catalog walkthrough.",
                "custodian_org": org,
                "access_level": "internal",
                "is_active": True,
                "source_system": DEMO_SOURCE,
                "source_ref": DEMO_TAG,
            },
        )
        dataset.programme_links.all().delete()
        if programme:
            dataset.programme_links.create(programme=programme, relationship_type="supporting")
        return dataset

    def _ensure_dataset_and_release(self, user, org):
        dataset, _ = Dataset.objects.update_or_create(
            uuid=DEMO_DATASET_UUID,
            defaults={
                "title": "Demo Reporting Dataset",
                "description": "Demo dataset for reporting releases.",
                "methodology": "Demo methodology summary.",
                "organisation": org,
                "created_by": user,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
            },
        )
        release, _ = DatasetRelease.objects.update_or_create(
            dataset=dataset,
            version="v1",
            defaults={
                "uuid": DEMO_DATASET_RELEASE_UUID,
                "release_date": DEMO_RELEASE_DATE,
                "snapshot_title": dataset.title,
                "snapshot_description": dataset.description,
                "snapshot_methodology": dataset.methodology,
                "organisation": org,
                "created_by": user,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
            },
        )
        return dataset, release

    def _ensure_evidence(self, user, org):
        evidence_public, _ = Evidence.objects.update_or_create(
            uuid=DEMO_EVIDENCE_PUBLIC_UUID,
            defaults={
                "title": "Demo Evidence (Public)",
                "description": "Public evidence item.",
                "evidence_type": "report",
                "source_url": "https://example.com/demo-evidence",
                "organisation": org,
                "created_by": user,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
            },
        )
        evidence_iplc, _ = Evidence.objects.update_or_create(
            uuid=DEMO_EVIDENCE_IPLC_UUID,
            defaults={
                "title": "Demo Evidence (IPLC-sensitive)",
                "description": "Consent-gated evidence item.",
                "evidence_type": "report",
                "source_url": "https://example.com/demo-evidence-iplc",
                "organisation": org,
                "created_by": user,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.IPLC_SENSITIVE,
            },
        )
        return evidence_public, evidence_iplc

    def _ensure_indicator_series(self, indicators, user, org):
        series_list = []
        indicator_map = {indicator.code: indicator for indicator in indicators}
        series_1, _ = IndicatorDataSeries.objects.update_or_create(
            indicator=indicator_map["DEMO-IND-1"],
            defaults={
                "uuid": DEMO_DATA_SERIES["DEMO-SERIES-1"],
                "title": "Demo series IND-1",
                "unit": "count",
                "value_type": "numeric",
                "methodology": "Demo methodology",
                "organisation": org,
                "created_by": user,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
            },
        )
        series_2, _ = IndicatorDataSeries.objects.update_or_create(
            indicator=indicator_map["DEMO-IND-2"],
            defaults={
                "uuid": DEMO_DATA_SERIES["DEMO-SERIES-2"],
                "title": "Demo series IND-2",
                "unit": "count",
                "value_type": "numeric",
                "methodology": "Demo methodology",
                "organisation": org,
                "created_by": user,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
            },
        )
        series_list.extend([series_1, series_2])
        return series_list

    def _ensure_indicator_points(self, series_list, release):
        series_map = {series.title: series for series in series_list}
        series_1 = series_map.get("Demo series IND-1")
        series_2 = series_map.get("Demo series IND-2")
        if series_1:
            IndicatorDataPoint.objects.update_or_create(
                series=series_1,
                year=2020,
                defaults={
                    "uuid": DEMO_DATA_POINTS["DEMO-P1"],
                    "value_numeric": 10,
                    "disaggregation": {},
                    "dataset_release": release,
                    "source_url": "https://example.com/demo-point",
                },
            )
            IndicatorDataPoint.objects.update_or_create(
                series=series_1,
                year=2021,
                defaults={
                    "uuid": DEMO_DATA_POINTS["DEMO-P2"],
                    "value_numeric": 12,
                    "disaggregation": {},
                    "dataset_release": release,
                },
            )
        if series_2:
            IndicatorDataPoint.objects.update_or_create(
                series=series_2,
                year=2020,
                defaults={
                    "uuid": DEMO_DATA_POINTS["DEMO-P3"],
                    "value_numeric": 5,
                    "disaggregation": {},
                    "dataset_release": release,
                },
            )
            IndicatorDataPoint.objects.update_or_create(
                series=series_2,
                year=2021,
                defaults={
                    "uuid": DEMO_DATA_POINTS["DEMO-P4"],
                    "value_numeric": 7,
                    "disaggregation": {},
                    "dataset_release": release,
                },
            )

    def _ensure_section_progress(
        self,
        instance,
        targets,
        framework_targets,
        series_list,
        evidence_public,
        evidence_iplc,
        release,
    ):
        target_map = {target.code: target for target in targets}
        framework_target_map = {target.code: target for target in framework_targets}
        series_map = {series.title: series for series in series_list}
        series_1 = series_map.get("Demo series IND-1")
        series_2 = series_map.get("Demo series IND-2")

        entry_1, _ = SectionIIINationalTargetProgress.objects.update_or_create(
            reporting_instance=instance,
            national_target=target_map["DEMO-NT-1"],
            defaults={
                "uuid": DEMO_SECTION_III["DEMO-III-1"],
                "progress_status": ProgressStatus.IN_PROGRESS,
                "summary": "Progress summary for NT-1",
                "actions_taken": "Actions taken",
                "outcomes": "Outcomes",
                "challenges": "Challenges",
                "support_needed": "Support needed",
                "period_start": DEMO_PERIOD_START,
                "period_end": DEMO_PERIOD_END,
            },
        )
        entry_2, _ = SectionIIINationalTargetProgress.objects.update_or_create(
            reporting_instance=instance,
            national_target=target_map["DEMO-NT-2"],
            defaults={
                "uuid": DEMO_SECTION_III["DEMO-III-2"],
                "progress_status": ProgressStatus.IN_PROGRESS,
                "summary": "Progress summary for NT-2",
                "actions_taken": "Actions taken",
                "outcomes": "Outcomes",
                "challenges": "Challenges",
                "support_needed": "Support needed",
                "period_start": DEMO_PERIOD_START,
                "period_end": DEMO_PERIOD_END,
            },
        )
        entry_1.indicator_data_series.set([series_1] if series_1 else [])
        entry_1.evidence_items.set([evidence_public])
        entry_1.dataset_releases.set([release])

        entry_2.indicator_data_series.set([series_2] if series_2 else [])
        entry_2.evidence_items.set([evidence_iplc])
        entry_2.dataset_releases.set([release])

        section_iv_1, _ = SectionIVFrameworkTargetProgress.objects.update_or_create(
            reporting_instance=instance,
            framework_target=framework_target_map["DEMO-T1"],
            defaults={
                "uuid": DEMO_SECTION_IV["DEMO-IV-1"],
                "progress_status": ProgressStatus.IN_PROGRESS,
                "summary": "Framework target progress 1",
                "actions_taken": "Actions",
                "outcomes": "Outcomes",
                "challenges": "Challenges",
                "support_needed": "Support needed",
                "period_start": DEMO_PERIOD_START,
                "period_end": DEMO_PERIOD_END,
            },
        )
        section_iv_2, _ = SectionIVFrameworkTargetProgress.objects.update_or_create(
            reporting_instance=instance,
            framework_target=framework_target_map["DEMO-T2"],
            defaults={
                "uuid": DEMO_SECTION_IV["DEMO-IV-2"],
                "progress_status": ProgressStatus.IN_PROGRESS,
                "summary": "Framework target progress 2",
                "actions_taken": "Actions",
                "outcomes": "Outcomes",
                "challenges": "Challenges",
                "support_needed": "Support needed",
                "period_start": DEMO_PERIOD_START,
                "period_end": DEMO_PERIOD_END,
            },
        )
        section_iv_1.indicator_data_series.set([series_1] if series_1 else [])
        section_iv_1.evidence_items.set([evidence_public])
        section_iv_1.dataset_releases.set([release])

        section_iv_2.indicator_data_series.set([series_2] if series_2 else [])
        section_iv_2.evidence_items.set([evidence_iplc])
        section_iv_2.dataset_releases.set([release])

    def _ensure_approvals(
        self,
        instance,
        user,
        targets,
        indicators,
        evidence_public,
        evidence_iplc,
        dataset,
        approve_all=False,
    ):
        target_map = {target.code: target for target in targets}
        indicator_map = {indicator.code: indicator for indicator in indicators}

        approve_for_instance(instance, target_map["DEMO-NT-1"], user)
        approve_for_instance(instance, indicator_map["DEMO-IND-1"], user)
        approve_for_instance(instance, evidence_public, user)
        if consent_is_granted(instance, evidence_iplc):
            approve_for_instance(instance, evidence_iplc, user)
        approve_for_instance(instance, dataset, user)

        if approve_all:
            approve_for_instance(instance, target_map["DEMO-NT-2"], user)
            approve_for_instance(instance, indicator_map["DEMO-IND-2"], user)

    def _ensure_consent(self, instance, user, objects):
        for obj in objects:
            if obj and requires_consent(obj):
                set_consent_status(instance, obj, user, ConsentStatus.GRANTED, note="demo consent")

    def _reset_demo(self):
        instance = ReportingInstance.objects.filter(uuid=DEMO_INSTANCE_UUID).first()
        if instance:
            ConsentRecord.objects.filter(reporting_instance=instance).delete()
            InstanceExportApproval.objects.filter(reporting_instance=instance).delete()
            SectionIIINationalTargetProgress.objects.filter(reporting_instance=instance).delete()
            SectionIVFrameworkTargetProgress.objects.filter(reporting_instance=instance).delete()
            instance.delete()

        ReportingCycle.objects.filter(uuid=DEMO_CYCLE_UUID).delete()

        IndicatorDataPoint.objects.filter(uuid__in=DEMO_DATA_POINTS.values()).delete()
        IndicatorDataSeries.objects.filter(uuid__in=DEMO_DATA_SERIES.values()).delete()

        IndicatorFrameworkIndicatorLink.objects.filter(
            indicator__uuid__in=DEMO_INDICATORS.values()
        ).delete()
        NationalTargetFrameworkTargetLink.objects.filter(
            national_target__uuid__in=DEMO_NATIONAL_TARGETS.values()
        ).delete()

        Indicator.objects.filter(uuid__in=DEMO_INDICATORS.values()).delete()
        NationalTarget.objects.filter(uuid__in=DEMO_NATIONAL_TARGETS.values()).delete()

        FrameworkIndicator.objects.filter(code__in=DEMO_FRAMEWORK_INDICATORS.keys()).delete()
        FrameworkTarget.objects.filter(code__in=DEMO_FRAMEWORK_TARGETS.keys()).delete()
        FrameworkGoal.objects.filter(code=DEMO_FRAMEWORK_GOAL_CODE).delete()
        Framework.objects.filter(uuid=DEMO_FRAMEWORK_UUID).delete()

        Evidence.objects.filter(uuid__in=[DEMO_EVIDENCE_PUBLIC_UUID, DEMO_EVIDENCE_IPLC_UUID]).delete()
        DatasetRelease.objects.filter(uuid=DEMO_DATASET_RELEASE_UUID).delete()
        Dataset.objects.filter(uuid=DEMO_DATASET_UUID).delete()

        MethodologyVersion.objects.filter(uuid=DEMO_METHODOLOGY_VERSION_UUID).delete()
        Methodology.objects.filter(uuid=DEMO_METHODOLOGY_UUID).delete()
        MonitoringProgramme.objects.filter(uuid=DEMO_MONITORING_PROGRAMME_UUID).delete()
        DatasetCatalog.objects.filter(uuid=DEMO_DATASET_CATALOG_UUID).delete()

        User.objects.filter(username__in=[DEMO_ADMIN_USERNAME, DEMO_MANAGER_USERNAME, DEMO_PARTNER_USERNAME]).delete()
        Organisation.objects.filter(org_code__in=[DEMO_ORG_A_CODE, DEMO_ORG_B_CODE]).delete()
