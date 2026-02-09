import uuid
from decimal import Decimal
import json

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

from nbms_app import spatial_fields


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

    class Meta:
        permissions = [
            ("system_admin", "System Admin access"),
        ]


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


class NationalIndicatorType(models.TextChoices):
    HEADLINE = "headline", "Headline"
    BINARY = "binary", "Binary"
    COMPONENT = "component", "Component"
    COMPLEMENTARY = "complementary", "Complementary"
    NATIONAL = "national", "National"
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


class ProgressLevel(models.TextChoices):
    ON_TRACK = "on_track", "On track"
    INSUFFICIENT_RATE = "insufficient_rate", "Insufficient rate"
    NO_CHANGE = "no_change", "No change"
    NOT_APPLICABLE = "not_applicable", "Not applicable"
    UNKNOWN = "unknown", "Unknown"
    ACHIEVED = "achieved", "Achieved"


class NbsapStatus(models.TextChoices):
    YES = "yes", "Yes"
    NO = "no", "No"
    IN_PROGRESS = "in_progress", "In progress"
    OTHER = "other", "Other"
    UNKNOWN = "unknown", "Unknown"


class StakeholderInvolvement(models.TextChoices):
    YES = "yes", "Yes"
    NO = "no", "No"
    UNKNOWN = "unknown", "Unknown"


class ExportStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending review"
    APPROVED = "approved", "Approved"
    RELEASED = "released", "Released"


class ReportingStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SECTION_REVIEW = "section_review", "Section review"
    TECHNICAL_REVIEW = "technical_review", "Technical review"
    SECRETARIAT_CONSOLIDATION = "secretariat_consolidation", "Secretariat consolidation"
    PUBLISHING_AUTHORITY_REVIEW = "publishing_authority_review", "Publishing authority review"
    PENDING_REVIEW = "pending_review", "Pending review"
    APPROVED = "approved", "Approved"
    SUBMITTED = "submitted", "Submitted"
    RELEASED = "released", "Released"
    ARCHIVED = "archived", "Archived"


class ReportCommentThreadStatus(models.TextChoices):
    OPEN = "open", "Open"
    RESOLVED = "resolved", "Resolved"


class SuggestedChangeStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"


class ReportWorkflowStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class ReportWorkflowActionType(models.TextChoices):
    SUBMIT = "submit", "Submit"
    REVIEW = "review", "Review"
    APPROVE = "approve", "Approve"
    REJECT = "reject", "Reject"
    TECHNICAL_APPROVE = "technical_approve", "Technical approve"
    CONSOLIDATE = "consolidate", "Consolidate"
    PUBLISHING_APPROVE = "publishing_approve", "Publishing authority approve"
    FINALIZE = "finalize", "Finalize"
    UNLOCK = "unlock", "Unlock"


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


class IndicatorUpdateFrequency(models.TextChoices):
    CONTINUOUS = "continuous", "Continuous"
    ANNUAL = "annual", "Annual"
    BIENNIAL = "biennial", "Biennial"
    EVERY_3_YEARS = "every_3_years", "Every 3 years"
    AD_HOC = "ad_hoc", "Ad hoc"
    UNKNOWN = "unknown", "Unknown"


class IndicatorReportingCapability(models.TextChoices):
    YES = "yes", "Yes"
    PARTIAL = "partial", "Partial"
    NO = "no", "No"
    UNKNOWN = "unknown", "Unknown"


class QaStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    REJECTED = "rejected", "Rejected"
    VALIDATED = "validated", "Validated"
    PUBLISHED = "published", "Published"
    DEPRECATED = "deprecated", "Deprecated"


class IndicatorMethodType(models.TextChoices):
    MANUAL = "manual", "Manual"
    CSV_IMPORT = "csv_import", "CSV import"
    API_CONNECTOR = "api_connector", "API connector"
    SCRIPTED_PYTHON = "scripted_python", "Scripted Python"
    SCRIPTED_R_CONTAINER = "scripted_r_container", "Scripted R container"
    SPATIAL_OVERLAY = "spatial_overlay", "Spatial overlay"
    SEEA_ACCOUNTING = "seea_accounting", "SEEA accounting"
    BINARY_QUESTIONNAIRE = "binary_questionnaire", "Binary questionnaire"


class IndicatorMethodReadiness(models.TextChoices):
    READY = "ready", "Ready"
    PARTIAL = "partial", "Partial"
    BLOCKED = "blocked", "Blocked"


class IndicatorMethodRunStatus(models.TextChoices):
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    BLOCKED = "blocked", "Blocked"


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


class ProgrammeRefreshCadence(models.TextChoices):
    MANUAL = "manual", "Manual"
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"
    ANNUAL = "annual", "Annual"
    AD_HOC = "ad_hoc", "Ad hoc"


class ProgrammeStewardRole(models.TextChoices):
    OWNER = "owner", "Owner"
    STEWARD = "steward", "Steward"
    OPERATOR = "operator", "Operator"
    REVIEWER = "reviewer", "Reviewer"


class ProgrammeRunType(models.TextChoices):
    FULL = "full", "Full"
    INGEST = "ingest", "Ingest"
    VALIDATE = "validate", "Validate"
    COMPUTE = "compute", "Compute"
    PUBLISH = "publish", "Publish"


class ProgrammeRunTrigger(models.TextChoices):
    MANUAL = "manual", "Manual"
    SCHEDULED = "scheduled", "Scheduled"
    INTEGRATION = "integration", "Integration"


class ProgrammeRunStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    BLOCKED = "blocked", "Blocked"
    CANCELLED = "cancelled", "Cancelled"


class ProgrammeStepType(models.TextChoices):
    INGEST = "ingest", "Ingest"
    VALIDATE = "validate", "Validate"
    COMPUTE = "compute", "Compute"
    PUBLISH = "publish", "Publish"


class ProgrammeAlertSeverity(models.TextChoices):
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    ERROR = "error", "Error"
    CRITICAL = "critical", "Critical"


class ProgrammeAlertState(models.TextChoices):
    OPEN = "open", "Open"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    RESOLVED = "resolved", "Resolved"


class ProgrammeQaStatus(models.TextChoices):
    PASS = "pass", "Pass"
    WARN = "warn", "Warn"
    FAIL = "fail", "Fail"


class IntegrationDataLayer(models.TextChoices):
    BRONZE = "bronze", "Bronze"
    SILVER = "silver", "Silver"
    GOLD = "gold", "Gold"


class ReportProductStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    GENERATED = "generated", "Generated"
    FAILED = "failed", "Failed"
    PUBLISHED = "published", "Published"


class RegistryReviewStatus(models.TextChoices):
    NEEDS_REVIEW = "needs_review", "Needs review"
    IN_REVIEW = "in_review", "In review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class IucnRleCategory(models.TextChoices):
    CR = "CR", "Critically Endangered"
    EN = "EN", "Endangered"
    VU = "VU", "Vulnerable"
    NT = "NT", "Near Threatened"
    LC = "LC", "Least Concern"
    DD = "DD", "Data Deficient"
    NE = "NE", "Not Evaluated"
    CO = "CO", "Collapsed"


class TaxonNameType(models.TextChoices):
    ACCEPTED = "accepted", "Accepted"
    SYNONYM = "synonym", "Synonym"
    VERNACULAR = "vernacular", "Vernacular"


class DwcEstablishmentMeans(models.TextChoices):
    NATIVE = "native", "Native"
    INTRODUCED = "introduced", "Introduced"
    INVASIVE = "invasive", "Invasive"
    MANAGED = "managed", "Managed"
    UNKNOWN = "unknown", "Unknown"


class DwcDegreeOfEstablishment(models.TextChoices):
    CAPTIVE = "captive", "Captive/cultivated"
    CASUAL = "casual", "Casual"
    NATURALISED = "naturalised", "Naturalised"
    INVASIVE = "invasive", "Invasive"
    WIDESPREAD_INVASIVE = "widespread_invasive", "Widespread invasive"
    UNKNOWN = "unknown", "Unknown"


class DwcPathwayCategory(models.TextChoices):
    RELEASE = "release", "Release"
    ESCAPE = "escape", "Escape"
    CONTAMINANT = "contaminant", "Contaminant"
    STOWAWAY = "stowaway", "Stowaway"
    CORRIDOR = "corridor", "Corridor"
    UNAIDED = "unaided", "Unaided"
    UNKNOWN = "unknown", "Unknown"


class EicatCategory(models.TextChoices):
    MC = "MC", "Minimal Concern"
    MN = "MN", "Minor"
    MO = "MO", "Moderate"
    MR = "MR", "Major"
    MV = "MV", "Massive"
    DD = "DD", "Data Deficient"
    NE = "NE", "Not Evaluated"
    NA = "NA", "Not Alien"


class SeicatCategory(models.TextChoices):
    MC = "MC", "Minimal Concern"
    MN = "MN", "Minor"
    MO = "MO", "Moderate"
    MR = "MR", "Major"
    MV = "MV", "Massive"
    DD = "DD", "Data Deficient"
    NE = "NE", "Not Evaluated"


class ProgrammeTemplateDomain(models.TextChoices):
    ECOSYSTEMS = "ecosystems", "Ecosystems"
    TAXA = "taxa", "Taxa"
    IAS = "ias", "Invasive alien species"
    PROTECTED_AREAS = "protected_areas", "Protected areas"
    CROSS_DOMAIN = "cross_domain", "Cross domain"


class EcosystemGoldDimension(models.TextChoices):
    PROVINCE = "province", "Province"
    BIOME = "biome", "Biome"
    BIOREGION = "bioregion", "Bioregion"
    THREAT_CATEGORY = "threat_category", "Threat category"


class IASGoldDimension(models.TextChoices):
    HABITAT = "habitat", "Habitat"
    SYSTEM = "system", "System"
    PROVINCE = "province", "Province"


class ReportingCycle(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    due_date = models.DateField()
    submission_window_start = models.DateField(blank=True, null=True)
    submission_window_end = models.DateField(blank=True, null=True)
    default_language = models.CharField(max_length=32, blank=True, default="English")
    allowed_languages = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} - {self.title}"


