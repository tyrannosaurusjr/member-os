import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ExternalProfile
from app.schemas.external_profile import ExternalProfileOut

router = APIRouter(prefix="/external-profiles", tags=["External Profiles"])


@router.get("", response_model=list[ExternalProfileOut])
async def list_external_profiles(
    source_system: str | None = None,
    person_id: uuid.UUID | None = None,
    sync_status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ExternalProfile)
    if source_system:
        stmt = stmt.where(ExternalProfile.source_system == source_system)
    if person_id:
        stmt = stmt.where(ExternalProfile.person_id == person_id)
    if sync_status:
        stmt = stmt.where(ExternalProfile.sync_status == sync_status)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{external_profile_id}", response_model=ExternalProfileOut)
async def get_external_profile(
    external_profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    profile = await db.get(ExternalProfile, external_profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="External profile not found")
    return profile


@router.post("/import/csv", status_code=202)
async def import_csv(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Import Apple Contacts or manual CSV records."""
    import hashlib
    import pandas as pd

    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))
    records_received = len(df)

    import_run_id = str(uuid.uuid4())

    # Store raw rows as external profiles (source: manual_csv)
    for _, row in df.iterrows():
        payload = row.dropna().to_dict()
        record_id = hashlib.sha256(str(payload).encode()).hexdigest()
        profile = ExternalProfile(
            source_system="manual_csv",
            source_record_id=record_id,
            source_payload_json=payload,
            sync_status="pending",
        )
        db.add(profile)

    await db.commit()
    return {"import_run_id": import_run_id, "records_received": records_received}
