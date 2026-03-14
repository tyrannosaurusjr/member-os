import base64
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STRIPE_API_BASE = 'https://api.stripe.com'
STRIPE_COMPANY_KEYS = (
    'company',
    'company_name',
    'organization',
    'organization_name',
    'business_name',
    'employer',
)
STRIPE_TITLE_KEYS = (
    'title',
    'job_title',
    'role',
    'position',
)

EXPORT_HEADERS = [
    'source_record_id',
    'full_name',
    'first_name',
    'last_name',
    'primary_email',
    'primary_phone',
    'company',
    'job_title',
    'membership_status',
    'notes',
    'stripe_customer_id',
    'stripe_created_at',
    'stripe_currency',
    'stripe_livemode',
    'stripe_delinquent',
    'stripe_balance',
    'stripe_metadata_json',
    'stripe_subscription_count',
    'stripe_active_subscription_count',
    'stripe_subscriptions_json',
]


def _basic_auth_header(api_key: str) -> str:
    token = base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('ascii')
    return f'Basic {token}'


def _request_json(api_key: str, path: str, params: dict | None = None) -> dict:
    query = urlencode(params or {}, doseq=True)
    url = f'{STRIPE_API_BASE}{path}'
    if query:
        url = f'{url}?{query}'

    request = Request(
        url,
        headers={
            'Authorization': _basic_auth_header(api_key),
            'User-Agent': 'member-os-stripe-export/1.0',
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(
            f'Stripe API request failed with status {exc.code}: {detail}'
        ) from exc
    except URLError as exc:
        raise RuntimeError(f'Unable to reach Stripe API: {exc.reason}') from exc


def _paginate_list(api_key: str, path: str, params: dict | None = None):
    request_params = dict(params or {})
    request_params.setdefault('limit', 100)

    while True:
        payload = _request_json(api_key, path, request_params)
        data = payload.get('data', [])
        for item in data:
            yield item

        if not payload.get('has_more') or not data:
            break

        request_params['starting_after'] = data[-1]['id']


def fetch_customers(api_key: str) -> list[dict]:
    return list(_paginate_list(api_key, '/v1/customers'))


def fetch_subscriptions(api_key: str) -> list[dict]:
    return list(
        _paginate_list(
            api_key,
            '/v1/subscriptions',
            params={'status': 'all'},
        )
    )


def _isoformat_timestamp(value) -> str:
    if not value:
        return ''
    return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()


def _split_name(full_name: str) -> tuple[str, str]:
    if not full_name:
        return '', ''
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return '', ''
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], ' '.join(parts[1:])


def _fallback_name_from_email(email: str) -> str:
    if not email:
        return ''
    local_part = email.split('@', 1)[0]
    tokens = [
        token for token in local_part.replace('.', ' ').replace('_', ' ').replace('-', ' ').split() if token
    ]
    return ' '.join(token.capitalize() for token in tokens)


def _extract_metadata_value(metadata: dict | None, keys: tuple[str, ...]) -> str:
    if not metadata:
        return ''
    for key in keys:
        value = metadata.get(key)
        if value:
            return str(value).strip()
    return ''


def _customer_display_name(customer: dict) -> str:
    for candidate in (
        customer.get('name'),
        customer.get('shipping', {}).get('name') if customer.get('shipping') else None,
        _fallback_name_from_email(customer.get('email', '')),
        customer.get('id'),
    ):
        if candidate:
            return str(candidate).strip()
    return ''


def _subscription_customer_id(subscription: dict) -> str:
    customer = subscription.get('customer')
    if isinstance(customer, dict):
        return customer.get('id', '')
    return customer or ''


def _subscription_export_payload(subscription: dict) -> dict:
    items = []
    for item in subscription.get('items', {}).get('data', []):
        price = item.get('price') or {}
        recurring = price.get('recurring') or {}
        items.append(
            {
                'price_id': price.get('id'),
                'product_id': price.get('product'),
                'unit_amount': price.get('unit_amount'),
                'currency': price.get('currency'),
                'interval': recurring.get('interval'),
                'interval_count': recurring.get('interval_count'),
                'nickname': price.get('nickname'),
            }
        )

    return {
        'id': subscription.get('id'),
        'status': subscription.get('status'),
        'cancel_at_period_end': subscription.get('cancel_at_period_end'),
        'current_period_start': _isoformat_timestamp(
            subscription.get('current_period_start')
        ),
        'current_period_end': _isoformat_timestamp(
            subscription.get('current_period_end')
        ),
        'items': items,
    }


def _derive_membership_status(subscriptions: list[dict]) -> str:
    statuses = {subscription.get('status') for subscription in subscriptions if subscription.get('status')}
    if statuses & {'active', 'trialing'}:
        return 'active'
    if statuses & {'past_due', 'unpaid'}:
        return 'past_due'
    if 'paused' in statuses:
        return 'suspended'
    if statuses & {'canceled', 'incomplete', 'incomplete_expired'}:
        return 'inactive'
    return ''


def _build_notes(customer: dict, subscriptions: list[dict]) -> str:
    notes = []
    description = (customer.get('description') or '').strip()
    if description:
        notes.append(description)

    if subscriptions:
        counts = Counter(
            subscription.get('status')
            for subscription in subscriptions
            if subscription.get('status')
        )
        status_summary = ', '.join(
            f'{status} x{count}' for status, count in sorted(counts.items())
        )
        notes.append(f'Stripe subscriptions: {status_summary}')

    return ' | '.join(notes)


def build_import_rows(
    customers: list[dict],
    subscriptions: list[dict],
) -> list[dict[str, str]]:
    subscriptions_by_customer: dict[str, list[dict]] = defaultdict(list)
    for subscription in subscriptions:
        customer_id = _subscription_customer_id(subscription)
        if customer_id:
            subscriptions_by_customer[customer_id].append(subscription)

    rows = []
    for customer in customers:
        metadata = customer.get('metadata') or {}
        customer_subscriptions = subscriptions_by_customer.get(customer.get('id', ''), [])
        full_name = _customer_display_name(customer)
        first_name, last_name = _split_name(full_name)
        serialized_subscriptions = [
            _subscription_export_payload(subscription)
            for subscription in customer_subscriptions
        ]
        rows.append(
            {
                'source_record_id': customer.get('id', ''),
                'full_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'primary_email': customer.get('email') or '',
                'primary_phone': customer.get('phone') or '',
                'company': _extract_metadata_value(metadata, STRIPE_COMPANY_KEYS),
                'job_title': _extract_metadata_value(metadata, STRIPE_TITLE_KEYS),
                'membership_status': _derive_membership_status(customer_subscriptions),
                'notes': _build_notes(customer, customer_subscriptions),
                'stripe_customer_id': customer.get('id', ''),
                'stripe_created_at': _isoformat_timestamp(customer.get('created')),
                'stripe_currency': customer.get('currency') or '',
                'stripe_livemode': json.dumps(bool(customer.get('livemode'))),
                'stripe_delinquent': json.dumps(bool(customer.get('delinquent'))),
                'stripe_balance': str(customer.get('balance') or 0),
                'stripe_metadata_json': json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                'stripe_subscription_count': str(len(customer_subscriptions)),
                'stripe_active_subscription_count': str(
                    sum(
                        1
                        for subscription in customer_subscriptions
                        if subscription.get('status') in {'active', 'trialing'}
                    )
                ),
                'stripe_subscriptions_json': json.dumps(
                    serialized_subscriptions,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )

    return rows


def export_customers(api_key: str) -> list[dict[str, str]]:
    customers = fetch_customers(api_key)
    subscriptions = fetch_subscriptions(api_key)
    return build_import_rows(customers, subscriptions)


def write_customers_csv(rows, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path