class ReportingInstance(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    cycle = models.ForeignKey(ReportingCycle, on_delete=models.CASCADE, related_name="instances")
    version_label = models.CharField(max_length=50, default="v1")
    report_title = models.CharField(max_length=255, blank=True)
    country_name = models.CharField(max_length=255, default="South Africa")
    focal_point_org = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="focal_point_reporting_instances",
        blank=True,
        null=True,
    )
    publishing_authority_org = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="publishing_authority_reporting_instances",
        blank=True,
        null=True,
    )
    is_public = models.BooleanField(default=False)
    status = models.CharField(max_length=40, choices=ReportingStatus.choices, default=ReportingStatus.DRAFT)
    frozen_at = models.DateTimeField(blank=True, null=True)
    frozen_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="frozen_reporting_instances",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_reporting_instances",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_reporting_instances",
        blank=True,
        null=True,
    )
    final_content_hash = models.CharField(max_length=64, blank=True)
    finalized_at = models.DateTimeField(blank=True, null=True)
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
    readiness_report_json = models.JSONField(default=dict, blank=True)
    readiness_overall_ready = models.BooleanField(default=False)
    readiness_blocking_gap_count = models.PositiveIntegerField(default=0)
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


class License(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class SourceDocument(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)
    citation = models.TextField(blank=True)
    version_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="source_documents",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.title or self.source_url or str(self.uuid)


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
    operating_institutions = models.ManyToManyField(
        Organisation,
        related_name="operating_monitoring_programmes",
        blank=True,
    )
    stewards = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="MonitoringProgrammeSteward",
        related_name="stewarded_monitoring_programmes",
        blank=True,
    )
    coverage_units = models.ManyToManyField(
        "SpatialUnit",
        related_name="coverage_programmes",
        blank=True,
    )
    start_year = models.PositiveIntegerField(blank=True, null=True)
    end_year = models.PositiveIntegerField(blank=True, null=True)
    geographic_scope = models.CharField(max_length=255, blank=True)
    spatial_coverage_description = models.TextField(blank=True)
    taxonomic_scope = models.CharField(max_length=255, blank=True)
    ecosystem_scope = models.CharField(max_length=255, blank=True)
    objectives = models.TextField(blank=True)
    sampling_design_summary = models.TextField(blank=True)
    update_frequency = models.CharField(max_length=20, choices=UpdateFrequency.choices, blank=True)
    refresh_cadence = models.CharField(
        max_length=20,
        choices=ProgrammeRefreshCadence.choices,
        default=ProgrammeRefreshCadence.MANUAL,
    )
    scheduler_enabled = models.BooleanField(default=False)
    next_run_at = models.DateTimeField(blank=True, null=True)
    last_run_at = models.DateTimeField(blank=True, null=True)
    pipeline_definition_json = models.JSONField(default=dict, blank=True)
    data_quality_rules_json = models.JSONField(default=dict, blank=True)
    lineage_notes = models.TextField(blank=True)
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


class MonitoringProgrammeSteward(TimeStampedModel):
    programme = models.ForeignKey(
        MonitoringProgramme,
        on_delete=models.CASCADE,
        related_name="steward_assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="monitoring_programme_assignments",
    )
    role = models.CharField(max_length=20, choices=ProgrammeStewardRole.choices, default=ProgrammeStewardRole.STEWARD)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["programme", "user", "role"], name="uq_programme_steward_assignment"),
        ]
        indexes = [
            models.Index(fields=["programme", "is_active"]),
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.programme.programme_code}:{self.user_id}:{self.role}"


class MonitoringProgrammeRun(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    programme = models.ForeignKey(
        MonitoringProgramme,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    run_type = models.CharField(max_length=20, choices=ProgrammeRunType.choices, default=ProgrammeRunType.FULL)
    trigger = models.CharField(max_length=20, choices=ProgrammeRunTrigger.choices, default=ProgrammeRunTrigger.MANUAL)
    status = models.CharField(max_length=20, choices=ProgrammeRunStatus.choices, default=ProgrammeRunStatus.QUEUED)
    dry_run = models.BooleanField(default=False)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="requested_programme_runs",
        blank=True,
        null=True,
    )
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    input_summary_json = models.JSONField(default=dict, blank=True)
    output_summary_json = models.JSONField(default=dict, blank=True)
    artifacts_json = models.JSONField(default=list, blank=True)
    lineage_json = models.JSONField(default=dict, blank=True)
    log_excerpt = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    request_id = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["programme", "created_at"]),
            models.Index(fields=["programme", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["run_type"]),
        ]

    def __str__(self):
        return f"{self.programme.programme_code}:{self.uuid}:{self.status}"


class MonitoringProgrammeRunStep(TimeStampedModel):
    run = models.ForeignKey(
        MonitoringProgrammeRun,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    ordering = models.PositiveIntegerField(default=0)
    step_key = models.CharField(max_length=50)
    step_type = models.CharField(max_length=20, choices=ProgrammeStepType.choices)
    status = models.CharField(max_length=20, choices=ProgrammeRunStatus.choices, default=ProgrammeRunStatus.QUEUED)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    details_json = models.JSONField(default=dict, blank=True)
    log_excerpt = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "ordering"], name="uq_programme_run_step_ordering"),
            models.UniqueConstraint(fields=["run", "step_key"], name="uq_programme_run_step_key"),
        ]
        indexes = [
            models.Index(fields=["run", "ordering"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["ordering", "id"]

    def __str__(self):
        return f"{self.run_id}:{self.step_key}:{self.status}"


class MonitoringProgrammeArtefactRef(TimeStampedModel):
    run = models.ForeignKey(
        MonitoringProgrammeRun,
        on_delete=models.CASCADE,
        related_name="artefacts",
    )
    step = models.ForeignKey(
        MonitoringProgrammeRunStep,
        on_delete=models.SET_NULL,
        related_name="artefacts",
        blank=True,
        null=True,
    )
    label = models.CharField(max_length=120)
    storage_path = models.CharField(max_length=512)
    media_type = models.CharField(max_length=120, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["run", "created_at"]),
            models.Index(fields=["step", "created_at"]),
            models.Index(fields=["label"]),
        ]

    def __str__(self):
        return f"{self.run_id}:{self.label}"


class MonitoringProgrammeQAResult(TimeStampedModel):
    run = models.ForeignKey(
        MonitoringProgrammeRun,
        on_delete=models.CASCADE,
        related_name="qa_results",
    )
    step = models.ForeignKey(
        MonitoringProgrammeRunStep,
        on_delete=models.SET_NULL,
        related_name="qa_results",
        blank=True,
        null=True,
    )
    code = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=ProgrammeQaStatus.choices, default=ProgrammeQaStatus.PASS)
    message = models.TextField()
    details_json = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["run", "status"]),
            models.Index(fields=["step", "status"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"{self.run_id}:{self.code}:{self.status}"


class MonitoringProgrammeAlert(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    programme = models.ForeignKey(
        MonitoringProgramme,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    run = models.ForeignKey(
        MonitoringProgrammeRun,
        on_delete=models.SET_NULL,
        related_name="alerts",
        blank=True,
        null=True,
    )
    severity = models.CharField(
        max_length=20,
        choices=ProgrammeAlertSeverity.choices,
        default=ProgrammeAlertSeverity.WARNING,
    )
    state = models.CharField(max_length=20, choices=ProgrammeAlertState.choices, default=ProgrammeAlertState.OPEN)
    code = models.CharField(max_length=100)
    message = models.TextField()
    details_json = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_programme_alerts",
        blank=True,
        null=True,
    )
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="resolved_programme_alerts",
        blank=True,
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["programme", "state"]),
            models.Index(fields=["programme", "severity"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.programme.programme_code}:{self.code}:{self.state}"


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


class IndicatorMethodologyVersionLink(TimeStampedModel):
    indicator = models.ForeignKey("Indicator", on_delete=models.CASCADE, related_name="methodology_version_links")
    methodology_version = models.ForeignKey(
        MethodologyVersion,
        on_delete=models.CASCADE,
        related_name="indicator_links",
    )
    is_primary = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    source = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["indicator", "methodology_version"],
                name="uq_indicator_methodology_version",
            ),
        ]


class DatasetCatalogIndicatorLink(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    dataset = models.ForeignKey(DatasetCatalog, on_delete=models.CASCADE, related_name="indicator_links")
    indicator = models.ForeignKey("Indicator", on_delete=models.CASCADE, related_name="dataset_catalog_links")
    relationship_type = models.CharField(max_length=20, choices=RelationshipType.choices, blank=True)
    role = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["dataset", "indicator"], name="uq_dataset_catalog_indicator"),
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


class SectionIReportContext(TimeStampedModel):
    reporting_instance = models.OneToOneField(
        "ReportingInstance",
        on_delete=models.CASCADE,
        related_name="section_i_context",
    )
    reporting_party_name = models.CharField(max_length=255)
    submission_language = models.CharField(max_length=64)
    additional_languages = models.JSONField(default=list, blank=True)
    responsible_authorities = models.TextField(blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    preparation_process = models.TextField(blank=True)
    preparation_challenges = models.TextField(blank=True)
    acknowledgements = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="section_i_updates",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"Section I context ({self.reporting_instance_id})"


class SectionIINBSAPStatus(TimeStampedModel):
    reporting_instance = models.OneToOneField(
        "ReportingInstance",
        on_delete=models.CASCADE,
        related_name="section_ii_status",
    )
    nbsap_updated_status = models.CharField(
        max_length=20,
        choices=NbsapStatus.choices,
        default=NbsapStatus.UNKNOWN,
    )
    nbsap_updated_other_text = models.TextField(blank=True)
    nbsap_expected_completion_date = models.DateField(blank=True, null=True)

    stakeholders_involved = models.CharField(
        max_length=20,
        choices=StakeholderInvolvement.choices,
        default=StakeholderInvolvement.UNKNOWN,
    )
    stakeholder_groups = models.JSONField(default=list, blank=True)
    stakeholder_groups_other_text = models.TextField(blank=True)
    stakeholder_groups_notes = models.TextField(blank=True)

    nbsap_adopted_status = models.CharField(
        max_length=20,
        choices=NbsapStatus.choices,
        default=NbsapStatus.UNKNOWN,
    )
    nbsap_adopted_other_text = models.TextField(blank=True)
    nbsap_adoption_mechanism = models.TextField(blank=True)
    nbsap_expected_adoption_date = models.DateField(blank=True, null=True)

    monitoring_system_description = models.TextField()
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="section_ii_updates",
        blank=True,
        null=True,
    )

    STAKEHOLDER_GROUP_OPTIONS = {
        "women",
        "youth",
        "indigenous_and_local_communities",
        "private_sector",
        "scientific_community",
        "civil_society_organizations",
        "local_and_subnational_government",
        "other",
        "other_stakeholders",
    }

    def clean(self):
        super().clean()
        errors = {}

        if self.nbsap_updated_status in {NbsapStatus.NO, NbsapStatus.IN_PROGRESS} and not self.nbsap_expected_completion_date:
            errors["nbsap_expected_completion_date"] = (
                "Completion date is required for no or in-progress status."
            )
        if self.nbsap_updated_status == NbsapStatus.OTHER and not self.nbsap_updated_other_text.strip():
            errors["nbsap_updated_other_text"] = "Please specify the other NBSAP update status."

        if self.stakeholders_involved == StakeholderInvolvement.YES and not self.stakeholder_groups:
            errors["stakeholder_groups"] = "Select at least one stakeholder group."
        if self.stakeholder_groups:
            invalid_groups = set(self.stakeholder_groups) - self.STAKEHOLDER_GROUP_OPTIONS
            if invalid_groups:
                errors["stakeholder_groups"] = (
                    "Invalid stakeholder groups: " + ", ".join(sorted(invalid_groups))
                )
        if {"other", "other_stakeholders"} & set(self.stakeholder_groups or []) and not self.stakeholder_groups_other_text.strip():
            errors["stakeholder_groups_other_text"] = "Please specify the other stakeholder group."

        if self.nbsap_adopted_status in {NbsapStatus.YES, NbsapStatus.IN_PROGRESS} and not self.nbsap_adoption_mechanism.strip():
            errors["nbsap_adoption_mechanism"] = "Adoption mechanism is required for adopted or in-progress status."
        if self.nbsap_adopted_status in {NbsapStatus.IN_PROGRESS, NbsapStatus.NO, NbsapStatus.OTHER} and not self.nbsap_expected_adoption_date:
            errors["nbsap_expected_adoption_date"] = (
                "Expected adoption date is required for no, other, or in-progress status."
            )
        if self.nbsap_adopted_status in {NbsapStatus.NO, NbsapStatus.OTHER} and not self.nbsap_adopted_other_text.strip():
            errors["nbsap_adopted_other_text"] = "Please specify the adoption details for no/other status."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Section II status ({self.reporting_instance_id})"


class SectionIVFrameworkGoalProgress(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        "ReportingInstance",
        on_delete=models.CASCADE,
        related_name="section_iv_goal_progress_entries",
    )
    framework_goal = models.ForeignKey(
        "FrameworkGoal",
        on_delete=models.CASCADE,
        related_name="section_iv_progress_entries",
    )
    progress_summary = models.TextField()
    actions_taken = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    challenges_and_approaches = models.TextField(blank=True)
    sdg_and_other_agreements = models.TextField(blank=True)
    evidence_items = models.ManyToManyField(
        "Evidence",
        related_name="section_iv_goal_progress_entries",
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="section_iv_goal_updates",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"Section IV goal {self.framework_goal.code} ({self.reporting_instance_id})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporting_instance", "framework_goal"],
                name="uq_section_iv_goal_progress",
            ),
        ]


