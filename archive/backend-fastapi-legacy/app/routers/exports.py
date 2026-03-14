import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Membership, Person, ReviewQueueItem

router = APIRouter(prefix="/exports", tags=["Exports"])


def _stream_csv(rows: list[dict], filename: str) -> StreamingResponse:
    if not rows:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/persons.csv")
async def export_persons(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Person))
    persons = result.scalars().all()
    rows = [
        {
            "person_id": str(p.person_id),
            "full_name": p.full_name,
            "primary_email": p.primary_email,
            "company": p.company,
            "job_title": p.job_title,
            "location": p.location,
            "primary_phone": p.primary_phone,
            "created_at": p.created_at.isoformat(),
        }
        for p in persons
    ]
    return _stream_csv(rows, "persons.csv")


@router.get("/memberships.csv")
async def export_memberships(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Membership))
    memberships = result.scalars().all()
    rows = [
        {
            "membership_id": str(m.membership_id),
            "person_id": str(m.person_id),
            "canonical_tier_id": str(m.canonical_tier_id),
            "status": m.status,
            "payment_method_type": m.payment_method_type,
            "price_paid": m.price_paid,
            "price_currency": m.price_currency,
            "discount_percent": m.discount_percent,
            "renewal_date": m.renewal_date,
        }
        for m in memberships
    ]
    return _stream_csv(rows, "memberships.csv")


@router.get("/review-queue.csv")
async def export_review_queue(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ReviewQueueItem).where(ReviewQueueItem.status == "open")
    )
    items = result.scalars().all()
    rows = [
        {
            "review_item_id": str(i.review_item_id),
            "item_type": i.item_type,
            "severity": i.severity,
            "title": i.title,
            "related_person_id": str(i.related_person_id) if i.related_person_id else "",
            "assigned_to": i.assigned_to or "",
            "created_at": i.created_at.isoformat(),
        }
        for i in items
    ]
    return _stream_csv(rows, "review-queue.csv")
