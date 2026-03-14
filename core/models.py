import uuid

from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower


def choice_constraint(
    field_name: str,
    choices: type[models.TextChoices],
    *,
    name: str,
    allow_null: bool = False,
) -> models.CheckConstraint:
    condition = Q(**{f'{field_name}__in': choices.values})
    if allow_null:
        condition |= Q(**{f'{field_name}__isnull': True})
    return models.CheckConstraint(condition=condition, name=name)


def percentage_constraint(field_name: str, *, name: str) -> models.CheckConstraint:
    return models.CheckConstraint(
        condition=(
            Q(**{f'{field_name}__gte': 0, f'{field_name}__lte': 100})
            | Q(**{f'{field_name}__isnull': True})
        ),
        name=name,
    )


class SourceSystem(models.TextChoices):
    STRIPE = 'stripe', 'Stripe'
    LUMA = 'luma', 'Luma'
    MAILCHIMP = 'mailchimp', 'Mailchimp'
    GOOGLE_SHEETS = 'google_sheets', 'Google Sheets'
    APPLE_CONTACTS = 'apple_contacts', 'Apple Contacts'
    MANUAL_CSV = 'manual_csv', 'Manual CSV'
    WHATSAPP = 'whatsapp', 'WhatsApp'
    LINKEDIN = 'linkedin', 'LinkedIn'
    CLAY = 'clay', 'Clay'
    OTHER = 'other', 'Other'


class ProfileSyncStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SYNCED = 'synced', 'Synced'
    ERROR = 'error', 'Error'
    IGNORED = 'ignored', 'Ignored'


class BillingFrequency(models.TextChoices):
    MONTHLY = 'monthly', 'Monthly'
    QUARTERLY = 'quarterly', 'Quarterly'
    ANNUAL = 'annual', 'Annual'
    ONE_TIME = 'one_time', 'One Time'
    CUSTOM = 'custom', 'Custom'


class MembershipRelationshipType(models.TextChoices):
    INDIVIDUAL = 'individual', 'Individual'
    CORPORATE_SEAT = 'corporate_seat', 'Corporate Seat'
    COMPLIMENTARY = 'complimentary', 'Complimentary'
    PARTNER = 'partner', 'Partner'
    SPONSOR = 'sponsor', 'Sponsor'
    INTERNAL = 'internal', 'Internal'
    STAFF = 'staff', 'Staff'


class MembershipStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'
    PAST_DUE = 'past_due', 'Past Due'
    COMPLIMENTARY = 'complimentary', 'Complimentary'
    MANUAL = 'manual', 'Manual'
    SUSPENDED = 'suspended', 'Suspended'
    UNKNOWN = 'unknown', 'Unknown'


class PaymentMethodType(models.TextChoices):
    STRIPE_AUTO = 'stripe_auto', 'Stripe Auto'
    BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
    CASH = 'cash', 'Cash'
    MANUAL_OVERRIDE = 'manual_override', 'Manual Override'
    COMPED = 'comped', 'Comped'
    UNKNOWN = 'unknown', 'Unknown'


class RelationshipStrength(models.TextChoices):
    CORE = 'core', 'Core'
    ACTIVE = 'active', 'Active'
    PERIPHERAL = 'peripheral', 'Peripheral'
    DORMANT = 'dormant', 'Dormant'
    PROSPECT = 'prospect', 'Prospect'


class MergeRecommendedAction(models.TextChoices):
    AUTO_MERGE = 'auto_merge', 'Auto Merge'
    REVIEW = 'review', 'Review'
    IGNORE = 'ignore', 'Ignore'


class MergeCandidateStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    MERGED = 'merged', 'Merged'
    IGNORED = 'ignored', 'Ignored'


class ReviewItemType(models.TextChoices):
    DUPLICATE_CONTACT = 'duplicate_contact', 'Duplicate Contact'
    UNKNOWN_TIER = 'unknown_tier', 'Unknown Tier'
    CONFLICTING_MEMBERSHIP = 'conflicting_membership', 'Conflicting Membership'
    MISSING_EMAIL = 'missing_email', 'Missing Email'
    MULTIPLE_STRIPE_CUSTOMERS = 'multiple_stripe_customers', 'Multiple Stripe Customers'
    PRICE_ANOMALY = 'price_anomaly', 'Price Anomaly'
    SYNC_ERROR = 'sync_error', 'Sync Error'
    UNKNOWN_WHATSAPP_IDENTITY = 'unknown_whatsapp_identity', 'Unknown WhatsApp Identity'
    ALIAS_CONFLICT = 'alias_conflict', 'Alias Conflict'
    PROFILE_LINK_REVIEW = 'profile_link_review', 'Profile Link Review'