class SectionVConclusions(TimeStampedModel):
    reporting_instance = models.OneToOneField(
        "ReportingInstance",
        on_delete=models.CASCADE,
        related_name="section_v_conclusions",
    )
    overall_assessment = models.TextField()
    decision_15_8_information = models.TextField(blank=True)
    decision_15_7_information = models.TextField(blank=True)
    decision_15_11_information = models.TextField(blank=True)
    plant_conservation_information = models.TextField(blank=True)
    additional_notes = models.TextField(blank=True)
    evidence_items = models.ManyToManyField(
        "Evidence",
        related_name="section_v_conclusions",
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="section_v_updates",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"Section V conclusions ({self.reporting_instance_id})"


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
    responsible_org = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="responsible_national_targets",
        blank=True,
        null=True,
    )
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.DRAFT)
    reporting_cadence = models.CharField(max_length=20, choices=UpdateFrequency.choices, blank=True)
    source_document = models.ForeignKey(
        SourceDocument,
        on_delete=models.SET_NULL,
        related_name="national_targets",
        blank=True,
        null=True,
    )
    license = models.ForeignKey(
        License,
        on_delete=models.SET_NULL,
        related_name="national_targets",
        blank=True,
        null=True,
    )
    provenance_notes = models.TextField(blank=True)
    spatial_coverage = models.TextField(blank=True)
    temporal_coverage = models.TextField(blank=True)
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
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

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
    indicator_type = models.CharField(
        max_length=20,
        choices=NationalIndicatorType.choices,
        default=NationalIndicatorType.OTHER,
    )
    reporting_cadence = models.CharField(max_length=20, choices=UpdateFrequency.choices, blank=True)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.DRAFT)
    responsible_org = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="responsible_indicators",
        blank=True,
        null=True,
    )
    data_steward = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="stewarded_indicators",
        blank=True,
        null=True,
    )
    indicator_lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="lead_indicators",
        blank=True,
        null=True,
    )
    source_document = models.ForeignKey(
        SourceDocument,
        on_delete=models.SET_NULL,
        related_name="indicators",
        blank=True,
        null=True,
    )
    license = models.ForeignKey(
        License,
        on_delete=models.SET_NULL,
        related_name="indicators",
        blank=True,
        null=True,
    )
    computation_notes = models.TextField(blank=True)
    limitations = models.TextField(blank=True)
    spatial_coverage = models.TextField(blank=True)
    temporal_coverage = models.TextField(blank=True)
    reporting_capability = models.CharField(
        max_length=20,
        choices=IndicatorReportingCapability.choices,
        default=IndicatorReportingCapability.UNKNOWN,
        blank=True,
    )
    reporting_no_reason_codes = models.JSONField(default=list, blank=True)
    reporting_no_reason_notes = models.TextField(blank=True)
    owner_organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="owned_indicators",
        blank=True,
        null=True,
    )
    update_frequency = models.CharField(
        max_length=20,
        choices=IndicatorUpdateFrequency.choices,
        default=IndicatorUpdateFrequency.UNKNOWN,
        blank=True,
    )
    last_updated_on = models.DateField(blank=True, null=True)
    coverage_geography = models.TextField(blank=True)
    coverage_time_start_year = models.IntegerField(blank=True, null=True)
    coverage_time_end_year = models.IntegerField(blank=True, null=True)
    data_quality_note = models.TextField(blank=True)
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
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.code} - {self.title}"

    REPORTING_NO_REASON_OPTIONS = {
        "no_data",
        "no_method",
        "no_owner",
        "no_mandate",
        "confidentiality_or_consent",
        "not_applicable",
        "other",
    }

    def clean(self):
        super().clean()
        errors = {}

        if not self.reporting_capability:
            self.reporting_capability = IndicatorReportingCapability.UNKNOWN

        codes = self.reporting_no_reason_codes
        if codes is None or codes == "":
            codes = []
        if not isinstance(codes, list):
            errors["reporting_no_reason_codes"] = "Reason codes must be a list of values."
        else:
            invalid = set(codes) - self.REPORTING_NO_REASON_OPTIONS
            if invalid:
                errors["reporting_no_reason_codes"] = (
                    "Invalid reason codes: " + ", ".join(sorted(invalid))
                )

        if self.reporting_capability == IndicatorReportingCapability.NO:
            if not codes:
                errors["reporting_no_reason_codes"] = (
                    "At least one reason code is required when reporting capability is no."
                )
        elif self.reporting_capability in {
            IndicatorReportingCapability.YES,
            IndicatorReportingCapability.PARTIAL,
        }:
            if codes:
                errors["reporting_no_reason_codes"] = (
                    "Reason codes are only allowed when reporting capability is no."
                )

        if (
            self.coverage_time_start_year
            and self.coverage_time_end_year
            and self.coverage_time_end_year < self.coverage_time_start_year
        ):
            errors["coverage_time_end_year"] = "End year cannot be earlier than start year."

        if errors:
            raise ValidationError(errors)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["created_by"]),
        ]


class IndicatorMethodProfile(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.CASCADE,
        related_name="method_profiles",
    )
    method_type = models.CharField(max_length=40, choices=IndicatorMethodType.choices)
    implementation_key = models.CharField(max_length=120, blank=True)
    summary = models.TextField(blank=True)
    required_inputs_json = models.JSONField(default=list, blank=True)
    disaggregation_requirements_json = models.JSONField(default=list, blank=True)
    output_schema_json = models.JSONField(default=dict, blank=True)
    readiness_state = models.CharField(
        max_length=20,
        choices=IndicatorMethodReadiness.choices,
        default=IndicatorMethodReadiness.BLOCKED,
    )
    readiness_notes = models.TextField(blank=True)
    last_run_at = models.DateTimeField(blank=True, null=True)
    last_success_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["indicator", "method_type", "implementation_key"],
                name="uq_indicator_method_profile",
            ),
        ]
        indexes = [
            models.Index(fields=["method_type", "is_active"]),
            models.Index(fields=["readiness_state"]),
        ]

    def __str__(self):
        impl = self.implementation_key or self.method_type
        return f"{self.indicator.code}:{impl}"


class IndicatorMethodRun(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    profile = models.ForeignKey(
        IndicatorMethodProfile,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    status = models.CharField(
        max_length=20,
        choices=IndicatorMethodRunStatus.choices,
        default=IndicatorMethodRunStatus.BLOCKED,
    )
    parameters_json = models.JSONField(default=dict, blank=True)
    input_hash = models.CharField(max_length=128, blank=True)
    output_json = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="indicator_method_runs",
        blank=True,
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["profile", "created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.profile_id}:{self.status}"


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
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="framework_goals",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_framework_goals",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.PUBLISHED)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.PUBLIC)
    review_note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.framework.code} Goal {self.code}"

    def save(self, *args, **kwargs):
        if hasattr(self, "status"):
            self.is_active = self.status != LifecycleStatus.ARCHIVED
            update_fields = kwargs.get("update_fields")
            if update_fields is not None and "status" in update_fields and "is_active" not in update_fields:
                update_fields = {field for field in update_fields}
                update_fields.add("is_active")
                kwargs["update_fields"] = list(update_fields)
        return super().save(*args, **kwargs)

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

    def clean(self):
        super().clean()
        if self.goal_id and self.framework_id and self.goal.framework_id != self.framework_id:
            raise ValidationError({"goal": "Goal must belong to the same framework as the target."})

    def save(self, *args, **kwargs):
        validate = kwargs.pop("validate", True)
        if validate:
            self.full_clean()
        return super().save(*args, **kwargs)

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

    def clean(self):
        super().clean()
        if (
            self.framework_target_id
            and self.framework_id
            and self.framework_target.framework_id != self.framework_id
        ):
            raise ValidationError(
                {"framework_target": "Framework target must belong to the same framework as the indicator."}
            )

    def save(self, *args, **kwargs):
        validate = kwargs.pop("validate", True)
        if validate:
            self.full_clean()
        return super().save(*args, **kwargs)

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
    is_active = models.BooleanField(default=True)

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
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["indicator", "framework_indicator"],
                name="uq_indicator_framework_indicator",
            ),
        ]


