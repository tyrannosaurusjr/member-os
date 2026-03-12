import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ReviewQueueItem
from app.schemas.review import ReviewItemOut, ReviewItemResolve, ReviewItemUpdate

router = APIRouter(prefix="/review-queue", tags=["Review Queue"])


@router.get("", response_model=list[ReviewItemOut])
async def list_review_items(
    item_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    assigned_to: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ReviewQueueItem)
    if item_type:
        stmt = stmt.where(ReviewQueueItem.item_type == item_type)
    if severity:
        stmt = stmt.where(ReviewQueueItem.severity == severity)
    if status:
        stmt = stmt.where(ReviewQueueItem.status == status)
    if assigned_to:
        stmt = stmt.where(ReviewQueueItem.assigned_to == assigned_to)
    stmt = stmt.order_by(ReviewQueueItem.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{review_item_id}", response_model=ReviewItemOut)
async def get_review_item(review_item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    item = await db.get(ReviewQueueItem, review_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    return item


@router.patch("/{review_item_id}", response_model=ReviewItemOut)
async def update_review_item(
    review_item_id: uuid.UUID, body: ReviewItemUpdate, db: AsyncSession = Depends(get_db)
):
    item = await db.get(ReviewQueueItem, review_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/{review_item_id}/resolve", status_code=200)
async def resolve_review_item(
    review_item_id: uuid.UUID, body: ReviewItemResolve, db: AsyncSession = Depends(get_db)
):
    item = await db.get(ReviewQueueItem, review_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    item.status = "resolved"
    item.resolved_at = datetime.now(timezone.utc)
    item.details = {**item.details, "resolution_note": body.resolution_note}
    await db.commit()
    return {"status": "resolved"}
