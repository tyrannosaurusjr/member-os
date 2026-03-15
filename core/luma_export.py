import csv
import json
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


LUMA_API_BASE = 'https://public-api.luma.com/v1'

EXPORT_HEADERS = [
    'source_record_id',
    'full_name',
    'first_name',
    'last_name',
    'primary_email',
    'secondary_email',
    'all_emails_json',
    'primary_phone',
    'company',
    'job_title',
    'notes',
    'luma_person_id',
    'luma_guest_count',
    'luma_event_count',
    'luma_last_registered_at',
    'luma_event_names_json',
    'luma_approval_statuses_json',
    'luma_events_json',
]


def _request_json(api_key: str, path: str, params: dict | None = None) -> dict:
    query = urlencode(params or {}, doseq=True)
    url = f'{LUMA_API_BASE}{path}'
    if query:
        url = f'{url}?{query}'

    request = Request(
        url,
        headers={
            'accept': 'application/json',
            'x-luma-api-key': api_key,
            'user-agent': 'member-os-luma-export/1.0',
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(
            f'Luma API request failed with status {exc.code}: {detail}'
        ) from exc
    except URLError as exc:
        raise RuntimeError(f'Unable to reach Luma API: {exc.reason}') from exc


def _paginate_entries(api_key: str, path: str, params: dict | None = None):
    request_params = dict(params or {})
    request_params.setdefault('pagination_limit', 100)
    cursor = None

    while True:
        if cursor:
            request_params['pagination_cursor'] = cursor
        payload = _request_json(api_key, path, request_params)
        entries = payload.get('entries', [])
        for entry in entries:
            yield entry

        pagination = payload.get('pagination') or {}
        if not pagination.get('has_next_page'):
            break
        cursor = pagination.get('next_cursor')
        if not cursor:
            break


def fetch_events(api_key: str) -> list[dict]:
    return list(_paginate_entries(api_key, '/calendar/list-events'))


def fetch_event_guests(api_key: str, event_api_id: str) -> list[dict]:
    try:
        return list(
            _paginate_entries(
                api_key,
                '/event/get-guests',
                params={'event_api_id': event_api_id},
            )
        )
    except RuntimeError as exc:
        if 'status 404' in str(exc):
            return []
        raise


def _split_name(full_name: str) -> tuple[str, str]:
    if not full_name:
        return '', ''
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return '', ''
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], ' '.join(parts[1:])


def _person_key(user: dict, guest: dict, event: dict) -> str:
    for candidate in (
        user.get('api_id'),
        user.get('email'),
        guest.get('api_id'),
        guest.get('email'),
        f"{event.get('api_id', '')}:{guest.get('api_id', '')}",
    ):
        if candidate:
            return str(candidate)
    return json.dumps(
        {
            'event_api_id': event.get('api_id'),
            'event_name': event.get('name'),
            'registered_at': guest.get('registered_at'),
        },
        sort_keys=True,
    )


def _event_payload(event: dict, guest: dict) -> dict:
    return {
        'event_api_id': event.get('api_id'),
        'event_name': event.get('name'),
        'event_start_at': event.get('start_at'),
        'guest_api_id': guest.get('api_id'),
        'approval_status': guest.get('approval_status'),
        'registered_at': guest.get('registered_at'),
        'checked_in_at': guest.get('checked_in_at'),
    }


def _notes_for_person(event_payloads: list[dict]) -> str:
    if not event_payloads:
        return ''

    status_counts = Counter(
        payload.get('approval_status')
        for payload in event_payloads
        if payload.get('approval_status')
    )
    parts = [f'Luma guest history across {len(event_payloads)} registration(s)']
    if status_counts:
        summary = ', '.join(
            f'{status} x{count}' for status, count in sorted(status_counts.items())
        )
        parts.append(f'approval statuses: {summary}')
    last_registered_at = max(
        (payload.get('registered_at') for payload in event_payloads if payload.get('registered_at')),
        default='',
    )
    if last_registered_at:
        parts.append(f'last registered at {last_registered_at}')
    return ' | '.join(parts)


def build_import_rows(events: list[dict], guests_by_event: dict[str, list[dict]]) -> list[dict[str, str]]:
    grouped_people: dict[str, dict] = {}

    for event in events:
        event_api_id = event.get('api_id', '')
        for guest in guests_by_event.get(event_api_id, []):
            user = guest.get('user') or {}
            key = _person_key(user, guest, event)
            record = grouped_people.setdefault(
                key,
                {
                    'source_record_id': user.get('api_id')
                    or user.get('email')
                    or guest.get('api_id')
                    or key,
                    'luma_person_id': user.get('api_id') or '',
                    'full_name': user.get('name') or guest.get('name') or '',
                    'emails': [],
                    'primary_phone': user.get('phone') or guest.get('phone') or '',
                    'company': '',
                    'job_title': '',
                    'event_payloads': [],
                    'event_names': [],
                    'approval_statuses': [],
                },
            )

            full_name = user.get('name') or guest.get('name') or ''
            if full_name and not record['full_name']:
                record['full_name'] = full_name

            email = user.get('email') or guest.get('email') or ''
            if email and email not in record['emails']:
                record['emails'].append(email)

            company = user.get('company') or guest.get('company') or ''
            if company and not record['company']:
                record['company'] = company

            job_title = user.get('job_title') or guest.get('job_title') or ''
            if job_title and not record['job_title']:
                record['job_title'] = job_title

            payload = _event_payload(event, guest)
            record['event_payloads'].append(payload)
            if event.get('name'):
                record['event_names'].append(event.get('name'))
            if guest.get('approval_status'):
                record['approval_statuses'].append(guest.get('approval_status'))

    rows = []
    for person in grouped_people.values():
        emails = person['emails']
        full_name = person['full_name']
        first_name, last_name = _split_name(full_name)
        event_names = sorted(set(person['event_names']))
        approval_statuses = sorted(set(person['approval_statuses']))
        last_registered_at = max(
            (
                payload.get('registered_at')
                for payload in person['event_payloads']
                if payload.get('registered_at')
            ),
            default='',
        )

        rows.append(
            {
                'source_record_id': person['source_record_id'],
                'full_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'primary_email': emails[0] if emails else '',
                'secondary_email': emails[1] if len(emails) > 1 else '',
                'all_emails_json': json.dumps(emails, ensure_ascii=False),
                'primary_phone': person['primary_phone'],
                'company': person['company'],
                'job_title': person['job_title'],
                'notes': _notes_for_person(person['event_payloads']),
                'luma_person_id': person['luma_person_id'],
                'luma_guest_count': str(len(person['event_payloads'])),
                'luma_event_count': str(len(event_names)),
                'luma_last_registered_at': last_registered_at,
                'luma_event_names_json': json.dumps(event_names, ensure_ascii=False),
                'luma_approval_statuses_json': json.dumps(
                    approval_statuses,
                    ensure_ascii=False,
                ),
                'luma_events_json': json.dumps(
                    person['event_payloads'],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )

    return sorted(rows, key=lambda row: row['source_record_id'])


def export_guests(api_key: str) -> list[dict[str, str]]:
    events = fetch_events(api_key)
    guests_by_event = {
        event.get('api_id', ''): fetch_event_guests(api_key, event.get('api_id', ''))
        for event in events
        if event.get('api_id')
    }
    return build_import_rows(events, guests_by_event)


def write_guests_csv(rows, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path