class Evidence(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    evidence_code = models.CharField(max_length=80, unique=True, blank=True, null=True)
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
        return self.evidence_code or self.title

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["created_by"]),
        ]


class Dataset(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    dataset_code = models.CharField(max_length=80, unique=True, blank=True, null=True)
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
        return self.dataset_code or self.title

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
    series_code = models.CharField(max_length=100, unique=True, blank=True, null=True)
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
    spatial_unit_type = models.ForeignKey(
        "SpatialUnitType",
        on_delete=models.SET_NULL,
        related_name="indicator_data_series",
        blank=True,
        null=True,
    )
    spatial_layer = models.ForeignKey(
        "SpatialLayer",
        on_delete=models.SET_NULL,
        related_name="indicator_data_series",
        blank=True,
        null=True,
    )
    spatial_resolution = models.CharField(max_length=120, blank=True)
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
            models.Index(fields=["series_code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["spatial_unit_type"]),
            models.Index(fields=["spatial_layer"]),
        ]


class IndicatorDataPoint(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    series = models.ForeignKey(IndicatorDataSeries, on_delete=models.CASCADE, related_name="data_points")
    year = models.PositiveIntegerField()
    value_numeric = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)
    value_text = models.TextField(blank=True, null=True)
    uncertainty = models.TextField(blank=True)
    disaggregation = models.JSONField(default=dict, blank=True)
    spatial_unit = models.ForeignKey(
        "SpatialUnit",
        on_delete=models.SET_NULL,
        related_name="indicator_data_points",
        blank=True,
        null=True,
    )
    spatial_layer = models.ForeignKey(
        "SpatialLayer",
        on_delete=models.SET_NULL,
        related_name="indicator_data_points",
        blank=True,
        null=True,
    )
    spatial_resolution = models.CharField(max_length=120, blank=True)
    dataset_release = models.ForeignKey(
        DatasetRelease,
        on_delete=models.SET_NULL,
        related_name="indicator_data_points",
        blank=True,
        null=True,
    )
    programme_run = models.ForeignKey(
        MonitoringProgrammeRun,
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
        indexes = [
            models.Index(fields=["series", "year"]),
            models.Index(fields=["spatial_unit"]),
            models.Index(fields=["spatial_layer"]),
            models.Index(fields=["programme_run"]),
        ]


class BinaryIndicatorGroup(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    key = models.CharField(max_length=64, unique=True)
    framework_target = models.ForeignKey(
        FrameworkTarget,
        on_delete=models.SET_NULL,
        related_name="binary_indicator_groups",
        blank=True,
        null=True,
    )
    framework_indicator = models.ForeignKey(
        FrameworkIndicator,
        on_delete=models.SET_NULL,
        related_name="binary_indicator_groups",
        blank=True,
        null=True,
    )
    target_code = models.CharField(max_length=50, blank=True)
    binary_indicator_code = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=255, blank=True)
    ordering = models.IntegerField(default=0)
    source_ref = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.key

    class Meta:
        indexes = [
            models.Index(fields=["framework_target"]),
            models.Index(fields=["framework_indicator"]),
        ]


class BinaryIndicatorGroupResponse(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="binary_indicator_group_responses",
    )
    group = models.ForeignKey(
        BinaryIndicatorGroup,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    comments = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="binary_indicator_group_responses",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.reporting_instance_id} {self.group_id}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporting_instance", "group"],
                name="uq_binary_indicator_group_response",
            ),
        ]


class BinaryQuestionType(models.TextChoices):
    SINGLE = "single", "Single"
    MULTIPLE = "multiple", "Multiple"
    TEXT = "text", "Text"


class BinaryIndicatorQuestion(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    framework_indicator = models.ForeignKey(
        FrameworkIndicator,
        on_delete=models.CASCADE,
        related_name="binary_questions",
    )
    group = models.ForeignKey(
        BinaryIndicatorGroup,
        on_delete=models.SET_NULL,
        related_name="questions",
        blank=True,
        null=True,
    )
    parent_question = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="child_questions",
        blank=True,
        null=True,
    )
    group_key = models.CharField(max_length=100)
    question_key = models.CharField(max_length=100)
    section = models.CharField(max_length=100, blank=True)
    number = models.CharField(max_length=50, blank=True)
    question_type = models.CharField(
        max_length=20,
        choices=BinaryQuestionType.choices,
        default=BinaryQuestionType.SINGLE,
    )
    question_text = models.TextField(blank=True)
    help_text = models.TextField(blank=True)
    multiple = models.BooleanField(default=False)
    mandatory = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    validations = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

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
    progress_level = models.CharField(
        max_length=30,
        choices=ProgressLevel.choices,
        default=ProgressLevel.UNKNOWN,
    )
    summary = models.TextField(blank=True)
    actions_taken = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    challenges_and_approaches = models.TextField(blank=True)
    effectiveness_examples = models.TextField(blank=True)
    sdg_and_other_agreements = models.TextField(blank=True)
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
    progress_level = models.CharField(
        max_length=30,
        choices=ProgressLevel.choices,
        default=ProgressLevel.UNKNOWN,
    )
    summary = models.TextField(blank=True)
    actions_taken = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    challenges_and_approaches = models.TextField(blank=True)
    effectiveness_examples = models.TextField(blank=True)
    sdg_and_other_agreements = models.TextField(blank=True)
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
    event_type = models.CharField(max_length=100, blank=True)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        blank=True,
        null=True,
    )
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    object_uuid = models.UUIDField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    request_path = models.CharField(max_length=255, blank=True)
    request_method = models.CharField(max_length=16, blank=True)
    ip_address = models.CharField(max_length=64, blank=True)
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=64, blank=True)
    request_id = models.CharField(max_length=64, blank=True)

    def __str__(self):
        label = self.event_type or self.action
        return f"{label} {self.object_type or '-'} {self.object_uuid or ''}".strip()


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


class SpatialLayerSourceType(models.TextChoices):
    NBMS_TABLE = "NBMS_TABLE", "NBMS table"
    UPLOADED_FILE = "UPLOADED_FILE", "Uploaded file"
    EXTERNAL_WMS = "EXTERNAL_WMS", "External WMS"
    EXTERNAL_WFS = "EXTERNAL_WFS", "External WFS"
    EXTERNAL_STAC = "EXTERNAL_STAC", "External STAC"
    EXTERNAL_TILE = "EXTERNAL_TILE", "External tile"
    STATIC = "static", "Static (legacy)"
    INDICATOR = "indicator", "Indicator (legacy)"


class SpatialUnitGeomType(models.TextChoices):
    POINT = "point", "Point"
    LINE = "line", "Line"
    POLYGON = "polygon", "Polygon"
    GEOMETRY = "geometry", "Geometry"


class SpatialIngestionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class SpatialSourceSyncStatus(models.TextChoices):
    READY = "ready", "Ready"
    SKIPPED = "skipped", "Skipped"
    BLOCKED = "blocked", "Blocked"
    FAILED = "failed", "Failed"


class SpatialSourceFormat(models.TextChoices):
    GEOJSON = "GeoJSON", "GeoJSON"
    GPKG = "GPKG", "GeoPackage"
    SHAPEFILE = "ESRI Shapefile", "ESRI Shapefile"
    ZIP_SHAPEFILE = "ZIP_ESRI_SHP", "ZIP Shapefile"
    OTHER = "OTHER", "Other"


class SpatialUnitType(TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    default_geom_type = models.CharField(
        max_length=20,
        choices=SpatialUnitGeomType.choices,
        default=SpatialUnitGeomType.POLYGON,
    )
    admin_level = models.PositiveIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class SpatialUnit(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    unit_code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=255)
    unit_type = models.ForeignKey(
        SpatialUnitType,
        on_delete=models.PROTECT,
        related_name="units",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="children",
        blank=True,
        null=True,
    )
    geom = spatial_fields.MultiPolygonField(srid=4326, blank=True, null=True)
    bbox = spatial_fields.PolygonField(srid=4326, blank=True, null=True)
    area_km2 = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)
    centroid = spatial_fields.PointField(srid=4326, blank=True, null=True)
    properties = models.JSONField(default=dict, blank=True)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.PUBLIC)
    consent_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="spatial_units",
        blank=True,
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["unit_code"]),
            models.Index(fields=["unit_type", "is_active"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
            spatial_fields.GistIndex(fields=["geom"], name="nbms_spatial_unit_geom_gix"),
        ]
        ordering = ["unit_type__code", "unit_code"]

    def save(self, *args, **kwargs):
        if self.geom and hasattr(self.geom, "envelope"):
            self.bbox = self.geom.envelope
            self.centroid = self.geom.centroid
            try:
                metric = self.geom.clone()
                metric.transform(6933)
                self.area_km2 = Decimal(str(round(metric.area / 1000000.0, 6)))
            except Exception:
                self.area_km2 = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.unit_code} - {self.name}"


