import re
from collections import defaultdict
from copy import deepcopy

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import (
    ExternalProfile,
    MergeAuditLog,
    MergeDecisionType,
    Person,
    ProfileSyncStatus,
    ReviewItemType,
    ReviewQueueItem,
    ReviewQueueStatus,
    ReviewSeverity,
)


OPEN_REVIEW_STATUSES = [
    ReviewQueueStatus.OPEN,
    ReviewQueueStatus.IN_PROGRESS,
]


def unique_nonempty(values):
    seen = set()
    ordered = []
    for value in values:
        if not value:
            continue
        normalized = value.strip() if isinstance(value, str) else value
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def latest_profile_payloads(profile: ExternalProfile):
    latest_snapshot = profile.snapshots.order_by('-created_at').first()
    raw_payload = deepcopy(profile.source_payload_json or {})
    normalized_payload = {}
    if latest_snapshot:
        normalized_payload = deepcopy(latest_snapshot.normalized_payload_json or {})
        raw_payload = deepcopy(latest_snapshot.raw_payload_json or raw_payload)
    return raw_payload, normalized_payload


def guess_name_from_email(email: str | None):
    if not email or '@' not in email:
        return None
    local_part = email.split('@', 1)[0]
    tokens = [token for token in re.split(r'[^a-zA-Z0-9]+', local_part) if token]
    if not tokens:
        return email
    return ' '.join(token.capitalize() for token in tokens)


def get_profile_preview(profile: ExternalProfile):
    raw_payload, normalized_payload = latest_profile_payloads(profile)
    preview_name = (
        normalized_payload.get('full_name')
        or raw_payload.get('full_name')
        or raw_payload.get('name')
        or raw_payload.get('display_name')
        or raw_payload.get('alias')
        or guess_name_from_email(
            normalized_payload.get('primary_email')
            or normalized_payload.get('email')
            or raw_payload.get('primary_email')
            or raw_payload.get('email')
        )
        or profile.source_record_id
    )
    preview_email = (
        normalized_payload.get('primary_email')
        or normalized_payload.get('email')
        or raw_payload.get('primary_email')
        or raw_payload.get('email')
    )
    preview_phone = (
        normalized_payload.get('primary_phone')
        or normalized_payload.get('phone')
        or raw_payload.get('primary_phone')
        or raw_payload.get('phone')
        or raw_payload.get('mobile')
    )
    preview_company = (
        normalized_payload.get('company')
        or raw_payload.get('company')
        or raw_payload.get('company_name')
        or raw_payload.get('organization')
    )
    preview_title = (
        normalized_payload.get('job_title')
        or raw_payload.get('job_title')
        or raw_payload.get('title')
    )

    return {
        'name': preview_name,
        'email': preview_email,
        'phone': preview_phone,
        'company': preview_company,
        'job_title': preview_title,
        'raw_payload': raw_payload,
        'normalized_payload': normalized_payload,
    }


def build_person_defaults_from_profile(profile: ExternalProfile):
    preview = get_profile_preview(profile)
    raw_payload = preview['raw_payload']
    normalized_payload = preview['normalized_payload']
    primary_email = preview['email']
    primary_phone = preview['phone']

    secondary_emails = unique_nonempty(
        [
            normalized_payload.get('alternate_email'),
            normalized_payload.get('secondary_email'),
            raw_payload.get('alternate_email'),
            raw_payload.get('secondary_email'),
        ]
    )
    secondary_emails = [email for email in secondary_emails if email != primary_email]

    secondary_phones = unique_nonempty(
        [
            raw_payload.get('secondary_phone'),
            raw_payload.get('mobile'),
            normalized_payload.get('secondary_phone'),
        ]
    )
    secondary_phones = [phone for phone in secondary_phones if phone != primary_phone]

    first_name = normalized_payload.get('first_name') or raw_payload.get('first_name')
    last_name = normalized_payload.get('last_name') or raw_payload.get('last_name')
    notes = raw_payload.get('notes')
    if notes:
        notes = f'{notes}\n\nImported from {profile.get_source_system_display()} ({profile.source_record_id}).'
    else:
        notes = f'Imported from {profile.get_source_system_display()} ({profile.source_record_id}).'

    return {
        'first_name': first_name or None,
        'last_name': last_name or None,
        'full_name': preview['name'],
        'primary_email': primary_email or None,
        'secondary_emails': secondary_emails,
        'primary_phone': primary_phone or None,
        'secondary_phones': secondary_phones,
        'company': preview['company'] or None,
        'job_title': preview['job_title'] or None,
        'location': raw_payload.get('location') or None,
        'linkedin_url': raw_payload.get('linkedin_url') or None,
        'website': raw_payload.get('website') or None,
        'notes': notes,
    }