class ReviewSeverity(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class ReviewQueueStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    IN_PROGRESS = 'in_progress', 'In Progress'
    RESOLVED = 'resolved', 'Resolved'
    DISMISSED = 'dismissed', 'Dismissed'


class SyncDirection(models.TextChoices):
    INBOUND = 'inbound', 'Inbound'
    OUTBOUND = 'outbound', 'Outbound'


class SyncRunStatus(models.TextChoices):
    STARTED = 'started', 'Started'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class SyncEventStatus(models.TextChoices):
    SUCCESS = 'success', 'Success'
    ERROR = 'error', 'Error'


class MergeDecisionType(models.TextChoices):
    AUTO_MERGE = 'auto_merge', 'Auto Merge'
    MANUAL_MERGE = 'manual_merge', 'Manual Merge'
    SPLIT = 'split', 'Split'
    TIER_REMAP = 'tier_remap', 'Tier Remap'
    FIELD_OVERRIDE = 'field_override', 'Field Override'
    IDENTITY_RECTIFICATION = 'identity_rectification', 'Identity Rectification'


class ExternalAliasType(models.TextChoices):
    DISPLAY_NAME = 'display_name', 'Display Name'
    USERNAME = 'username', 'Username'
    GROUP_NICKNAME = 'group_nickname', 'Group Nickname'
    IMPORTED_ALIAS = 'imported_alias', 'Imported Alias'
    MANUAL_LABEL = 'manual_label', 'Manual Label'


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CreatedAtModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class Organization(TimestampedModel):
    organization_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.TextField()
    website = models.TextField(blank=True, null=True)
    domain = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'organizations'

    def __str__(self) -> str:
        return self.name


class Person(TimestampedModel):
    person_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.TextField(blank=True, null=True)
    last_name = models.TextField(blank=True, null=True)
    full_name = models.TextField()
    primary_email = models.TextField(blank=True, null=True)
    secondary_emails = models.JSONField(default=list, blank=True)
    primary_phone = models.TextField(blank=True, null=True)
    secondary_phones = models.JSONField(default=list, blank=True)
    company = models.TextField(blank=True, null=True)
    job_title = models.TextField(blank=True, null=True)
    location = models.TextField(blank=True, null=True)
    linkedin_url = models.TextField(blank=True, null=True)
    website = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    source_confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
    )
    last_verified_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'persons'
        constraints = [
            percentage_constraint(
                'source_confidence_score',
                name='persons_source_confidence_between_0_100',
            ),
        ]
        indexes = [
            models.Index(Lower('primary_email'), name='idx_persons_primary_email'),
            GinIndex(
                fields=['full_name'],
                name='idx_persons_full_name_trgm',
                opclasses=['gin_trgm_ops'],
            ),
        ]

    def __str__(self) -> str:
        return self.full_name


class PersonOrganization(CreatedAtModel):
    person_organization_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='organization_links',
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='person_links',
    )
    relationship_type = models.TextField(default='member')
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = 'person_organizations'

    def __str__(self) -> str:
        return f'{self.person} -> {self.organization}'