class SpatialIngestionRun(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    run_id = models.CharField(max_length=80, unique=True)
    layer = models.ForeignKey(
        "SpatialLayer",
        on_delete=models.CASCADE,
        related_name="ingestion_runs",
    )
    source = models.ForeignKey(
        "SpatialSource",
        on_delete=models.SET_NULL,
        related_name="ingestion_runs",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=SpatialIngestionStatus.choices,
        default=SpatialIngestionStatus.PENDING,
    )
    source_filename = models.CharField(max_length=255, blank=True)
    source_format = models.CharField(max_length=50, blank=True)
    source_hash = models.CharField(max_length=64, blank=True)
    source_storage_path = models.CharField(max_length=512, blank=True)
    source_layer_name = models.CharField(max_length=255, blank=True)
    rows_ingested = models.PositiveIntegerField(default=0)
    invalid_geom_before_fix = models.PositiveIntegerField(default=0)
    invalid_geom_after_fix = models.PositiveIntegerField(default=0)
    report_json = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="spatial_ingestion_runs",
        blank=True,
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["layer", "created_at"]),
            models.Index(fields=["source", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.run_id}:{self.status}"


class SpatialSource(TimeStampedModel):
    code = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    source_url = models.URLField()
    source_format = models.CharField(max_length=40, choices=SpatialSourceFormat.choices, default=SpatialSourceFormat.OTHER)
    source_layer_name = models.CharField(max_length=255, blank=True)
    license = models.CharField(max_length=255, blank=True)
    attribution = models.CharField(max_length=255, blank=True)
    terms_url = models.URLField(blank=True)
    requires_token = models.BooleanField(default=False)
    token_env_var = models.CharField(max_length=120, blank=True)
    update_frequency = models.CharField(max_length=20, choices=UpdateFrequency.choices, blank=True)
    enabled_by_default = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    source_type = models.CharField(
        max_length=30,
        choices=SpatialLayerSourceType.choices,
        default=SpatialLayerSourceType.UPLOADED_FILE,
    )
    layer_code = models.CharField(max_length=100, unique=True)
    layer_title = models.CharField(max_length=255, blank=True)
    layer_description = models.TextField(blank=True)
    theme = models.CharField(max_length=60, blank=True)
    default_style_json = models.JSONField(default=dict, blank=True)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.PUBLIC)
    consent_required = models.BooleanField(default=False)
    export_approved = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    publish_to_geoserver = models.BooleanField(default=True)
    expected_checksum = models.CharField(max_length=64, blank=True)
    clip_bbox = models.CharField(max_length=120, blank=True)
    country_iso3 = models.CharField(max_length=3, blank=True)
    last_sync_at = models.DateTimeField(blank=True, null=True)
    last_checksum = models.CharField(max_length=64, blank=True)
    last_status = models.CharField(
        max_length=20,
        choices=SpatialSourceSyncStatus.choices,
        default=SpatialSourceSyncStatus.READY,
    )
    last_error = models.TextField(blank=True)
    last_feature_count = models.PositiveIntegerField(default=0)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="spatial_sources",
        blank=True,
        null=True,
    )
    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.SET_NULL,
        related_name="spatial_sources",
        blank=True,
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["enabled_by_default", "is_active"]),
            models.Index(fields=["layer_code"]),
            models.Index(fields=["publish_to_geoserver"]),
            models.Index(fields=["country_iso3"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["theme"]),
        ]
        ordering = ["code"]

    def __str__(self):
        return self.code


class SpatialLayer(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    layer_code = models.CharField(max_length=100, unique=True, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    source_type = models.CharField(
        max_length=30,
        choices=SpatialLayerSourceType.choices,
        default=SpatialLayerSourceType.NBMS_TABLE,
    )
    data_ref = models.CharField(max_length=255, blank=True)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.PUBLIC)
    consent_required = models.BooleanField(default=False)
    export_approved = models.BooleanField(default=False)
    publish_to_geoserver = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    theme = models.CharField(max_length=60, blank=True)
    default_style_json = models.JSONField(default=dict, blank=True)
    attribution = models.CharField(max_length=255, blank=True)
    license = models.CharField(max_length=255, blank=True)
    temporal_extent = models.JSONField(default=dict, blank=True)
    update_frequency = models.CharField(max_length=20, choices=UpdateFrequency.choices, blank=True)
    source_file = models.FileField(upload_to="spatial/uploads/", blank=True, null=True)
    source_file_hash = models.CharField(max_length=64, blank=True)
    geoserver_layer_name = models.CharField(max_length=160, blank=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="spatial_layers",
        blank=True,
        null=True,
    )
    spatial_source = models.ForeignKey(
        "SpatialSource",
        on_delete=models.SET_NULL,
        related_name="layers",
        blank=True,
        null=True,
    )
    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.SET_NULL,
        related_name="spatial_layers",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_spatial_layers",
        blank=True,
        null=True,
    )
    latest_ingestion_run = models.ForeignKey(
        SpatialIngestionRun,
        on_delete=models.SET_NULL,
        related_name="latest_for_layers",
        blank=True,
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["layer_code"]),
            models.Index(fields=["theme"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "is_public"]),
            models.Index(fields=["publish_to_geoserver"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["organisation"]),
        ]

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = self.name
        if not self.name:
            self.name = self.title
        if not self.layer_code:
            if self.slug:
                self.layer_code = self.slug.upper().replace("-", "_")
            elif self.title:
                self.layer_code = slugify(self.title).replace("-", "_").upper()
        if not self.slug and self.layer_code:
            self.slug = slugify(self.layer_code)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title or self.name


class IndicatorInputRequirement(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    indicator = models.OneToOneField(
        Indicator,
        on_delete=models.CASCADE,
        related_name="input_requirement",
    )
    required_map_layers = models.ManyToManyField(
        "SpatialLayer",
        related_name="indicator_input_requirements",
        blank=True,
    )
    required_map_sources = models.ManyToManyField(
        "SpatialSource",
        related_name="indicator_input_requirements",
        blank=True,
    )
    disaggregation_expectations_json = models.JSONField(default=dict, blank=True)
    cadence = models.CharField(max_length=20, choices=UpdateFrequency.choices, blank=True)
    notes = models.TextField(blank=True)
    last_checked_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["cadence"]),
        ]

    def __str__(self):
        return f"{self.indicator.code}:input-requirements"


class IndicatorRegistryCoverageRequirement(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    indicator = models.OneToOneField(
        Indicator,
        on_delete=models.CASCADE,
        related_name="registry_coverage_requirement",
    )
    require_ecosystem_registry = models.BooleanField(default=False)
    require_taxon_registry = models.BooleanField(default=False)
    require_ias_registry = models.BooleanField(default=False)
    min_ecosystem_count = models.PositiveIntegerField(default=1)
    min_taxon_count = models.PositiveIntegerField(default=1)
    min_ias_count = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    last_checked_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["require_ecosystem_registry", "require_taxon_registry", "require_ias_registry"]),
        ]

    def __str__(self):
        return f"{self.indicator.code}:registry-coverage"


def _extract_coords(node):
    if isinstance(node, (list, tuple)):
        if len(node) >= 2 and isinstance(node[0], (int, float)) and isinstance(node[1], (int, float)):
            yield float(node[0]), float(node[1])
        else:
            for item in node:
                yield from _extract_coords(item)


def _bbox_from_geojson(geometry):
    if not isinstance(geometry, dict):
        return None
    coords = list(_extract_coords(geometry.get("coordinates")))
    if not coords:
        return None
    xs = [coord[0] for coord in coords]
    ys = [coord[1] for coord in coords]
    return min(xs), min(ys), max(xs), max(ys)


class SpatialFeature(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    layer = models.ForeignKey(
        SpatialLayer,
        on_delete=models.CASCADE,
        related_name="features",
    )
    feature_id = models.CharField(max_length=160, blank=True)
    feature_key = models.CharField(max_length=120)
    name = models.CharField(max_length=255, blank=True)
    province_code = models.CharField(max_length=20, blank=True)
    year = models.PositiveIntegerField(blank=True, null=True)
    indicator = models.ForeignKey(
        Indicator,
        on_delete=models.SET_NULL,
        related_name="spatial_features",
        blank=True,
        null=True,
    )
    spatial_unit = models.ForeignKey(
        SpatialUnit,
        on_delete=models.SET_NULL,
        related_name="spatial_features",
        blank=True,
        null=True,
    )
    geom = spatial_fields.GeometryField(srid=4326, blank=True, null=True)
    properties = models.JSONField(default=dict, blank=True)
    valid_from = models.DateField(blank=True, null=True)
    valid_to = models.DateField(blank=True, null=True)
    properties_json = models.JSONField(default=dict, blank=True)
    geometry_json = models.JSONField(default=dict, blank=True)
    minx = models.FloatField(blank=True, null=True)
    miny = models.FloatField(blank=True, null=True)
    maxx = models.FloatField(blank=True, null=True)
    maxy = models.FloatField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["layer", "feature_key"], name="uq_spatial_feature_layer_key"),
            models.UniqueConstraint(
                fields=["layer", "feature_id"],
                condition=~models.Q(feature_id=""),
                name="uq_spatial_feature_layer_id",
            ),
        ]
        indexes = [
            models.Index(fields=["layer", "feature_key"]),
            models.Index(fields=["layer", "feature_id"]),
            models.Index(fields=["province_code"]),
            models.Index(fields=["year"]),
            models.Index(fields=["indicator"]),
            models.Index(fields=["spatial_unit"]),
            models.Index(fields=["minx", "maxx"]),
            models.Index(fields=["miny", "maxy"]),
            GinIndex(fields=["properties"], name="nbms_spatial_feature_props_gin"),
            spatial_fields.GistIndex(fields=["geom"], name="nbms_spatial_feature_geom_gix"),
        ]

    def save(self, *args, **kwargs):
        if not self.feature_id:
            self.feature_id = self.feature_key
        if not self.feature_key:
            self.feature_key = self.feature_id
        if self.properties_json and not self.properties:
            self.properties = self.properties_json
        if self.properties and not self.properties_json:
            self.properties_json = self.properties
        if self.geom and not self.geometry_json and hasattr(self.geom, "geojson"):
            self.geometry_json = json.loads(self.geom.geojson) if self.geom.geojson else {}
        elif self.geometry_json and not self.geom and spatial_fields.GIS_ENABLED:
            try:
                from django.contrib.gis.geos import GEOSGeometry

                self.geom = GEOSGeometry(str(self.geometry_json), srid=4326)
            except Exception:
                self.geom = None

        bbox = _bbox_from_geojson(self.geometry_json)
        if bbox:
            self.minx, self.miny, self.maxx, self.maxy = bbox
        elif self.geom and hasattr(self.geom, "extent"):
            self.minx, self.miny, self.maxx, self.maxy = self.geom.extent
        super().save(*args, **kwargs)

    def __str__(self):
        return self.feature_id or self.feature_key


class IucnGetNode(TimeStampedModel):
    code = models.CharField(max_length=80, unique=True)
    level = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)])
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="children",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["level", "code"]),
            models.Index(fields=["is_active"]),
        ]
        ordering = ["level", "code"]

    def __str__(self):
        return f"L{self.level} {self.code}"


