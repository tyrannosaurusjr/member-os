"""
Membership Normalization Service

Resolves source-specific tier names → canonical tiers.
Evaluates pricing anomalies and flags records for review.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import CanonicalMembershipTier, Membership, MembershipAliasMapping, ReviewQueueItem


async def resolve_tier_alias(
    db: AsyncSession,
    source_system: str,
    source_tier_name: str | None = None,
    source_product_id: str | None = None,
    source_plan_id: str | None = None,
    source_price: float | None = None,
) -> tuple[CanonicalMembershipTier | None, float]:
    """
    Look up an alias mapping and return (canonical_tier, confidence_score).
    Returns (None, 0) if no match found.
    """
    stmt = select(MembershipAliasMapping).where(
        MembershipAliasMapping.source_system == source_system
    )

    filters = []
    if source_tier_name:
        filters.append(MembershipAliasMapping.source_tier_name == source_tier_name)
    if source_product_id:
        filters.append(MembershipAliasMapping.source_product_id == source_product_id)
    if source_plan_id:
        filters.append(MembershipAliasMapping.source_plan_id == source_plan_id)

    if filters:
        from sqlalchemy import or_
        stmt = stmt.where(or_(*filters))

    stmt = stmt.order_by(MembershipAliasMapping.confidence_score.desc())
    result = await db.execute(stmt)
    alias = result.scalars().first()

    if not alias:
        return None, 0.0

    tier = await db.get(CanonicalMembershipTier, alias.canonical_tier_id)
    return tier, float(alias.confidence_score)


async def flag_unknown_tier(
    db: AsyncSession,
    source_system: str,
    source_tier_name: str,
    related_person_id=None,
    related_membership_id=None,
) -> None:
    """Create a review queue item for an unrecognized tier name."""
    item = ReviewQueueItem(
        item_type="unknown_tier",
        related_person_id=related_person_id,
        related_membership_id=related_membership_id,
        severity="medium",
        title=f"Unknown tier '{source_tier_name}' from {source_system}",
        details={"source_system": source_system, "source_tier_name": source_tier_name},
    )
    db.add(item)
    await db.flush()


async def check_price_anomaly(
    db: AsyncSession,
    membership: Membership,
) -> bool:
    """
    Flag memberships where price_paid is suspiciously low relative to list price.
    Returns True if anomaly was flagged.
    """
    if not membership.price_paid or not membership.list_price_snapshot:
        return False
    if membership.list_price_snapshot <= 0:
        return False

    ratio = membership.price_paid / membership.list_price_snapshot
    if ratio < settings.PRICE_ANOMALY_THRESHOLD:
        item = ReviewQueueItem(
            item_type="price_anomaly",
            related_person_id=membership.person_id,
            related_membership_id=membership.membership_id,
            severity="low",
            title=f"Price anomaly: paid {membership.price_paid} vs list {membership.list_price_snapshot}",
            details={
                "price_paid": float(membership.price_paid),
                "list_price": float(membership.list_price_snapshot),
                "ratio": round(ratio, 3),
                "currency": membership.price_currency,
            },
        )
        db.add(item)
        await db.flush()
        return True
    return False


def derive_discount_percent(price_paid: float | None, list_price: float | None) -> float | None:
    """Calculate discount percentage from paid vs list price."""
    if not price_paid or not list_price or list_price <= 0:
        return None
    discount = (list_price - price_paid) / list_price * 100
    return round(max(discount, 0.0), 2)


async def normalize_membership(
    db: AsyncSession,
    membership: Membership,
) -> None:
    """
    Run full normalization on an existing membership record:
    - Fill discount_percent if missing
    - Flag price anomalies
    - Set review_required if no canonical tier resolution exists
    """
    if membership.price_paid and membership.list_price_snapshot and membership.discount_percent is None:
        membership.discount_percent = derive_discount_percent(
            float(membership.price_paid), float(membership.list_price_snapshot)
        )

    await check_price_anomaly(db, membership)

    if membership.review_required:
        existing = (
            await db.execute(
                select(ReviewQueueItem).where(
                    ReviewQueueItem.item_type == "conflicting_membership",
                    ReviewQueueItem.related_membership_id == membership.membership_id,
                    ReviewQueueItem.status == "open",
                )
            )
        ).scalar_one_or_none()
        if not existing:
            item = ReviewQueueItem(
                item_type="conflicting_membership",
                related_person_id=membership.person_id,
                related_membership_id=membership.membership_id,
                severity="high",
                title=f"Membership requires review",
                details={"membership_id": str(membership.membership_id)},
            )
            db.add(item)
