from typing import Any

import httpx

from app.config import settings
from app.connectors.base import BaseConnector

LUMA_BASE_URL = "https://api.lu.ma/public/v1"


class LumaConnector(BaseConnector):
    source_system = "luma"

    def __init__(self):
        self.headers = {
            "x-luma-api-key": settings.LUMA_API_KEY,
            "accept": "application/json",
        }

    def test_connection(self) -> dict[str, Any]:
        try:
            response = httpx.get(f"{LUMA_BASE_URL}/calendar/list-events", headers=self.headers)
            response.raise_for_status()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def fetch_all(self) -> list[dict[str, Any]]:
        """Fetch all event guests across calendar events."""
        events = self._get_events()
        records = []
        for event in events:
            guests = self._get_event_guests(event["api_id"])
            for guest in guests:
                records.append(self._normalize_guest(guest, event))
        return records

    def _get_events(self) -> list[dict]:
        records = []
        cursor = None
        while True:
            params: dict[str, Any] = {"pagination_limit": 100}
            if cursor:
                params["pagination_cursor"] = cursor
            response = httpx.get(
                f"{LUMA_BASE_URL}/calendar/list-events",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            records.extend(data.get("entries", []))
            pagination = data.get("pagination", {})
            if not pagination.get("has_next_page"):
                break
            cursor = pagination.get("next_cursor")
        return records

    def _get_event_guests(self, event_api_id: str) -> list[dict]:
        records = []
        cursor = None
        while True:
            params: dict[str, Any] = {"event_api_id": event_api_id, "pagination_limit": 100}
            if cursor:
                params["pagination_cursor"] = cursor
            response = httpx.get(
                f"{LUMA_BASE_URL}/event/get-guests",
                headers=self.headers,
                params=params,
            )
            if response.status_code == 404:
                break
            response.raise_for_status()
            data = response.json()
            records.extend(data.get("entries", []))
            pagination = data.get("pagination", {})
            if not pagination.get("has_next_page"):
                break
            cursor = pagination.get("next_cursor")
        return records

    def _normalize_guest(self, guest: dict, event: dict) -> dict[str, Any]:
        user = guest.get("user", {})
        return {
            "source_system": "luma",
            "source_record_id": f"{event.get('api_id')}:{user.get('api_id', '')}",
            "email": user.get("email"),
            "name": user.get("name"),
            "event_id": event.get("api_id"),
            "event_name": event.get("name"),
            "event_start": event.get("start_at"),
            "approval_status": guest.get("approval_status"),
            "registered_at": guest.get("registered_at"),
        }
