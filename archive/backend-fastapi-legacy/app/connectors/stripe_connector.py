from typing import Any

import stripe

from app.config import settings
from app.connectors.base import BaseConnector


class StripeConnector(BaseConnector):
    source_system = "stripe"

    def __init__(self):
        stripe.api_key = settings.STRIPE_API_KEY

    def test_connection(self) -> dict[str, Any]:
        try:
            account = stripe.Account.retrieve()
            return {"status": "ok", "account_id": account.id}
        except stripe.error.AuthenticationError as e:
            return {"status": "error", "detail": str(e)}

    def fetch_all(self) -> list[dict[str, Any]]:
        """Fetch all Stripe customers with their subscriptions."""
        records = []
        params: dict[str, Any] = {"limit": 100, "expand": ["data.subscriptions"]}

        while True:
            page = stripe.Customer.list(**params)
            for customer in page.data:
                records.append(self._normalize_customer(customer))
            if not page.has_more:
                break
            params["starting_after"] = page.data[-1].id

        return records

    def fetch_incremental(self, since=None) -> list[dict[str, Any]]:
        if not since:
            return self.fetch_all()
        import time
        ts = int(since.timestamp()) if hasattr(since, "timestamp") else int(since)
        records = []
        params: dict[str, Any] = {
            "limit": 100,
            "created": {"gte": ts},
            "expand": ["data.subscriptions"],
        }
        while True:
            page = stripe.Customer.list(**params)
            for customer in page.data:
                records.append(self._normalize_customer(customer))
            if not page.has_more:
                break
            params["starting_after"] = page.data[-1].id
        return records

    def _normalize_customer(self, customer) -> dict[str, Any]:
        subscriptions = []
        if customer.subscriptions:
            for sub in customer.subscriptions.data:
                subscriptions.append({
                    "subscription_id": sub.id,
                    "status": sub.status,
                    "current_period_end": sub.current_period_end,
                    "plan_id": sub.plan.id if sub.plan else None,
                    "product_id": sub.plan.product if sub.plan else None,
                    "amount": sub.plan.amount if sub.plan else None,
                    "currency": sub.plan.currency if sub.plan else None,
                    "interval": sub.plan.interval if sub.plan else None,
                })
        return {
            "source_system": "stripe",
            "source_record_id": customer.id,
            "email": customer.email,
            "name": customer.name,
            "phone": customer.phone,
            "metadata": dict(customer.metadata) if customer.metadata else {},
            "subscriptions": subscriptions,
            "created": customer.created,
        }

    def push_update(self, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update Stripe customer metadata."""
        customer = stripe.Customer.modify(record_id, metadata=payload.get("metadata", {}))
        return {"status": "ok", "customer_id": customer.id}
