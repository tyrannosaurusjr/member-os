import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class OrganizationBase(BaseModel):
    name: str
    website: str | None = None
    domain: str | None = None
    notes: str | None = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: str | None = None
    website: str | None = None
    domain: str | None = None
    notes: str | None = None


class OrganizationOut(OrganizationBase):
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    full_name: str
    primary_email: str | None = None
    secondary_emails: list[str] = []
    primary_phone: str | None = None
    secondary_phones: list[str] = []
    company: str | None = None
    job_title: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    website: str | None = None
    notes: str | None = None


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    primary_email: str | None = None
    secondary_emails: list[str] | None = None
    primary_phone: str | None = None
    secondary_phones: list[str] | None = None
    company: str | None = None
    job_title: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    website: str | None = None
    notes: str | None = None


class PersonOut(PersonBase):
    person_id: uuid.UUID
    source_confidence_score: float | None = None
    last_verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonDetail(PersonOut):
    memberships: list = []
    external_profiles: list = []
    review_items: list = []


class MergeRequest(BaseModel):
    source_person_id: uuid.UUID
    reason: str | None = None


class SplitRequest(BaseModel):
    reason: str


class PersonListParams(BaseModel):
    search: str | None = None
    email: str | None = None
    company: str | None = None
    membership_status: str | None = None
    canonical_tier_id: uuid.UUID | None = None
    page: int = 1
    page_size: int = 50