def serialize_person(person: Person):
    return {
        'person_id': str(person.person_id),
        'full_name': person.full_name,
        'primary_email': person.primary_email,
        'primary_phone': person.primary_phone,
        'company': person.company,
        'job_title': person.job_title,
        'secondary_emails': person.secondary_emails,
        'secondary_phones': person.secondary_phones,
        'notes': person.notes,
    }


def serialize_profile(profile: ExternalProfile):
    return {
        'external_profile_id': str(profile.external_profile_id),
        'person_id': str(profile.person_id) if profile.person_id else None,
        'source_system': profile.source_system,
        'source_record_id': profile.source_record_id,
        'sync_status': profile.sync_status,
        'source_payload_json': deepcopy(profile.source_payload_json or {}),
    }


def find_person_suggestions_for_profile(profile: ExternalProfile, *, limit: int = 5):
    preview = get_profile_preview(profile)
    scores = defaultdict(
        lambda: {
            'score': 0,
            'strong_signal_count': 0,
            'medium_signal_count': 0,
            'weak_signal_count': 0,
            'reasons': [],
            'person': None,
        }
    )

    def add_matches(queryset, points, label, strength):
        for person in queryset:
            entry = scores[person.person_id]
            entry['person'] = person
            entry['score'] += points
            entry['reasons'].append(label)
            key = f'{strength}_signal_count'
            entry[key] += 1

    if preview['email']:
        add_matches(
            Person.objects.filter(
                Q(primary_email=preview['email'])
                | Q(secondary_emails__contains=[preview['email']])
            ),
            95,
            'Exact email match',
            'strong',
        )

    if preview['phone']:
        add_matches(
            Person.objects.filter(
                Q(primary_phone=preview['phone'])
                | Q(secondary_phones__contains=[preview['phone']])
            ),
            90,
            'Exact phone match',
            'strong',
        )

    if preview['name']:
        add_matches(
            Person.objects.filter(full_name__iexact=preview['name']),
            72,
            'Exact full name match',
            'medium',
        )

    if preview['name'] and preview['company']:
        add_matches(
            Person.objects.filter(
                full_name__iexact=preview['name'],
                company__iexact=preview['company'],
            ),
            18,
            'Matching company context',
            'medium',
        )

    if preview['company']:
        add_matches(
            Person.objects.filter(company__iexact=preview['company']),
            12,
            'Company name overlap',
            'weak',
        )

    suggestions = []
    for entry in scores.values():
        if entry['person'] is None:
            continue
        person = entry['person']
        suggestions.append(
            {
                'person': person,
                'person_id': str(person.person_id),
                'full_name': person.full_name,
                'primary_email': person.primary_email,
                'company': person.company,
                'job_title': person.job_title,
                'score': min(entry['score'], 100),
                'reasons': entry['reasons'],
                'strong_signal_count': entry['strong_signal_count'],
                'medium_signal_count': entry['medium_signal_count'],
                'weak_signal_count': entry['weak_signal_count'],
            }
        )

    suggestions.sort(
        key=lambda item: (
            -item['score'],
            -item['strong_signal_count'],
            -item['medium_signal_count'],
            item['full_name'].lower(),
        )
    )
    return suggestions[:limit]


