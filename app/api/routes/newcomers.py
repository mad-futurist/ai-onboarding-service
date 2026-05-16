from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.user import User
from app.models.newcomer import NewcomerProfile
from app.models.onboarding_plan import OnboardingPlan
from app.schemas.newcomer import NewcomerCreate, NewcomerRead
from app.schemas.onboarding_plan import OnboardingPlanWithTasksRead


router = APIRouter(prefix="/newcomers", tags=["Newcomers"])


def serialize_newcomer(newcomer: NewcomerProfile) -> dict:
    return {
        "id": newcomer.id,
        "user_id": newcomer.user_id,
        "mentor_id": newcomer.mentor_id,
        "full_name": newcomer.user.full_name if newcomer.user else None,
        "email": newcomer.user.email if newcomer.user else None,
        "job_title": newcomer.job_title,
        "seniority": newcomer.seniority,
        "team": newcomer.team,
        "start_date": newcomer.start_date,
        "onboarding_status": newcomer.onboarding_status,
        "created_at": newcomer.created_at,
    }


@router.post("/", response_model=NewcomerRead)
def create_newcomer(payload: NewcomerCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    mentor_id = payload.mentor_id
    if mentor_id:
        mentor = db.query(User).filter(User.id == payload.mentor_id).first()

        if not mentor:
            mentor_id = None

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        role="newcomer",
    )

    db.add(user)
    db.flush()

    newcomer = NewcomerProfile(
        user_id=user.id,
        mentor_id=mentor_id,
        job_title=payload.job_title,
        seniority=payload.seniority,
        team=payload.team,
        start_date=payload.start_date,
        onboarding_status="not_started",
    )

    db.add(newcomer)
    db.commit()
    db.refresh(newcomer)
    newcomer = (
        db.query(NewcomerProfile)
        .options(joinedload(NewcomerProfile.user))
        .filter(NewcomerProfile.id == newcomer.id)
        .first()
    )

    return serialize_newcomer(newcomer)


@router.get("/", response_model=list[NewcomerRead])
def list_newcomers(
    mentor_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(NewcomerProfile).options(joinedload(NewcomerProfile.user))
    if mentor_id:
        query = query.filter(NewcomerProfile.mentor_id == mentor_id)
    newcomers = query.order_by(NewcomerProfile.id.desc()).all()
    return [serialize_newcomer(newcomer) for newcomer in newcomers]


@router.get("/{newcomer_id}", response_model=NewcomerRead)
def get_newcomer(newcomer_id: int, db: Session = Depends(get_db)):
    newcomer = (
        db.query(NewcomerProfile)
        .options(joinedload(NewcomerProfile.user))
        .filter(NewcomerProfile.id == newcomer_id)
        .first()
    )

    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    return serialize_newcomer(newcomer)


@router.get("/{newcomer_id}/onboarding-plan", response_model=OnboardingPlanWithTasksRead)
def get_newcomer_active_plan(newcomer_id: int, db: Session = Depends(get_db)):
    newcomer = db.query(NewcomerProfile).filter(NewcomerProfile.id == newcomer_id).first()

    if not newcomer:
        raise HTTPException(status_code=404, detail="Newcomer not found")

    plan = (
        db.query(OnboardingPlan)
        .filter(OnboardingPlan.newcomer_id == newcomer_id)
        .order_by(OnboardingPlan.id.desc())
        .first()
    )

    if not plan:
        raise HTTPException(status_code=404, detail="Onboarding plan not found")

    return plan
