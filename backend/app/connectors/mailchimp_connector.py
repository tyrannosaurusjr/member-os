from typing import Any

import mailchimp_marketing as MailchimpClient
from mailchimp_marketing.api_client import ApiClientError

from app.config import settings
from app.connectors.base import BaseConnector


class MailchimpConnector(BaseConnector):
    source_system = "mailchimp"

    def __init__(self):
        self.client = MailchimpClient.Client()
        self.client.set_config({
            "api_key": settings.MAILCHIMP_API_KEY,
            "server": settings.MAILCHIMP_SERVER_PREFIX,
        })

    def test_connection(self) -> dict[str, Any]:
        try:
            response = self.client.ping.get()
            return {"status": "ok", "health_status": response.get("health_status")}
        except ApiClientError as e:
            return {"status": "error", "detail": str(e)}

    def _get_lists(self) -> list[dict]:
        response = self.client.lists.get_all_lists()
        return response.get("lists", [])

    def fetch_all(self) -> list[dict[str, Any]]:
        records = []
        for lst in self._get_lists():
            list_id = lst["id"]
            offset = 0
            count = 100
            while True:
                response = self.client.lists.get_list_members_info(
                    list_id, count=count, offset=offset
                )
                members = response.get("members", [])
                for member in members:
                    records.append(self._normalize_member(member, list_id))
                if len(members) < count:
                    break
                offset += count
        return records

    def _normalize_member(self, member: dict, list_id: str) -> dict[str, Any]:
        merge_fields = member.get("merge_fields", {})
        return {
            "source_system": "mailchimp",
            "source_record_id": member["id"],
            "list_id": list_id,
            "email": member.get("email_address"),
            "status": member.get("status"),
            "first_name": merge_fields.get("FNAME"),
            "last_name": merge_fields.get("LNAME"),
            "tags": [t["name"] for t in member.get("tags", [])],
            "merge_fields": merge_fields,
            "last_changed": member.get("last_changed"),
        }

    def push_update(self, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update a Mailchimp member. record_id is 'list_id:member_id'."""
        list_id, member_id = record_id.split(":", 1)
        response = self.client.lists.update_list_member(
            list_id,
            member_id,
            {
                "merge_fields": payload.get("merge_fields", {}),
                "tags": payload.get("tags", []),
            },
        )
        return {"status": "ok", "email": response.get("email_address")}