class ExternalProfile(TimestampedModel):
    external_profile_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='external_profiles',
    )
    source_system = models.CharField(max_length=32, choices=SourceSystem)
    source_record_id = models.TextField()
    source_payload_json = models.JSONField(default=dict, blank=True)
    source_hash = models.TextField(blank=True, null=True)
    source_last_seen_at = models.DateTimeField(blank=True, null=True)
    last_synced_at = models.DateTimeField(blank=True, null=True)
    sync_status = models.CharField(
        max_length=16,
        choices=ProfileSyncStatus,
        default=ProfileSyncStatus.PENDING,
    )

    class Meta:
        db_table = 'external_profiles'
        constraints = [
            models.UniqueConstraint(
                fields=['source_system', 'source_record_id'],
                name='external_profiles_source_system_source_record_id_uniq',
            ),
            choice_constraint(
                'source_system',
                SourceSystem,
                name='external_profiles_source_system_valid',
            ),
            choice_constraint(
                'sync_status',
                ProfileSyncStatus,
                name='external_profiles_sync_status_valid',
            ),
        ]
        indexes = [
            models.Index(fields=['person'], name='idx_ext_profiles_person'),
            models.Index(
                fields=['source_system', 'source_record_id'],
                name='idx_ext_profiles_source',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.source_system}:{self.source_record_id}'


class ExternalProfileSnapshot(CreatedAtModel):
    external_profile_snapshot_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    external_profile = models.ForeignKey(
        ExternalProfile,
        on_delete=models.CASCADE,
        related_name='snapshots',
    )
    sync_run = models.ForeignKey(
        'SyncRun',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='profile_snapshots',
    )
    raw_payload_json = models.JSONField(default=dict, blank=True)
    normalized_payload_json = models.JSONField(default=dict, blank=True)
    source_hash = models.TextField(blank=True, null=True)
    observed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'external_profile_snapshots'
        indexes = [
            models.Index(
                fields=['external_profile', 'created_at'],
                name='idx_ext_prof_snap_created',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.external_profile} snapshot @ {self.created_at.isoformat()}'


class ExternalProfileAlias(CreatedAtModel):
    external_profile_alias_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    external_profile = models.ForeignKey(
        ExternalProfile,
        on_delete=models.CASCADE,
        related_name='aliases',
    )
    alias_value = models.TextField()
    alias_type = models.CharField(
        max_length=32,
        choices=ExternalAliasType,
        default=ExternalAliasType.DISPLAY_NAME,
    )
    is_primary = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    source_confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = 'external_profile_aliases'
        constraints = [
            models.UniqueConstraint(
                fields=['external_profile', 'alias_value', 'alias_type'],
                name='external_profile_aliases_unique_alias_per_profile',
            ),
            choice_constraint(
                'alias_type',
                ExternalAliasType,
                name='external_profile_aliases_alias_type_valid',
            ),
            percentage_constraint(
                'source_confidence_score',
                name='external_profile_aliases_confidence_between_0_100',
            ),
        ]

    def __str__(self) -> str:
        return self.alias_value


class ExternalProfileGroupObservation(CreatedAtModel):
    external_profile_group_observation_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    external_profile = models.ForeignKey(
        ExternalProfile,
        on_delete=models.CASCADE,
        related_name='group_observations',
    )
    source_group_id = models.TextField(blank=True, null=True)
    source_group_name = models.TextField(blank=True, null=True)
    observed_role = models.TextField(blank=True, null=True)
    first_seen_at = models.DateTimeField(blank=True, null=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    source_payload_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'external_profile_group_observations'
        indexes = [
            models.Index(
                fields=['external_profile', 'source_group_id'],
                name='idx_ext_profile_group_lookup',
            ),
        ]

    def __str__(self) -> str:
        return self.source_group_name or self.source_group_id or str(
            self.external_profile_id
        )


class CanonicalMembershipTier(TimestampedModel):
    canonical_tier_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    canonical_tier_name = models.TextField(unique=True)
    tier_family = models.TextField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'canonical_membership_tiers'

    def __str__(self) -> str:
        return self.canonical_tier_name


class TierPriceSchedule(CreatedAtModel):
    tier_price_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical_tier = models.ForeignKey(
        CanonicalMembershipTier,
        on_delete=models.CASCADE,
        related_name='price_schedules',
    )
    list_price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.TextField(default='JPY')
    billing_frequency = models.CharField(max_length=16, choices=BillingFrequency)
    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'tier_price_schedules'
        constraints = [
            choice_constraint(
                'billing_frequency',
                BillingFrequency,
                name='tier_price_schedules_billing_frequency_valid',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.canonical_tier} @ {self.list_price} {self.currency}'


class MembershipAliasMapping(CreatedAtModel):
    alias_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_system = models.CharField(max_length=32, choices=SourceSystem)
    source_tier_name = models.TextField(blank=True, null=True)
    source_product_id = models.TextField(blank=True, null=True)
    source_plan_id = models.TextField(blank=True, null=True)
    source_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )
    currency = models.TextField(default='JPY', blank=True)
    canonical_tier = models.ForeignKey(
        CanonicalMembershipTier,
        on_delete=models.CASCADE,
        related_name='alias_mappings',
    )
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    effective_from = models.DateField(blank=True, null=True)
    effective_to = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'membership_alias_mappings'
        constraints = [
            choice_constraint(
                'source_system',
                SourceSystem,
                name='membership_alias_mappings_source_system_valid',
            ),
            percentage_constraint(
                'confidence_score',
                name='membership_alias_mappings_confidence_between_0_100',
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    'source_system',
                    'source_tier_name',
                    'source_product_id',
                    'source_plan_id',
                ],
                name='idx_member_alias_lookup',
            ),
        ]

    def __str__(self) -> str:
        return self.source_tier_name or self.source_product_id or self.source_plan_id or str(
            self.alias_id
        )


class Membership(TimestampedModel):
    membership_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='memberships',
    )
    canonical_tier = models.ForeignKey(
        CanonicalMembershipTier,
        on_delete=models.RESTRICT,
        related_name='memberships',
    )
    membership_relationship_type = models.CharField(
        max_length=32,
        choices=MembershipRelationshipType,
        default=MembershipRelationshipType.INDIVIDUAL,
    )
    status = models.CharField(
        max_length=16,
        choices=MembershipStatus,
        default=MembershipStatus.UNKNOWN,
    )
    payment_method_type = models.CharField(
        max_length=24,
        choices=PaymentMethodType,
        default=PaymentMethodType.MANUAL_OVERRIDE,
    )
    price_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )
    price_currency = models.TextField(default='JPY')
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
    )
    discount_reason = models.TextField(blank=True, null=True)
    list_price_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )
    billing_frequency = models.CharField(
        max_length=16,
        choices=BillingFrequency,
        blank=True,
        null=True,
    )
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    renewal_date = models.DateField(blank=True, null=True)
    last_payment_date = models.DateField(blank=True, null=True)
    amount_last_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )
    source_of_truth = models.TextField(blank=True, null=True)
    relationship_strength = models.CharField(
        max_length=16,
        choices=RelationshipStrength,
        blank=True,
        null=True,
    )
    review_required = models.BooleanField(default=False)

    class Meta:
        db_table = 'memberships'
        constraints = [
            choice_constraint(
                'membership_relationship_type',
                MembershipRelationshipType,
                name='memberships_relationship_type_valid',
            ),
            choice_constraint(
                'status',
                MembershipStatus,
                name='memberships_status_valid',
            ),
            choice_constraint(
                'payment_method_type',
                PaymentMethodType,
                name='memberships_payment_method_type_valid',
            ),
            choice_constraint(
                'billing_frequency',
                BillingFrequency,
                name='memberships_billing_frequency_valid',
                allow_null=True,
            ),
            choice_constraint(
                'relationship_strength',
                RelationshipStrength,
                name='memberships_relationship_strength_valid',
                allow_null=True,
            ),
            percentage_constraint(
                'discount_percent',
                name='memberships_discount_percent_between_0_100',
            ),
        ]
        indexes = [
            models.Index(fields=['person'], name='idx_memberships_person_id'),
            models.Index(fields=['status'], name='idx_memberships_status'),
        ]

    def __str__(self) -> str:
        return f'{self.person} - {self.canonical_tier}'


