from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_event import OnboardingEvent
from app.schemas.onboarding_event import OnboardingEventRead


router = APIRouter(prefix="/onboarding-events", tags=["Onboarding Events"])


@router.get("/", response_model=list[OnboardingEventRead])
def list_events(db: Session = Depends(get_db)):
    return (
        db.query(OnboardingEvent)
        .order_by(OnboardingEvent.id.desc())
        .all()
    )


@router.get("/newcomers/{newcomer_id}", response_model=list[OnboardingEventRead])
def list_events_for_newcomer(
    newcomer_id: int,
    db: Session = Depends(get_db),
):
    newcomer = (
        db.query(NewcomerProfile)
        .filter(NewcomerProfile.id == newcomer_id)
        .first()
    )

    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    return (
        db.query(OnboardingEvent)
        .filter(OnboardingEvent.newcomer_id == newcomer_id)
        .order_by(OnboardingEvent.id.desc())
        .all()
    )