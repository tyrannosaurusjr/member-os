from django.contrib import admin

from .models import (
    CanonicalMembershipTier,
    ExternalProfile,
    ExternalProfileAlias,
    ExternalProfileGroupObservation,
    FieldSourcePriority,
    Membership,
    MembershipAliasMapping,
    MembershipSeat,
    MergeAuditLog,
    MergeCandidate,
    Organization,
    Person,
    PersonOrganization,
    ReviewQueueItem,
    SyncEvent,
    SyncRun,
    TierPriceSchedule,
)


admin.site.register(
    [
        Organization,
        Person,
        PersonOrganization,
        ExternalProfile,
        ExternalProfileAlias,
        ExternalProfileGroupObservation,
        CanonicalMembershipTier,
        TierPriceSchedule,
        MembershipAliasMapping,
        Membership,
        MembershipSeat,
        MergeCandidate,
        ReviewQueueItem,
        SyncRun,
        SyncEvent,
        MergeAuditLog,
        FieldSourcePriority,
    ]
)

# Register your models here.
