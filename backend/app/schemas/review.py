import uuid
from datetime import datetime

from pydantic import BaseModel


class ReviewItemOut(BaseModel):
    review_item_id: uuid.UUID
    item_type: str
    related_person_id: uuid.UUID | None = None
    related_membership_id: uuid.UUID | None = None
    related_external_profile_id: uuid.UUID | None = None
    severity: str
    title: str
    details: dict
    status: str
    assigned_to: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReviewItemUpdate(BaseModel):
    status: str | None = None
    assigned_to: str | None = None


class ReviewItemResolve(BaseModel):
    resolution_note: str
