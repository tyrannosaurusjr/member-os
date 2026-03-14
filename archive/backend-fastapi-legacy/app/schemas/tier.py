import uuid
from datetime import date, datetime

from pydantic import BaseModel


class TierCreate(BaseModel):
    canonical_tier_name: str
    tier_family: str
    description: str | None = None
    is_active: bool = True


class TierUpdate(BaseModel):
    canonical_tier_name: str | None = None
    tier_family: str | None = None
    description: str | None = None
    is_active: bool | None = None


class TierOut(BaseModel):
    canonical_tier_id: uuid.UUID
    canonical_tier_name: str
    tier_family: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TierPriceScheduleCreate(BaseModel):
    canonical_tier_id: uuid.UUID
    list_price: float
    currency: str = "JPY"
    billing_frequency: str
    effective_from: date
    effective_to: date | None = None


class TierPriceScheduleOut(TierPriceScheduleCreate):
    tier_price_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class AliasCreate(BaseModel):
    source_system: str
    source_tier_name: str | None = None
    source_product_id: str | None = None
    source_plan_id: str | None = None
    source_price: float | None = None
    currency: str = "JPY"
    canonical_tier_id: uuid.UUID
    confidence_score: float = 0
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str | None = None


class AliasUpdate(BaseModel):
    canonical_tier_id: uuid.UUID | None = None
    confidence_score: float | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str | None = None


class AliasOut(AliasCreate):
    alias_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
