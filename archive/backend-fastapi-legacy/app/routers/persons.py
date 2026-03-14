import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import MergeAuditLog, Person
from app.schemas.person import (
    MergeRequest,
    PersonCreate,
    PersonDetail,
    PersonOut,
    PersonUpdate,
    SplitRequest,
)

router = APIRouter(prefix="/persons", tags=["Persons"])


@router.get("", response_model=list[PersonOut])
async def list_persons(
    search: str | None = None,
    email: str | None = None,
    company: str | None = None,
    membership_status: str | None = None,
    canonical_tier_id: uuid.UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Person)

    if search:
        stmt = stmt.where(
            or_(
                Person.full_name.ilike(f"%{search}%"),
                Person.primary_email.ilike(f"%{search}%"),
                Person.company.ilike(f"%{search}%"),
            )
        )
    if email:
        stmt = stmt.where(func.lower(Person.primary_email) == email.lower())
    if company:
        stmt = stmt.where(Person.company.ilike(f"%{company}%"))

    stmt = stmt.offset((page - 1) * page_size).limit(page_size).order_by(Person.full_name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{person_id}", response_model=PersonDetail)
async def get_person(person_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Person)
        .where(Person.person_id == person_id)
        .options(
            selectinload(Person.memberships),
            selectinload(Person.external_profiles),
            selectinload(Person.review_items),
        )
    )
    result = await db.execute(stmt)
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.post("", response_model=PersonOut, status_code=201)
async def create_person(body: PersonCreate, db: AsyncSession = Depends(get_db)):
    person = Person(**body.model_dump())
    db.add(person)
    await db.commit()
    await db.refresh(person)
    return person


@router.patch("/{person_id}", response_model=PersonOut)
async def update_person(
    person_id: uuid.UUID, body: PersonUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Person).where(Person.person_id == person_id))
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(person, field, value)

    await db.commit()
    await db.refresh(person)
    return person


@router.post("/{person_id}/merge", status_code=200)
async def merge_person(
    person_id: uuid.UUID, body: MergeRequest, db: AsyncSession = Depends(get_db)
):
    target = await db.get(Person, person_id)
    source = await db.get(Person, body.source_person_id)

    if not target or not source:
        raise HTTPException(status_code=404, detail="Person not found")

    before_json = {
        "target": {"person_id": str(target.person_id), "full_name": target.full_name},
        "source": {"person_id": str(source.person_id), "full_name": source.full_name},
    }

    # Reassign related records from source to target
    from app.models import ExternalProfile, Membership, ReviewQueueItem

    for profile in source.external_profiles:
        profile.person_id = target.person_id
    for membership in source.memberships:
        membership.person_id = target.person_id
    for item in source.review_items:
        item.related_person_id = target.person_id

    after_json = {"merged_into": str(target.person_id), "source_deleted": str(source.person_id)}
    log = MergeAuditLog(
        decision_type="manual_merge",
        performed_by=body.reason,
        reason=body.reason,
        before_json=before_json,
        after_json=after_json,
    )
    db.add(log)
    await db.delete(source)
    await db.commit()

    return {"merged_into": str(target.person_id)}


@router.post("/{person_id}/split", status_code=200)
async def split_person(
    person_id: uuid.UUID, body: SplitRequest, db: AsyncSession = Depends(get_db)
):
    # Splitting requires human judgement on which records to move;
    # here we create an audit log entry and flag it for manual follow-up.
    person = await db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    log = MergeAuditLog(
        decision_type="split",
        reason=body.reason,
        before_json={"person_id": str(person_id), "full_name": person.full_name},
        after_json={"status": "pending_manual_split"},
    )
    db.add(log)
    await db.commit()
    return {"status": "split_requested", "person_id": str(person_id)}