class EcosystemType(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ecosystem_code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    realm = models.CharField(max_length=120, blank=True)
    biome = models.CharField(max_length=255, blank=True)
    bioregion = models.CharField(max_length=255, blank=True)
    vegmap_version = models.CharField(max_length=80, blank=True)
    vegmap_source_id = models.CharField(max_length=120, blank=True)
    get_node = models.ForeignKey(
        IucnGetNode,
        on_delete=models.SET_NULL,
        related_name="ecosystem_types",
        blank=True,
        null=True,
    )
    description = models.TextField(blank=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="ecosystem_types",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_ecosystem_types",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.DRAFT)
    export_approved = models.BooleanField(default=False)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["ecosystem_code"]),
            models.Index(fields=["realm", "biome"]),
            models.Index(fields=["bioregion"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["qa_status"]),
            models.Index(fields=["organisation"]),
        ]
        ordering = ["ecosystem_code", "name"]

    def __str__(self):
        return f"{self.ecosystem_code} - {self.name}"


class EcosystemTypologyCrosswalk(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ecosystem_type = models.ForeignKey(
        EcosystemType,
        on_delete=models.CASCADE,
        related_name="typology_crosswalks",
    )
    get_node = models.ForeignKey(
        IucnGetNode,
        on_delete=models.CASCADE,
        related_name="ecosystem_crosswalks",
    )
    confidence = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    evidence = models.TextField(blank=True)
    review_status = models.CharField(
        max_length=20,
        choices=RegistryReviewStatus.choices,
        default=RegistryReviewStatus.NEEDS_REVIEW,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_ecosystem_crosswalks",
        blank=True,
        null=True,
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.DRAFT)
    export_approved = models.BooleanField(default=False)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ecosystem_type", "get_node"], name="uq_ecosystem_crosswalk_mapping"),
        ]
        indexes = [
            models.Index(fields=["ecosystem_type", "review_status"]),
            models.Index(fields=["get_node", "review_status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
        ]
        ordering = ["ecosystem_type__ecosystem_code", "-is_primary", "-confidence", "get_node__code"]

    def __str__(self):
        return f"{self.ecosystem_type.ecosystem_code}->{self.get_node.code}"


class EcosystemRiskAssessment(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ecosystem_type = models.ForeignKey(
        EcosystemType,
        on_delete=models.CASCADE,
        related_name="risk_assessments",
    )
    assessment_year = models.PositiveIntegerField()
    assessment_scope = models.CharField(max_length=120, default="national")
    category = models.CharField(max_length=4, choices=IucnRleCategory.choices, default=IucnRleCategory.NE)
    criterion_a = models.CharField(max_length=255, blank=True)
    criterion_b = models.CharField(max_length=255, blank=True)
    criterion_c = models.CharField(max_length=255, blank=True)
    criterion_d = models.CharField(max_length=255, blank=True)
    criterion_e = models.CharField(max_length=255, blank=True)
    evidence = models.TextField(blank=True)
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ecosystem_risk_assessments_assessed",
        blank=True,
        null=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ecosystem_risk_assessments_reviewed",
        blank=True,
        null=True,
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    review_status = models.CharField(
        max_length=20,
        choices=RegistryReviewStatus.choices,
        default=RegistryReviewStatus.NEEDS_REVIEW,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.DRAFT)
    export_approved = models.BooleanField(default=False)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ecosystem_type", "assessment_year", "assessment_scope"],
                name="uq_ecosystem_risk_assessment_scope_year",
            ),
        ]
        indexes = [
            models.Index(fields=["assessment_year", "category"]),
            models.Index(fields=["review_status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
        ]
        ordering = ["-assessment_year", "ecosystem_type__ecosystem_code"]

    def __str__(self):
        return f"{self.ecosystem_type.ecosystem_code}:{self.assessment_year}:{self.category}"


class TaxonConcept(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    taxon_code = models.CharField(max_length=120, unique=True)
    scientific_name = models.CharField(max_length=255)
    canonical_name = models.CharField(max_length=255, blank=True)
    taxon_rank = models.CharField(max_length=80, blank=True)
    taxonomic_status = models.CharField(max_length=80, blank=True)
    kingdom = models.CharField(max_length=120, blank=True)
    phylum = models.CharField(max_length=120, blank=True)
    class_name = models.CharField(max_length=120, blank=True)
    order = models.CharField(max_length=120, blank=True)
    family = models.CharField(max_length=120, blank=True)
    genus = models.CharField(max_length=120, blank=True)
    species = models.CharField(max_length=120, blank=True)
    gbif_taxon_key = models.BigIntegerField(blank=True, null=True)
    gbif_usage_key = models.BigIntegerField(blank=True, null=True)
    gbif_accepted_taxon_key = models.BigIntegerField(blank=True, null=True)
    primary_source_system = models.CharField(max_length=120, blank=True)
    is_native = models.BooleanField(blank=True, null=True)
    is_endemic = models.BooleanField(default=False)
    has_national_voucher_specimen = models.BooleanField(default=False)
    voucher_specimen_count = models.PositiveIntegerField(default=0)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="taxon_concepts",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_taxon_concepts",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.DRAFT)
    export_approved = models.BooleanField(default=False)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["taxon_code"]),
            models.Index(fields=["taxon_rank", "taxonomic_status"]),
            models.Index(fields=["kingdom", "family", "genus"]),
            models.Index(fields=["gbif_taxon_key"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["qa_status"]),
            models.Index(fields=["organisation"]),
        ]
        ordering = ["scientific_name", "taxon_rank", "taxon_code"]

    def __str__(self):
        return f"{self.taxon_code} - {self.scientific_name}"


class TaxonName(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    taxon = models.ForeignKey(
        TaxonConcept,
        on_delete=models.CASCADE,
        related_name="names",
    )
    name = models.CharField(max_length=255)
    name_type = models.CharField(max_length=20, choices=TaxonNameType.choices, default=TaxonNameType.SYNONYM)
    language = models.CharField(max_length=20, blank=True)
    is_preferred = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.PUBLIC)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["taxon", "name", "name_type", "language"],
                name="uq_taxon_name_variant",
            ),
        ]
        indexes = [
            models.Index(fields=["taxon", "name_type"]),
            models.Index(fields=["language"]),
            models.Index(fields=["is_preferred"]),
        ]
        ordering = ["taxon__taxon_code", "-is_preferred", "name_type", "name"]

    def __str__(self):
        return f"{self.taxon.taxon_code}:{self.name}"


class TaxonSourceRecord(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    taxon = models.ForeignKey(
        TaxonConcept,
        on_delete=models.CASCADE,
        related_name="source_records",
    )
    source_system = models.CharField(max_length=100)
    source_ref = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)
    retrieved_at = models.DateTimeField()
    payload_json = models.JSONField(default=dict, blank=True)
    payload_hash = models.CharField(max_length=64, blank=True)
    licence = models.CharField(max_length=255, blank=True)
    citation = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.DRAFT)
    export_approved = models.BooleanField(default=False)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="taxon_source_records",
        blank=True,
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["taxon", "source_system"]),
            models.Index(fields=["retrieved_at"]),
            models.Index(fields=["is_primary"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
        ]
        ordering = ["-retrieved_at", "source_system", "id"]

    def __str__(self):
        return f"{self.taxon.taxon_code}:{self.source_system}:{self.retrieved_at.date()}"


class SpecimenVoucher(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    taxon = models.ForeignKey(
        TaxonConcept,
        on_delete=models.CASCADE,
        related_name="specimen_vouchers",
    )
    institution_code = models.CharField(max_length=80, blank=True)
    collection_code = models.CharField(max_length=80, blank=True)
    catalog_number = models.CharField(max_length=120, blank=True)
    occurrence_id = models.CharField(max_length=255, unique=True)
    basis_of_record = models.CharField(max_length=120, blank=True)
    recorded_by = models.CharField(max_length=255, blank=True)
    event_date = models.DateField(blank=True, null=True)
    country_code = models.CharField(max_length=2, default="ZA")
    locality = models.TextField(blank=True)
    decimal_latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    decimal_longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    coordinate_uncertainty_m = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    has_sensitive_locality = models.BooleanField(default=False)
    consent_required = models.BooleanField(default=False)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="specimen_vouchers",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_specimen_vouchers",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.RESTRICTED)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.DRAFT)
    export_approved = models.BooleanField(default=False)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["taxon", "country_code"]),
            models.Index(fields=["institution_code", "catalog_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
            models.Index(fields=["qa_status"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["has_sensitive_locality"]),
        ]
        ordering = ["taxon__taxon_code", "-event_date", "occurrence_id"]

    def __str__(self):
        return self.occurrence_id


class AlienTaxonProfile(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    taxon = models.ForeignKey(
        TaxonConcept,
        on_delete=models.CASCADE,
        related_name="alien_profiles",
    )
    country_code = models.CharField(max_length=2, default="ZA")
    establishment_means_code = models.CharField(
        max_length=40,
        choices=DwcEstablishmentMeans.choices,
        default=DwcEstablishmentMeans.UNKNOWN,
    )
    establishment_means_label = models.CharField(max_length=120, blank=True)
    degree_of_establishment_code = models.CharField(
        max_length=40,
        choices=DwcDegreeOfEstablishment.choices,
        default=DwcDegreeOfEstablishment.UNKNOWN,
    )
    degree_of_establishment_label = models.CharField(max_length=120, blank=True)
    pathway_code = models.CharField(max_length=40, choices=DwcPathwayCategory.choices, default=DwcPathwayCategory.UNKNOWN)
    pathway_label = models.CharField(max_length=120, blank=True)
    habitat_types_json = models.JSONField(default=list, blank=True)
    regulatory_status = models.CharField(max_length=120, blank=True)
    is_invasive = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="alien_taxon_profiles",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_alien_taxon_profiles",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.DRAFT)
    export_approved = models.BooleanField(default=False)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["taxon", "country_code"], name="uq_alien_taxon_profile_country"),
        ]
        indexes = [
            models.Index(fields=["country_code", "is_invasive"]),
            models.Index(fields=["establishment_means_code"]),
            models.Index(fields=["degree_of_establishment_code"]),
            models.Index(fields=["pathway_code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
        ]
        ordering = ["taxon__taxon_code", "country_code"]

    def __str__(self):
        return f"{self.taxon.taxon_code}:{self.country_code}"


class EICATAssessment(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    profile = models.ForeignKey(
        AlienTaxonProfile,
        on_delete=models.CASCADE,
        related_name="eicat_assessments",
    )
    category = models.CharField(max_length=3, choices=EicatCategory.choices, default=EicatCategory.NE)
    mechanisms_json = models.JSONField(default=list, blank=True)
    impact_scope = models.CharField(max_length=120, blank=True)
    confidence = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    uncertainty_notes = models.TextField(blank=True)
    evidence = models.TextField(blank=True)
    assessed_on = models.DateField(blank=True, null=True)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="eicat_assessed_rows",
        blank=True,
        null=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="eicat_reviewed_rows",
        blank=True,
        null=True,
    )
    review_status = models.CharField(
        max_length=20,
        choices=RegistryReviewStatus.choices,
        default=RegistryReviewStatus.NEEDS_REVIEW,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.DRAFT)
    export_approved = models.BooleanField(default=False)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["profile", "category"]),
            models.Index(fields=["review_status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
        ]
        ordering = ["profile__taxon__taxon_code", "-assessed_on", "id"]

    def __str__(self):
        return f"EICAT {self.profile.taxon.taxon_code}:{self.category}"


class SEICATAssessment(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    profile = models.ForeignKey(
        AlienTaxonProfile,
        on_delete=models.CASCADE,
        related_name="seicat_assessments",
    )
    category = models.CharField(max_length=3, choices=SeicatCategory.choices, default=SeicatCategory.NE)
    wellbeing_constituents_json = models.JSONField(default=list, blank=True)
    activity_change_narrative = models.TextField(blank=True)
    confidence = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    uncertainty_notes = models.TextField(blank=True)
    evidence = models.TextField(blank=True)
    assessed_on = models.DateField(blank=True, null=True)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="seicat_assessed_rows",
        blank=True,
        null=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="seicat_reviewed_rows",
        blank=True,
        null=True,
    )
    review_status = models.CharField(
        max_length=20,
        choices=RegistryReviewStatus.choices,
        default=RegistryReviewStatus.NEEDS_REVIEW,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.DRAFT)
    export_approved = models.BooleanField(default=False)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["profile", "category"]),
            models.Index(fields=["review_status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
        ]
        ordering = ["profile__taxon__taxon_code", "-assessed_on", "id"]

    def __str__(self):
        return f"SEICAT {self.profile.taxon.taxon_code}:{self.category}"


class IASCountryChecklistRecord(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    taxon = models.ForeignKey(
        TaxonConcept,
        on_delete=models.SET_NULL,
        related_name="ias_country_records",
        blank=True,
        null=True,
    )
    scientific_name = models.CharField(max_length=255)
    canonical_name = models.CharField(max_length=255, blank=True)
    country_code = models.CharField(max_length=2, default="ZA")
    source_dataset = models.CharField(max_length=120, blank=True)
    source_identifier = models.CharField(max_length=255)
    is_alien = models.BooleanField(default=True)
    is_invasive = models.BooleanField(default=False)
    establishment_means_code = models.CharField(
        max_length=40,
        choices=DwcEstablishmentMeans.choices,
        default=DwcEstablishmentMeans.UNKNOWN,
    )
    degree_of_establishment_code = models.CharField(
        max_length=40,
        choices=DwcDegreeOfEstablishment.choices,
        default=DwcDegreeOfEstablishment.UNKNOWN,
    )
    pathway_code = models.CharField(max_length=40, choices=DwcPathwayCategory.choices, default=DwcPathwayCategory.UNKNOWN)
    remarks = models.TextField(blank=True)
    retrieved_at = models.DateTimeField(blank=True, null=True)
    payload_json = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.DRAFT)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.DRAFT)
    export_approved = models.BooleanField(default=False)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_system", "source_identifier"],
                name="uq_ias_country_record_source_identifier",
            ),
        ]
        indexes = [
            models.Index(fields=["country_code", "is_invasive"]),
            models.Index(fields=["establishment_means_code"]),
            models.Index(fields=["degree_of_establishment_code"]),
            models.Index(fields=["pathway_code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
        ]
        ordering = ["scientific_name", "source_identifier"]

    def __str__(self):
        return f"{self.country_code}:{self.scientific_name}"


class RegistryEvidenceLink(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="registry_evidence_links")
    object_uuid = models.UUIDField()
    evidence = models.ForeignKey(
        Evidence,
        on_delete=models.CASCADE,
        related_name="registry_object_links",
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_registry_evidence_links",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.PUBLISHED)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_uuid", "evidence"],
                name="uq_registry_evidence_link",
            ),
        ]
        indexes = [
            models.Index(fields=["content_type", "object_uuid"]),
            models.Index(fields=["evidence"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
        ]
        ordering = ["content_type", "object_uuid", "evidence__title", "id"]

    def __str__(self):
        return f"{self.content_type_id}:{self.object_uuid}:{self.evidence_id}"


class TaxonGoldSummary(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    snapshot_date = models.DateField()
    taxon_rank = models.CharField(max_length=80, blank=True)
    is_native = models.BooleanField(blank=True, null=True)
    is_endemic = models.BooleanField(default=False)
    has_voucher = models.BooleanField(default=False)
    is_ias = models.BooleanField(default=False)
    taxon_count = models.PositiveIntegerField(default=0)
    voucher_count = models.PositiveIntegerField(default=0)
    ias_profile_count = models.PositiveIntegerField(default=0)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="taxon_gold_summaries",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.PUBLISHED)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.PUBLIC)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "snapshot_date",
                    "taxon_rank",
                    "is_native",
                    "is_endemic",
                    "has_voucher",
                    "is_ias",
                    "organisation",
                ],
                name="uq_taxon_gold_summary_dims",
            ),
        ]
        indexes = [
            models.Index(fields=["snapshot_date", "taxon_rank"]),
            models.Index(fields=["is_native", "is_endemic"]),
            models.Index(fields=["has_voucher", "is_ias"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
        ]
        ordering = ["-snapshot_date", "taxon_rank", "organisation_id"]

    def __str__(self):
        return f"{self.snapshot_date}:{self.taxon_rank or 'unknown'}:{self.taxon_count}"


class EcosystemGoldSummary(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    snapshot_date = models.DateField()
    dimension = models.CharField(
        max_length=30,
        choices=EcosystemGoldDimension.choices,
        default=EcosystemGoldDimension.BIOME,
    )
    dimension_key = models.CharField(max_length=120)
    dimension_label = models.CharField(max_length=255, blank=True)
    ecosystem_count = models.PositiveIntegerField(default=0)
    threatened_count = models.PositiveIntegerField(default=0)
    total_area_km2 = models.DecimalField(max_digits=16, decimal_places=3, default=Decimal("0"))
    protected_area_km2 = models.DecimalField(max_digits=16, decimal_places=3, default=Decimal("0"))
    protected_percent = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal("0"))
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="ecosystem_gold_summaries",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.PUBLISHED)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.PUBLIC)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot_date", "dimension", "dimension_key", "organisation"],
                name="uq_ecosystem_gold_summary_dims",
            ),
        ]
        indexes = [
            models.Index(fields=["snapshot_date", "dimension"]),
            models.Index(fields=["dimension_key"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
        ]
        ordering = ["-snapshot_date", "dimension", "dimension_key"]

    def __str__(self):
        return f"{self.snapshot_date}:{self.dimension}:{self.dimension_key}"


class IASGoldSummary(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    snapshot_date = models.DateField()
    dimension = models.CharField(max_length=20, choices=IASGoldDimension.choices, default=IASGoldDimension.HABITAT)
    dimension_key = models.CharField(max_length=120)
    dimension_label = models.CharField(max_length=255, blank=True)
    eicat_category = models.CharField(max_length=3, choices=EicatCategory.choices, default=EicatCategory.NE)
    seicat_category = models.CharField(max_length=3, choices=SeicatCategory.choices, default=SeicatCategory.NE)
    profile_count = models.PositiveIntegerField(default=0)
    invasive_count = models.PositiveIntegerField(default=0)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="ias_gold_summaries",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.PUBLISHED)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.PUBLIC)
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot_date", "dimension", "dimension_key", "eicat_category", "seicat_category", "organisation"],
                name="uq_ias_gold_summary_dims",
            ),
        ]
        indexes = [
            models.Index(fields=["snapshot_date", "dimension"]),
            models.Index(fields=["dimension_key"]),
            models.Index(fields=["eicat_category", "seicat_category"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
        ]
        ordering = ["-snapshot_date", "dimension", "dimension_key", "eicat_category", "seicat_category"]

    def __str__(self):
        return (
            f"{self.snapshot_date}:{self.dimension}:{self.dimension_key}:"
            f"{self.eicat_category}/{self.seicat_category}"
        )


class ProgrammeTemplate(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    template_code = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    domain = models.CharField(max_length=40, choices=ProgrammeTemplateDomain.choices, default=ProgrammeTemplateDomain.CROSS_DOMAIN)
    pipeline_definition_json = models.JSONField(default=dict, blank=True)
    required_outputs_json = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=LifecycleStatus.choices, default=LifecycleStatus.PUBLISHED)
    sensitivity = models.CharField(max_length=20, choices=SensitivityLevel.choices, default=SensitivityLevel.PUBLIC)
    qa_status = models.CharField(max_length=20, choices=QaStatus.choices, default=QaStatus.PUBLISHED)
    export_approved = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        related_name="programme_templates",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_programme_templates",
        blank=True,
        null=True,
    )
    source_system = models.CharField(max_length=100, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["template_code"]),
            models.Index(fields=["domain", "is_active"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sensitivity"]),
        ]
        ordering = ["domain", "template_code"]

    def __str__(self):
        return self.template_code


class ReportTemplatePack(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    mea_code = models.CharField(max_length=50)
    version = models.CharField(max_length=30, default="v1")
    description = models.TextField(blank=True)
    framework = models.ForeignKey(
        Framework,
        on_delete=models.SET_NULL,
        related_name="template_packs",
        blank=True,
        null=True,
    )
    export_handler = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["mea_code", "is_active"]),
        ]

    def __str__(self):
        return f"{self.code} ({self.version})"


class ReportTemplatePackSection(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    pack = models.ForeignKey(
        ReportTemplatePack,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    code = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    ordering = models.PositiveIntegerField(default=0)
    schema_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pack", "code"], name="uq_template_pack_section_code"),
        ]
        ordering = ["pack__code", "ordering", "code"]

    def __str__(self):
        return f"{self.pack.code}:{self.code}"


class ReportTemplatePackResponse(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="template_pack_responses",
    )
    section = models.ForeignKey(
        ReportTemplatePackSection,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    response_json = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="template_pack_responses",
        blank=True,
        null=True,
    )
    current_version = models.PositiveIntegerField(default=1)
    current_content_hash = models.CharField(max_length=64, blank=True)
    locked_for_editing = models.BooleanField(default=False)
    locked_at = models.DateTimeField(blank=True, null=True)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="locked_template_pack_responses",
        blank=True,
        null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporting_instance", "section"],
                name="uq_template_pack_response",
            ),
        ]

    def __str__(self):
        return f"{self.reporting_instance_id}:{self.section_id}"


