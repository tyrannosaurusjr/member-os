import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReviewQueueItem(Base):
    __tablename__ = "review_queue_items"

    review_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    related_person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.person_id", ondelete="SET NULL")
    )
    related_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.membership_id", ondelete="SET NULL")
    )
    related_external_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_profiles.external_profile_id", ondelete="SET NULL")
    )
    severity: Mapped[str] = mapped_column(Text, nullable=False, default="medium")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    assigned_to: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    related_person: Mapped["Person | None"] = relationship(back_populates="review_items")
    related_membership: Mapped["Membership | None"] = relationship(back_populates="review_items")


from app.models.person import Person  # noqa: E402
from app.models.membership import Membership  # noqa: E402
