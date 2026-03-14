import json
from typing import Any

from app.config import settings
from app.connectors.base import BaseConnector


class GoogleSheetsConnector(BaseConnector):
    source_system = "google_sheets"

    def __init__(self):
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service

        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        creds_json = settings.GOOGLE_SERVICE_ACCOUNT_JSON
        if not creds_json:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

        creds_data = json.loads(creds_json)
        creds = Credentials.from_service_account_info(
            creds_data,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )
        self._service = build("sheets", "v4", credentials=creds)
        return self._service

    def test_connection(self) -> dict[str, Any]:
        try:
            self._get_service()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def fetch_all(self) -> list[dict[str, Any]]:
        """
        Fetch all rows from a configured sheet.
        The spreadsheet_id and range should be passed via environment or config.
        """
        return []

    def fetch_sheet(self, spreadsheet_id: str, range_name: str) -> list[dict[str, Any]]:
        service = self._get_service()
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        values = result.get("values", [])
        if not values:
            return []

        headers = values[0]
        records = []
        for row in values[1:]:
            # Pad row to header length
            padded = row + [""] * (len(headers) - len(row))
            record = dict(zip(headers, padded))
            record["source_system"] = "google_sheets"
            record["source_record_id"] = f"{spreadsheet_id}:{values.index(row) + 1}"
            records.append(record)
        return records

    def push_update(self, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Write back to a sheet. record_id format: 'spreadsheet_id:sheet_name:row_index'.
        payload should contain 'values': list of values to write.
        """
        service = self._get_service()
        spreadsheet_id, sheet_name, row_index = record_id.split(":", 2)
        range_name = f"{sheet_name}!A{row_index}"
        body = {"values": [payload.get("values", [])]}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
        return {"status": "ok", "range": range_name}
