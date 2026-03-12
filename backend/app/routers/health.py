from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MergeCandidate, Person, Membership, ReviewQueueItem, SyncRun
from app.schemas.sync import SystemSummary

router = APIRouter(tags=["System"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/system/summary", response_model=SystemSummary)
async def system_summary(db: AsyncSession = Depends(get_db)):
    total_persons = (await db.execute(select(func.count()).select_from(Person))).scalar_one()
    total_memberships = (await db.execute(select(func.count()).select_from(Membership))).scalar_one()

    unresolved_duplicates = (
        await db.execute(
            select(func.count()).select_from(MergeCandidate).where(MergeCandidate.status == "open")
        )
    ).scalar_one()

    unknown_tiers = (
        await db.execute(
            select(func.count())
            .select_from(ReviewQueueItem)
            .where(ReviewQueueItem.item_type == "unknown_tier", ReviewQueueItem.status == "open")
        )
    ).scalar_one()

    sync_errors = (
        await db.execute(
            select(func.count()).select_from(SyncRun).where(SyncRun.status == "failed")
        )
    ).scalar_one()

    # Last successful sync per source
    rows = (
        await db.execute(
            select(SyncRun.source_system, func.max(SyncRun.completed_at))
            .where(SyncRun.status == "completed")
            .group_by(SyncRun.source_system)
        )
    ).all()
    last_sync = {row[0]: row[1] for row in rows}

    return SystemSummary(
        total_persons=total_persons,
        total_memberships=total_memberships,
        unresolved_duplicates=unresolved_duplicates,
        unknown_tiers=unknown_tiers,
        sync_errors=sync_errors,
        last_successful_sync_by_source=last_sync,
    )
