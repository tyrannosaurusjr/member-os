import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CanonicalMembershipTier(Base):
    __tablename__ = "canonical_membership_tiers"

    canonical_tier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    canonical_tier_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    tier_family: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    price_schedules: Mapped[list["TierPriceSchedule"]] = relationship(back_populates="tier")
    alias_mappings: Mapped[list["MembershipAliasMapping"]] = relationship(back_populates="tier")
    memberships: Mapped[list["Membership"]] = relationship(back_populates="tier")


class TierPriceSchedule(Base):
    __tablename__ = "tier_price_schedules"

    tier_price_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    canonical_tier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canonical_membership_tiers.canonical_tier_id", ondelete="CASCADE"),
        nullable=False,
    )
    list_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="JPY")
    billing_frequency: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tier: Mapped["CanonicalMembershipTier"] = relationship(back_populates="price_schedules")


class MembershipAliasMapping(Base):
    __tablename__ = "membership_alias_mappings"

    alias_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_system: Mapped[str] = mapped_column(Text, nullable=False)
    source_tier_name: Mapped[str | None] = mapped_column(Text)
    source_product_id: Mapped[str | None] = mapped_column(Text)
    source_plan_id: Mapped[str | None] = mapped_column(Text)
    source_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(Text, default="JPY")
    canonical_tier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canonical_membership_tiers.canonical_tier_id", ondelete="CASCADE"),
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tier: Mapped["CanonicalMembershipTier"] = relationship(back_populates="alias_mappings")


from app.models.membership import Membership  # noqa: E402
