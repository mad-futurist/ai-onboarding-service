from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.mentor_digest import MentorDigest
from app.schemas.mentor_digest import MentorDigestGenerateRequest, MentorDigestRead
from app.services.mentor_digest_service import generate_mentor_digest

router = APIRouter(prefix="/mentor-digests", tags=["Mentor Digests"])


@router.post("/generate", response_model=MentorDigestRead)
def generate_digest(payload: MentorDigestGenerateRequest, db: Session = Depends(get_db)):
    try:
        return generate_mentor_digest(db=db, mentor_id=payload.mentor_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/mentors/{mentor_id}", response_model=list[MentorDigestRead])
def list_mentor_digests(mentor_id: int, db: Session = Depends(get_db)):
    return (
        db.query(MentorDigest)
        .filter(MentorDigest.mentor_id == mentor_id)
        .order_by(MentorDigest.id.desc())
        .all()
    )


@router.get("/{digest_id}", response_model=MentorDigestRead)
def get_digest(digest_id: int, db: Session = Depends(get_db)):
    digest = db.query(MentorDigest).filter(MentorDigest.id == digest_id).first()
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return digest