class ReportSectionRevision(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    section_response = models.ForeignKey(
        ReportTemplatePackResponse,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    version = models.PositiveIntegerField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="report_section_revisions",
        blank=True,
        null=True,
    )
    content_snapshot = models.JSONField(default=dict, blank=True)
    content_hash = models.CharField(max_length=64)
    parent_hash = models.CharField(max_length=64, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["section_response", "version"],
                name="uq_report_section_revision_version",
            ),
            models.UniqueConstraint(
                fields=["section_response", "content_hash"],
                name="uq_report_section_revision_hash",
            ),
        ]
        indexes = [
            models.Index(fields=["section_response", "version"]),
            models.Index(fields=["content_hash"]),
        ]
        ordering = ["section_response_id", "-version", "-id"]

    def __str__(self):
        return f"{self.section_response_id}:v{self.version}"


class ReportCommentThread(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    section_response = models.ForeignKey(
        ReportTemplatePackResponse,
        on_delete=models.CASCADE,
        related_name="comment_threads",
    )
    json_path = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="report_comment_threads",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ReportCommentThreadStatus.choices,
        default=ReportCommentThreadStatus.OPEN,
    )
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="resolved_report_comment_threads",
        blank=True,
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["section_response", "status"]),
            models.Index(fields=["json_path"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.section_response_id}:{self.json_path}:{self.status}"


class ReportComment(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    thread = models.ForeignKey(
        ReportCommentThread,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="report_comments",
        blank=True,
        null=True,
    )
    body = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=["thread", "created_at"]),
        ]
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.thread_id}:{self.id}"


