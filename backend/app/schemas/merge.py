import uuid
from datetime import datetime

from pydantic import BaseModel


class MergeCandidateOut(BaseModel):
    merge_candidate_id: uuid.UUID
    left_person_id: uuid.UUID
    right_person_id: uuid.UUID
    confidence_score: float
    strong_signal_count: int
    medium_signal_count: int
    weak_signal_count: int
    explanation: list[dict]
    recommended_action: str
    status: str
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class MergeApproveRequest(BaseModel):
    performed_by: str
    reason: str | None = None


class MergeRejectRequest(BaseModel):
    performed_by: str
    reason: str | None = None


class MatchRunRequest(BaseModel):
    person_ids: list[uuid.UUID] | None = None
