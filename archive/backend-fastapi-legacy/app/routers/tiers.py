import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import CanonicalMembershipTier, MembershipAliasMapping
from app.schemas.tier import AliasCreate, AliasOut, AliasUpdate, TierCreate, TierOut, TierUpdate

router = APIRouter(tags=["Tiers"])


@router.get("/tiers", response_model=list[TierOut])
async def list_tiers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CanonicalMembershipTier).order_by(CanonicalMembershipTier.canonical_tier_name))
    return result.scalars().all()


@router.post("/tiers", response_model=TierOut, status_code=201)
async def create_tier(body: TierCreate, db: AsyncSession = Depends(get_db)):
    tier = CanonicalMembershipTier(**body.model_dump())
    db.add(tier)
    await db.commit()
    await db.refresh(tier)
    return tier


@router.patch("/tiers/{canonical_tier_id}", response_model=TierOut)
async def update_tier(
    canonical_tier_id: uuid.UUID, body: TierUpdate, db: AsyncSession = Depends(get_db)
):
    tier = await db.get(CanonicalMembershipTier, canonical_tier_id)
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tier, field, value)
    await db.commit()
    await db.refresh(tier)
    return tier


@router.get("/tier-aliases", response_model=list[AliasOut])
async def list_aliases(
    source_system: str | None = None,
    canonical_tier_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MembershipAliasMapping)
    if source_system:
        stmt = stmt.where(MembershipAliasMapping.source_system == source_system)
    if canonical_tier_id:
        stmt = stmt.where(MembershipAliasMapping.canonical_tier_id == canonical_tier_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/tier-aliases", response_model=AliasOut, status_code=201)
async def create_alias(body: AliasCreate, db: AsyncSession = Depends(get_db)):
    alias = MembershipAliasMapping(**body.model_dump())
    db.add(alias)
    await db.commit()
    await db.refresh(alias)
    return alias


@router.patch("/tier-aliases/{alias_id}", response_model=AliasOut)
async def update_alias(
    alias_id: uuid.UUID, body: AliasUpdate, db: AsyncSession = Depends(get_db)
):
    alias = await db.get(MembershipAliasMapping, alias_id)
    if not alias:
        raise HTTPException(status_code=404, detail="Alias not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(alias, field, value)
    await db.commit()
    await db.refresh(alias)
    return alias
