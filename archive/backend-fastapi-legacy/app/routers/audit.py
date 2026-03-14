import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MergeAuditLog

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditLogOut(BaseModel):
    decision_id: uuid.UUID
    decision_type: str
    performed_by: str | None
    reason: str | None
    before_json: dict
    after_json: dict
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/merges", response_model=list[AuditLogOut])
async def list_merge_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MergeAuditLog).order_by(MergeAuditLog.created_at.desc())
    )
    return [
        AuditLogOut(
            decision_id=row.decision_id,
            decision_type=row.decision_type,
            performed_by=row.performed_by,
            reason=row.reason,
            before_json=row.before_json,
            after_json=row.after_json,
            created_at=row.created_at.isoformat(),
        )
        for row in result.scalars().all()
    ]


@router.get("/merges/{decision_id}", response_model=AuditLogOut)
async def get_merge_log(decision_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    log = await db.get(MergeAuditLog, decision_id)
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return AuditLogOut(
        decision_id=log.decision_id,
        decision_type=log.decision_type,
        performed_by=log.performed_by,
        reason=log.reason,
        before_json=log.before_json,
        after_json=log.after_json,
        created_at=log.created_at.isoformat(),
    )
