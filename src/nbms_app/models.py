import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organisation(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    org_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    org_type = models.CharField(max_length=100, blank=True, null=True)
    parent_org = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="child_organisations",
        blank=True,
        null=True,
    )
    website_url = models.URLField(blank=True)
    primary_contact_name = models.CharField(max_length=255, blank=True)
    primary_contact_email = models.EmailField(blank=True)
    alternative_contact_name = models.CharField(max_length=255, blank=True)
    alternative_contact_email = models.EmailField(blank=True)
    contact_email = models.EmailField(blank=True, null=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

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


class FrameworkIndicatorType(models.TextChoices):
    HEADLINE = "headline", "Headline"
    BINARY = "binary", "Binary"
    COMPONENT = "component", "Component"
    COMPLEMENTARY = "complementary", "Complementary"
    OTHER = "other", "Other"


class IndicatorValueType(models.TextChoices):
    NUMERIC = "numeric", "Numeric"
    PERCENT = "percent", "Percent"
    INDEX = "index", "Index"
    TEXT = "text", "Text"


class ProgressStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not started"
    IN_PROGRESS = "in_progress", "In progress"
    PARTIALLY_ACHIEVED = "partially_achieved", "Partially achieved"
    ACHIEVED = "achieved", "Achieved"
    UNKNOWN = "unknown", "Unknown"


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


class ReviewDecisionStatus(models.TextChoices):
    APPROVED = "approved", "Approved"
    CHANGES_REQUESTED = "changes_requested", "Changes requested"


class AccessLevel(models.TextChoices):
    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Internal"
    RESTRICTED = "restricted", "Restricted"


class UpdateFrequency(models.TextChoices):
    ANNUAL = "annual", "Annual"
    QUARTERLY = "quarterly", "Quarterly"
    MONTHLY = "monthly", "Monthly"
    AD_HOC = "ad_hoc", "Ad hoc"
    CONTINUOUS = "continuous", "Continuous"


class QaStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    REJECTED = "rejected", "Rejected"
    VALIDATED = "validated", "Validated"
    PUBLISHED = "published", "Published"
    DEPRECATED = "deprecated", "Deprecated"


class AgreementType(models.TextChoices):
    MOU = "MOU", "MOU"
    DATA_SHARING = "data_sharing", "Data sharing"
    SLA = "SLA", "SLA"
    LICENCE = "licence", "Licence"
    CUSTOM = "custom", "Custom"


class ProgrammeType(models.TextChoices):
    NATIONAL = "national", "National"
    PROVINCIAL = "provincial", "Provincial"
    DISTRICT_MUNICIPALITY = "district_municipality", "District municipality"
    LOCAL_MUNICIPALITY = "local_municipality", "Local municipality"
    BIOME = "biome", "Biome"
    VEGETATION_TYPE = "vegetation_type", "Vegetation type"
    SITE = "site", "Site"
    PROJECT = "project", "Project"


class MethodologyStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    DEPRECATED = "deprecated", "Deprecated"


class RelationshipType(models.TextChoices):
    LEAD = "lead", "Lead"
    PARTNER = "partner", "Partner"
    SUPPORTING = "supporting", "Supporting"
    CONTEXTUAL = "contextual", "Contextual"
    DERIVED = "derived", "Derived"


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


class ReportingSnapshot(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    snapshot_type = models.CharField(max_length=50, default="NR7_V2_EXPORT")
    payload_json = models.JSONField()
    payload_hash = models.CharField(max_length=64)
    exporter_schema = models.CharField(max_length=100)
    exporter_version = models.CharField(max_length=50)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_reporting_snapshots",
        blank=True,
        null=True,
    )
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Reporting snapshots are immutable.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reporting_instance_id} {self.snapshot_type} {self.created_at:%Y-%m-%d}"

    class Meta:
        indexes = [
            models.Index(fields=["reporting_instance", "created_at"]),
            models.Index(fields=["payload_hash"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["reporting_instance", "payload_hash"],
                name="uq_reporting_snapshot_instance_hash",
            ),
        ]


class ReviewDecision(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="review_decisions",
    )
    snapshot = models.ForeignKey(
        ReportingSnapshot,
        on_delete=models.PROTECT,
        related_name="review_decisions",
    )
    decision = models.CharField(max_length=32, choices=ReviewDecisionStatus.choices)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_review_decisions",
        blank=True,
        null=True,
    )
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="superseded_by",
        blank=True,
        null=True,
    )

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("Review decisions are immutable.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reporting_instance_id} {self.decision} {self.created_at:%Y-%m-%d}"

    class Meta:
        indexes = [
            models.Index(fields=["reporting_instance", "created_at"]),
        ]


class SensitivityClass(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    sensitivity_code = models.CharField(max_length=50, unique=True)
    sensitivity_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    access_level_default = models.CharField(max_length=20, choices=AccessLevel.choices, default=AccessLevel.INTERNAL)
    consent_required_default = models.BooleanField(default=False)
    redaction_policy = models.TextField(blank=True)
    legal_basis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.sensitivity_code} - {self.sensitivity_name}"


class DataAgreement(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    agreement_code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    agreement_type = models.CharField(max_length=50, choices=AgreementType.choices, blank=True)
    status = models.CharField(max_length=50, blank=True)
    parties = models.ManyToManyField(Organisation, related_name="data_agreements", blank=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    licence = models.CharField(max_length=100, blank=True)
    restrictions_summary = models.TextField(blank=True)
    benefit_sharing_terms = models.TextField(blank=True)
    citation_requirement = models.TextField(blank=True)
    document_url = models.URLField(blank=True)
    primary_contact_name = models.CharField(max_length=255, blank=True)
    primary_contact_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.agreement_code} - {self.title}"


class DatasetCatalog(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    dataset_code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    dataset_type = models.CharField(max_length=100, blank=True)
    custodian_org = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="catalog_datasets_custodian",
        blank=True,
        null=True,
    )
    producer_org = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="catalog_datasets_producer",
        blank=True,
        null=True,
    )
    licence = models.CharField(max_length=100, blank=True)
    access_level = models.CharField(max_length=20, choices=AccessLevel.choices, default=AccessLevel.INTERNAL)
    sensitivity_class = models.ForeignKey(
        SensitivityClass,
        on_delete=models.SET_NULL,
        related_name="dataset_catalogs",
        blank=True,
        null=True,
    )
    consent_required = models.BooleanField(default=False)
    agreement = models.ForeignKey(
        DataAgreement,
        on_delete=models.SET_NULL,
        related_name="dataset_catalogs",
        blank=True,
        null=True,
    )
    temporal_start = models.DateField(blank=True, null=True)
    temporal_end = models.DateField(blank=True, null=True)
    update_frequency = models.CharField(max_length=20, choices=UpdateFrequency.choices, blank=True)
    spatial_coverage_description = models.TextField(blank=True)
    spatial_resolution = models.CharField(max_length=100, blank=True)
    taxonomy_standard = models.CharField(max_length=255, blank=True)
    ecosystem_classification = models.CharField(max_length=255, blank=True)
    doi_or_identifier = models.CharField(max_length=255, blank=True)
    landing_page_url = models.URLField(blank=True)
    api_endpoint_url = models.URLField(blank=True)
    file_formats = models.CharField(max_length=255, blank=True)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, blank=True)
    citation = models.TextField(blank=True)
    keywords = models.CharField(max_length=255, blank=True)
    last_updated_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.dataset_code} - {self.title}"


