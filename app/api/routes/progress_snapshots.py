from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.newcomer import NewcomerProfile
from app.models.progress_snapshot import ProgressSnapshot
from app.schemas.progress_snapshot import ProgressSnapshotRead
from app.services.progress_snapshot_service import generate_snapshot

router = APIRouter(prefix="/progress-snapshots", tags=["Progress Snapshots"])


@router.post("/generate/newcomers/{newcomer_id}", response_model=ProgressSnapshotRead)
def generate_progress_snapshot(newcomer_id: int, db: Session = Depends(get_db)):
    try:
        return generate_snapshot(db=db, newcomer_id=newcomer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/newcomers/{newcomer_id}", response_model=list[ProgressSnapshotRead])
def list_snapshots(newcomer_id: int, db: Session = Depends(get_db)):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")
    return (
        db.query(ProgressSnapshot)
        .filter(ProgressSnapshot.newcomer_id == newcomer_id)
        .order_by(ProgressSnapshot.id.desc())
        .all()
    )
