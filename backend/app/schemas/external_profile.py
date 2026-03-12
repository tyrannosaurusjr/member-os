import uuid
from datetime import datetime

from pydantic import BaseModel


class ExternalProfileOut(BaseModel):
    external_profile_id: uuid.UUID
    person_id: uuid.UUID | None = None
    source_system: str
    source_record_id: str
    source_payload_json: dict
    source_hash: str | None = None
    source_last_seen_at: datetime | None = None
    last_synced_at: datetime | None = None
    sync_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
