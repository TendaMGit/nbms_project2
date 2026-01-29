from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from nbms_app.models import (
    AuditEvent,
    FrameworkGoal,
    IndicatorMethodologyVersionLink,
    LifecycleStatus,
    MethodologyIndicatorLink,
    MethodologyVersion,
)
from nbms_app.services.audit import record_event


class Command(BaseCommand):
    help = "Verify post-migration and backfill invariants for migration 0026."

    def handle(self, *args, **options):
        errors = []

        missing_event_types = AuditEvent.objects.filter(event_type="").count() + AuditEvent.objects.filter(
            event_type__isnull=True
        ).count()
        if missing_event_types:
            errors.append(f"AuditEvent missing event_type for {missing_event_types} rows.")

        inconsistent_archived = FrameworkGoal.objects.filter(
            status=LifecycleStatus.ARCHIVED, is_active=True
        ).count()
        inconsistent_active = FrameworkGoal.objects.exclude(status=LifecycleStatus.ARCHIVED).filter(
            is_active=False
        ).count()
        if inconsistent_archived or inconsistent_active:
            errors.append(
                f"FrameworkGoal status/is_active mismatch: archived_active={inconsistent_archived}, active_false={inconsistent_active}."
            )

        missing_links = []
        for link in MethodologyIndicatorLink.objects.all():
            versions = MethodologyVersion.objects.filter(methodology_id=link.methodology_id, is_active=True)
            if versions.count() != 1:
                continue
            version = versions.first()
            exists = IndicatorMethodologyVersionLink.objects.filter(
                indicator_id=link.indicator_id, methodology_version_id=version.id
            ).exists()
            if not exists:
                missing_links.append(str(link.indicator_id))
        if missing_links:
            errors.append(
                f"Missing IndicatorMethodologyVersionLink for {len(missing_links)} indicators with exactly one active version."
            )

        redaction_errors = self._verify_audit_redaction()
        if redaction_errors:
            errors.extend(redaction_errors)

        if errors:
            raise CommandError("Post-migration verification failed:\n- " + "\n- ".join(errors))

        self.stdout.write(self.style.SUCCESS("Post-migration verification passed."))

    def _verify_audit_redaction(self):
        errors = []
        User = get_user_model()
        user, _created = User.objects.get_or_create(username="audit-verifier")
        event = None
        try:
            with transaction.atomic():
                record_event(
                    user,
                    "audit_redaction_probe",
                    metadata={
                        "notes": "secret",
                        "payload": {"token": "secret"},
                        "safe": "ok",
                    },
                )
                event = AuditEvent.objects.filter(event_type="audit_redaction_probe").order_by("-created_at").first()
                if not event:
                    errors.append("Audit redaction probe event was not created.")
                else:
                    if event.metadata.get("notes") != "[redacted]":
                        errors.append("Audit redaction failed for notes field.")
                    if event.metadata.get("payload") != "[redacted]":
                        errors.append("Audit redaction failed for payload field.")
                    if event.metadata.get("safe") != "ok":
                        errors.append("Audit redaction unexpectedly modified safe field.")
        finally:
            if event:
                AuditEvent.objects.filter(id=event.id).delete()
        return errors