class MembershipSeat(CreatedAtModel):
    membership_seat_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name='seats',
    )
    membership_holder_person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='membership_seats_owned',
    )
    seat_holder_person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='membership_seats_held',
    )
    seat_title = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'membership_seats'

    def __str__(self) -> str:
        return self.seat_title or str(self.membership_id)


class MergeCandidate(CreatedAtModel):
    merge_candidate_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    left_person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='merge_candidates_as_left',
    )
    right_person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='merge_candidates_as_right',
    )
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)
    strong_signal_count = models.IntegerField(default=0)
    medium_signal_count = models.IntegerField(default=0)
    weak_signal_count = models.IntegerField(default=0)
    explanation = models.JSONField(default=list, blank=True)
    recommended_action = models.CharField(
        max_length=16,
        choices=MergeRecommendedAction,
        default=MergeRecommendedAction.REVIEW,
    )
    status = models.CharField(
        max_length=16,
        choices=MergeCandidateStatus,
        default=MergeCandidateStatus.OPEN,
    )
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'merge_candidates'
        constraints = [
            choice_constraint(
                'recommended_action',
                MergeRecommendedAction,
                name='merge_candidates_recommended_action_valid',
            ),
            choice_constraint(
                'status',
                MergeCandidateStatus,
                name='merge_candidates_status_valid',
            ),
            percentage_constraint(
                'confidence_score',
                name='merge_candidates_confidence_between_0_100',
            ),
            models.CheckConstraint(
                condition=~Q(left_person=F('right_person')),
                name='merge_candidates_distinct_people',
            ),
            models.CheckConstraint(
                condition=Q(strong_signal_count__gte=0),
                name='merge_candidates_strong_signal_count_nonnegative',
            ),
            models.CheckConstraint(
                condition=Q(medium_signal_count__gte=0),
                name='merge_candidates_medium_signal_count_nonnegative',
            ),
            models.CheckConstraint(
                condition=Q(weak_signal_count__gte=0),
                name='merge_candidates_weak_signal_count_nonnegative',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.left_person} vs {self.right_person}'


class ReviewQueueItem(CreatedAtModel):
    review_item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_type = models.CharField(max_length=32, choices=ReviewItemType)
    related_person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='review_queue_items',
    )
    related_membership = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='review_queue_items',
    )
    related_external_profile = models.ForeignKey(
        ExternalProfile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='review_queue_items',
    )
    severity = models.CharField(
        max_length=16,
        choices=ReviewSeverity,
        default=ReviewSeverity.MEDIUM,
    )
    title = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16,
        choices=ReviewQueueStatus,
        default=ReviewQueueStatus.OPEN,
    )
    assigned_to = models.TextField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'review_queue_items'
        constraints = [
            choice_constraint(
                'item_type',
                ReviewItemType,
                name='review_queue_items_item_type_valid',
            ),
            choice_constraint(
                'severity',
                ReviewSeverity,
                name='review_queue_items_severity_valid',
            ),
            choice_constraint(
                'status',
                ReviewQueueStatus,
                name='review_queue_items_status_valid',
            ),
        ]

    def __str__(self) -> str:
        return self.title


