import csv
import hashlib
import io
import json
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from .normalization import normalize_email, normalize_name, normalize_phone
from .models import (
    ExternalProfile,
    ExternalProfileSnapshot,
    ProfileSyncStatus,
    SourceSystem,
    SyncDirection,
    SyncEvent,
    SyncEventStatus,
    SyncRun,
    SyncRunStatus,
)

SOURCE_RECORD_ID_KEYS = (
    'source_record_id',
    'external_id',
    'record_id',
    'id',
    'contact_id',
    'member_id',
    'whatsapp_id',
    'wa_id',
    'phone',
    'primary_phone',
    'mobile',
    'email',
    'primary_email',
)

IDENTITY_HINT_KEYS = {
    'source_record_id',
    'external_id',
    'record_id',
    'id',
    'contact_id',
    'member_id',
    'whatsapp_id',
    'wa_id',
    'phone',
    'primary_phone',
    'mobile',
    'email',
    'primary_email',
    'full_name',
    'first_name',
    'last_name',
    'name',
    'alias',
    'display_name',
    'username',
}

EMAIL_KEYS = {
    'email',
    'primary_email',
    'secondary_email',
    'alternate_email',
}

PHONE_KEYS = {
    'phone',
    'primary_phone',
    'secondary_phone',
    'mobile',
    'whatsapp_id',
    'wa_id',
}

NAME_KEYS = {
    'full_name',
    'first_name',
    'last_name',
    'name',
    'alias',
    'display_name',
    'username',
}


class CsvImportError(ValueError):
    pass


@dataclass
class CsvImportResult:
    sync_run: SyncRun
    records_received: int


def normalize_header(header: str | None) -> str:
    if not header:
        return ''
    normalized = header.strip().lower().replace('-', '_').replace(' ', '_')
    while '__' in normalized:
        normalized = normalized.replace('__', '_')
    return normalized.strip('_')