class MonitoringProgramme(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    programme_code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    programme_type = models.CharField(max_length=50, choices=ProgrammeType.choices, blank=True)
    lead_org = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="lead_monitoring_programmes",
        blank=True,
        null=True,
    )
    partners = models.ManyToManyField(Organisation, related_name="partner_monitoring_programmes", blank=True)
    start_year = models.PositiveIntegerField(blank=True, null=True)
    end_year = models.PositiveIntegerField(blank=True, null=True)
    geographic_scope = models.CharField(max_length=255, blank=True)
    spatial_coverage_description = models.TextField(blank=True)
    taxonomic_scope = models.CharField(max_length=255, blank=True)
    ecosystem_scope = models.CharField(max_length=255, blank=True)
    objectives = models.TextField(blank=True)
    sampling_design_summary = models.TextField(blank=True)
    update_frequency = models.CharField(max_length=20, choices=UpdateFrequency.choices, blank=True)
    qa_process_summary = models.TextField(blank=True)
    sensitivity_class = models.ForeignKey(
        SensitivityClass,
        on_delete=models.SET_NULL,
        related_name="monitoring_programmes",
        blank=True,
        null=True,
    )
    consent_required = models.BooleanField(default=False)
    agreement = models.ForeignKey(
        DataAgreement,
        on_delete=models.SET_NULL,
        related_name="monitoring_programmes",
        blank=True,
        null=True,
    )
    website_url = models.URLField(blank=True)
    primary_contact_name = models.CharField(max_length=255, blank=True)
    primary_contact_email = models.EmailField(blank=True)
    alternative_contact_name = models.CharField(max_length=255, blank=True)
    alternative_contact_email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.programme_code} - {self.title}"


