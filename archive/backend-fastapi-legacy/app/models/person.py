import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    website: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    person_orgs: Mapped[list["PersonOrganization"]] = relationship(back_populates="organization")
    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")


class Person(Base):
    __tablename__ = "persons"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    primary_email: Mapped[str | None] = mapped_column(Text)
    secondary_emails: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    primary_phone: Mapped[str | None] = mapped_column(Text)
    secondary_phones: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    company: Mapped[str | None] = mapped_column(Text)
    job_title: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    linkedin_url: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    source_confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    person_orgs: Mapped[list["PersonOrganization"]] = relationship(back_populates="person")
    external_profiles: Mapped[list["ExternalProfile"]] = relationship(back_populates="person")
    memberships: Mapped[list["Membership"]] = relationship(back_populates="person")
    review_items: Mapped[list["ReviewQueueItem"]] = relationship(back_populates="related_person")
    merge_candidates_left: Mapped[list["MergeCandidate"]] = relationship(
        foreign_keys="MergeCandidate.left_person_id", back_populates="left_person"
    )
    merge_candidates_right: Mapped[list["MergeCandidate"]] = relationship(
        foreign_keys="MergeCandidate.right_person_id", back_populates="right_person"
    )


class PersonOrganization(Base):
    __tablename__ = "person_organizations"

    person_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.person_id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.organization_id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(Text, nullable=False, default="member")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    person: Mapped["Person"] = relationship(back_populates="person_orgs")
    organization: Mapped["Organization"] = relationship(back_populates="person_orgs")


# Fix forward references
from app.models.external_profile import ExternalProfile  # noqa: E402
from app.models.membership import Membership  # noqa: E402
from app.models.merge import MergeCandidate  # noqa: E402
from app.models.review import ReviewQueueItem  # noqa: E402