def sync_review_item_for_external_profile(profile: ExternalProfile):
    open_items = ReviewQueueItem.objects.filter(
        item_type=ReviewItemType.PROFILE_LINK_REVIEW,
        related_external_profile=profile,
        status__in=OPEN_REVIEW_STATUSES,
    )

    if profile.person_id:
        open_items.update(
            status=ReviewQueueStatus.RESOLVED,
            resolved_at=timezone.now(),
        )
        return None

    preview = get_profile_preview(profile)
    suggestions = find_person_suggestions_for_profile(profile, limit=3)
    severity = (
        ReviewSeverity.HIGH
        if suggestions and suggestions[0]['score'] >= 90
        else ReviewSeverity.MEDIUM
    )
    title = f'Link or create person for {preview["name"]}'
    details = {
        'source_system': profile.source_system,
        'source_record_id': profile.source_record_id,
        'preview': {
            'name': preview['name'],
            'email': preview['email'],
            'phone': preview['phone'],
            'company': preview['company'],
            'job_title': preview['job_title'],
        },
        'suggestions': [
            {
                'person_id': suggestion['person_id'],
                'full_name': suggestion['full_name'],
                'score': suggestion['score'],
                'reasons': suggestion['reasons'],
            }
            for suggestion in suggestions
        ],
    }

    review_item = open_items.order_by('-created_at').first()
    if review_item is None:
        review_item = ReviewQueueItem(
            item_type=ReviewItemType.PROFILE_LINK_REVIEW,
            related_external_profile=profile,
            status=ReviewQueueStatus.OPEN,
        )

    review_item.severity = severity
    review_item.title = title
    review_item.details = details
    review_item.resolved_at = None
    review_item.save()
    return review_item


def merge_person_defaults(person: Person, profile: ExternalProfile):
    defaults = build_person_defaults_from_profile(profile)
    changed_fields = []

    for field in ['first_name', 'last_name', 'full_name', 'primary_email', 'primary_phone', 'company', 'job_title', 'location', 'linkedin_url', 'website', 'notes']:
        current_value = getattr(person, field)
        new_value = defaults[field]
        if not current_value and new_value:
            setattr(person, field, new_value)
            changed_fields.append(field)

    merged_secondary_emails = unique_nonempty(person.secondary_emails + defaults['secondary_emails'])
    if merged_secondary_emails != person.secondary_emails:
        person.secondary_emails = merged_secondary_emails
        changed_fields.append('secondary_emails')

    merged_secondary_phones = unique_nonempty(person.secondary_phones + defaults['secondary_phones'])
    if merged_secondary_phones != person.secondary_phones:
        person.secondary_phones = merged_secondary_phones
        changed_fields.append('secondary_phones')

    return changed_fields


@transaction.atomic
def create_person_from_external_profile(profile: ExternalProfile, *, performed_by: str | None = None):
    if profile.person_id:
        return profile.person

    before_profile = serialize_profile(profile)
    person = Person.objects.create(**build_person_defaults_from_profile(profile))
    now = timezone.now()
    profile.person = person
    profile.sync_status = ProfileSyncStatus.SYNCED
    profile.last_synced_at = now
    profile.save(update_fields=['person', 'sync_status', 'last_synced_at', 'updated_at'])
    sync_review_item_for_external_profile(profile)
    MergeAuditLog.objects.create(
        decision_type=MergeDecisionType.IDENTITY_RECTIFICATION,
        performed_by=performed_by,
        reason='create_person_from_external_profile',
        before_json={'person': None, 'external_profile': before_profile},
        after_json={
            'person': serialize_person(person),
            'external_profile': serialize_profile(profile),
        },
    )
    return person


@transaction.atomic
def link_external_profile_to_person(
    profile: ExternalProfile,
    person: Person,
    *,
    performed_by: str | None = None,
):
    before_profile = serialize_profile(profile)
    before_person = serialize_person(person)
    merge_person_defaults(person, profile)
    person.save()
    now = timezone.now()
    profile.person = person
    profile.sync_status = ProfileSyncStatus.SYNCED
    profile.last_synced_at = now
    profile.save(update_fields=['person', 'sync_status', 'last_synced_at', 'updated_at'])
    sync_review_item_for_external_profile(profile)
    MergeAuditLog.objects.create(
        decision_type=MergeDecisionType.IDENTITY_RECTIFICATION,
        performed_by=performed_by,
        reason='link_external_profile_to_person',
        before_json={'person': before_person, 'external_profile': before_profile},
        after_json={
            'person': serialize_person(person),
            'external_profile': serialize_profile(profile),
        },
    )
    return person