class SyncRun(models.Model):
    sync_run_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_system = models.CharField(max_length=32, choices=SourceSystem)
    direction = models.CharField(max_length=16, choices=SyncDirection)
    status = models.CharField(max_length=16, choices=SyncRunStatus)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    records_processed = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    error_summary = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'sync_runs'
        constraints = [
            choice_constraint(
                'source_system',
                SourceSystem,
                name='sync_runs_source_system_valid',
            ),
            choice_constraint(
                'direction',
                SyncDirection,
                name='sync_runs_direction_valid',
            ),
            choice_constraint(
                'status',
                SyncRunStatus,
                name='sync_runs_status_valid',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.source_system} {self.direction} {self.status}'


class SyncEvent(CreatedAtModel):
    sync_event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sync_run = models.ForeignKey(
        SyncRun,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='events',
    )
    source_system = models.CharField(max_length=32, choices=SourceSystem)
    related_person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='sync_events',
    )
    related_membership = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='sync_events',
    )
    action_type = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=SyncEventStatus)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'sync_events'
        constraints = [
            choice_constraint(
                'source_system',
                SourceSystem,
                name='sync_events_source_system_valid',
            ),
            choice_constraint(
                'status',
                SyncEventStatus,
                name='sync_events_status_valid',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.source_system} {self.action_type}'


class MergeAuditLog(CreatedAtModel):
    decision_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    decision_type = models.CharField(max_length=32, choices=MergeDecisionType)
    performed_by = models.TextField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    before_json = models.JSONField()
    after_json = models.JSONField()

    class Meta:
        db_table = 'merge_audit_logs'
        constraints = [
            choice_constraint(
                'decision_type',
                MergeDecisionType,
                name='merge_audit_logs_decision_type_valid',
            ),
        ]

    def __str__(self) -> str:
        return self.decision_type


class FieldSourcePriority(CreatedAtModel):
    field_source_priority_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    field_name = models.TextField()
    source_system = models.CharField(max_length=32, choices=SourceSystem)
    priority_rank = models.IntegerField()

    class Meta:
        db_table = 'field_source_priorities'
        constraints = [
            models.UniqueConstraint(
                fields=['field_name', 'source_system'],
                name='field_source_priorities_field_source_unique',
            ),
            models.UniqueConstraint(
                fields=['field_name', 'priority_rank'],
                name='field_source_priorities_field_rank_unique',
            ),
            choice_constraint(
                'source_system',
                SourceSystem,
                name='field_source_priorities_source_system_valid',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.field_name}:{self.source_system}:{self.priority_rank}'
