import csv
import json
from pathlib import Path


EXPORT_HEADERS = [
    'source_record_id',
    'full_name',
    'first_name',
    'last_name',
    'primary_email',
    'company',
    'job_title',
    'membership_status',
    'notes',
    'substack_subscriber_id',
    'substack_subscription_status',
    'substack_subscription_type',
    'substack_subscribed_at',
    'substack_metadata_json',
]

HEADER_ALIASES = {
    'subscriber_id': 'subscriber_id',
    'id': 'subscriber_id',
    'email': 'email',
    'email_address': 'email',
    'name': 'full_name',
    'full_name': 'full_name',
    'first_name': 'first_name',
    'last_name': 'last_name',
    'status': 'status',
    'subscription_status': 'status',
    'subscriber_status': 'status',
    'subscription_type': 'subscription_type',
    'type': 'subscription_type',
    'plan': 'subscription_type',
    'subscribed_at': 'subscribed_at',
    'created_at': 'subscribed_at',
    'signup_date': 'subscribed_at',
    'joined_at': 'subscribed_at',
    'notes': 'notes',
    'note': 'notes',
    'company': 'company',
    'organization': 'company',
    'job_title': 'job_title',
    'title': 'job_title',
}


def _normalize_header(header: str | None) -> str:
    if not header:
        return ''
    normalized = header.strip().lower().replace('-', '_').replace(' ', '_')
    while '__' in normalized:
        normalized = normalized.replace('__', '_')
    return normalized.strip('_')


def _canonical_row(raw_row: dict[str | None, str | None]) -> dict[str, str]:
    normalized = {}
    for key, value in raw_row.items():
        normalized_key = _normalize_header(key)
        if not normalized_key:
            continue
        canonical_key = HEADER_ALIASES.get(normalized_key, normalized_key)
        normalized[canonical_key] = (value or '').strip()
    return normalized


def _split_name(full_name: str) -> tuple[str, str]:
    if not full_name:
        return '', ''
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return '', ''
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], ' '.join(parts[1:])


def _membership_status(row: dict[str, str]) -> str:
    status = (row.get('status') or '').strip().lower()
    subscription_type = (row.get('subscription_type') or '').strip().lower()

    if status in {'active', 'paid', 'subscribed'}:
        return 'active'
    if status in {'past_due', 'unpaid'}:
        return 'past_due'
    if status in {'canceled', 'cancelled', 'expired', 'inactive', 'unsubscribed'}:
        return 'inactive'
    if subscription_type in {'paid', 'founding', 'annual', 'monthly', 'comped'}:
        return 'active'
    if subscription_type == 'free':
        return 'active'
    return ''


def _source_record_id(row: dict[str, str]) -> str:
    for key in ('subscriber_id', 'email', 'full_name'):
        value = row.get(key)
        if value:
            return value
    return json.dumps(row, sort_keys=True)


def parse_substack_csv(input_path) -> list[dict[str, str]]:
    input_path = Path(input_path)
    with input_path.open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        return [_canonical_row(row) for row in reader if any((value or '').strip() for value in row.values())]


def build_import_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    import_rows = []
    for row in rows:
        full_name = row.get('full_name', '')
        first_name = row.get('first_name', '')
        last_name = row.get('last_name', '')
        if full_name and not (first_name or last_name):
            first_name, last_name = _split_name(full_name)
        elif not full_name:
            full_name = ' '.join(part for part in (first_name, last_name) if part).strip()

        notes_parts = [part for part in [row.get('notes', ''), row.get('status', ''), row.get('subscription_type', '')] if part]
        notes = ' | '.join(notes_parts)

        import_rows.append(
            {
                'source_record_id': _source_record_id(row),
                'full_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'primary_email': row.get('email', ''),
                'company': row.get('company', ''),
                'job_title': row.get('job_title', ''),
                'membership_status': _membership_status(row),
                'notes': notes,
                'substack_subscriber_id': row.get('subscriber_id', ''),
                'substack_subscription_status': row.get('status', ''),
                'substack_subscription_type': row.get('subscription_type', ''),
                'substack_subscribed_at': row.get('subscribed_at', ''),
                'substack_metadata_json': json.dumps(row, ensure_ascii=False, sort_keys=True),
            }
        )
    return import_rows


def write_members_csv(rows, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path