class Methodology(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    methodology_code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner_org = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="methodologies",
        blank=True,
        null=True,
    )
    scope = models.CharField(max_length=255, blank=True)
    references_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.methodology_code} - {self.title}"


class MethodologyVersion(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    methodology = models.ForeignKey(Methodology, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=MethodologyStatus.choices, default=MethodologyStatus.DRAFT)
    effective_date = models.DateField(blank=True, null=True)
    deprecated_date = models.DateField(blank=True, null=True)
    change_log = models.TextField(blank=True)
    protocol_url = models.URLField(blank=True)
    computational_script_url = models.URLField(blank=True)
    parameters_json = models.JSONField(default=dict, blank=True)
    qa_steps_summary = models.TextField(blank=True)
    peer_reviewed = models.BooleanField(default=False)
    approval_body = models.CharField(max_length=255, blank=True)
    approval_reference = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.methodology.methodology_code} v{self.version}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["methodology", "version"], name="uq_methodology_version"),
        ]


class ProgrammeDatasetLink(TimeStampedModel):
    programme = models.ForeignKey(MonitoringProgramme, on_delete=models.CASCADE, related_name="dataset_links")
    dataset = models.ForeignKey(DatasetCatalog, on_delete=models.CASCADE, related_name="programme_links")
    relationship_type = models.CharField(max_length=20, choices=RelationshipType.choices, blank=True)
    role = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["programme", "dataset"], name="uq_programme_dataset"),
        ]


class ProgrammeIndicatorLink(TimeStampedModel):
    programme = models.ForeignKey(MonitoringProgramme, on_delete=models.CASCADE, related_name="indicator_links")
    indicator = models.ForeignKey("Indicator", on_delete=models.CASCADE, related_name="programme_links")
    relationship_type = models.CharField(max_length=20, choices=RelationshipType.choices, blank=True)
    role = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["programme", "indicator"], name="uq_programme_indicator"),
        ]


class MethodologyDatasetLink(TimeStampedModel):
    methodology = models.ForeignKey(Methodology, on_delete=models.CASCADE, related_name="dataset_links")
    dataset = models.ForeignKey(DatasetCatalog, on_delete=models.CASCADE, related_name="methodology_links")
    relationship_type = models.CharField(max_length=20, choices=RelationshipType.choices, blank=True)
    role = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["methodology", "dataset"], name="uq_methodology_dataset"),
        ]


class MethodologyIndicatorLink(TimeStampedModel):
    methodology = models.ForeignKey(Methodology, on_delete=models.CASCADE, related_name="indicator_links")
    indicator = models.ForeignKey("Indicator", on_delete=models.CASCADE, related_name="methodology_links")
    relationship_type = models.CharField(max_length=20, choices=RelationshipType.choices, blank=True)
    role = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["methodology", "indicator"], name="uq_methodology_indicator"),
        ]


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


class AlignmentRelationType(models.TextChoices):
    EQUIVALENT = "equivalent", "Equivalent"
    CONTRIBUTES_TO = "contributes_to", "Contributes to"
    PARTIAL = "partial", "Partial"
    SUPPORTS = "supports", "Supports"


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


class Framework(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="frameworks",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_frameworks",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.PUBLISHED)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.PUBLIC)
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


class FrameworkGoal(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name="goals")
    code = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    official_text = models.TextField(blank=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.framework.code} Goal {self.code}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["framework", "code"], name="uq_framework_goal"),
        ]
        ordering = ["framework__code", "sort_order", "code"]


class FrameworkTarget(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name="targets")
    goal = models.ForeignKey(
        FrameworkGoal,
        on_delete=models.SET_NULL,
        related_name="targets",
        blank=True,
        null=True,
    )
    code = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    official_text = models.TextField(blank=True)
    description = models.TextField(blank=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="framework_targets",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_framework_targets",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.PUBLISHED)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.PUBLIC)
    review_note = models.TextField(blank=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.framework.code} {self.code}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["framework", "code"], name="uq_framework_target"),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["created_by"]),
        ]


