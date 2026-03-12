import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import SyncEvent, SyncRun
from app.schemas.sync import ConnectorPullRequest, SyncEventOut, SyncRunOut, SyncRunRequest

router = APIRouter(tags=["Sync"])


@router.post("/sync/run", status_code=202)
async def start_sync(body: SyncRunRequest, db: AsyncSession = Depends(get_db)):
    from app.workers.tasks import run_sync
    run_sync.delay(
        source_system=body.source_system,
        direction=body.direction,
        dry_run=body.dry_run,
    )
    return {"status": "queued", "source_system": body.source_system, "direction": body.direction}


@router.get("/sync/runs", response_model=list[SyncRunOut])
async def list_sync_runs(
    source_system: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SyncRun).order_by(SyncRun.started_at.desc())
    if source_system:
        stmt = stmt.where(SyncRun.source_system == source_system)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/sync/runs/{sync_run_id}", response_model=SyncRunOut)
async def get_sync_run(sync_run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    run = await db.get(SyncRun, sync_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found")
    return run


@router.get("/sync/events", response_model=list[SyncEventOut])
async def list_sync_events(
    sync_run_id: uuid.UUID | None = None,
    source_system: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SyncEvent).order_by(SyncEvent.created_at.desc())
    if sync_run_id:
        stmt = stmt.where(SyncEvent.sync_run_id == sync_run_id)
    if source_system:
        stmt = stmt.where(SyncEvent.source_system == source_system)
    if status:
        stmt = stmt.where(SyncEvent.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/connectors/{source_system}/pull", status_code=202)
async def pull_connector(source_system: str, body: ConnectorPullRequest):
    from app.workers.tasks import run_connector_pull
    run_connector_pull.delay(source_system=source_system, full_refresh=body.full_refresh)
    return {"status": "queued", "source_system": source_system}


@router.post("/connectors/{source_system}/test")
async def test_connector(source_system: str):
    from app.connectors import get_connector
    connector = get_connector(source_system)
    result = connector.test_connection()
    return {"source_system": source_system, "result": result}
