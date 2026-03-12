"""Base class for all source connectors."""

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    source_system: str = ""

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        """Verify credentials and connectivity. Returns status dict."""
        ...

    @abstractmethod
    def fetch_all(self) -> list[dict[str, Any]]:
        """Pull all records from the source. Returns list of raw payloads."""
        ...

    def fetch_incremental(self, since=None) -> list[dict[str, Any]]:
        """Pull records updated since a given timestamp. Default: full fetch."""
        return self.fetch_all()

    def push_update(self, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Push a canonical update back to the source. Override where supported."""
        raise NotImplementedError(f"{self.source_system} does not support outbound sync yet")