class FrameworkIndicator(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name="indicators")
    framework_target = models.ForeignKey(
        FrameworkTarget,
        on_delete=models.SET_NULL,
        related_name="framework_indicators",
        blank=True,
        null=True,
    )
    code = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    indicator_type = models.CharField(
        max_length=20,
        choices=FrameworkIndicatorType.choices,
        default=FrameworkIndicatorType.OTHER,
    )
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="framework_indicators",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_framework_indicators",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.PUBLISHED)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.PUBLIC)
    review_note = models.TextField(blank=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.framework.code} {self.code}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["framework", "code"], name="uq_framework_indicator"),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["created_by"]),
        ]


class NationalTargetFrameworkTargetLink(TimeStampedModel):
    national_target = models.ForeignKey(
        NationalTarget,
        on_delete=models.CASCADE,
        related_name="framework_target_links",
    )
    framework_target = models.ForeignKey(
        FrameworkTarget,
        on_delete=models.CASCADE,
        related_name="national_target_links",
    )
    relation_type = models.CharField(
        max_length=50,
        choices=AlignmentRelationType.choices,
        default=AlignmentRelationType.CONTRIBUTES_TO,
    )
    confidence = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    notes = models.TextField(blank=True)
    source = models.URLField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["national_target", "framework_target"],
                name="uq_national_target_framework_target",
            ),
        ]


class IndicatorFrameworkIndicatorLink(TimeStampedModel):
    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.CASCADE,
        related_name="framework_indicator_links",
    )
    framework_indicator = models.ForeignKey(
        FrameworkIndicator,
        on_delete=models.CASCADE,
        related_name="national_indicator_links",
    )
    relation_type = models.CharField(
        max_length=50,
        choices=AlignmentRelationType.choices,
        default=AlignmentRelationType.CONTRIBUTES_TO,
    )
    confidence = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    notes = models.TextField(blank=True)
    source = models.URLField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["indicator", "framework_indicator"],
                name="uq_indicator_framework_indicator",
            ),
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


class IndicatorDataSeries(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    framework_indicator = models.ForeignKey(
        FrameworkIndicator,
        on_delete=models.CASCADE,
        related_name="data_series",
        blank=True,
        null=True,
    )
    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.CASCADE,
        related_name="data_series",
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=255, blank=True)
    unit = models.CharField(max_length=100, blank=True)
    value_type = models.CharField(
        max_length=20,
        choices=IndicatorValueType.choices,
        default=IndicatorValueType.NUMERIC,
    )
    methodology = models.TextField(blank=True)
    disaggregation_schema = models.JSONField(default=dict, blank=True)
    source_notes = models.TextField(blank=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="indicator_data_series",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_indicator_data_series",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    export_approved = models.BooleanField(default=False)
    review_note = models.TextField(blank=True)

    def __str__(self):
        indicator = self.framework_indicator or self.indicator
        return f"Indicator data series {indicator.code if indicator else self.uuid}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(framework_indicator__isnull=False, indicator__isnull=True)
                    | models.Q(framework_indicator__isnull=True, indicator__isnull=False)
                ),
                name="ck_indicator_data_series_single_identity",
            ),
            models.UniqueConstraint(
                fields=["framework_indicator"],
                condition=models.Q(framework_indicator__isnull=False),
                name="uq_indicator_data_series_framework_indicator",
            ),
            models.UniqueConstraint(
                fields=["indicator"],
                condition=models.Q(indicator__isnull=False),
                name="uq_indicator_data_series_indicator",
            ),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["created_by"]),
        ]


class IndicatorDataPoint(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    series = models.ForeignKey(IndicatorDataSeries, on_delete=models.CASCADE, related_name="data_points")
    year = models.PositiveIntegerField()
    value_numeric = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)
    value_text = models.TextField(blank=True, null=True)
    uncertainty = models.TextField(blank=True)
    disaggregation = models.JSONField(default=dict, blank=True)
    dataset_release = models.ForeignKey(
        DatasetRelease,
        on_delete=models.SET_NULL,
        related_name="indicator_data_points",
        blank=True,
        null=True,
    )
    source_url = models.URLField(blank=True)
    footnote = models.TextField(blank=True)

    def __str__(self):
        return f"{self.series_id} {self.year}"

    def clean(self):
        super().clean()
        if not self.series_id:
            return
        if self.series.value_type == IndicatorValueType.TEXT:
            if not self.value_text:
                raise ValidationError("value_text is required for text indicators.")
        else:
            if self.value_numeric is None:
                raise ValidationError("value_numeric is required for numeric indicators.")

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(value_numeric__isnull=False) | models.Q(value_text__isnull=False),
                name="ck_indicator_data_point_value_present",
            )
        ]


