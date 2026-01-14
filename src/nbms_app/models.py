import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
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
