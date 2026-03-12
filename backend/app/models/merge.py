import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MergeCandidate(Base):
    __tablename__ = "merge_candidates"

    merge_candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    left_person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.person_id", ondelete="CASCADE"), nullable=False
    )
    right_person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.person_id", ondelete="CASCADE"), nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    strong_signal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    medium_signal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weak_signal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    explanation: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False, default="review")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    left_person: Mapped["Person"] = relationship(
        foreign_keys=[left_person_id], back_populates="merge_candidates_left"
    )
    right_person: Mapped["Person"] = relationship(
        foreign_keys=[right_person_id], back_populates="merge_candidates_right"
    )


from app.models.person import Person  # noqa: E402
