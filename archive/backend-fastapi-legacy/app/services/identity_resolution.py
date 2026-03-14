"""
Identity Resolution Engine

Compares person records and generates merge candidates with confidence scores.

Signal categories (matching the spec):
  Strong (95+)  → auto-merge
  Medium (75–94) → send to review queue
  Weak (<75)    → do not merge
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import MergeCandidate, Person, ReviewQueueItem


@dataclass
class MatchSignal:
    name: str
    weight: float
    matched: bool
    detail: str = ""


@dataclass
class MatchResult:
    left_person_id: Any
    right_person_id: Any
    score: float
    signals: list[MatchSignal] = field(default_factory=list)

    @property
    def strong_count(self) -> int:
        return sum(1 for s in self.signals if s.matched and s.weight >= 30)

    @property
    def medium_count(self) -> int:
        return sum(1 for s in self.signals if s.matched and 10 <= s.weight < 30)

    @property
    def weak_count(self) -> int:
        return sum(1 for s in self.signals if s.matched and s.weight < 10)

    @property
    def recommended_action(self) -> str:
        if self.score >= settings.AUTO_MERGE_THRESHOLD:
            return "auto_merge"
        if self.score >= settings.REVIEW_THRESHOLD:
            return "review"
        return "ignore"

    def to_explanation(self) -> list[dict]:
        return [
            {"signal": s.name, "matched": s.matched, "weight": s.weight, "detail": s.detail}
            for s in self.signals
        ]


def _normalize_email(email: str | None) -> str | None:
    return email.strip().lower() if email else None


def _normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit())
    return digits if len(digits) >= 7 else None


def score_pair(left: Person, right: Person) -> MatchResult:
    """Score a pair of persons and return a MatchResult."""
    signals: list[MatchSignal] = []
    score = 0.0

    # --- Strong signals ---
    left_email = _normalize_email(left.primary_email)
    right_email = _normalize_email(right.primary_email)
    if left_email and right_email and left_email == right_email:
        signals.append(MatchSignal("exact_email_match", 40, True, left_email))
        score += 40
    else:
        signals.append(MatchSignal("exact_email_match", 40, False))

    left_phone = _normalize_phone(left.primary_phone)
    right_phone = _normalize_phone(right.primary_phone)
    if left_phone and right_phone and left_phone == right_phone:
        signals.append(MatchSignal("exact_phone_match", 35, True, left_phone))
        score += 35
    else:
        signals.append(MatchSignal("exact_phone_match", 35, False))

    # --- Medium signals ---
    left_name = (left.full_name or "").strip().lower()
    right_name = (right.full_name or "").strip().lower()
    left_company = (left.company or "").strip().lower()
    right_company = (right.company or "").strip().lower()

    if left_name and right_name and left_name == right_name and left_company and left_company == right_company:
        signals.append(MatchSignal("same_name_and_company", 25, True))
        score += 25
    else:
        signals.append(MatchSignal("same_name_and_company", 25, False))

    # Similar email domain
    if left_email and right_email:
        left_domain = left_email.split("@")[-1] if "@" in left_email else ""
        right_domain = right_email.split("@")[-1] if "@" in right_email else ""
        if left_domain and right_domain and left_domain == right_domain:
            signals.append(MatchSignal("same_email_domain", 15, True, left_domain))
            score += 15
        else:
            signals.append(MatchSignal("same_email_domain", 15, False))

    # --- Weak signals ---
    if left_name and right_name:
        # Simple token overlap
        left_tokens = set(left_name.split())
        right_tokens = set(right_name.split())
        overlap = left_tokens & right_tokens
        if len(overlap) >= 2:
            signals.append(MatchSignal("similar_name", 8, True, " ".join(overlap)))
            score += 8
        else:
            signals.append(MatchSignal("similar_name", 8, False))
    else:
        signals.append(MatchSignal("similar_name", 8, False))

    if left_company and right_company and left_company == right_company:
        signals.append(MatchSignal("same_company", 5, True, left_company))
        score += 5
    else:
        signals.append(MatchSignal("same_company", 5, False))

    score = min(score, 100.0)
    return MatchResult(
        left_person_id=left.person_id,
        right_person_id=right.person_id,
        score=score,
        signals=signals,
    )


async def run_resolution(db: AsyncSession, person_ids: list | None = None) -> int:
    """
    Run identity resolution over all (or specified) persons.
    Returns the number of candidates created.
    """
    if person_ids:
        result = await db.execute(select(Person).where(Person.person_id.in_(person_ids)))
    else:
        result = await db.execute(select(Person))
    persons = result.scalars().all()

    created = 0
    # O(n²) — acceptable for moderate member counts; use DB-side trgm for large scale
    for i, left in enumerate(persons):
        for right in persons[i + 1:]:
            match = score_pair(left, right)
            if match.score < settings.REVIEW_THRESHOLD:
                continue

            # Skip if candidate already exists
            existing = (
                await db.execute(
                    select(MergeCandidate).where(
                        (
                            (MergeCandidate.left_person_id == left.person_id)
                            & (MergeCandidate.right_person_id == right.person_id)
                        )
                        | (
                            (MergeCandidate.left_person_id == right.person_id)
                            & (MergeCandidate.right_person_id == left.person_id)
                        )
                    )
                )
            ).scalar_one_or_none()
            if existing:
                continue

            candidate = MergeCandidate(
                left_person_id=left.person_id,
                right_person_id=right.person_id,
                confidence_score=match.score,
                strong_signal_count=match.strong_count,
                medium_signal_count=match.medium_count,
                weak_signal_count=match.weak_count,
                explanation=match.to_explanation(),
                recommended_action=match.recommended_action,
            )
            db.add(candidate)

            if match.recommended_action == "review":
                review_item = ReviewQueueItem(
                    item_type="duplicate_contact",
                    related_person_id=left.person_id,
                    severity="medium" if match.score < 90 else "high",
                    title=f"Possible duplicate: {left.full_name} / {right.full_name}",
                    details={"confidence_score": match.score, "signals": match.to_explanation()},
                )
                db.add(review_item)

            created += 1

    await db.commit()
    return created
