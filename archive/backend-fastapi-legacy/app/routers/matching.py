import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MergeAuditLog, MergeCandidate, Person
from app.schemas.merge import (
    MergeApproveRequest,
    MergeCandidateOut,
    MergeRejectRequest,
    MatchRunRequest,
)

router = APIRouter(tags=["Matching"])


@router.get("/merge-candidates", response_model=list[MergeCandidateOut])
async def list_merge_candidates(
    status: str | None = None,
    min_confidence: float | None = None,
    recommended_action: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MergeCandidate)
    if status:
        stmt = stmt.where(MergeCandidate.status == status)
    if min_confidence is not None:
        stmt = stmt.where(MergeCandidate.confidence_score >= min_confidence)
    if recommended_action:
        stmt = stmt.where(MergeCandidate.recommended_action == recommended_action)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/merge-candidates/{merge_candidate_id}", response_model=MergeCandidateOut)
async def get_merge_candidate(
    merge_candidate_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    candidate = await db.get(MergeCandidate, merge_candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Merge candidate not found")
    return candidate


@router.post("/matching/run", status_code=202)
async def run_matching(body: MatchRunRequest, db: AsyncSession = Depends(get_db)):
    from app.workers.tasks import run_identity_resolution
    run_identity_resolution.delay(
        person_ids=[str(p) for p in body.person_ids] if body.person_ids else None
    )
    return {"status": "queued"}


@router.post("/merge-candidates/{merge_candidate_id}/approve", status_code=200)
async def approve_merge(
    merge_candidate_id: uuid.UUID,
    body: MergeApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    candidate = await db.get(MergeCandidate, merge_candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Merge candidate not found")
    if candidate.status != "open":
        raise HTTPException(status_code=400, detail="Candidate is not open")

    left = await db.get(Person, candidate.left_person_id)
    right = await db.get(Person, candidate.right_person_id)
    if not left or not right:
        raise HTTPException(status_code=404, detail="One or both persons not found")

    # Reassign right person's records to left
    from app.models import ExternalProfile, Membership, ReviewQueueItem

    for profile in right.external_profiles:
        profile.person_id = left.person_id
    for membership in right.memberships:
        membership.person_id = left.person_id
    for item in right.review_items:
        item.related_person_id = left.person_id

    candidate.status = "merged"
    candidate.resolved_at = datetime.now(timezone.utc)

    log = MergeAuditLog(
        decision_type="manual_merge",
        performed_by=body.performed_by,
        reason=body.reason,
        before_json={
            "left": {"person_id": str(left.person_id), "full_name": left.full_name},
            "right": {"person_id": str(right.person_id), "full_name": right.full_name},
        },
        after_json={"merged_into": str(left.person_id)},
    )
    db.add(log)
    await db.delete(right)
    await db.commit()
    return {"status": "merged", "canonical_person_id": str(left.person_id)}


@router.post("/merge-candidates/{merge_candidate_id}/reject", status_code=200)
async def reject_merge(
    merge_candidate_id: uuid.UUID,
    body: MergeRejectRequest,
    db: AsyncSession = Depends(get_db),
):
    candidate = await db.get(MergeCandidate, merge_candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Merge candidate not found")
    candidate.status = "rejected"
    candidate.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "rejected"}


@router.post("/merge-candidates/{merge_candidate_id}/ignore", status_code=200)
async def ignore_merge(merge_candidate_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    candidate = await db.get(MergeCandidate, merge_candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Merge candidate not found")
    candidate.status = "ignored"
    candidate.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "ignored"}
