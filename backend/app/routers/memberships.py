import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Membership, MembershipSeat
from app.schemas.membership import (
    MembershipCreate,
    MembershipOut,
    MembershipSeatCreate,
    MembershipSeatOut,
    MembershipUpdate,
)

router = APIRouter(prefix="/memberships", tags=["Memberships"])


@router.get("", response_model=list[MembershipOut])
async def list_memberships(
    person_id: uuid.UUID | None = None,
    canonical_tier_id: uuid.UUID | None = None,
    status: str | None = None,
    payment_method_type: str | None = None,
    review_required: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Membership)
    if person_id:
        stmt = stmt.where(Membership.person_id == person_id)
    if canonical_tier_id:
        stmt = stmt.where(Membership.canonical_tier_id == canonical_tier_id)
    if status:
        stmt = stmt.where(Membership.status == status)
    if payment_method_type:
        stmt = stmt.where(Membership.payment_method_type == payment_method_type)
    if review_required is not None:
        stmt = stmt.where(Membership.review_required == review_required)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{membership_id}", response_model=MembershipOut)
async def get_membership(membership_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    membership = await db.get(Membership, membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    return membership


@router.post("", response_model=MembershipOut, status_code=201)
async def create_membership(body: MembershipCreate, db: AsyncSession = Depends(get_db)):
    membership = Membership(**body.model_dump())
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


@router.patch("/{membership_id}", response_model=MembershipOut)
async def update_membership(
    membership_id: uuid.UUID, body: MembershipUpdate, db: AsyncSession = Depends(get_db)
):
    membership = await db.get(Membership, membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(membership, field, value)
    await db.commit()
    await db.refresh(membership)
    return membership


@router.post("/{membership_id}/seats", response_model=MembershipSeatOut, status_code=201)
async def create_seat(
    membership_id: uuid.UUID, body: MembershipSeatCreate, db: AsyncSession = Depends(get_db)
):
    membership = await db.get(Membership, membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    seat = MembershipSeat(membership_id=membership_id, **body.model_dump())
    db.add(seat)
    await db.commit()
    await db.refresh(seat)
    return seat
