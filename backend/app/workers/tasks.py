"""
Celery tasks for background processing.

All DB work uses synchronous SQLAlchemy (via SYNC_DATABASE_URL) since Celery
workers are not async. FastAPI routes use the async engine.
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.workers.celery_app import celery_app

sync_engine = create_engine(settings.SYNC_DATABASE_URL, pool_pre_ping=True)
SyncSession = sessionmaker(sync_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Connector pull
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_connector_pull(self, source_system: str, full_refresh: bool = False):
    from app.connectors import get_connector
    from app.models import ExternalProfile, SyncRun

    connector = get_connector(source_system)

    with SyncSession() as db:
        run = SyncRun(
            source_system=source_system,
            direction="inbound",
            status="started",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            records = connector.fetch_all() if full_refresh else connector.fetch_incremental()
            processed = 0
            failed = 0

            for record in records:
                try:
                    record_id = record.get("source_record_id")
                    existing = db.execute(
                        select(ExternalProfile).where(
                            ExternalProfile.source_system == source_system,
                            ExternalProfile.source_record_id == record_id,
                        )
                    ).scalar_one_or_none()

                    if existing:
                        existing.source_payload_json = record
                        existing.source_last_seen_at = datetime.now(timezone.utc)
                    else:
                        profile = ExternalProfile(
                            source_system=source_system,
                            source_record_id=record_id,
                            source_payload_json=record,
                            source_last_seen_at=datetime.now(timezone.utc),
                            sync_status="pending",
                        )
                        db.add(profile)
                    processed += 1
                except Exception:
                    failed += 1

            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.records_processed = processed
            run.records_failed = failed
            db.commit()

        except Exception as exc:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.error_summary = str(exc)
            db.commit()
            raise self.retry(exc=exc)

    return {"source_system": source_system, "status": "completed"}


# ---------------------------------------------------------------------------
# Identity resolution
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def run_identity_resolution(self, person_ids: list[str] | None = None):
    import asyncio
    from app.database import AsyncSessionLocal
    from app.services.identity_resolution import run_resolution

    async def _run():
        async with AsyncSessionLocal() as db:
            ids = [__import__("uuid").UUID(p) for p in person_ids] if person_ids else None
            count = await run_resolution(db, ids)
            return count

    count = asyncio.run(_run())
    return {"candidates_created": count}


# ---------------------------------------------------------------------------
# Sync (outbound)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_sync(self, source_system: str, direction: str, dry_run: bool = False):
    from app.models import SyncRun

    with SyncSession() as db:
        run = SyncRun(
            source_system=source_system,
            direction=direction,
            status="started",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            if direction == "outbound":
                _run_outbound_sync(db, source_system, dry_run, run)
            else:
                run_connector_pull.delay(source_system=source_system)
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception as exc:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.error_summary = str(exc)
            db.commit()
            raise self.retry(exc=exc)

    return {"source_system": source_system, "direction": direction, "dry_run": dry_run}


def _run_outbound_sync(db: Session, source_system: str, dry_run: bool, run):
    from app.connectors import get_connector
    from app.models import ExternalProfile, Person, SyncEvent

    connector = get_connector(source_system)
    profiles = db.execute(
        select(ExternalProfile).where(
            ExternalProfile.source_system == source_system,
            ExternalProfile.sync_status == "pending",
            ExternalProfile.person_id.isnot(None),
        )
    ).scalars().all()

    processed = 0
    failed = 0

    for profile in profiles:
        person = db.get(Person, profile.person_id)
        if not person:
            continue
        payload = {
            "email": person.primary_email,
            "name": person.full_name,
            "merge_fields": {"FNAME": person.first_name or "", "LNAME": person.last_name or ""},
        }
        event = SyncEvent(
            sync_run_id=run.sync_run_id,
            source_system=source_system,
            related_person_id=person.person_id,
            action_type="update",
            payload=payload,
            status="success",
        )
        if not dry_run:
            try:
                connector.push_update(profile.source_record_id, payload)
                profile.sync_status = "synced"
            except Exception as e:
                event.status = "error"
                event.error_message = str(e)
                failed += 1
                processed -= 1
        db.add(event)
        processed += 1

    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    run.records_processed = processed
    run.records_failed = failed
    db.commit()
