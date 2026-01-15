import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organisation(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    org_type = models.CharField(max_length=100, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="users",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.get_username()


class LifecycleStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending review"
    APPROVED = "approved", "Approved"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class SensitivityLevel(models.TextChoices):
    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Internal"
    RESTRICTED = "restricted", "Restricted"
    IPLC_SENSITIVE = "iplc_sensitive", "IPLC-sensitive"


class ExportStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending review"
    APPROVED = "approved", "Approved"
    RELEASED = "released", "Released"


class ReportingStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending review"
    APPROVED = "approved", "Approved"
    RELEASED = "released", "Released"
    ARCHIVED = "archived", "Archived"


class ReportingCycle(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    due_date = models.DateField()
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} - {self.title}"


class ReportingInstance(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    cycle = models.ForeignKey(ReportingCycle, on_delete=models.CASCADE, related_name="instances")
    version_label = models.CharField(max_length=50, default="v1")
    status = models.CharField(max_length=20, choices=ReportingStatus.choices, default=ReportingStatus.DRAFT)
    frozen_at = models.DateTimeField(blank=True, null=True)
    frozen_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="frozen_reporting_instances",
        blank=True,
        null=True,
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.cycle.code} {self.version_label}"


class ReportSectionTemplate(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    ordering = models.PositiveIntegerField(default=0)
    schema_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordering", "code"]

    def __str__(self):
        return f"{self.code} - {self.title}"


class ReportSectionResponse(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="section_responses",
    )
    template = models.ForeignKey(
        ReportSectionTemplate,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    response_json = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="report_section_responses",
        blank=True,
        null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporting_instance", "template"],
                name="uq_report_section_response",
            ),
        ]

    def __str__(self):
        return f"{self.reporting_instance} - {self.template.code}"


class ValidationScope(models.TextChoices):
    REPORT_TYPE = "report_type", "Report type"
    INSTANCE = "instance", "Instance"
    CYCLE = "cycle", "Cycle"


class ValidationRuleSet(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=100, unique=True)
    applies_to = models.CharField(
        max_length=20,
        choices=ValidationScope.choices,
        default=ValidationScope.REPORT_TYPE,
    )
    rules_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="validation_rule_sets",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.code} ({self.applies_to})"


class ApprovalDecision(models.TextChoices):
    APPROVED = "approved", "Approved"
    REVOKED = "revoked", "Revoked"


class ConsentStatus(models.TextChoices):
    REQUIRED = "required", "Required"
    GRANTED = "granted", "Granted"
    DENIED = "denied", "Denied"
    REVOKED = "revoked", "Revoked"


class ConsentRecord(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_uuid = models.UUIDField()
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.SET_NULL,
        related_name="consent_records",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=ConsentStatus.choices, default=ConsentStatus.REQUIRED)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="consent_records",
        blank=True,
        null=True,
    )
    granted_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    consent_document = models.FileField(upload_to="consent/", blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporting_instance", "content_type", "object_uuid"],
                name="uq_consent_record",
            ),
        ]

class InstanceExportApproval(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_uuid = models.UUIDField()
    decision = models.CharField(max_length=20, choices=ApprovalDecision.choices, default=ApprovalDecision.APPROVED)
    approval_scope = models.CharField(max_length=50, default="export")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="instance_export_approvals",
        blank=True,
        null=True,
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporting_instance", "content_type", "object_uuid", "approval_scope"],
                name="uq_instance_export_approval",
            ),
        ]

class NationalTarget(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="national_targets",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_national_targets",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    export_approved = models.BooleanField(default=False)
    review_note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code} - {self.title}"

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["created_by"]),
        ]


class Indicator(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    national_target = models.ForeignKey(NationalTarget, on_delete=models.CASCADE, related_name="indicators")
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="indicators",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_indicators",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    export_approved = models.BooleanField(default=False)
    review_note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code} - {self.title}"

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["created_by"]),
        ]


class Evidence(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    evidence_type = models.CharField(max_length=100, blank=True)
    source_url = models.URLField(blank=True)
    file = models.FileField(upload_to="evidence/", blank=True, null=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="evidence_items",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_evidence_items",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    export_approved = models.BooleanField(default=False)
    review_note = models.TextField(blank=True)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["created_by"]),
        ]


class Dataset(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    methodology = models.TextField(blank=True)
    source_url = models.URLField(blank=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="datasets",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_datasets",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    export_approved = models.BooleanField(default=False)
    review_note = models.TextField(blank=True)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["created_by"]),
        ]


class DatasetRelease(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="releases")
    version = models.CharField(max_length=50)
    release_date = models.DateField(blank=True, null=True)
    snapshot_title = models.CharField(max_length=255)
    snapshot_description = models.TextField(blank=True)
    snapshot_methodology = models.TextField(blank=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="dataset_releases",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_dataset_releases",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    export_approved = models.BooleanField(default=False)
    review_note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.dataset.title} {self.version}"

    def save(self, *args, **kwargs):
        if self.dataset:
            if not self.snapshot_title:
                self.snapshot_title = self.dataset.title
            if not self.snapshot_description:
                self.snapshot_description = self.dataset.description
            if not self.snapshot_methodology:
                self.snapshot_methodology = self.dataset.methodology
            if not self.organisation:
                self.organisation = self.dataset.organisation
            if not self.created_by:
                self.created_by = self.dataset.created_by
            if not self.sensitivity:
                self.sensitivity = self.dataset.sensitivity
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["created_by"]),
        ]


class IndicatorEvidenceLink(TimeStampedModel):
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name="evidence_links")
    evidence = models.ForeignKey(Evidence, on_delete=models.CASCADE, related_name="indicator_links")
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["indicator", "evidence"], name="uq_indicator_evidence"),
        ]


class IndicatorDatasetLink(TimeStampedModel):
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name="dataset_links")
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="indicator_links")
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["indicator", "dataset"], name="uq_indicator_dataset"),
        ]


class ExportPackage(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ExportStatus.choices, default=ExportStatus.DRAFT)
    review_note = models.TextField(blank=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.SET_NULL,
        related_name="export_packages",
        blank=True,
        null=True,
    )
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="export_packages",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_export_packages",
        blank=True,
        null=True,
    )
    payload = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(blank=True, null=True)
    released_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["created_by"]),
        ]


class AuditEvent(TimeStampedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        blank=True,
        null=True,
    )
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100)
    object_uuid = models.UUIDField()
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.action} {self.object_type} {self.object_uuid}"


class Notification(TimeStampedModel):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.recipient_id}"