class ReportSuggestedChange(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    section_response = models.ForeignKey(
        ReportTemplatePackResponse,
        on_delete=models.CASCADE,
        related_name="suggested_changes",
    )
    base_version = models.PositiveIntegerField()
    patch_json = models.JSONField(default=dict, blank=True)
    rationale = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_report_suggested_changes",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=SuggestedChangeStatus.choices,
        default=SuggestedChangeStatus.PENDING,
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="decided_report_suggested_changes",
        blank=True,
        null=True,
    )
    decided_at = models.DateTimeField(blank=True, null=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["section_response", "status"]),
            models.Index(fields=["base_version"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.section_response_id}:v{self.base_version}:{self.status}"


class ReportWorkflowDefinition(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    object_type = models.CharField(max_length=80)
    name = models.CharField(max_length=120)
    steps_json = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["object_type", "name"], name="uq_report_workflow_definition"),
        ]
        indexes = [
            models.Index(fields=["object_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.object_type}:{self.name}"


class ReportWorkflowInstance(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    definition = models.ForeignKey(
        ReportWorkflowDefinition,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="workflow_instances",
    )
    status = models.CharField(
        max_length=20,
        choices=ReportWorkflowStatus.choices,
        default=ReportWorkflowStatus.ACTIVE,
    )
    current_step = models.CharField(max_length=120, blank=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    locked = models.BooleanField(default=False)
    latest_content_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["reporting_instance", "status"]),
            models.Index(fields=["current_step"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.reporting_instance_id}:{self.definition.name}:{self.status}"


class ReportWorkflowAction(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    workflow_instance = models.ForeignKey(
        ReportWorkflowInstance,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="report_workflow_actions",
        blank=True,
        null=True,
    )
    action_type = models.CharField(max_length=32, choices=ReportWorkflowActionType.choices)
    comment = models.TextField(blank=True)
    payload_hash = models.CharField(max_length=64, blank=True)
    payload_json = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["workflow_instance", "created_at"]),
            models.Index(fields=["action_type", "created_at"]),
        ]
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.workflow_instance_id}:{self.action_type}"


class ReportWorkflowSectionApproval(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    workflow_instance = models.ForeignKey(
        ReportWorkflowInstance,
        on_delete=models.CASCADE,
        related_name="section_approvals",
    )
    section = models.ForeignKey(
        ReportTemplatePackSection,
        on_delete=models.CASCADE,
        related_name="workflow_approvals",
    )
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_report_sections",
        blank=True,
        null=True,
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workflow_instance", "section"],
                name="uq_report_workflow_section_approval",
            ),
        ]
        indexes = [
            models.Index(fields=["workflow_instance", "approved"]),
        ]
        ordering = ["section__ordering", "section__code"]

    def __str__(self):
        return f"{self.workflow_instance_id}:{self.section.code}:{self.approved}"


class ReportExportArtifact(TimeStampedModel):
    FORMAT_PDF = "pdf"
    FORMAT_DOCX = "docx"
    FORMAT_JSON = "json"
    FORMAT_DOSSIER = "dossier"
    FORMAT_CHOICES = (
        (FORMAT_PDF, "PDF"),
        (FORMAT_DOCX, "DOCX"),
        (FORMAT_JSON, "JSON"),
        (FORMAT_DOSSIER, "Dossier ZIP"),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="report_export_artifacts",
    )
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES)
    storage_path = models.CharField(max_length=512)
    content_hash = models.CharField(max_length=64)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="generated_report_export_artifacts",
        blank=True,
        null=True,
    )
    immutable = models.BooleanField(default=False)
    linked_action = models.ForeignKey(
        ReportWorkflowAction,
        on_delete=models.SET_NULL,
        related_name="export_artifacts",
        blank=True,
        null=True,
    )
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["reporting_instance", "format", "created_at"]),
            models.Index(fields=["content_hash"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.reporting_instance_id}:{self.format}:{self.content_hash[:8]}"


class ReportDossierArtifact(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="dossier_artifacts",
    )
    storage_path = models.CharField(max_length=512)
    content_hash = models.CharField(max_length=64)
    manifest_json = models.JSONField(default=dict, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="generated_report_dossiers",
        blank=True,
        null=True,
    )
    linked_action = models.ForeignKey(
        ReportWorkflowAction,
        on_delete=models.SET_NULL,
        related_name="dossier_artifacts",
        blank=True,
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["reporting_instance", "created_at"]),
            models.Index(fields=["content_hash"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.reporting_instance_id}:{self.content_hash[:8]}"


class AnnexSectionResponse(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.CASCADE,
        related_name="annex_responses",
    )
    decision_topic_code = models.CharField(max_length=120)
    title = models.CharField(max_length=255)
    ordering = models.PositiveIntegerField(default=0)
    is_enabled = models.BooleanField(default=True)
    response_json = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="annex_responses",
        blank=True,
        null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporting_instance", "decision_topic_code"],
                name="uq_annex_response_topic",
            ),
        ]
        indexes = [
            models.Index(fields=["reporting_instance", "is_enabled"]),
            models.Index(fields=["ordering", "decision_topic_code"]),
        ]
        ordering = ["ordering", "decision_topic_code"]

    def __str__(self):
        return f"{self.reporting_instance_id}:{self.decision_topic_code}"


class IntegrationDataAsset(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    source_system = models.CharField(max_length=80)
    layer = models.CharField(max_length=20, choices=IntegrationDataLayer.choices)
    dataset_key = models.CharField(max_length=120)
    record_key = models.CharField(max_length=160)
    payload_json = models.JSONField(default=dict, blank=True)
    payload_hash = models.CharField(max_length=64, blank=True)
    source_endpoint = models.CharField(max_length=255, blank=True)
    source_version = models.CharField(max_length=80, blank=True)
    is_restricted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_system", "layer", "dataset_key", "record_key"],
                name="uq_integration_asset_record",
            ),
        ]
        indexes = [
            models.Index(fields=["source_system", "layer"]),
            models.Index(fields=["dataset_key", "record_key"]),
            models.Index(fields=["is_restricted"]),
        ]

    def __str__(self):
        return f"{self.source_system}:{self.layer}:{self.dataset_key}:{self.record_key}"


class BirdieSpecies(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    species_code = models.CharField(max_length=80, unique=True)
    common_name = models.CharField(max_length=255)
    scientific_name = models.CharField(max_length=255, blank=True)
    guild = models.CharField(max_length=120, blank=True)
    is_restricted = models.BooleanField(default=False)
    source_ref = models.CharField(max_length=255, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["species_code"]

    def __str__(self):
        return self.species_code


class BirdieSite(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    site_code = models.CharField(max_length=80, unique=True)
    site_name = models.CharField(max_length=255)
    province_code = models.CharField(max_length=20, blank=True)
    convention_type = models.CharField(max_length=120, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    is_restricted = models.BooleanField(default=False)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["site_code"]

    def __str__(self):
        return self.site_code


class BirdieModelOutput(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    species = models.ForeignKey(
        BirdieSpecies,
        on_delete=models.SET_NULL,
        related_name="outputs",
        blank=True,
        null=True,
    )
    site = models.ForeignKey(
        BirdieSite,
        on_delete=models.SET_NULL,
        related_name="outputs",
        blank=True,
        null=True,
    )
    indicator = models.ForeignKey(
        "Indicator",
        on_delete=models.SET_NULL,
        related_name="birdie_outputs",
        blank=True,
        null=True,
    )
    metric_code = models.CharField(max_length=80)
    year = models.PositiveIntegerField()
    value_numeric = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True)
    value_text = models.TextField(blank=True)
    value_json = models.JSONField(default=dict, blank=True)
    model_version = models.CharField(max_length=80, blank=True)
    provenance_json = models.JSONField(default=dict, blank=True)
    is_restricted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["species", "site", "metric_code", "year"],
                name="uq_birdie_output_row",
            ),
        ]
        indexes = [
            models.Index(fields=["metric_code", "year"]),
            models.Index(fields=["site", "year"]),
            models.Index(fields=["indicator", "year"]),
        ]
        ordering = ["metric_code", "year", "id"]

    def __str__(self):
        return f"{self.metric_code}:{self.year}"


class ReportProductTemplate(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    version = models.CharField(max_length=30, default="v1")
    description = models.TextField(blank=True)
    export_handler = models.CharField(max_length=120, blank=True)
    schema_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.code}:{self.version}"


class ReportProductRun(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    template = models.ForeignKey(
        ReportProductTemplate,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    reporting_instance = models.ForeignKey(
        ReportingInstance,
        on_delete=models.SET_NULL,
        related_name="report_product_runs",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=ReportProductStatus.choices, default=ReportProductStatus.DRAFT)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="report_product_runs",
        blank=True,
        null=True,
    )
    payload_json = models.JSONField(default=dict, blank=True)
    html_content = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    generated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["template", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.template.code}:{self.uuid}:{self.status}"
