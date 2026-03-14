import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Membership(Base):
    __tablename__ = "memberships"

    membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.person_id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.organization_id", ondelete="SET NULL")
    )
    canonical_tier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canonical_membership_tiers.canonical_tier_id", ondelete="RESTRICT"),
        nullable=False,
    )
    membership_relationship_type: Mapped[str] = mapped_column(Text, nullable=False, default="individual")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    payment_method_type: Mapped[str] = mapped_column(Text, nullable=False, default="manual_override")

    price_paid: Mapped[float | None] = mapped_column(Numeric(12, 2))
    price_currency: Mapped[str] = mapped_column(Text, nullable=False, default="JPY")
    discount_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    discount_reason: Mapped[str | None] = mapped_column(Text)
    list_price_snapshot: Mapped[float | None] = mapped_column(Numeric(12, 2))
    billing_frequency: Mapped[str | None] = mapped_column(Text)

    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    renewal_date: Mapped[date | None] = mapped_column(Date)
    last_payment_date: Mapped[date | None] = mapped_column(Date)
    amount_last_paid: Mapped[float | None] = mapped_column(Numeric(12, 2))

    source_of_truth: Mapped[str | None] = mapped_column(Text)
    relationship_strength: Mapped[str | None] = mapped_column(Text)
    review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    person: Mapped["Person"] = relationship(back_populates="memberships")
    organization: Mapped["Organization | None"] = relationship(back_populates="memberships")
    tier: Mapped["CanonicalMembershipTier"] = relationship(back_populates="memberships")
    seats: Mapped[list["MembershipSeat"]] = relationship(back_populates="membership")
    review_items: Mapped[list["ReviewQueueItem"]] = relationship(back_populates="related_membership")
    sync_events: Mapped[list["SyncEvent"]] = relationship(back_populates="related_membership")


class MembershipSeat(Base):
    __tablename__ = "membership_seats"

    membership_seat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.membership_id", ondelete="CASCADE"), nullable=False
    )
    membership_holder_person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.person_id", ondelete="SET NULL")
    )
    seat_holder_person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.person_id", ondelete="SET NULL")
    )
    seat_title: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    membership: Mapped["Membership"] = relationship(back_populates="seats")


from app.models.person import Organization, Person  # noqa: E402
from app.models.tier import CanonicalMembershipTier  # noqa: E402
from app.models.review import ReviewQueueItem  # noqa: E402
from app.models.sync import SyncEvent  # noqa: E402
