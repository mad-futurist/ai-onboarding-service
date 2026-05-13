from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_reflection import OnboardingReflection
from app.schemas.onboarding_reflection import OnboardingReflectionCreate, OnboardingReflectionRead

router = APIRouter(prefix="/onboarding-reflections", tags=["Onboarding Reflections"])


@router.post("/", response_model=OnboardingReflectionRead, status_code=201)
def create_reflection(payload: OnboardingReflectionCreate, db: Session = Depends(get_db)):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == payload.newcomer_id).first()
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    reflection = OnboardingReflection(**payload.model_dump())
    db.add(reflection)
    db.commit()
    db.refresh(reflection)
    return reflection


@router.get("/newcomers/{newcomer_id}", response_model=list[OnboardingReflectionRead])
def list_reflections(newcomer_id: int, db: Session = Depends(get_db)):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()
    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")
    return (
        db.query(OnboardingReflection)
        .filter(OnboardingReflection.newcomer_id == newcomer_id)
        .order_by(OnboardingReflection.id.desc())
        .all()
    )