class BinaryQuestionType(models.TextChoices):
    OPTION = "option", "Option"
    CHECKBOX = "checkbox", "Checkbox"
    HEADER = "header", "Header"


class BinaryIndicatorQuestion(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    framework_indicator = models.ForeignKey(
        FrameworkIndicator,
        on_delete=models.CASCADE,
        related_name="binary_questions",
    )
    group_key = models.CharField(max_length=100)
    question_key = models.CharField(max_length=100)
    section = models.CharField(max_length=100, blank=True)
    number = models.CharField(max_length=50, blank=True)
    question_type = models.CharField(
        max_length=20,
        choices=BinaryQuestionType.choices,
        default=BinaryQuestionType.OPTION,
    )
    question_text = models.TextField(blank=True)
    help_text = models.TextField(blank=True)
    multiple = models.BooleanField(default=False)
    mandatory = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.framework_indicator.code} {self.question_key}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["framework_indicator", "group_key", "question_key"],
                name="uq_binary_indicator_question",
            ),
        ]
        indexes = [
            models.Index(fields=["framework_indicator"]),
            models.Index(fields=["group_key"]),
        ]


class BinaryIndicatorResponse(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="binary_indicator_responses",
    )
    question = models.ForeignKey(
        BinaryIndicatorQuestion,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    response = models.JSONField(default=list, blank=True)
    comments = models.TextField(blank=True)

    def __str__(self):
        return f"{self.reporting_instance_id} {self.question_id}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporting_instance", "question"],
                name="uq_binary_indicator_response",
            ),
        ]


class SectionIIINationalTargetProgress(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="section_iii_progress_entries",
    )
    national_target = models.ForeignKey(
        NationalTarget,
        on_delete=models.CASCADE,
        related_name="section_iii_progress_entries",
    )
    progress_status = models.CharField(
        max_length=30,
        choices=ProgressStatus.choices,
        default=ProgressStatus.NOT_STARTED,
    )
    summary = models.TextField(blank=True)
    actions_taken = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    support_needed = models.TextField(blank=True)
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)
    indicator_data_series = models.ManyToManyField(
        "IndicatorDataSeries",
        related_name="section_iii_progress_entries",
        blank=True,
    )
    binary_indicator_responses = models.ManyToManyField(
        "BinaryIndicatorResponse",
        related_name="section_iii_progress_entries",
        blank=True,
    )
    evidence_items = models.ManyToManyField(
        "Evidence",
        related_name="section_iii_progress_entries",
        blank=True,
    )
    dataset_releases = models.ManyToManyField(
        "DatasetRelease",
        related_name="section_iii_progress_entries",
        blank=True,
    )

    def __str__(self):
        return f"Section III {self.national_target.code} ({self.reporting_instance_id})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporting_instance", "national_target"],
                name="uq_section_iii_progress",
            ),
        ]


class SectionIVFrameworkTargetProgress(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="section_iv_progress_entries",
    )
    framework_target = models.ForeignKey(
        FrameworkTarget,
        on_delete=models.CASCADE,
        related_name="section_iv_progress_entries",
    )
    progress_status = models.CharField(
        max_length=30,
        choices=ProgressStatus.choices,
        default=ProgressStatus.NOT_STARTED,
    )
    summary = models.TextField(blank=True)
    actions_taken = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    support_needed = models.TextField(blank=True)
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)
    indicator_data_series = models.ManyToManyField(
        "IndicatorDataSeries",
        related_name="section_iv_progress_entries",
        blank=True,
    )
    binary_indicator_responses = models.ManyToManyField(
        "BinaryIndicatorResponse",
        related_name="section_iv_progress_entries",
        blank=True,
    )
    evidence_items = models.ManyToManyField(
        "Evidence",
        related_name="section_iv_progress_entries",
        blank=True,
    )
    dataset_releases = models.ManyToManyField(
        "DatasetRelease",
        related_name="section_iv_progress_entries",
        blank=True,
    )

    def __str__(self):
        return f"Section IV {self.framework_target.code} ({self.reporting_instance_id})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporting_instance", "framework_target"],
                name="uq_section_iv_progress",
            ),
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
