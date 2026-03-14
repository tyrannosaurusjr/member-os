import uuid
from datetime import datetime

from pydantic import BaseModel


class SyncRunRequest(BaseModel):
    source_system: str
    direction: str  # inbound | outbound
    dry_run: bool = False


class SyncRunOut(BaseModel):
    sync_run_id: uuid.UUID
    source_system: str
    direction: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    records_processed: int
    records_failed: int
    error_summary: str | None = None

    model_config = {"from_attributes": True}


class SyncEventOut(BaseModel):
    sync_event_id: uuid.UUID
    sync_run_id: uuid.UUID | None = None
    source_system: str
    related_person_id: uuid.UUID | None = None
    related_membership_id: uuid.UUID | None = None
    action_type: str
    payload: dict
    status: str
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectorPullRequest(BaseModel):
    full_refresh: bool = False


class SystemSummary(BaseModel):
    total_persons: int
    total_memberships: int
    unresolved_duplicates: int
    unknown_tiers: int
    sync_errors: int
    last_successful_sync_by_source: dict[str, datetime | None]
