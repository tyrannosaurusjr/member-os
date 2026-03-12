import uuid
from datetime import date, datetime

from pydantic import BaseModel


class MembershipCreate(BaseModel):
    person_id: uuid.UUID
    organization_id: uuid.UUID | None = None
    canonical_tier_id: uuid.UUID
    membership_relationship_type: str = "individual"
    status: str = "unknown"
    payment_method_type: str = "manual_override"
    price_paid: float | None = None
    price_currency: str = "JPY"
    discount_percent: float | None = None
    discount_reason: str | None = None
    list_price_snapshot: float | None = None
    billing_frequency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    renewal_date: date | None = None
    last_payment_date: date | None = None
    amount_last_paid: float | None = None
    source_of_truth: str | None = None
    relationship_strength: str | None = None
    review_required: bool = False


class MembershipUpdate(BaseModel):
    canonical_tier_id: uuid.UUID | None = None
    status: str | None = None
    payment_method_type: str | None = None
    price_paid: float | None = None
    discount_percent: float | None = None
    discount_reason: str | None = None
    list_price_snapshot: float | None = None
    billing_frequency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    renewal_date: date | None = None
    review_required: bool | None = None


class MembershipOut(MembershipCreate):
    membership_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MembershipSeatCreate(BaseModel):
    membership_holder_person_id: uuid.UUID
    seat_holder_person_id: uuid.UUID
    seat_title: str | None = None


class MembershipSeatOut(MembershipSeatCreate):
    membership_seat_id: uuid.UUID
    membership_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
