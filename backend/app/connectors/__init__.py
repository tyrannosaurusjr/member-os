from app.connectors.base import BaseConnector
from app.connectors.stripe_connector import StripeConnector
from app.connectors.mailchimp_connector import MailchimpConnector
from app.connectors.luma_connector import LumaConnector
from app.connectors.sheets_connector import GoogleSheetsConnector

_REGISTRY: dict[str, type[BaseConnector]] = {
    "stripe": StripeConnector,
    "mailchimp": MailchimpConnector,
    "luma": LumaConnector,
    "google_sheets": GoogleSheetsConnector,
}


def get_connector(source_system: str) -> BaseConnector:
    cls = _REGISTRY.get(source_system)
    if not cls:
        raise ValueError(f"Unknown connector: {source_system}")
    return cls()