def normalize_row(raw_row: dict[str | None, str | None]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for header, value in raw_row.items():
        key = normalize_header(header)
        if not key:
            continue
        normalized[key] = (value or '').strip()
    return normalized


def normalize_identity_row(row: dict[str, str]) -> dict[str, str]:
    normalized = dict(row)

    for key in EMAIL_KEYS:
        if key not in normalized:
            continue
        value = normalize_email(normalized.get(key))
        normalized[key] = value or ''

    for key in PHONE_KEYS:
        if key not in normalized:
            continue
        value = normalize_phone(normalized.get(key))
        normalized[key] = value or ''

    for key in NAME_KEYS:
        if key not in normalized:
            continue
        value = normalize_name(normalized.get(key))
        normalized[key] = value or ''

    if not normalized.get('full_name'):
        for candidate_key in ('name', 'display_name', 'alias', 'username'):
            candidate_value = normalized.get(candidate_key)
            if candidate_value:
                normalized['full_name'] = candidate_value
                break

    if not normalized.get('primary_email') and normalized.get('email'):
        normalized['primary_email'] = normalized['email']

    if not normalized.get('primary_phone'):
        for candidate_key in ('phone', 'mobile', 'whatsapp_id', 'wa_id'):
            candidate_value = normalized.get(candidate_key)
            if candidate_value:
                normalized['primary_phone'] = candidate_value
                break

    return normalized


def stable_row_hash(row: dict[str, str]) -> str:
    serialized = json.dumps(row, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def derive_source_record_id(row: dict[str, str]) -> str:
    for key in SOURCE_RECORD_ID_KEYS:
        value = row.get(key)
        if value:
            return value
    return f'hash:{stable_row_hash(row)}'


def has_identity_hint(row: dict[str, str]) -> bool:
    return any(row.get(key) for key in IDENTITY_HINT_KEYS)


def parse_csv(uploaded_file) -> csv.DictReader:
    try:
        contents = uploaded_file.read().decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise CsvImportError('CSV file must be UTF-8 encoded.') from exc

    reader = csv.DictReader(io.StringIO(contents))
    if not reader.fieldnames:
        raise CsvImportError('CSV file must include a header row.')
    return reader


def serialize_import_run(sync_run: SyncRun) -> dict:
    failure_events = sync_run.events.filter(status=SyncEventStatus.ERROR).order_by(
        'created_at'
    )

    return {
        'import_run_id': str(sync_run.sync_run_id),
        'source_system': sync_run.source_system,
        'status': sync_run.status,
        'records_received': sync_run.records_processed + sync_run.records_failed,
        'records_processed': sync_run.records_processed,
        'records_failed': sync_run.records_failed,
        'error_summary': sync_run.error_summary,
        'started_at': sync_run.started_at.isoformat(),
        'completed_at': (
            sync_run.completed_at.isoformat() if sync_run.completed_at else None
        ),
        'failures': [
            {
                'row_number': event.payload.get('row_number'),
                'source_record_id': event.payload.get('source_record_id'),
                'error_message': event.error_message,
                'row': event.payload.get('row'),
            }
            for event in failure_events
        ],
    }


def import_external_profiles_from_csv(
    uploaded_file,
    source_system: str,
) -> CsvImportResult:
    if source_system not in SourceSystem.values:
        raise CsvImportError(f'Unsupported source_system: {source_system}')

    reader = parse_csv(uploaded_file)
    sync_run = SyncRun.objects.create(
        source_system=source_system,
        direction=SyncDirection.INBOUND,
        status=SyncRunStatus.STARTED,
    )

    records_received = 0
    records_processed = 0
    records_failed = 0

    for row_number, raw_row in enumerate(reader, start=2):
        raw_payload = normalize_row(raw_row)
        if not any(raw_payload.values()):
            continue

        records_received += 1

        try:
            normalized_row = normalize_identity_row(raw_payload)
            if not has_identity_hint(normalized_row):
                raise CsvImportError(
                    'Row is missing an identity hint like email, phone, name, alias, or source id.'
                )

            source_record_id = derive_source_record_id(normalized_row)
            source_hash = stable_row_hash(raw_payload)

            with transaction.atomic():
                profile, created = ExternalProfile.objects.get_or_create(
                    source_system=source_system,
                    source_record_id=source_record_id,
                    defaults={'sync_status': ProfileSyncStatus.PENDING},
                )
                observed_at = timezone.now()
                profile.source_payload_json = raw_payload
                profile.source_hash = source_hash
                profile.source_last_seen_at = observed_at
                profile.sync_status = ProfileSyncStatus.PENDING
                profile.save(
                    update_fields=[
                        'source_payload_json',
                        'source_hash',
                        'source_last_seen_at',
                        'sync_status',
                        'updated_at',
                    ]
                )

                snapshot = ExternalProfileSnapshot.objects.create(
                    external_profile=profile,
                    sync_run=sync_run,
                    raw_payload_json=raw_payload,
                    normalized_payload_json=normalized_row,
                    source_hash=source_hash,
                    observed_at=observed_at,
                )

                SyncEvent.objects.create(
                    sync_run=sync_run,
                    source_system=source_system,
                    action_type='csv_import_row',
                    payload={
                        'row_number': row_number,
                        'source_record_id': source_record_id,
                        'external_profile_id': str(profile.external_profile_id),
                        'external_profile_snapshot_id': str(
                            snapshot.external_profile_snapshot_id
                        ),
                        'result': 'created' if created else 'updated',
                    },
                    status=SyncEventStatus.SUCCESS,
                )

            records_processed += 1
        except Exception as exc:
            records_failed += 1
            SyncEvent.objects.create(
                sync_run=sync_run,
                source_system=source_system,
                action_type='csv_import_row',
                payload={'row_number': row_number, 'row': raw_payload},
                status=SyncEventStatus.ERROR,
                error_message=str(exc),
            )

    sync_run.records_processed = records_processed
    sync_run.records_failed = records_failed
    sync_run.completed_at = timezone.now()

    if records_received == 0:
        sync_run.status = SyncRunStatus.FAILED
        sync_run.error_summary = 'CSV file did not contain any non-empty data rows.'
        sync_run.save(
            update_fields=[
                'records_processed',
                'records_failed',
                'completed_at',
                'status',
                'error_summary',
            ]
        )
        raise CsvImportError('CSV file did not contain any non-empty data rows.')

    sync_run.status = (
        SyncRunStatus.COMPLETED if records_processed > 0 else SyncRunStatus.FAILED
    )
    if records_failed:
        sync_run.error_summary = f'{records_failed} row(s) failed during import.'

    sync_run.save(
        update_fields=[
            'records_processed',
            'records_failed',
            'completed_at',
            'status',
            'error_summary',
        ]
    )

    return CsvImportResult(sync_run=sync_run, records_received=records_received)
